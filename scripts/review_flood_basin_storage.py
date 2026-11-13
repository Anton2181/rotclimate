"""Independent scalar field/river accounting, terrain/input checks and replay."""
import csv,gzip,hashlib,json,math,subprocess,sys
from pathlib import Path
import numpy as np
from scipy import ndimage as ndi
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'scripts')]
import land_people_earth as L
from land_people import CROPS,DAYS,sunlight_top
OUT=ROOT/'output/flood_basin_storage_20261114'


def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()


def scalar_year(rain,crop,bare,area,source,capacity,eff,capture,initial):
    nf=len(area);stock=list(initial)
    names=['start_mm','end_mm','request_mm','delivered_mm','crop_et_actual_mm','bare_et_actual_mm','rain_spill_mm','rain_excluded_mm']
    result={k:np.zeros((12,nf)) for k in names}
    for k in ['requested','withdrawal','delivered','loss','outlet']:result['river_'+k+'_m3']=np.zeros((12,1))
    for month in range(12):
        request=[]
        for i in range(nf):
            result['start_mm'][month,i]=stock[i];wet=stock[i]+.8*float(rain[month,i])
            result['rain_spill_mm'][month,i]=max(wet-capacity,0);result['rain_excluded_mm'][month,i]=.2*float(rain[month,i])
            stock[i]=min(capacity,wet);request.append(max(capacity-stock[i],0) if capture and month in (7,8,9) else 0)
        total=math.fsum(v*float(a)/1000 for v,a in zip(request,area));delivered=min(total,float(source[month])*eff)
        withdrawal=delivered/eff;ratio=delivered/total if total else 0
        for key,value in [('requested',total),('withdrawal',withdrawal),('delivered',delivered),('loss',withdrawal-delivered),('outlet',float(source[month])-withdrawal)]:result['river_'+key+'_m3'][month,0]=value
        for i in range(nf):
            water=request[i]*ratio;stock[i]+=water;et=min(stock[i],float(crop[month,i]+bare[month,i]));stock[i]-=et
            result['end_mm'][month,i]=stock[i];result['request_mm'][month,i]=request[i];result['delivered_mm'][month,i]=water
            result['crop_et_actual_mm'][month,i]=et if crop[month,i]>0 else 0
            result['bare_et_actual_mm'][month,i]=et if bare[month,i]>0 else 0
    result.update(initial_mm=np.array(initial),final_mm=np.array(stock));return result


def main():
    r=json.loads((OUT/'results.json').read_text());plan=json.loads((ROOT/'calibration/flood_basin_storage_20261114/plan.json').read_text())
    for name,digest in {**r['sources'],**r['producers'],**r['unchanged_atlas_sha256']}.items():assert sha(ROOT/name)==digest,name
    for name,digest in r['files_sha256'].items():assert sha(OUT/name)==digest,name
    assert '52 passed' in json.loads((OUT/'controls.json').read_text())['stdout']
    assert len(r['rows'])==96 and len({v['case'] for v in r['rows']})==96
    with np.load(OUT/'fields.npz') as archive:z={name:archive[name] for name in archive.files}
    nav,_=L.river_masks((672,1644));elev=np.load(ROOT/'data/cache/arable_slope_earth/etopo60_window.npy');terrain_counts={}
    # Independent aggregation into a dictionary rather than the producer's unique/bincount path.
    for basin,spec in plan['regions'].items():
        expected={}
        for south,north,west,east in spec['boxes']:
            y0,y1=int((56-north)*60),int((56-south)*60);x0,x1=int((west+12)*60),int((east+12)*60)
            ys=slice(max(0,y0-60),y1+60);xs=slice(max(0,x0-60),x1+60)
            metric=(111.32/60,111.32/60*math.cos(math.radians(float(np.mean(56-(np.arange(ys.start,ys.stop)+.5)/60)))))
            distance,nearest=ndi.distance_transform_edt(~nav[ys,xs],sampling=metric,return_indices=True)
            local=elev[ys,xs];height=local-local[nearest[0],nearest[1]]
            inner=(slice(y0-ys.start,y1-ys.start),slice(x0-xs.start,x1-xs.start))
            mask=(local[inner]>0)&(height[inner]<=5)&(distance[inner]<=30)
            for yy,xx in zip(*np.nonzero(mask)):
                gy,gx=int(yy)+y0,int(xx)+x0;key=(gy//5,gx//5);a=(111.32/60)**2*math.cos(math.radians(56-(gy+.5)/60))
                count,total=expected.get(key,(0,0.));expected[key]=(count+1,total+a)
        rows=z[basin+'__row'];cols=z[basin+'__col'];assert len(rows)==len(expected)
        for i,key in enumerate(zip(rows,cols)):
            count,area=expected[key];assert count==z[basin+'__fine_count'][i]
            np.testing.assert_allclose(area,z[basin+'__area_km2'][i],rtol=2e-14)
        terrain_counts[basin]=sum(v[0] for v in expected.values())
    del nav,elev
    for month in range(1,13):
        for var,key in [('tavg','T'),('prec','P'),('tmax','D')]:
            a=L.wc(var,month)[L.window_slices()]
            if key=='D':a-=L.wc('tmin',month)[L.window_slices()]
            for basin in plan['regions']:
                np.testing.assert_array_equal(a[z[basin+'__row'],z[basin+'__col']],z[basin+'__'+key][month-1])
    phase=json.loads((ROOT/'output/flood_basin_seasonality_20261113/results.json').read_text());checked=0;field_checks=0
    coverage_by_case={};indices_by_case={}
    for row in r['rows']:
        case=row['case'];basin=row['region'];prefix=basin+'__';c=CROPS[row['crop']];T=z[prefix+'T'];P=z[prefix+'P'];D=z[prefix+'D'];lat=z[prefix+'lat'];allarea=z[prefix+'area_km2']
        qualified=np.isfinite(T).all(0)&np.isfinite(P).all(0)&np.isfinite(D).all(0)&(P>=0).all(0)
        chosen=[]
        for i in range(len(lat)):
            ts=[float(T[m,i]) for m in (10,11,0,1,2)]
            if qualified[i] and min(ts)>=c['window'][0] and max(ts)<=c['window'][1] and max(ts)>=c['need_warm'] and math.fsum(max(v-c['base'],0) for v in ts)*DAYS>=c['heat']:chosen.append(i)
        idx=np.array(chosen,dtype=int);indices_by_case[case]=set(chosen)
        np.testing.assert_array_equal(idx,z[case+'__field_index']);np.testing.assert_array_equal(qualified,z[prefix+'qualified'])
        pet=.0023*np.maximum(T+17.8,0)*np.sqrt(np.maximum(D,0))*sunlight_top(lat,L.TILT,L.WS_DAY)*DAYS
        np.testing.assert_allclose(pet,z[prefix+'PET'],rtol=1e-14,equal_nan=True)
        crop=np.zeros((12,len(idx)));crop[[10,11,0,1,2]]=c['kc']*pet[[10,11,0,1,2]][:,idx]
        bare=row['bare_ET_fraction']*pet[:,idx];bare[[10,11,0,1,2]]=0
        np.testing.assert_allclose(z[case+'__crop_et_demand_mm'],crop,rtol=1e-14)
        np.testing.assert_allclose(z[case+'__bare_et_demand_mm'],bare,rtol=1e-14)
        gauge=next(v for v in phase['rows'] if v['id']==plan['regions'][basin]['gauge']);q=gauge['mean_monthly_flow_m3s'];average=math.fsum(q)/12
        source=np.array([max(value-average,0)*DAYS*86400 for value in q]);np.testing.assert_allclose(z[prefix+'source_m3'][:,0],source,rtol=1e-14)
        initial=np.zeros(len(idx));capture=row['capture']!='none'
        for year in range(1,51):
            scalar=scalar_year(P[:,idx],crop,bare,allarea[idx]*1e6,source,row['capacity_mm'],row['efficiency'],capture,initial)
            residual=float(np.max(np.abs(scalar['final_mm']-initial),initial=0))
            if residual<=1e-6:break
            initial=scalar['final_mm']
        assert row['spinup_years']==year and row['periodic']==(residual<=1e-6)
        assert row['eligible_fields']==len(idx)
        assert math.isclose(row['eligible_area_km2'],float(allarea[idx].sum()),abs_tol=1e-8)
        assert math.isclose(row['candidate_area_km2'],float(allarea.sum()),abs_tol=1e-8)
        assert math.isclose(row['source_m3'],float(source.sum()),rel_tol=1e-14)
        for name,value in scalar.items():np.testing.assert_allclose(z[case+'__'+name],value,rtol=2e-12,atol=2e-5 if name.startswith('river_') else 1e-9,err_msg=case+' '+name)
        area=allarea[idx]*1e6
        np.testing.assert_allclose(scalar['start_mm']+P[:,idx]+scalar['delivered_mm'],scalar['end_mm']+scalar['crop_et_actual_mm']+scalar['bare_et_actual_mm']+scalar['rain_spill_mm']+scalar['rain_excluded_mm'],atol=1e-9)
        np.testing.assert_allclose((scalar['delivered_mm']*area/1000).sum(1),scalar['river_delivered_m3'][:,0],rtol=2e-12,atol=2e-5)
        np.testing.assert_allclose(source,(scalar['river_delivered_m3']+scalar['river_loss_m3']+scalar['river_outlet_m3'])[:,0],rtol=2e-12,atol=2e-5)
        coverage=scalar['crop_et_actual_mm'].sum(0)/crop.sum(0);coverage_by_case[case]={int(i):float(v) for i,v in zip(idx,coverage)}
        np.testing.assert_allclose(z[case+'__coverage'],coverage,atol=1e-11)
        assert math.isclose(row['adequate_area_km2'],float(allarea[idx][coverage>=.95].sum()),abs_tol=1e-6)
        assert math.isclose(row['mean_crop_ET_coverage'],float(np.average(coverage,weights=area)),abs_tol=1e-12)
        for label,field in [('delivered_m3','river_delivered_m3'),('loss_m3','river_loss_m3'),('outlet_m3','river_outlet_m3')]:assert math.isclose(row[label],float(scalar[field].sum()),rel_tol=2e-12,abs_tol=1e-4)
        checked+=12*len(idx);field_checks+=len(idx)
    csv_rows=0;case_index={v['case']:v for v in r['rows']}
    with gzip.open(OUT/'fields.csv.gz','rt',newline='') as f:
        for v in csv.DictReader(f):
            case=v['case'];i=int(v['field']);basin=case_index[case]['region'];j=np.flatnonzero(z[case+'__field_index']==i)
            assert int(v['crop_eligible'])==int(i in indices_by_case[case]);assert float(v['candidate_area_km2'])==z[basin+'__area_km2'][i]
            assert int(v['climate_qualified'])==int(z[basin+'__qualified'][i])
            assert float(v['latitude'])==z[basin+'__lat'][i] and float(v['longitude'])==z[basin+'__lon'][i]
            if len(j):
                assert math.isclose(float(v['crop_et_coverage']),coverage_by_case[case][i],abs_tol=1e-11)
                for col,name in [('annual_delivered_mm','delivered_mm'),('annual_crop_et_mm','crop_et_actual_mm'),('annual_bare_et_mm','bare_et_actual_mm')]:assert float(v[col])==z[case+'__'+name][:,j[0]].sum()
                for col in ('initial_mm','final_mm'):assert float(v[col])==z[case+'__'+col][j[0]]
            else:assert v['crop_et_coverage']==''
            csv_rows+=1
    fresh=OUT/'fresh';subprocess.run([sys.executable,str(ROOT/'scripts/flood_basin_storage.py'),'--out',str(fresh)],check=True,cwd=ROOT)
    exact={}
    for name in ['results.json','fields.npz','fields.csv.gz']:
        assert (OUT/name).read_bytes()==(fresh/name).read_bytes(),name;exact[name]=sha(OUT/name)
    assert not r['adopt'] and not r['heldout_qualified'] and not r['irrigated_area_or_harvest_calibrated']
    result=dict(status='passed',reviewer_sha256=sha(Path(__file__)),results_sha256=sha(OUT/'results.json'),terrain_fine_cells=terrain_counts,scenario_rows=96,field_years=field_checks,monthly_field_balances=checked,csv_rows=csv_rows,method='Independent dictionary terrain aggregation, raw climate samples, scalar field/river simulation from zero spinup, soil/river closures and all CSVs',fresh_byte_exact=exact,unchanged_earth_atlas_files=len(r['unchanged_atlas_sha256']),heldout='unqualified',adopt=False)
    (OUT/'review.json').write_text(json.dumps(result,indent=2)+'\n');print(result)


if __name__=='__main__':main()
