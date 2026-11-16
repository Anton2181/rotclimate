"""Independent PROJ geometry and scalar supplied-site population/size review."""
import csv
import hashlib
import json
import math
from pathlib import Path
import subprocess
import sys

import numpy as np
from pyproj import Transformer

ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'scripts')]
from review_urban_diagnosis import source,snap,cdf_bound,LOW,HIGH

BASE=ROOT/'output/urban_diagnosis_20261116'
OUT=ROOT/'output/urban_given_sites_20261116'


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def scalar_people(x,points,cell):
    result=[0.]*len(points);pts=points.tolist()
    for yy,xx in zip(*np.nonzero(x['land'])):
        mass=float(x['density'][yy,xx])*cell**2
        if mass==0:continue
        distances=[(float(yy)-p[0])**2+(float(xx)-p[1])**2 for p in pts];nearest=min(distances)
        if nearest*cell**2>60**2:continue
        owners=[i for i,d in enumerate(distances) if d==nearest];part=mass/len(owners)
        for i in owners:result[i]+=part
    return np.array(result)


def density(a):
    return 100+400*max(0,min(1,(math.log(max(a,1e-9))-math.log(50))/(math.log(400)-math.log(50))))


def main():
    result=json.loads((OUT/'results.json').read_text());previous=json.loads((BASE/'review.json').read_text());inputs=json.loads((BASE/'input_receipt.json').read_text())
    assert previous['reviewer_sha256']==sha(ROOT/'scripts/review_urban_diagnosis.py')
    for name,digest in {**result['producers'],**result['sources'],**result['protected_sha256'],**inputs['inputs']}.items():assert sha(ROOT/name)==digest,name
    for name,digest in result['files_sha256'].items():assert sha(OUT/name)==digest,name
    with np.load(OUT/'model.npz') as z:arrays={k:z[k] for k in z.files}
    fit=json.loads((ROOT/'output/settlement_release4_20261116/earth_results.json').read_text())['sizes']['primary'];model=fit['models'][fit['selected']];coef=model['full_coefficients'];sigma=model['heldout_sigma'];bounds=fit['area_range_ha']
    maxH=0.;maxarea=0.;maxprojection=0.;checked=0
    for pool in ['floodplains','mexico']:
        folder=BASE/'archived_replay'/pool
        with np.load(folder/'inputs_3km.npz') as z:x3={k:z[k] for k in z.files}
        with np.load(folder/'model.npz') as z:mask=z['3km__surveyed']
        records,_=snap(source(pool),x3,pool,mask);records=[a for a in records if a['value']>=(3 if pool=='floodplains' else 10)]
        assert len(records)==(119 if pool=='floodplains' else 27)
        lo=np.array([LOW[int(a['value'])] if pool=='floodplains' else a['value'] for a in records]);hi=np.array([HIGH[int(a['value'])] if pool=='floodplains' else a['value'] for a in records])
        np.testing.assert_array_equal(lo,arrays[pool+'__lower_ha']);np.testing.assert_array_equal(hi,arrays[pool+'__upper_ha'])
        for cell in [3,9]:
            with np.load(folder/f'inputs_{cell}km.npz') as z:x={k:z[k] for k in z.files}
            # PROJ's spherical AEQD implementation is independent of the producer's forward function.
            target=f'+proj=aeqd +lat_0={float(x["lat0"])} +lon_0={float(x["lon0"])} +R=6371000 +units=m +no_defs'
            transform=Transformer.from_crs('EPSG:4326',target,always_xy=True)
            gx,gy=transform.transform(x['lon'],x['lat'])
            err=max(float(np.max(np.abs(gx/1000-x['x']))),float(np.max(np.abs(gy/1000-x['y']))));maxprojection=max(maxprojection,err);assert err<1e-7
            px,py=transform.transform([a['longitude'] for a in records],[a['latitude'] for a in records]);points=np.column_stack([(x['y'][0,0]-np.array(py)/1000)/cell,(np.array(px)/1000-x['x'][0,0])/cell])
            H=scalar_people(x,points,cell);key=f'{pool}_{cell}km';actualH=arrays[key+'__H']
            maxH=max(maxH,float(np.max(np.abs(H-actualH))));np.testing.assert_allclose(H,actualH,atol=1e-6,rtol=1e-11)
            available=math.fsum(float(v)*cell**2 for v in x['density'][x['land']]);allocated=math.fsum(H)
            geo=result['geometry'][pool][str(cell)]
            assert allocated<=available+1e-6
            assert abs(available-geo['available_model_people'])<1e-6 and abs(allocated-geo['allocated_hinterland_people'])<1e-6
            assert geo['records']==len(records) and geo['supported_records']==int((H>0).sum())
            assert geo['distinct_fractional_points']==len(np.unique(points,axis=0))
            assert geo['distinct_rounded_cells']==len(np.unique(np.rint(points),axis=0))
            for row in [a for a in result['cases'] if a['pool']==pool and a['cell_km']==cell]:
                e=np.clip(np.random.default_rng(row['seed']).standard_normal(len(records)),-2.5,2.5)
                area=np.zeros(len(H));valid=H>0
                area[valid]=np.clip(np.exp(coef[0]+coef[1]*np.log(H[valid])+sigma*e[valid]),*bounds)
                actual=arrays[key+f'__areas_{row["seed"]}'];maxarea=max(maxarea,float(np.max(np.abs(actual-area))))
                np.testing.assert_allclose(area,actual,atol=1e-8,rtol=1e-11)
                assert row['supplied_towns']==len(records) and row['supported_towns']==int(valid.sum())
                assert abs(area.sum()-row['model_total_area_ha'])<1e-7 and abs(area.max()-row['model_largest_area_ha'])<1e-8
                assert row['model_above200']==int((area>200).sum())
                assert abs(row['source_total_lower_ha']-math.fsum(lo))<1e-9
                if np.isinf(hi).any():assert row['source_total_upper_ha'] is None
                else:assert abs(row['source_total_upper_ha']-sum(hi))<1e-9
                assert abs(cdf_bound(area,lo,hi)-row['interval_ks_lower_bound'])<1e-12
                if pool=='floodplains':
                    paired=sum(a>=l and a<=h for a,l,h in zip(area,lo,hi))/len(area)
                    ranked=sum(1+sum(a>edge for edge in [4.05,10.05,20.05,40.05,200.5])==int(b) for a,b in zip(sorted(area,reverse=True),sorted([a['value'] for a in records],reverse=True)))/len(area)
                    assert paired==row['paired_band_hit'] and ranked==row['sorted_band_hit']
                else:assert row['paired_band_hit'] is None and row['sorted_band_hit'] is None
                central=math.fsum(a*density(a) for a in area);flat=math.fsum(100*a for a in area)
                assert abs(central-row['model_sliding_residents'])<1e-6 and abs(flat-row['model_flat100_residents'])<1e-6
                assert abs(central/available-row['urban_share_if_sliding'])<1e-12 and abs(flat/available-row['urban_share_if_flat100'])<1e-12
                checked+=1
    with (OUT/'cases.csv').open() as f:rows=list(csv.DictReader(f))
    assert len(rows)==20
    for row,actual in zip(rows,result['cases']):
        for key,value in actual.items():
            if value is None:assert row[key]==''
            elif isinstance(value,bool):assert row[key]==str(value)
            elif isinstance(value,(int,float)):assert float(row[key])==value
            else:assert row[key]==value
    assert not result['fit_performed'] and not result['site_forecast'] and not result['new_blind_test'] and not result['adopt'] and not result['climate_changed']
    fresh={}
    for name in ['results.json','model.npz','cases.csv','geometry.json']:
        assert (OUT/name).read_bytes()==(OUT/'fresh'/name).read_bytes(),name;fresh[name]=sha(OUT/name)
    tests=subprocess.run([sys.executable,'-m','pytest','-q','tests/test_observed_hinterlands.py','tests/test_urban_observations.py'],cwd=ROOT,text=True,capture_output=True,check=True)
    assert '26 passed' in tests.stdout
    report=dict(status='passed',reviewer_sha256=sha(Path(__file__)),raw_reviewer_sha256=sha(ROOT/'scripts/review_urban_diagnosis.py'),results_sha256=sha(OUT/'results.json'),method='No given-site producer or hinterland/observation component import. Independent raw-source cohort,PROJ spherical AEQD geometry,scalar cell ownership/ties/cutoff,population conservation,direct size/density equations and CDF envelopes;all CSV cells checked.',cases=checked,max_projection_difference_km=maxprojection,max_hinterland_difference_people=maxH,max_area_difference_ha=maxarea,controls_stdout=tests.stdout,fresh_byte_exact=fresh,protected_files=len(result['protected_sha256']),adopt=False,new_blind_test=False)
    (OUT/'review.json').write_text(json.dumps(report,indent=2)+'\n');print('Reviewed20supplied-site cases,independent projection/accounting,26controls and four fresh files',flush=True)


if __name__=='__main__':main()
