"""Independent population equations/sampling and brute-force centre allocation."""
import csv
import hashlib
import json
import math
from pathlib import Path
import re
import subprocess
import sys

import numpy as np

ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'scripts')]
from rotclimate import biomes
import settlement_release2_earth as R

OUT=ROOT/'output/urban_population_recipe_20261116'


def sha(p):
    with p.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()


def quantile(values,q):
    if not len(values):return None
    values=sorted(values);position=(len(values)-1)*q;i=math.floor(position);j=math.ceil(position)
    return values[i]+(values[j]-values[i])*(position-i)


def aggregate(H,old,total,oldtotal):
    pairs=[(float(a),float(b)) for a,b in zip(H,old) if a>0 and b>0]
    delta=[math.log(a/b) for a,b in pairs];share=[v-math.log(total/oldtotal) for v in delta]
    row=dict(n=len(H),positive_H_rows=sum(h>0 for h in H),zero_H_rows=sum(h==0 for h in H),positive_pair_rows=len(pairs))
    for label,values in [('H_people',H),('positive_pair_log_H_change',delta),('positive_pair_log_H_share_change',share)]:
        for name,q in [('min',0),('p25',.25),('p50',.5),('p75',.75),('max',1)]:row[label+'_'+name]=quantile(values,q)
    return row


def compare(a,b):
    assert set(a)==set(b)
    for key,value in b.items():
        if value is None or isinstance(value,(str,bool)):assert a[key]==value,(key,a[key],value)
        else:assert math.isclose(a[key],value,rel_tol=2e-10,abs_tol=2e-6),(key,a[key],value)


def main():
    result=json.loads((OUT/'results.json').read_text());restore=json.loads((OUT/'restoration.json').read_text())
    assert restore['status']=='passed_exact_qualified_grid_replay'
    failure=json.loads((OUT/'failed_legacy_wrapper/restoration.json').read_text())
    assert failure['status']=='failed_preserved_unqualified_candidate' and 'extra_crops' in failure['error']
    assert failure['sources_sha256']['scripts/restore_urban_population_inputs.py']==sha(OUT/'failed_legacy_wrapper/restorer_snapshot.txt')
    for name,digest in {**result['producers'],**result['protected_sha256']}.items():assert sha(ROOT/name)==digest,name
    for name,digest in result['files_sha256'].items():assert sha(OUT/name)==digest,name
    for name,digest in restore['files_sha256'].items():assert sha(ROOT/name)==digest,name
    grid=OUT/'restored/grid/earth.npz';assert sha(grid)==restore['expected_grid_sha256']=='3b57d0cba03802d3693eb46e661771d6375715dc2f17f8555217ff0ff33fb338'
    assert (OUT/'restored/grid/regions.json').read_bytes()==(ROOT/'output/land_people/earth_floodplain/regions.json').read_bytes()
    with np.load(OUT/'restored/basin/fields.npz') as z:assert int((z['s']>0).sum())==restore['qualifying_cells']==1275
    with np.load(R.POOLS/'rome_inputs.npz') as z:x={k:z[k] for k in z.files}
    with np.load(ROOT/'output/urban_measurement_pilot_20261116/design.npz') as z:d={k:z[k] for k in z.files}
    with np.load(OUT/'model.npz') as z:actual={k:z[k] for k in z.files}
    # Biome classification is reused unchanged; all subsequent density equations
    # and the nearest-pixel sampler are independently evaluated here.
    with np.load(grid) as z:
        b=biomes.classify(np.nan_to_num(z['T_ann']),np.nan_to_num(z['P_ann']),z['land'])
        lat,lon=z['lat'],z['lon'];step=float(lat[0]-lat[1])
        yy=(float(lat[0])+step/2-x['lat'])/step-.5;xx=(x['lon']-(float(lon[0])-step/2))/step-.5
        inside=(yy>=-.5)&(yy<=len(lat)-.5)&(xx>=-.5)&(xx<=len(lon)-.5)
        iy=np.floor(np.clip(yy,0,len(lat)-1)+.5).astype(int);ix=np.floor(np.clip(xx,0,len(lon)-1)+.5).astype(int)
        sample=lambda k:np.nan_to_num(z[k])[iy,ix]
        crop=np.maximum(sample('capacity').astype(float),0);npp=sample('npp');arable=sample('arable');malaria=sample('malaria');irr=sample('irr_distance');biome=b[iy,ix]
    spec=json.loads((ROOT/'data/harvest_model.json').read_text());g=spec['grazing']
    def coefficient(table):return np.array([table.get(str(int(v)),1.) for v in biome.ravel()]).reshape(biome.shape)
    clearance=coefficient(spec['biome_crop_realization']);forage=coefficient(g['edible_forage_share'])
    lp=(ROOT/'scripts/land_people.py').read_text();farmed=float(re.search(r'^FARMED_SHARE = ([0-9.e+]+)',lp,re.M)[1]);need=float(re.search(r'^NEED_KCAL = ([0-9.e+]+)',lp,re.M)[1])
    occupation=float(re.search(r'^OCCUPATION_CENTRAL = ([0-9.e+]+)',(ROOT/'polity/earth.py').read_text(),re.M)[1])
    # Preserve the source float32 multiplications before promotion by tables.
    pasture=(np.maximum(npp,0)*1000*g['aboveground_npp_share']*forage*g['sustainable_use']*
             np.clip(1-arable*farmed,0,1)*g['human_kcal_per_kg_consumed_forage']/need)
    water=np.minimum(-6*np.log(np.maximum(irr,1e-12)),300.)
    access=spec['river_access_floor']+(1-spec['river_access_floor'])*np.exp(-np.maximum(water,0)/spec['river_access_length_km'])
    health=1-spec['maximum_malaria_penalty']*np.clip(malaria,0,1)
    land=x['land'];allowed=land & x['allowed'];cell=float(x['cell_km']);cellarea=cell*cell
    base=np.where(land & inside,(crop*clearance+pasture)*access*health*occupation,0.)
    pattern=np.where(land & inside,crop*x['history'],0.)
    target=61.4e6;factor=target/math.fsum(float(v)*cellarea for v in pattern[allowed])
    densities=[x['density'],base,pattern*factor];variants=['legacy','floodplain_settlement_base','floodplain_P2_Frier']
    # Every land cell chooses its nearest fixed integer centre, with full tie
    # search (no production tree/assignment routine),radius60km and conservation.
    centres=np.column_stack(np.unravel_index(x['real'],land.shape));lr,lc=np.nonzero(land)
    H=np.zeros((3,len(centres)));mass=np.array([a[lr,lc]*cellarea for a in densities])
    for start in range(0,len(lr),2000):
        rr,cc=lr[start:start+2000],lc[start:start+2000]
        distance=(rr[:,None]-centres[None,:,0])**2+(cc[:,None]-centres[None,:,1])**2
        nearest=distance.min(axis=1);owner=(distance==nearest[:,None]) & (nearest[:,None]*cellarea<=3600.)
        weights=owner/np.maximum(owner.sum(axis=1)[:,None],1)
        H+=mass[:,start:start+2000]@weights
    old,_,_=R.cohort();old=[r for r in old if r['area'] not in (20.,30.)];cells=[r['cell'] for r in old]
    names=sorted({r['province'] for r in old});province=np.array([names.index(r['province']) for r in old]);np.testing.assert_array_equal(province,d['province'])
    windows=[];cohorts=[];provinces=[];maxdiff=0.;total=[math.fsum(float(v)*cellarea for v in a[land]) for a in densities]
    for i,variant in enumerate(variants):
        rowH=H[i,cells];expectedH=actual[variant+'__centre_H'];maxdiff=max(maxdiff,float(np.max(np.abs(expectedH-H[i]))))
        np.testing.assert_allclose(expectedH,H[i],atol=2e-6,rtol=2e-10)
        np.testing.assert_allclose(actual[variant+'__row_H'],rowH,atol=2e-6,rtol=2e-10)
        if i==0:np.testing.assert_allclose(np.log(rowH),d['lnH'],atol=1e-11,rtol=1e-12)
        assigned=math.fsum(H[i]);assert assigned<=total[i]+1e-6
        windows.append(dict(variant=variant,window_people=total[i],allowed_people=math.fsum(float(v)*cellarea for v in densities[i][allowed]),assigned_centre_H_people=assigned,
                            unassigned_people=total[i]-assigned,centres=len(centres),zero_H_centres=sum(h==0 for h in H[i]),zero_density_land_cells=int((densities[i][land]==0).sum()),
                            nonfinite_density_cells=int((~np.isfinite(densities[i])).sum()),harvest_coverage_of_land=float(inside[land].mean()),P2_level_factor=factor if i==2 else None))
        for cohort,mask in [('mixed',np.ones(len(old),bool)),('strict',d['strict'])]:
            cohorts.append(dict(variant=variant,cohort=cohort,**aggregate(rowH[mask],H[0,cells][mask],total[i],total[0])))
            for code,name in enumerate(names):
                use=mask & (province==code)
                provinces.append(dict(variant=variant,cohort=cohort,province=code,province_name=name,small_sample=bool(use.sum()<5),**aggregate(rowH[use],H[0,cells][use],total[i],total[0])))
    csvcells=0
    for key,records in [('windows',windows),('cohorts',cohorts),('provinces',provinces)]:
        assert len(result[key])==len(records)
        for a,b in zip(result[key],records):compare(a,b)
        with (OUT/f'{key}.csv').open() as f:rows=list(csv.DictReader(f))
        assert len(rows)==len(records)
        for a,b in zip(rows,records):
            assert set(a)==set(b)
            for k,v in b.items():
                if v is None:assert a[k]==''
                elif isinstance(v,(str,bool)):assert a[k]==str(v)
                else:assert math.isclose(float(a[k]),v,rel_tol=2e-10,abs_tol=2e-6),(k,a[k],v)
                csvcells+=1
    assert result['fixed_eligible_records']==664 and result['strict_records']==153 and result['centre_geometry_unchanged'] and result['zero_H_rows_retained']
    assert abs(windows[2]['allowed_people']-target)<1e-6
    assert all(result[k] is False for k in ['fit_performed','predictive_score','new_blind_test','climate_fit','adopt'])
    fresh={}
    for name in ['results.json','model.npz','windows.csv','cohorts.csv','provinces.csv']:
        assert (OUT/name).read_bytes()==(OUT/'fresh'/name).read_bytes();fresh[name]=sha(OUT/name)
    tests=subprocess.run([sys.executable,'-m','pytest','-q','tests/test_urban_crop_compatibility.py'],cwd=ROOT,text=True,capture_output=True,check=True);assert '6 passed' in tests.stdout
    report=dict(status='passed',reviewer_sha256=sha(Path(__file__)),results_sha256=sha(OUT/'results.json'),
                method='Exact qualified global SHA/regional bytes/1275cells. Shared unchanged biome classifier only;independent pixel sampler/settlement population equations,Frier normalization,brute full nearest-centre search with ties/radius and scalar mass/quantile/log-change accounting. Legacy geometry row mapping reused pinned R.cohort.',
                variants=3,provinces=51,cohort_cases=6,province_cases=306,csv_cells=csvcells,max_H_difference_people=maxdiff,
                controls_stdout=tests.stdout,fresh_byte_exact=fresh,fit_performed=False,adopt=False)
    (OUT/'review.json').write_text(json.dumps(report,indent=2)+'\n');print(f'Reviewed3population recipes,306province summaries,{csvcells}CSVcells,independent density/ownership and six adapter controls')


if __name__=='__main__':main()
