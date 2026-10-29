"""Read-only complete-month scoring under the committed masks and calendar."""
from pathlib import Path
import argparse,json,sys
import numpy as np
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'scripts')]
from local_benchmark_protocol import file_hash,write_json
from monitor_extended_spinup import load,energy
from rotclimate.rainfall_validation import aggregate_footprints,rainfall_metrics
from earth_calendar import monthly_stats,MONTH_DAYS
from circulation_reference import projection_jacobian


def bins(prediction,observed,reference):
    result={};mask=reference['score_mask'];e=reference['mean_elevation_m'];c=reference['mean_coast_km'];area=reference['valid_area_km2']
    for name,select in [('lowland',e<500),('upland',e>=500),('coastal',c<100),('inland',c>=100)]:
        use=mask&select;result[name]=rainfall_metrics(prediction,observed,area,use) if use.any() else dict(cells=0,score=None)
    return result


def analyze(out,dest):
    plan=json.loads((out/'frozen_protocol.json').read_text());literal=ROOT/'calibration/regional_rainfall_benchmark_20261029/plan.json';assert literal.read_bytes()==(out/'frozen_protocol.json').read_bytes()
    for n,h in plan['sources'].items():assert file_hash(ROOT/n)==h,n
    references={region:load(ROOT/path) for region,path in plan['reference_footprints'].items()};baseline={};trials={};combined={};records={};monthly_fields={};all_primary=[];qualifications={}
    month_by_region={'north_india':7,'mexico':8,'pacific_nw':7}
    progress_path=out/'verification.json' if (out/'verification.json').exists() else out/'progress.json'
    progress=json.loads(progress_path.read_text()) if progress_path.exists() else {}
    finished={r['name']:r for r in progress.get('results',progress.get('finished_cases',[]))}
    for spec in plan['cases']:
        region=spec['region'];folder=out/spec['name'];receipt=folder/'verification.json';p=json.loads((ROOT/spec['plan']).read_text());ref=references[region];month=month_by_region[region];duration=float(MONTH_DAYS[month-1]);observed=ref['observed_monthly_rain'][month-1]/duration
        combined.update({region+'_reference_'+k:v for k,v in ref.items()})
        if not receipt.exists():
            status='driver_failed' if spec['name'] in finished else 'pending'
            if spec['kind']=='legacy':baseline[region]=dict(status=status,qualified=False)
            else:trials[spec['name']]=dict(status=status,primary=spec['primary'],region=region,initial_water=spec['initial_water'],dt_s=spec['dt_s'])
            continue
        r=json.loads(receipt.read_text());assert file_hash(ROOT/spec['plan'])==r['literal_plan_sha256'];assert (ROOT/spec['plan']).read_bytes()==(folder/'frozen_plan.json').read_bytes();records[spec['name']]=dict(receipt_sha256=file_hash(receipt),status=r.get('status'))
        if spec['kind']=='legacy':
            qualified=r['qualified_r39_reproduced'] and r['legacy_strict_passes_added']==1
            baseline[region]=dict(status=r['status'],qualified=qualified)
            if not qualified:continue
            path=folder/'raw.npz';assert file_hash(path)==r['fields_sha256'];a=load(path);definition=p['region_spec'];area=p['cell_km']**2/projection_jacobian(a['latitude'],a['longitude'],definition['lat0'],definition['lon0'])[-1];valid=a['land'].astype(bool)&a['inmap'].astype(bool)&np.isfinite(a['observed_rain']).all(0)
            reference_check=aggregate_footprints(a['observed_rain'],valid,area,stride=4)
            np.testing.assert_array_equal(reference_check['mean'],ref['observed_monthly_rain']);np.testing.assert_array_equal(reference_check['valid_area_km2'],ref['valid_area_km2'])
            gregorian=monthly_stats(a['temperature'],a['rain_rate'],a['days']);rate=gregorian['Pm'][month-1]/duration;prediction=aggregate_footprints(rate,valid,area,stride=4)['mean'];metrics=rainfall_metrics(prediction,observed,ref['valid_area_km2'],ref['score_mask'])
            baseline[region].update(month=month,metrics=metrics,geographic=bins(prediction,observed,ref));combined[region+'_r39_rate']=prediction;monthly_fields[spec['name']]=prediction
            continue
        row=r['results'][0];region_dir=folder/region;initial=load(region_dir/'initial.npz');np.testing.assert_array_equal(initial['latitude'],ref['latitude']);np.testing.assert_array_equal(initial['longitude'],ref['longitude']);np.testing.assert_array_equal(initial['land'].astype(bool),ref['land'].astype(bool));mass=-np.diff(initial['pressure_edges'])/9.80665;cells=initial['land'].size;e0=energy(initial,mass);w0=float(initial['vapor'].sum()+initial['surface_liquid'].sum())
        final_path=region_dir/'forced'/(str(spec['dt_s'])+('.npz' if row['status']=='completed' else '_partial.npz'))
        expected=row['fields_sha256'] if row['status']=='completed' else row['partial_fields_sha256'];assert file_hash(final_path)==expected;final=load(final_path)
        supply=row['history'][-1] if row['history'] else dict(cumulative_net_external_energy_j_m2=0,cumulative_outward_water_kg_m2=0)
        final_e=abs(energy(final,mass)-e0-supply['cumulative_net_external_energy_j_m2']*cells)/abs(e0)
        final_w=abs(final['vapor'].sum()+final['surface_liquid'].sum()-w0+supply['cumulative_outward_water_kg_m2']*cells)/w0
        count=0;maxe=maxw=0.;cold=[];min_surface=[];daily_checks=[]
        for day in range(1,int(p['duration_s']//86400)+1):
            stem=region_dir/'forced'/f'day_{day}_{spec["dt_s"]}';jp=stem.with_suffix('.json')
            if not jp.exists():break
            d=json.loads(jp.read_text());a=load(stem.with_suffix('.npz'));assert d==row['daily'][day-1];assert file_hash(stem.with_suffix('.npz'))==d['fields_sha256']
            ee=abs(energy(a,mass)-e0-d['net_external_energy_j_m2']*cells)/abs(e0);we=abs(a['vapor'].sum()+a['surface_liquid'].sum()-w0+d['net_outward_water_kg_m2']*cells)/w0;maxe=max(maxe,ee);maxw=max(maxw,we);count+=1
            daily_checks.append(dict(day=day,energy_relative_error=float(ee),water_relative_error=float(we),fields_sha256=d['fields_sha256']))
            if day>p['calendar']['prelude_days']:
                mask=ref['score_mask'];area=ref['valid_area_km2'];frozen=(a['surface_temperature']<273.15)&(a['surface_liquid']>0)
                cold.append(float(np.sum(area[mask]*frozen[mask])/area[mask].sum()));min_surface.append(float(a['surface_temperature'][mask].min()))
        quality=bool(max(maxe,maxw,final_e,final_w)<1e-10);full=bool(row['status']=='completed' and count==45 and row['steps']==p['duration_s']//spec['dt_s'] and quality)
        trials[spec['name']]=dict(status=row['status'],region=region,initial_water=spec['initial_water'],dt_s=spec['dt_s'],primary=spec['primary'],available_complete_days=count,complete_scored_month=full,saved_budgets_pass=quality,maximum_daily_energy_relative_error=float(maxe),maximum_daily_water_relative_error=float(maxw),final_or_partial_energy_relative_error=float(final_e),final_or_partial_water_relative_error=float(final_w),daily_budget_checks=daily_checks)
        if not full:continue
        first=load(region_dir/'forced'/f'day_14_{spec["dt_s"]}.npz');last=load(region_dir/'forced'/f'day_45_{spec["dt_s"]}.npz');rain=last['rain']-first['rain'];assert np.min(rain)>=0;prediction=rain/p['calendar']['evaluation_days'];metrics=rainfall_metrics(prediction,observed,ref['valid_area_km2'],ref['score_mask']);monthly_fields[spec['name']]=prediction
        for k in final:assert final[k].tobytes()==last[k].tobytes(),k
        trials[spec['name']].update(month=month,metrics=metrics,geographic=bins(prediction,observed,ref),mean_daily_scored_area_fraction_liquid_below_freezing=float(np.mean(cold)),minimum_scored_surface_temperature_k=min(min_surface),initial_fields_sha256=file_hash(region_dir/'initial.npz'))
        duration=p['calendar']['evaluation_days'];mask=ref['score_mask'];weights=ref['valid_area_km2'][mask];weights=weights/weights.sum()
        liquid_change=(last['surface_liquid']-first['surface_liquid'])/duration
        vapor_change=(last['vapor']-first['vapor']).sum(0)/duration
        evaporation=prediction-liquid_change;net_import=vapor_change+liquid_change
        trials[spec['name']]['monthly_column_water_budget']=dict(rain_mm_day=float(weights@prediction[mask]),net_evaporation_mm_day=float(weights@evaporation[mask]),net_horizontal_water_import_mm_day=float(weights@net_import[mask]),vapor_storage_change_mm_day=float(weights@vapor_change[mask]),surface_storage_change_mm_day=float(weights@liquid_change[mask]),scope='Inferred from complete-month saved vapor/soil/rain stores under the fixed mask: P=E+import-vapor change. No runoff/ice; these are model identities, not independent water-origin tracers or observed evaporation.')
        combined[spec['name']+'_rain_rate']=prediction
        for label,fields in [('initial',initial),('day14',first),('day45',last)]:combined.update({spec['name']+'_'+label+'_'+k:v for k,v in fields.items()})
        if spec['primary']:all_primary.append(spec['name'])
    complete=bool(len(all_primary)==6 and len(baseline)==3 and all(v.get('qualified') and 'metrics' in v for v in baseline.values()))
    primary=None
    if complete:
        candidate=float(np.mean([trials[name]['metrics']['mae_mm_day'] for name in all_primary]));control=float(np.mean([v['metrics']['mae_mm_day'] for v in baseline.values()]));primary=dict(candidate_equal_region_and_scenario_mae_mm_day=candidate,r39_equal_region_mae_mm_day=control,absolute_mae_gain_mm_day=control-candidate,relative_mae_gain_fraction=(control-candidate)/control if control>0 else None,scenario_rule='Mean of six independently scored900s losses; no averaging predictions or selecting favorable starts.')
    scenario={}
    for region in references:
        wet,dry=region+'_wet_900',region+'_dry_900'
        if wet in monthly_fields and dry in monthly_fields:
            scenario[region]=dict(wet_mae_mm_day=trials[wet]['metrics']['mae_mm_day'],dry_mae_mm_day=trials[dry]['metrics']['mae_mm_day'],worst_mae_mm_day=max(trials[wet]['metrics']['mae_mm_day'],trials[dry]['metrics']['mae_mm_day']),rainfall_rate_rms_difference_mm_day=float(np.sqrt(np.average((monthly_fields[wet]-monthly_fields[dry])[references[region]['score_mask']]**2,weights=references[region]['valid_area_km2'][references[region]['score_mask']]))))
    sensitivity=None
    if 'mexico_wet_900' in monthly_fields and 'mexico_wet_450' in monthly_fields:
        mask=references['mexico']['score_mask'];area=references['mexico']['valid_area_km2'][mask];delta=(monthly_fields['mexico_wet_450']-monthly_fields['mexico_wet_900'])[mask]
        sensitivity=dict(mean_rain_rate_difference_mm_day=float(np.average(delta,weights=area)),spatial_rain_rate_rms_difference_mm_day=float(np.sqrt(np.average(delta**2,weights=area))))
    dest.mkdir(parents=True,exist_ok=True);np.savez_compressed(dest/'evaluation_fields.npz',**combined)
    result=dict(status='complete_primary_benchmark' if complete else 'available_complete_cases_only',primary_comparison_available=complete,primary=primary,baselines=baseline,trials=trials,scenario_comparisons=scenario,mexico_wet_timestep_comparison=sensitivity,case_receipts=records,global_protocol_sha256=file_hash(literal),analyzer_sha256=file_hash(Path(__file__)),fields_sha256=file_hash(dest/'evaluation_fields.npz'),new_integrations_started=0,physical_adoption=False,recalibration=False,scope='Read-only analysis under fixed masks/calendar/objective. Pending/incomplete/invalid primary cases withhold pooled score. Three reused region/month pairs, fixed simulated laterals and initialization brackets are not annual/global validation; liquid-only and flat-terrain limitations retained.')
    write_json(dest/'analysis.json',result);print(json.dumps(dict(status=result['status'],qualified_baselines={n:r.get('qualified') for n,r in baseline.items()},complete_month_cases=len(monthly_fields)-sum('metrics' in v for v in baseline.values()),primary=primary),indent=2))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--out',type=Path,required=True);p.add_argument('--dest',type=Path,required=True);a=p.parse_args();analyze(a.out,a.dest)
