"""Frozen-control exterior pressure change versus the actual coupled child.

Uses saved completed cases only; no climate integration, candidate selection or
new threshold. Pressure-gradient accelerations are not total wind responses.
"""
import json
from pathlib import Path
import sys
import numpy as np
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'scripts'),str(ROOT)]
from local_benchmark_protocol import file_hash,write_json
from experiments.nested_pressure_context import nested_pressure
from rotclimate.model import gauss
from rotclimate.koppen import monthly_stats
PLAN=ROOT/'calibration/nested_pressure_context_20261127/plan.json'
OUT=ROOT/'output/nested_pressure_context_20261127'


def mean_month(array,days,ii,jj):
    return monthly_stats(array[:,ii,jj],array[:,ii,jj],days,365.)['Tm'].mean(1).tolist()


def forces(pressure):
    # Map rows increase toward map-down; east/right, north/up at center.
    return (-np.gradient(pressure,axis=-1)/(56000.*1.2),
             np.gradient(pressure,axis=-2)/(56000.*1.2))


def main():
    target=OUT/'frozen_pressure_analysis.json'
    assert not target.exists()
    plan=json.loads(PLAN.read_text())
    review=json.loads((OUT/'review.json').read_text())
    for name,digest in plan['model_sources_sha256'].items():
        assert file_hash(ROOT/name)==digest
    protocol_params=json.loads((OUT/'default_off_dev31/protocol.json').read_text())['params']
    p=protocol_params
    records,inputs=[],{}
    for name in plan['default_off_controls']:
        s=next(s for s in plan['cases'] if s['region']==name)
        arrays={}
        for arm in ['default_off','parent','nested']:
            folder=OUT/(arm+'_'+s['part'])
            f=folder/'cells'/(name+'_context.npz')
            record=json.loads((folder/'cases'/(name+'.json')).read_text())
            assert record['status']=='passed' and record['numerics']['all_checks_passed']
            assert file_hash(f)==record['context_capture_sha256']
            inputs[str(f.relative_to(ROOT))]=file_hash(f)
            with np.load(f) as z:
                arrays[arm]=dict(z)
        control,parent,child=[arrays[a] for a in ['default_off','parent','nested']]
        np.testing.assert_array_equal(control['days'],parent['days'])
        np.testing.assert_array_equal(control['days'],child['days'])
        frozen=np.stack([nested_pressure(pa,ca,52,p['slp_scale_km']/56.,
            p['slp_local_km']/56.,p['slp_large'],p['slp_local'],gauss)
            for pa,ca in zip(parent['anomaly'],control['anomaly'],strict=True)])
        ii,jj=control['wind_i'],control['wind_j']
        days=control['days']
        result=dict(region=name,monthly={},units=dict(pressure='Pa',pressure_gradient_acceleration='m/s^2'))
        for arm,field in [('control',control['pressure']),('frozen_parent_exterior',frozen),('coupled_child',child['pressure'])]:
            fx,fy=forces(field)
            result['monthly'][arm]=dict(pressure_Pa=mean_month(field,days,ii,jj),
                pressure_force_right_m_s2=mean_month(fx,days,ii,jj),
                pressure_force_up_m_s2=mean_month(fy,days,ii,jj))
        result['monthly_exterior_only_pressure_change_Pa']=mean_month(frozen-control['pressure'],days,ii,jj)
        result['monthly_coupled_minus_frozen_pressure_change_Pa']=mean_month(child['pressure']-frozen,days,ii,jj)
        records.append(result)
    write_json(target,dict(status='offline_frozen_native_pressure_response_not_climate_forecast',
        records=records,inputs_sha256=inputs,producer_sha256=file_hash(__file__),
        hypothesis_sha256=file_hash(ROOT/'experiments/nested_pressure_context.py'),
        completed_review_sha256=file_hash(OUT/'review.json'),climate_integrations=0,
        interpretation='Only exterior thermal context changes in frozen calculation. Coupled-minus-frozen includes changed child thermal states and all feedback, not an isolated individual process. Forces are in map axes; not total winds or forecast accuracy. No thresholds or selection.'))


if __name__=='__main__':
    main()
