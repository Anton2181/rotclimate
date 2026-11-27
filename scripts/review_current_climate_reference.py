"""Verify the fixed current-source reference from raw97-region saved arrays."""
import json
from pathlib import Path
import sys
import numpy as np
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from local_benchmark_protocol import file_hash,write_json
OUT=ROOT/'output/climate_reference_20261127'
PLAN=ROOT/'calibration/current_climate_reference_20261127/plan.json'


def rounding_radius(array):
    values=np.asarray(array,np.float32)
    return .5*np.maximum(np.abs(np.spacing(values)).astype(float),np.abs(np.spacing(np.nextafter(values,-np.inf))).astype(float))


def score_bounds(s):
    T,To,P,Po=[s[k].astype(float) for k in ['Ts','To','Ps','Po']]
    terr=np.abs(T-To);tu=rounding_radius(s['Ts'])+rounding_radius(s['To'])
    temperature=[float(np.maximum(terr-tu,0).mean()),float((terr+tu).mean())]
    pu,ou=rounding_radius(s['Ps']),rounding_radius(s['Po'])
    lo,hi=np.maximum(P-pu,0).sum(0),np.maximum(P+pu,0).sum(0)
    olo,ohi=np.maximum(Po-ou,0).sum(0),np.maximum(Po+ou,0).sum(0)
    loglo=np.log((lo+50)/(ohi+50));loghi=np.log((hi+50)/(olo+50))
    nearest=np.where((loglo<=0)&(loghi>=0),0,np.minimum(np.abs(loglo),np.abs(loghi)))
    farthest=np.maximum(np.abs(loglo),np.abs(loghi))
    err=np.abs(P-Po);uncertainty=pu+ou
    rain=[.5*(np.sqrt(np.mean(nearest**2))+12*np.maximum(err-uncertainty,0).mean()/(ohi.mean()+120)),
          .5*(np.sqrt(np.mean(farthest**2))+12*(err+uncertainty).mean()/(olo.mean()+120))]
    return temperature,[float(x) for x in rain]


def main():
    assert not (OUT/'review.json').exists()
    plan=json.loads(PLAN.read_text());protocol=json.loads((OUT/'protocol.json').read_text())
    results=json.loads((OUT/'results.json').read_text())
    assert file_hash(PLAN)==protocol['plan_sha256']
    assert file_hash(OUT/'protocol.json')==results['protocol_sha256']
    assert file_hash(OUT/'preparation.json')==protocol['preparation_sha256']
    for section in ['inputs_sha256','model_sources_sha256','execution_sources_sha256']:
        for name,digest in plan[section].items():assert file_hash(ROOT/name)==digest,name
    for name,digest in plan['private_files_sha256'].items():assert file_hash(OUT/'model'/name)==digest,name
    assert len(results['rows'])==len(plan['cases'])==97
    observations=['To','Po','lat','lon','elev','elev_max','coast_km','i','j']
    records,files,part_members=[],{},{}
    for row,spec in zip(results['rows'],plan['cases'],strict=True):
        folder=OUT/'ref58'/('r58_'+spec['part']);name=spec['region']
        assert row['region']==name and row['part']==spec['part']
        local={k:v for k,v in row.items() if k!='part'}
        assert local==json.loads((folder/'cases'/(name+'.json')).read_text())
        assert row['status']=='passed' and row['numerics']['all_checks_passed']
        assert row['case_identity']==spec['case_identity']
        p=json.loads((folder/'protocol.json').read_text())
        assert p['params']==json.loads((ROOT/plan['parts_by_name'][spec['part']]['historical_protocol']).read_text())['params']
        assert p['sources']==plan['benchmark_protocol_sources_sha256']
        attempt=json.loads((folder/'attempts'/(name+'.json')).read_text())
        assert attempt['spec']==spec and attempt['protocol_sha256']==file_hash(folder/'protocol.json')
        assert file_hash(folder/'cells'/(name+'.npz'))==row['cells_sha256']
        assert file_hash(ROOT/spec['historical_cells'])==spec['historical_cells_sha256']
        with np.load(folder/'cells'/(name+'.npz')) as z:s=dict(z)
        with np.load(ROOT/spec['historical_cells']) as z:old=dict(z)
        assert set(s)==set(old)
        for key in s:assert s[key].shape==old[key].shape and np.isfinite(s[key]).all(),(name,key)
        assert (s['Ps']>=0).all() and (s['Po']>=0).all()
        for key in observations:assert s[key].dtype==old[key].dtype and s[key].tobytes()==old[key].tobytes(),(name,key)
        tb,pb=score_bounds(s)
        t,rain=row['temperature']['monthly_mae_C'],row['rain']['loss']
        assert tb[0]-1e-12<=t<=tb[1]+1e-12,(name,t,tb)
        assert pb[0]-1e-12<=rain<=pb[1]+1e-12,(name,rain,pb)
        historical=json.loads((ROOT/spec['historical_record']).read_text())
        unchanged=all(s[k].dtype==old[k].dtype and s[k].tobytes()==old[k].tobytes() for k in ['Ts','Ps'])
        records.append(dict(region=name,part=spec['part'],temperature_mae_C=t,rain_loss=rain,
            annual_temperature_bias_C=row['temperature']['annual_bias_C'],annual_rain_bias_mm=row['rain']['annual_bias_mm'],
            annual_rain_mm=row['rain']['sim_mean_annual_mm'],observed_annual_rain_mm=row['rain']['obs_mean_annual_mm'],
            historical_TP_arrays_byte_exact=unchanged,
            historical_temperature_mae_change_C=t-historical['temperature']['monthly_mae_C'],
            historical_rain_loss_change=rain-historical['rain']['loss'],
            original_score_within_propagated_archive_rounding=True))
        part_members.setdefault(spec['part'],[]).append(name)
        for rel in ['cases/'+name+'.json','cells/'+name+'.npz','attempts/'+name+'.json']:
            f=folder/rel;files[str(f.relative_to(OUT))]=file_hash(f)
    for part in plan['parts']:
        folder=OUT/'ref58'/('r58_'+part['name']);summary=json.loads((folder/'summary.json').read_text())
        assert summary['complete'] and part_members[part['name']]==part['regions']
        assert set(summary['regions'])==set(part['regions'])
        for name,row in summary['regions'].items():assert row==json.loads((folder/'cases'/(name+'.json')).read_text())
        for rel in ['protocol.json','summary.json']:files[str((folder/rel).relative_to(OUT))]=file_hash(folder/rel)
    repeats=[]
    for spec in plan['recent_exact_controls']:
        folder=OUT/'ref58'/('r58_'+spec['part'])
        with np.load(folder/'cells'/(spec['region']+'.npz')) as current,np.load(ROOT/spec['capture']) as old:
            for k,oldkey in [('Ts','T'),('Ps','P'),('To','obs_T'),('Po','obs_P')]:
                expected=old[oldkey].astype(np.float32)
                assert current[k].dtype==expected.dtype and current[k].tobytes()==expected.tobytes(),(spec['region'],k)
        repeats.append(spec['region'])
    write_json(OUT/'review.json',dict(status='verified_current_source97_reference_not_accuracy_adoption',
        plan_sha256=file_hash(PLAN),results_sha256=file_hash(OUT/'results.json'),regions=97,numerical_certificates=97,
        statistics=records,mean_temperature_mae_C=float(np.mean([r['temperature_mae_C'] for r in records])),
        mean_rain_loss=float(np.mean([r['rain_loss'] for r in records])),
        changed_historical_TP_regions=[r['region'] for r in records if not r['historical_TP_arrays_byte_exact']],
        recent_current_source_repeat_arrays_exact=repeats,
        worst_temperature_regions=sorted(records,key=lambda r:r['temperature_mae_C'],reverse=True)[:12],
        worst_rain_regions=sorted(records,key=lambda r:r['rain_loss'],reverse=True)[:12],files_sha256=files,
        candidate_integrations=0,AA_opened=False,W18c_reopened=False,atlas_changed=False))
    print('Independently verified97 current-source cases, exact inputs, rounding-bounded scores and three recent repeat fields.')


if __name__=='__main__':main()
