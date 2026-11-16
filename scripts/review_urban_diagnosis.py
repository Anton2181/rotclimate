"""Independent raw-source, spatial, size-equation and censoring review.

Does not import either new diagnostic producer or its observation component.
Reuses unchanged placement primitives with a separately built confluence prior.
"""
import csv
import hashlib
import io
import json
import math
import os
from pathlib import Path
import subprocess
import sys
import zipfile

import numpy as np
import openpyxl
from pyproj import Transformer
from scipy import ndimage as ndi
from scipy.stats import ks_2samp

ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'scripts')]
from polity.settlement_locations import match_count,prior_tiling_sites,site_fields

OUT=ROOT/'output/urban_diagnosis_20261116'
LOW={1:.1,2:4.1,3:10.1,4:20.1,5:40.1,6:201.}
HIGH={1:4.,2:10.,3:20.,4:40.,5:200.,6:float('inf')}


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def number(v):
    try:return float(str(v).replace(',',''))
    except (ValueError,TypeError):return float('nan')


def source(pool):
    if pool=='floodplains':
        with zipfile.ZipFile(ROOT/'data/cache/floodplains_archiraq/archiraq-master.zip') as archive:
            raw=list(csv.DictReader(io.StringIO(archive.read('archiraq-master/docs/papers/1/data_stacked.csv').decode())))
        records=[]
        for i,a in enumerate(raw):
            records.append(dict(index=i,id=a['Id'],latitude=number(a['Longitude']),longitude=number(a['Latitude']),value=number(a['SizeHa']),active=number(a['StartDate'])<=200<=number(a['EndDate'])))
    else:
        book=openpyxl.load_workbook(ROOT/'data/cache/valley_of_mexico/site-survey-data.xlsx',read_only=True,data_only=True)
        it=book.worksheets[0].iter_rows(values_only=True);header=list(next(it));records=[];transform=Transformer.from_crs(32614,4326,always_xy=True)
        for i,row in enumerate(it):
            a=dict(zip(header,row));lon,lat=transform.transform(1000*number(a['East']),1000*number(a['North']))
            records.append(dict(index=i,id=str(a['SiteCode']),latitude=lat,longitude=lon,value=number(a['Area']),active=a['Period'] in ('Classic','Early Classic'),pop=number(a['Population']),low=number(a['PopMin']),high=number(a['PopMax'])))
        book.close()
    best={}
    for a in records:
        if not a['active'] or not math.isfinite(a['latitude']) or not math.isfinite(a['longitude']):continue
        if pool=='floodplains' and not a['value']>0:continue
        value=a['value'] if math.isfinite(a['value']) else 0
        if a['id'] not in best or value>(best[a['id']]['value'] if math.isfinite(best[a['id']]['value']) else 0):best[a['id']]=a
    return sorted(best.values(),key=lambda a:a['index'])


def xyz(latitude,longitude):
    a,b=np.radians(latitude),np.radians(longitude)
    return np.column_stack([np.cos(a)*np.cos(b),np.cos(a)*np.sin(b),np.sin(a)])


def snap(records,x,pool,surveyed):
    lat0,lon0,width,height=(31.8,45.6,600,500) if pool=='floodplains' else (19.6,-98.95,160,180)
    rows=[a for a in records if abs(a['latitude']-lat0)<height/2/111.32 and abs(a['longitude']-lon0)<width/2/(111.32*math.cos(math.radians(lat0)))]
    grid=xyz(x['lat'].ravel(),x['lon'].ravel());points=xyz([a['latitude'] for a in rows],[a['longitude'] for a in rows])
    indices=np.concatenate([np.argmax(points[j:j+32]@grid.T,axis=1) for j in range(0,len(points),32)])
    keep=surveyed.ravel()[indices]
    return [a for a,k in zip(rows,keep) if k],indices[keep]


def cdf_bound(sample,lower,upper):
    edges=set(map(float,sample))|set(map(float,lower))|{float(v) for v in upper if math.isfinite(v)}
    bound=0.
    for edge in edges:
        for value in [edge,np.nextafter(edge,-np.inf)]:
            f=sum(a<=value for a in sample)/len(sample)
            bottom=sum(a<=value for a in upper)/len(upper);top=sum(a<=value for a in lower)/len(lower)
            bound=max(bound,bottom-f,f-top)
    return bound


def scalar_hinterland(towns,x,cell):
    yy,xx=np.nonzero(x['land']);mass=x['density'][yy,xx]*cell**2
    d2=(yy[:,None]-towns[None,:,0])**2+(xx[:,None]-towns[None,:,1])**2
    closest=d2.min(1);ties=d2==closest[:,None]
    weights=ties/ties.sum(1)[:,None];weights[closest*cell**2>60**2]=0
    h=np.sum(mass[:,None]*weights,axis=0)
    assert h.sum()<=mass.sum()+1e-6
    return h


def confluence(x,cell):
    river=x['water_km']<=1e-6;pad=np.pad(river,1);counts=np.zeros(river.shape,int)
    for dy in range(3):
        for dx in range(3):
            if dy!=1 or dx!=1:counts+=pad[dy:dy+river.shape[0],dx:dx+river.shape[1]]
    junction=river&(counts>=3);p=np.pad(junction,1)
    j=junction|p[:-2,1:-1]|p[2:,1:-1]|p[1:-1,:-2]|p[1:-1,2:]
    return np.exp(-(ndi.distance_transform_edt(~j)*cell/15)**2) if j.any() else np.zeros(j.shape)


def main():
    result=json.loads((OUT/'results.json').read_text());inputs=json.loads((OUT/'input_receipt.json').read_text());obs=json.loads((OUT/'observations.json').read_text())
    for name,digest in {**result['producers'],**result['protected_sha256'],**inputs['inputs']}.items():assert sha(ROOT/name)==digest,name
    for name,digest in result['files_sha256'].items():assert sha(OUT/name)==digest,name
    assert result['input_receipt_sha256']==sha(OUT/'input_receipt.json')
    for pool,a in inputs['checks'].items():assert a['results_byte_exact'] and a['model_archive_byte_exact']
    with np.load(OUT/'model.npz') as z:arrays={k:z[k] for k in z.files}
    fit=json.loads((ROOT/'output/settlement_release4_20261116/earth_results.json').read_text())['sizes']['primary'];m=fit['models'][fit['selected']];coef=m['full_coefficients'];sigma=m['heldout_sigma'];limits=fit['area_range_ha']
    maxh=0.;maxarea=0.;checks=0;saved=os.environ.pop('ROTCLIMATE_CONFLUENCE_K',None)
    try:
        for pool in ['floodplains','mexico']:
            raw=source(pool)
            for cell in [3,9]:
                prefix=f'{pool}_{cell}km'
                with np.load(OUT/'archived_replay'/pool/f'inputs_{cell}km.npz') as z:x={k:z[k] for k in z.files}
                surveyed=arrays[prefix+'__surveyed'];records,cells=snap(raw,x,pool,surveyed)
                np.testing.assert_array_equal(cells,arrays[prefix+'__observed_cells'])
                values=np.array([a['value'] for a in records]);np.testing.assert_array_equal(values,arrays[prefix+'__observed_values'])
                town=values>= (3 if pool=='floodplains' else 10)
                assert int(town.sum())==obs[pool][str(cell)]['town_records']
                assert len(set(cells[town]))==obs[pool][str(cell)]['distinct_town_grid_cells']
                lo=np.array([LOW[int(a)] for a in values]) if pool=='floodplains' else values
                hi=np.array([HIGH[int(a)] for a in values]) if pool=='floodplains' else values
                np.testing.assert_array_equal(lo,arrays[prefix+'__lower_ha']);np.testing.assert_array_equal(hi,arrays[prefix+'__upper_ha'])
                info=obs[pool][str(cell)];assert info['survey_proxy_area_km2']==int(surveyed.sum())*cell**2
                if pool=='mexico':
                    population=sum(a['pop'] for a in records);low=sum(a['low'] for a in records);high=sum(a['high'] for a in records);area=sum(a['value'] for a in records if a['value']>0)
                    assert population==info['population_estimate'] and low==info['population_min'] and high==info['population_max']
                    assert abs(area-info['observed_area_ha'])<1e-9 and abs(population/area-info['estimated_people_per_area_ha'])<1e-10
                    assert sum(a['pop']==a['high'] for a in records)==info['estimate_equals_max_rows']
                    assert max(a['value'] for a in records)==info['selected_largest_area_ha']
                    assert max(a['pop'] for a in records)==info['largest_population_estimate']
                    density=lambda a:100+400*max(0,min(1,(math.log(max(a,1e-9))-math.log(50))/(math.log(400)-math.log(50))))
                    central=sum(a['value']*density(a['value']) for a in records if a['value']>0)
                    assert abs(central-info['old_world_sliding_residents_on_observed_areas'])<1e-7
                args={k:x[k] for k in ['density','land','water_km','road','elev','allowed','aridity']};args['cell_km']=cell
                score,eligible=site_fields(**args);cf=confluence(x,cell)
                for row in [a for a in result['positions'] if a['pool']==pool and a['cell_km']==cell]:
                    variant=row['variant'];key=prefix+'__'+variant;new=variant=='release4_full_draw';towns=arrays[key+'__towns']
                    prior=x['history800']*(1+cf if new else 1)
                    _,expected=match_count(lambda sp:prior_tiling_sites(**args,prior=prior,seat_people=sp),row['count_target'])
                    np.testing.assert_array_equal(towns,expected)
                    field=np.where(eligible,score*prior,0);np.testing.assert_allclose(field,arrays[key+'__field'],atol=1e-12,rtol=1e-12)
                    ids=np.unique(cells[town]);background=field[surveyed]
                    pct=sum((sum(background<v)+.5*sum(background==v))/len(background) for v in field.ravel()[ids])/len(ids)
                    points=np.column_stack(np.divmod(ids,field.shape[1]));dist=np.sqrt(((points[:,None,:]-towns[None,:,:])**2).sum(2)).min(1)*cell
                    assert abs(pct-row['town_field_percentile'])<1e-12 and float(np.mean(dist<=10))==row['capture_10km']
                    assert row['survey_proxy_towns']==int(surveyed[towns[:,0],towns[:,1]].sum());checks+=1
                    if cell!=9:continue
                    H=scalar_hinterland(towns,x,cell);maxh=max(maxh,float(abs(H-arrays[key+'__H']).max()));np.testing.assert_allclose(H,arrays[key+'__H'],atol=1e-7,rtol=1e-12)
                    keep=surveyed[towns[:,0],towns[:,1]]&(H>0);np.testing.assert_array_equal(keep,arrays[key+'__keep'])
                    for a in [a for a in result['sizes'] if a['pool']==pool and a['variant']==variant]:
                        n=int(keep.sum());assert a['survey_model_towns']==n
                        rng=np.random.default_rng(a['seed']);e=np.clip(rng.standard_normal(n if variant=='release3_subset_draw' else len(H)),-2.5,2.5)
                        h=H[keep] if variant=='release3_subset_draw' else H
                        generated=np.clip(np.exp(coef[0]+coef[1]*np.log(h)+sigma*e),*limits)
                        generated=generated if variant=='release3_subset_draw' else generated[keep]
                        savedarea=arrays[key+f'__areas_{a["seed"]}'];maxarea=max(maxarea,float(np.max(np.abs(generated-savedarea))) if n else 0.)
                        np.testing.assert_allclose(savedarea,generated,atol=1e-8,rtol=1e-12)
                        assert abs(generated.sum()-a['model_total_ha'])<1e-7
                        if not n:assert a['shape_status']=='not_evaluable_no_model_towns' and a['original_ks'] is None and a['interval_ks_lower_bound'] is None;continue
                        gen=np.sort(generated)[::-1];ranked=np.sort(values[np.isfinite(values)&(values>0)])[::-1][:n]
                        if pool=='floodplains':
                            bins=np.searchsorted([4.05,10.05,20.05,40.05,200.5],gen)+1
                            assert float(np.mean(bins==ranked))==a['original_same_band']
                            if (ranked==6).any():assert a['topn_upper_ha'] is None
                            else:assert a['topn_upper_ha'] is not None
                        else:
                            assert ks_2samp(gen,ranked).statistic==a['original_ks']
                            assert abs(gen.sum()/ranked.sum()-a['original_total_ratio'])<1e-10
                        threshold=10.1 if pool=='floodplains' else 10;comparable=generated[generated>=threshold]
                        assert len(comparable)==a['threshold_model_count']
                        if len(comparable):assert abs(cdf_bound(comparable,lo[town],hi[town])-a['interval_ks_lower_bound'])<1e-12
    finally:
        if saved is not None:os.environ['ROTCLIMATE_CONFLUENCE_K']=saved
    # Original subset case must reproduce every archived seed metric, not only the averages.
    old=json.loads((ROOT/'output/floodplains_blind_20261115/results.json').read_text())['grids']['9']['sizes']['models']['published_refit']['runs']
    actual=[a for a in result['sizes'] if a['pool']=='floodplains' and a['variant']=='release3_subset_draw']
    for a,b in zip(actual,old):assert a['seed']==b['seed'] and abs(a['model_total_ha']-b['model_total'])<1e-9 and a['original_same_band']==b['same_band_share']
    for name,key in [('positions.csv','positions'),('sizes.csv','sizes')]:
        with (OUT/name).open() as f:rows=list(csv.DictReader(f))
        assert len(rows)==len(result[key])
        for a,b in zip(rows,result[key]):
            for key,value in b.items():
                if value is None:assert a[key]==''
                elif isinstance(value,bool):assert a[key]==str(value)
                elif isinstance(value,(int,float)):assert float(a[key])==value
                else:assert a[key]==value
    fresh={}
    for name in ['results.json','observations.json','positions.csv','sizes.csv','model.npz']:
        assert (OUT/name).read_bytes()==(OUT/'fresh'/name).read_bytes(),name;fresh[name]=sha(OUT/name)
    tests=subprocess.run([sys.executable,'-m','pytest','-q','tests/test_urban_observations.py'],cwd=ROOT,text=True,capture_output=True,check=True)
    assert '12 passed' in tests.stdout
    report=dict(status='passed',reviewer_sha256=sha(Path(__file__)),results_sha256=sha(OUT/'results.json'),method='No new producer/component import. Independently decoded raw sources and dot-product grid snap; scalar tie-aware hinterland allocation; separately constructed confluence prior; direct stochastic size equations and interval CDF envelopes; all CSV cells and exact archived controls.',position_cases=checks,size_cases=len(result['sizes']),max_hinterland_difference_people=maxh,max_area_difference_ha=maxarea,controls_stdout=tests.stdout,fresh_byte_exact=fresh,protected_files=len(result['protected_sha256']),adopt=False,new_blind_test=False)
    (OUT/'review.json').write_text(json.dumps(report,indent=2)+'\n');print('Reviewed12position/30size cases,raw cohorts,archived controls,12unit controls and five fresh exports',flush=True)


if __name__=='__main__':main()
