"""Independent annual source/work/demand/flow checks and calendar readiness audit.

Does not import annual producers, field-support, work-choice or freight allocators.
Geometry uses the existing projection and nearest-land raster only.
"""
import csv
import hashlib
import io
import json
from pathlib import Path
import sys

import numpy as np
from scipy import ndimage as ndi

ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from rotclimate.earth import forward

OUT=ROOT/'output/urban_seasonal_transfer_20261116'
RESTORE=ROOT/'output/urban_population_recipe_20261116/restored'
KCAL=912500.


def sha(p):
    with Path(p).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()


def read(p):return json.loads(p.read_text())


def sample(z,field,lat,lon):
    step=float(z['lat'][0]-z['lat'][1])
    r=(z['lat'][0]-lat)/step;c=(lon-z['lon'][0])/step
    inside=(r>=-.5)&(r<=len(z['lat'])-.5)&(c>=-.5)&(c<=len(z['lon'])-.5)
    # scipy order=0 rounds half upwards, after clipping to the raster.
    ri=np.floor(np.clip(r,0,len(z['lat'])-1)+.5).astype(int)
    ci=np.floor(np.clip(c,0,len(z['lon'])-1)+.5).astype(int)
    return np.where(inside,np.nan_to_num(field)[ri,ci],0.)


def expected_demands(a,name):
    cache=ROOT/'data/cache/roman_city_source_recovery_20261113'
    cities=list(csv.DictReader(io.StringIO((cache/'cities.csv').read_bytes().decode('cp1252'))))
    areas={r['Primary Key']:r for r in csv.DictReader(io.StringIO((cache/'areas.csv').read_bytes().decode('utf-8-sig')))}
    records=[r for r in cities if float(r['Start Date'])<=150 and (r['End Date'].strip().upper()=='NULL' or float(r['End Date'])>=150)]
    lat=np.array([float(r['Latitude (Y)']) for r in records]);lon=np.array([float(r['Longitude (X)']) for r in records])
    window=read(ROOT/'calibration/polity_20261025/plan.json')['earth_windows']['rome']
    px,py=forward(lat,lon,window['lat0'],window['lon0']);ny,nx=a['land'].shape;cell=float(a['cell_km'])
    cols=np.rint(px/cell+(nx-1)/2).astype(int);rows=np.rint((ny-1)/2-py/cell).astype(int)
    inside=(rows>=0)&(rows<ny)&(cols>=0)&(cols<nx)
    _,nearest=ndi.distance_transform_edt(~a['land'],return_indices=True)
    rr,cc=nearest[:,np.clip(rows,0,ny-1),np.clip(cols,0,nx-1)]
    eligible=inside&a['allowed'][rr,cc]
    raw=np.array([float(areas[r['Primary Key']]['Area']) if r['Primary Key'] in areas else np.nan for r in records])
    filled=np.where(np.isfinite(raw),raw,np.quantile(raw[eligible&np.isfinite(raw)],.25))
    scope=set() if name=='control' else {'Achaea','Macedonia','Epirus'}
    if name=='greece_and_asia_minor':scope|={'Asia','Lycia et Pamphylia'}
    factors=np.ones(len(records))
    for i,r in enumerate(records):
        area=areas.get(r['Primary Key'])
        if area and r['Province'] in scope and area['Estimate Basis'].startswith('Walls'):
            factors[i]=1/3 if float(area['Area'])>=100 else .5
    corrected=filled*factors
    density=100+400*np.clip(np.log(np.maximum(corrected,1e-9)/50)/np.log(8),0,1)
    if name=='low':density=np.full_like(filled,100.)
    demand=corrected*density
    if name=='greece_hansen_150':demand=np.where(factors<1,filled*factors*150,demand)
    nodes=(rr*nx+cc)[eligible];unique=np.unique(nodes)
    sums=np.array([demand[eligible][nodes==n].sum() for n in unique])
    np.testing.assert_array_equal(unique,a['nodes'])
    np.testing.assert_allclose(sums,a['residents'],rtol=2e-15,atol=1e-8)
    return dict(catalogue_AD150=len(records),eligible_rows=int(eligible.sum()),
                known_area_rows=int((eligible&np.isfinite(raw)).sum()),
                imputed_area_rows=int((eligible&~np.isfinite(raw)).sum()),
                filled_at_q25_ha=float(np.quantile(raw[eligible&np.isfinite(raw)],.25)),
                area_is_independent_population_observation=False)


def flow_surface(a,reference,parameters):
    """Rebuild all 50 aggregate settings using scatter-add and a sorted link ledger."""
    residents=a['residents'];masks=[np.ones(len(residents),bool),a['lon']<=np.median(a['lon'])]
    masks.append(~masks[1]);max_error=0.;checks=0
    for limit in parameters['haul_limit_L_road_km']:
        source=np.maximum(1-a['dist'].astype(float)/limit,0)
        source=np.where(a['owner']>=0,source,0)
        between=np.maximum(1-a['between'].astype(float)/limit,0).mean(0)
        np.fill_diagonal(between,0)
        for j,share in enumerate(parameters['marketed_share_e']):
            local=np.zeros(len(residents))
            for month in range(4):
                ok=a['owner'][month]>=0
                np.add.at(local,a['owner'][month,ok],a['surplus'][ok]*share/4*source[month,ok])
            excess=np.maximum(local-residents,0);remaining=np.maximum(residents-local,0)
            sender,receiver=np.nonzero((between>0)&(excess[:,None]>0)&(remaining[None,:]>0))
            ledger=sorted(zip(sender.tolist(),receiver.tolist()),key=lambda pair:(-between[pair],pair[0],pair[1]))
            received=np.zeros_like(residents)
            for s,t in ledger:
                if excess[s]<=0 or remaining[t]<=0:continue
                take=min(excess[s],remaining[t]/between[s,t]);arrival=take*between[s,t]
                excess[s]-=take;remaining[t]-=arrival;received[t]+=arrival
                if remaining[t]<1e-9*max(1.,take):remaining[t]=0
            fed=np.minimum(local,residents)+received
            assert np.all(fed>=0) and np.all(fed<=residents+1e-7)
            for part,mask in zip(['all','west','east'],masks):
                value=float(fed[mask].sum()/residents[mask].sum())
                error=abs(value-reference['surface'][str(limit)][part]['fed_share'][j])
                assert error<2e-12,(limit,share,part,error)
                max_error=max(max_error,error);checks+=1
    return dict(settings=50,aggregate_checks=checks,max_absolute_fed_share_difference=max_error)


def main():
    grid=dict(np.load(RESTORE/'grid/earth.npz'));basin=dict(np.load(RESTORE/'basin/fields.npz'))
    parameters=read(ROOT/'calibration/settlement_supply_calibration_20261113/plan.json')['parameters']
    cases=[];inputs={};protected={};passed=True;flow_settings=0
    for stage in ['greek','low']:
        receipt=OUT/stage/'control.json'
        if not receipt.exists():receipt=OUT/stage/'failure.json'
        if not receipt.exists():continue
        control=read(receipt);qualified=control['status']=='passed_byte_exact_archived_annual_controls';passed&=qualified
        inputs[str(receipt.relative_to(ROOT))]=sha(receipt)
        result=read(OUT/stage/'results.json')
        archived=read(ROOT/('output/greek_walls_20261114/results.json' if stage=='greek' else 'output/supply_low_reading_20261114/results.json'))
        if qualified:assert sha(OUT/stage/'results.json')==control['archived_sha256']
        else:assert control['error']=='AssertionError: Annual result JSON differs from archived control'
        prior=read(ROOT/'output/urban_candidate_seasonal_20261116/results.json')
        for path,digest in {**control['sources_sha256'],**prior['protected_sha256']}.items():assert sha(ROOT/path)==digest,path
        protected.update(prior['protected_sha256'])
        for capture in control['captures']:
            name=capture['name'];path=OUT/'prepared'/f'{stage}_{name}.npz'
            assert sha(path)==capture['prepared_sha256'];a=dict(np.load(path))
            for key in ['nodes','dist','owner','between']:
                if stage=='greek' and name=='control':base={k:a[k] for k in ['nodes','dist','owner','between']}
                np.testing.assert_array_equal(a[key],base[key])
            lat,lon=a['lat'],a['grid_lon'];allowed=a['land']&a['allowed'];area=100*float(a['cell_km'])**2*a['arable']
            raw=sample(grid,grid['capacity'],lat,lon)*a['history']*a['land']
            density=raw*61.4e6/(raw[allowed]*float(a['cell_km'])**2).sum()
            np.testing.assert_array_equal(density,a['density'])
            people=np.where(allowed,density,0).ravel()*float(a['cell_km'])**2
            np.testing.assert_array_equal(people,a['people']);assert abs(people.sum()-61.4e6)<1e-7
            rural=people*(1-a['residents'].sum()/people.sum())
            np.testing.assert_array_equal(rural,a['rural'])
            sb=sample(grid,basin['s'],lat,lon)
            unit=np.where(grid['arable']>0,basin['basin_unit_capacity']*1.1e6/(100*np.maximum(grid['arable'],1e-9)),0.)
            boost=sample(grid,unit,lat,lon)*.95/.36
            energies=np.array([(1-sb)*sample(grid,grid['kcal_'+crop],lat,lon)+sb*boost for crop in ['wheat','barley']])
            efficiency=energies/np.array([336,208])[:,None,None]
            chosen=efficiency.argmax(0);best=np.take_along_axis(energies,chosen[None],axis=0)[0]
            expected_crop=np.where(best>0,chosen+1,0)
            np.testing.assert_array_equal(expected_crop.ravel(),a['crop'])
            energy=np.where(allowed,best*area*.36,0).ravel()
            np.testing.assert_allclose(energy,a['potential_kcal'],rtol=1e-12,atol=.01)
            total_hours=np.divide(1e6*np.array([336,208])[chosen],best,out=np.zeros_like(best),where=best>0).ravel()
            reap_hours=np.divide(1e6*np.array([48,32])[chosen],best,out=np.zeros_like(best),where=best>0).ravel()
            np.testing.assert_allclose(total_hours,a['listed'],rtol=1e-12,atol=1e-7)
            np.testing.assert_allclose(reap_hours,a['reaping'],rtol=1e-12,atol=1e-7)
            annual=rural*.4*600;peak=rural*.4*240
            required=energy*total_hours/1e6;reap=energy*reap_hours/1e6
            fraction=np.minimum(1,np.minimum(np.divide(annual,required,out=np.ones_like(annual),where=required>0),np.divide(peak,reap,out=np.ones_like(peak),where=reap>0)))
            grown=energy*fraction
            np.testing.assert_allclose(grown,a['grown_kcal'],rtol=1e-12,atol=.01)
            np.testing.assert_allclose(np.maximum(grown/KCAL-rural,0),a['surplus'],rtol=1e-10,atol=1e-7)
            assert np.all(required*fraction<=annual+.01) and np.all(reap*fraction<=peak+.01)
            demands=expected_demands(a,name)
            ref=result['variants' if stage=='greek' else 'readings'][name]
            # Check every preserved failed surface; otherwise the two primary density readings.
            flows=flow_surface(a,ref,parameters) if stage=='low' or not qualified else None
            if flows:flow_settings+=flows['settings']
            archived_case=archived['variants' if stage=='greek' else 'readings'][name]
            production=a['potential_kcal'];positive=(production>0)
            cases.append(dict(stage=stage,name=name,cities=len(a['nodes']),residents=float(a['residents'].sum()),
                source_cells=int(allowed.sum()),positive_production_cells=int(positive.sum()),
                wheat_cells=int(((a['crop']==1)&allowed.ravel()).sum()),barley_cells=int(((a['crop']==2)&allowed.ravel()).sum()),
                basin_source_cells=int(((sb>0)&allowed).sum()),basin_potential_share=capture['basin_potential_share'],
                potential_person_years=float(production.sum()/KCAL),grown_person_years=float(grown.sum()/KCAL),
                rural_people=float(rural.sum()),annual_rural_deficit_person_years=float(np.maximum(rural-a['grown_kcal']/KCAL,0).sum()),
                calendar_missing_production_share=1.,calendar_missing_positive_cells=int(positive.sum()),
                physical_origin_recipe='Uniform global recruitment; rank-one W_ij=origin_people_i*city_people_j/61.4e6',
                annual_result_exact_to_archive=qualified,
                archived_e95=archived_case['decision']['e95_all_at_L_used'],
                replay_e95=ref['decision']['e95_all_at_L_used'],
                demands=demands,independent_flow_replay=flows))
            print(stage,name,'source/work/demand checks PASS',flush=True)
    readiness=dict(status='annual_controls_passed_calendar_recovery_required' if passed else 'blocked_annual_control_mismatch_and_missing_calendars',
        reviewer_sha256=sha(Path(__file__)),inputs_sha256=inputs,protected_sha256=protected,cases=cases,
        annual_archived_result_bytes_exact=passed,annual_cases=len(cases),independent_flow_settings=flow_settings,
        grid_fields=sorted(grid),basin_fields=sorted(basin),
        harvest_calendar_present=False,monthly_crop_inputs_retained_in_annual_cache=False,
        missing_calendar_production_share=1.,
        transport='All four seasonal float32 distance/owner/city-pair matrices identical across captured cases. Original full Dijkstra is rerun; bounded-memory projection retains only the city columns consumed by the canonical producer. This does not establish identity to the missing archived network arrays.',
        portability_gaps=[
            'No annual production cell retains a harvest boundary; current monthly transport weather is not demonstrated identical to the crop-source climate samples.',
            'Original crop_yield returns a first-strict-best growing-season mask; annual writer discarded it. Recover source yield windows using the original engine, not the fantasy tied-window calendar engine.',
            'Floodplain boost is one winter-cereal maximum assigned to both blended wheat and barley options. Preserve base/basin energy partitions and recover winter crop identity and timing before assigning calendars or labour.',
            'Urban demand is area multiplied by density assumptions, with q25-filled areas and Greek wall corrections; it is not an independent observed resident census.',
            'Global uniform urban recruitment is implicit, unlike the fantasy local physical-origin matrices. A future port must declare the rank-one global origin scenario explicitly.',
            'Annual routes average four snapshots and store float32. A seasonal port must preserve that annual control, declare monthly mapping/leg delay/stores and distinguish changed dispatch assumptions from changed physics.'
        ],
        seasonal_trial_ready=False,seasonal_trial_performed=False,new_fit=False,new_validation_claim=False,adopt=False)
    (OUT/'readiness.json').write_text(json.dumps(readiness,indent=2)+'\n')
    print(readiness['status'],flush=True)


if __name__=='__main__':main()
