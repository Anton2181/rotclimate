"""New native guards cannot alter old physical-control array contracts."""
from copy import deepcopy
from importlib import import_module
import json
from types import SimpleNamespace

import numpy as np
import pytest

from rotclimate.config import Params
from scripts import check_vapor_flux as vapor
from scripts import paired_physics_pilot as paired
from test_vapor_flux_gate import cases


def extra_plan():
    return dict(extra_circulation_regions=['pacific_nw'],
        extra_circulation_reference_plan='new_reference.json',
        extra_circulation_control='column_control',
        extra_circulation_groups={'pacific_nw':'ocean'},
        extra_circulation_max_ratio=.90,extra_humidity_max_ratio=1.02,
        extra_circulation_reference_archive='audit/reference.npz')


def report(error):
    footprint=dict(native_cells=4,area_km2=191166.)
    return dict(scores={'q925_300':{'ocean':dict(footprint,vector_rmse_ms=error)}},
        humidity={'scores':{'ocean':dict(footprint,partial_water_mae_mm=1.,partial_q_ratio_mae=.1)}})


def rows_with_extra():
    plan,rows=cases();plan.update(extra_plan())
    # The corrected control is independent of the original r39 accuracy baseline.
    controls=[dict(deepcopy(row),name='column_control',legacy_exact=False)
              for row in rows if row['name']=='reference']
    plan['profiles']['column_control']={};rows+=controls
    for row in rows:
        if row['region']=='pacific_nw':
            row['extra_circulation']=report(10. if row['name']=='column_control' else 9.)
    return plan,rows


def test_new_native_guard_uses_corrected_control_and_retains_original_accuracy_guards():
    plan,rows=rows_with_extra()
    reference=next(r for r in rows if r['name']=='reference' and r['region']=='pacific_nw')
    reference['extra_circulation']=report(.1)
    assert vapor.screening(rows,plan)['flux_conservative_storm']['qualifies']
    candidate=next(r for r in rows if r['name']=='flux_conservative_storm' and r['region']=='pacific_nw')
    candidate['extra_circulation']['scores']['q925_300']['ocean']['vector_rmse_ms']=9.01
    assert not vapor.screening(rows,plan)['flux_conservative_storm']['qualifies']
    candidate['extra_circulation']=report(9.)
    candidate['rain']['loss']=1.2
    assert not vapor.screening(rows,plan)['flux_conservative_storm']['qualifies']


@pytest.mark.parametrize('missing',['extra_circulation','wind','humidity','control'])
def test_missing_new_native_evidence_fails_closed(missing):
    plan,rows=rows_with_extra()
    candidate=next(r for r in rows if r['name']=='flux_conservative_storm' and r['region']=='pacific_nw')
    if missing=='extra_circulation':candidate.pop('extra_circulation')
    elif missing=='wind':candidate['extra_circulation'].pop('scores')
    elif missing=='humidity':candidate['extra_circulation'].pop('humidity')
    else:rows=[r for r in rows if r['name']!='column_control']
    assert not vapor.screening(rows,plan)['flux_conservative_storm']['qualifies']


@pytest.mark.parametrize('key',['partial_water_mae_mm','partial_q_ratio_mae'])
def test_each_humidity_error_must_pass_despite_good_wind(key):
    plan,rows=rows_with_extra()
    candidate=next(r for r in rows if r['name']=='flux_conservative_storm' and r['region']=='pacific_nw')
    score=candidate['extra_circulation']['humidity']['scores']['ocean']
    score[key]*=1.03
    assert not vapor.screening(rows,plan)['flux_conservative_storm']['qualifies']


@pytest.mark.parametrize('change',['case','wind_area','humidity_cells','nan'])
def test_native_pairing_and_finite_wind_errors_are_mandatory(change):
    plan,rows=rows_with_extra()
    candidate=next(r for r in rows if r['name']=='flux_conservative_storm' and r['region']=='pacific_nw')
    if change=='nan':
        candidate['extra_circulation']['scores']['q925_300']['ocean']['vector_rmse_ms']=float('nan')
        assert not vapor.screening(rows,plan)['flux_conservative_storm']['qualifies']
        return
    if change=='case':candidate['case_identity']='changed'
    elif change=='wind_area':candidate['extra_circulation']['scores']['q925_300']['ocean']['area_km2']-=1
    else:candidate['extra_circulation']['humidity']['scores']['ocean']['native_cells']-=1
    with pytest.raises(ValueError):vapor.screening(rows,plan)


def test_new_reference_epoch_freezes_archive_record_actual_sources_and_reader(tmp_path,monkeypatch):
    plan=extra_plan();(tmp_path/'new_reference.json').write_text('{}')
    monkeypatch.setattr(vapor,'ROOT',tmp_path)
    monkeypatch.setattr(import_module('circulation_reference'),'acquire',
        lambda root,p:({}, {'data/uwnd.ascii':{'sha256':'test'},'data/shum.ascii':{'sha256':'test'}}))
    paths=set(vapor.extra_circulation_sources(plan))
    for name in ['new_reference.json','audit/reference.npz','audit/reference.json',
            'data/uwnd.ascii','data/shum.ascii','scripts/circulation_reference.py',
            'scripts/earth_calendar.py','experiments/v10_forcing_audit.py','experiments/v10_thermodynamics.py']:
        assert tmp_path/name in paths
    assert vapor.extra_circulation_sources({})==[]


def test_independent_reference_rejects_changed_native_vectors(tmp_path,monkeypatch):
    plan=extra_plan();archive=tmp_path/plan['extra_circulation_reference_archive'];archive.parent.mkdir()
    native=np.arange(24.).reshape(12,2,1)
    np.savez_compressed(archive,circulation_model=native)
    archive.with_suffix('.json').write_text(json.dumps(dict(status='passed',
        numerics={'all_checks_passed':True},arrays_sha256=paired.file_hash(archive))))
    monkeypatch.setattr(paired,'ROOT',tmp_path)
    monkeypatch.setattr(paired,'circulation_fields',lambda path:{})
    output={'circulation_model':native.copy()}
    monkeypatch.setattr(import_module('circulation_reference'),'diagnose_model',
        lambda *args:(report(9.),output))
    assert paired.extra_circulation_diagnostics(None,None,None,None,plan,reference=True)[0]['legacy_exact']
    output['circulation_model'][0,0,0]+=1
    with pytest.raises(ValueError,match='Exact extra native'):
        paired.extra_circulation_diagnostics(None,None,None,None,plan,reference=True)


def test_json_only_extra_diagnostic_preserves_historical_npz_fieldset(tmp_path,monkeypatch):
    p=Params();shape=(3,3);land=np.ones(shape,bool);monthly=np.ones((12,)+shape)
    grid=SimpleNamespace(inmap=land,land=land,elev=np.zeros(shape),obs_sst=monthly,
                         map_slice=lambda:(slice(None),slice(None)))
    case=SimpleNamespace(grid=grid,obs_T=monthly,obs_P=monthly)
    result=SimpleNamespace(numerics={'all_checks_passed':True},days=np.arange(12.),T=monthly,P=monthly,
                           layer_water=None,moisture_budget={})
    trace=[dict(moisture_u=np.ones(1),moisture_v=np.ones(1),SST=np.ones(1)) for _ in range(12)]
    model=SimpleNamespace(trace=trace,run=lambda **kwargs:result)
    monkeypatch.setattr(paired,'ROOT',tmp_path)
    monkeypatch.setattr(paired,'case_hash',lambda *args,**kwargs:'same')
    monkeypatch.setattr(paired,'load_params',lambda path:None)
    monkeypatch.setattr(paired.joint,'update_block',lambda *args:None)
    monkeypatch.setattr(paired.joint,'earth_profile',lambda *args:None)
    monkeypatch.setattr(paired.earth,'earth_params',lambda *args:p)
    monkeypatch.setattr(paired.earth,'region_case',lambda *args:case)
    monkeypatch.setattr(paired,'ClimateModel',lambda *args,**kwargs:model)
    monkeypatch.setattr(paired,'monthly_stats',lambda *args,**kwargs:dict(Tm=monthly,Pm=monthly))
    monkeypatch.setattr(paired,'monthly_weights',lambda *args:np.eye(12))
    extra_fields={'circulation_model':np.ones((12,2,1)),'circulation_area':np.array([191166.])}
    monkeypatch.setattr(paired,'extra_circulation_diagnostics',lambda *args,**kwargs:(report(9.),extra_fields))
    historical=tmp_path/'historical';historical.mkdir()
    fields=dict(valid=land,elev=grid.elev,observed=monthly,simulated=monthly)
    archive=historical/'pacific_nw.npz';np.savez_compressed(archive,**fields)
    archive.with_suffix('.json').write_text(json.dumps(dict(status='passed',
        numerics={'all_checks_passed':True},arrays_sha256=paired.file_hash(archive))))
    plan=dict(extra_plan(),physics='physics.json',cell_km=56.,
              profile_control_archives={'column_control':'historical'})
    out=tmp_path/'run';out.mkdir()
    row=paired.run_one(('column_control','pacific_nw',{},plan,'identity',str(out)))
    assert row['status']=='passed' and row['physical_control_exact']
    assert row['extra_circulation']==report(9.)
    with np.load(out/'column_control/pacific_nw.npz') as saved:
        assert set(saved.files)==set(fields)
        for key,value in fields.items():np.testing.assert_array_equal(saved[key],value)
    companion=out/'column_control/pacific_nw_extra.npz'
    assert row['extra_circulation_arrays_sha256']==paired.file_hash(companion)
    with np.load(companion) as saved:
        assert set(saved.files)==set(extra_fields)
        for key,value in extra_fields.items():np.testing.assert_array_equal(saved[key],value)
    # Resume verifies companion integrity before accepting the cached climate.
    assert paired.run_one(('column_control','pacific_nw',{},plan,'identity',str(out)))==json.loads(json.dumps(row))
    np.savez_compressed(companion,circulation_model=np.zeros((12,2,1)))
    with pytest.raises(ValueError,match='extra native circulation arrays'):
        paired.run_one(('column_control','pacific_nw',{},plan,'identity',str(out)))
