"""Publish all fourteen-day initialization outcomes and saved daily budgets."""
from pathlib import Path
import argparse,json,shutil,sys
import numpy as np
from PIL import Image
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'scripts')]
from local_benchmark_protocol import file_hash,write_json
from monitor_extended_spinup import monitor,load


def publish(wet,dry,out):
    out.mkdir(parents=True,exist_ok=True);records={};started=completed=0
    for name,folder in [('wet',wet),('dry',dry)]:
        r=json.loads((folder/'verification.json').read_text());literal=ROOT/f'calibration/extended_surface_spinup_20261029/{name}_plan.json'
        assert file_hash(literal)==r['literal_plan_sha256'] and literal.read_bytes()==(folder/'frozen_plan.json').read_bytes()
        assert r['actual_earth_initialized_integrations_started']==3 and len(r['results'])==3
        started+=r['actual_earth_initialized_integrations_started'];completed+=r['integrations_completed'];records[name]=dict(protocol=json.loads(literal.read_text()),run=r,receipt_sha256=file_hash(folder/'verification.json'))
        for row in r['results']:
            stem=folder/row['region']/'forced'/'900';path=stem.with_suffix('.npz') if row['status']=='completed' else stem.with_name('900_partial').with_suffix('.npz')
            expected=row['fields_sha256'] if row['status']=='completed' else row['partial_fields_sha256'];assert file_hash(path)==expected
    snapshot=out/'daily_checks';monitor(wet,dry,snapshot);daily=json.loads((snapshot/'progress_verification.json').read_text())
    combined={};analysis={};table=[]
    for region in ['north_india','mexico','pacific_nw']:
        geo=load(wet/region/'initial.npz');land=geo['land'].astype(bool);edge=np.zeros(land.shape,bool);edge[[0,-1]]=True;edge[:,[0,-1]]=True;interior=land&~edge
        branch={};common=daily['checks'][region]['latest_matched_day'];gaps={}
        for name,folder in [('wet',wet),('dry',dry)]:
            rows=daily['daily'][name+'_'+region];count=len(rows);initial=load(folder/region/'initial.npz');combined.update({name+'_'+region+'_initial_'+k:v for k,v in initial.items()})
            status=next(r for r in records[name]['run']['results'] if r['region']==region)
            branch[name]=dict(status=status['status'],completed_steps=status.get('steps',status.get('completed_steps',0)),available_daily_checkpoints=count)
            for d in range(1,count+1):
                a=load(folder/region/'forced'/f'day_{d}_900.npz');combined.update({name+'_'+region+f'_day{d}_'+k:v for k,v in a.items()})
            if count==14:
                late=rows[7:14];last=rows[-1];branch[name].update(late_land_rain_mm_day=float(np.mean([r['land_rain_mm'] for r in late])),late_land_evaporation_mm_day=float(np.mean([r['land_evaporation_mm'] for r in late])),late_land_net_horizontal_import_mm_day=float(np.mean([r['land_net_horizontal_import_mm'] for r in late])),late_land_storage_linear_trend_mm_day=float(np.polyfit([r['day'] for r in late],[r['land_liquid_mm'] for r in late],1)[0]),final_land_liquid_mm=last['land_liquid_mm'],final_land_temperature_k=last['land_temperature_k'])
                table.append(f'<tr><td>{region.replace("_"," ")}</td><td>{name}</td><td>{branch[name]["late_land_rain_mm_day"]:.3f}</td><td>{branch[name]["late_land_evaporation_mm_day"]:.3f}</td><td>{branch[name]["late_land_storage_linear_trend_mm_day"]:.3f}</td><td>{last["land_liquid_mm"]:.2f}</td><td>{last["land_temperature_k"]:.2f}</td></tr>')
            else:table.append(f'<tr><td>{region.replace("_"," ")}</td><td>{name}</td><td colspan="5">{status["status"]}; {count} complete daily checkpoints retained</td></tr>')
        for d in [3,7,14]:
            if d>common:continue
            arrays={n:load(folder/region/'forced'/f'day_{d}_900.npz') for n,folder in [('wet',wet),('dry',dry)]};w,a=arrays['wet'],arrays['dry']
            difference=w['day_rain']-a['day_rain'];storage=w['surface_liquid']-a['surface_liquid'];temperature=w['surface_temperature']-a['surface_temperature']
            gaps[str(d)]=dict(land_rain_wet_minus_dry_mm_day=float(difference[land].mean()),interior_land_rain_wet_minus_dry_mm_day=float(difference[interior].mean()),land_rain_spatial_rms_difference_mm_day=float(np.sqrt(np.mean(difference[land]**2))),land_liquid_wet_minus_dry_mm=float(storage[land].mean()),land_surface_temperature_wet_minus_dry_k=float(temperature[land].mean()),atmospheric_temperature_rms_difference_k=float(np.sqrt(np.mean((w['temperature']-a['temperature'])**2))))
        analysis[region]=dict(branches=branch,declared_day_gaps=gaps)
    all_days=[row for rows in daily['daily'].values() for row in rows]
    np.savez_compressed(out/'publication_fields.npz',**combined)
    figures={}
    for source,target in [('extended_spinup_progress.png','extended_spinup_series.png'),('extended_spinup_water.png','extended_spinup_water.png')]:
        shutil.copyfile(snapshot/source,out/target);figures[target]=file_hash(out/target)
    result=dict(status='fourteen_day_outcomes_independently_checked',new_earth_integrations=started,integrations_completed=completed,new_failed_cases=started-completed,cumulative_prototype_starts=87+started,cumulative_prototype_completions=83+completed,cumulative_retained_failures=4+started-completed,legacy_benchmark_attempts_added=0,physical_adoption=False,recalibration=False,monthly_skill=False,analysis=analysis,maximum_actual_daily_energy_relative_error=max(r['actual_energy_relative_error'] for r in all_days),maximum_actual_daily_water_relative_error=max(r['actual_water_relative_error'] for r in all_days),first_three_day_reproduction=daily['first_three_day_reproduction'],figures_sha256=figures,raw_fields_sha256=file_hash(out/'publication_fields.npz'),publisher_sha256=file_hash(Path(__file__)),daily_checker_sha256=file_hash(ROOT/'scripts/monitor_extended_spinup.py'),scope='All declared wet/dry outcomes retained. Days8–14 and day3/7/14 gaps fixed before outcomes. Persistence of initialization sensitivity is not proof of multiple equilibria or optimizer local minima; solar season advances and lateral reservoirs remain fixed.')
    write_json(out/'publication.json',result);dest=ROOT/'atlases/climate_accuracy/data';write_json(dest/'extended_spinup.json',dict(records=records,publication=result,daily_checks=daily))
    shutil.copyfile(out/'publication_fields.npz',dest/'extended_spinup_fields.npz')
    for f in figures:shutil.copyfile(out/f,dest/f)
    image_html=[]
    for f,alt in [('extended_spinup_series.png','All fourteen daily wet and dry rainfall, liquid storage, surface temperature and evaporation histories'),('extended_spinup_water.png','Matched daily rainfall and wet minus dry evaporation and horizontal column water input, with visible coastlines')]:
        with Image.open(out/f) as im:width,height=im.size
        image_html.append(f'<figure><a href="data/{f}"><img src="data/{f}" width="{width}" height="{height}" loading="lazy" alt="{alt}"></a></figure>')
    section=f'''<!--extended-spinup-start--><section aria-labelledby="extended-spinup-h"><h2 id="extended-spinup-h">Fourteen days still retain substantial starting soil-water effects</h2>
<p>The wet/dry comparison now extends to fourteen days without changing physical parameters. {completed} of {started} declared integrations complete; every outcome is retained. The initial atmosphere and temperatures are common, while land water starts at 50 versus 0 kg/m² before shared conversion rain. That water changes both evaporation and heat capacity, so the branches do not have equal initial energy.</p>
{image_html[0]}
<div class="table"><table><caption>Fixed days 8–14 window; daily land means and final storage</caption><thead><tr><th>Region</th><th>Start</th><th>Rain mm/day</th><th>Evap mm/day</th><th>Soil trend mm/day</th><th>Final soil kg/m²</th><th>Final surface K</th></tr></thead><tbody>{''.join(table)}</tbody></table></div>
<p>Full day 3/7/14 gaps and spatial differences are downloadable. Persistent wet/dry differences show that this short spinup does not remove initialization uncertainty. Storage trends, seasonal solar changes and fixed lateral initial-state reservoirs prevent interpreting these runs as two equilibria or evidence of a calibration local minimum. We do not select whichever starting soil state happens to rain more.</p>
{image_html[1]}
<p>Maps use the matched day shown for each region and a common rain scale within each regional pair. Net evaporation equals rain minus change in surface liquid; net horizontal column input equals change in atmospheric plus surface water. These are conserved storage identities, not moisture-origin tracers. Dark coasts have a white halo for visibility.</p>
<p>The first three days reproduce all six earlier coarse wet/dry cases within the tolerances committed before integration. Every saved daily gas/kinetic/surface energy and atmospheric/surface water budget is independently reconstructed against actual supplies. The faster phase and exact transport-factor backend changes computation, not physical parameters.</p>
<p class="note">This adds {started} prototype starts and {completed} completions; cumulative {87+started} starts /{83+completed} completions /{4+started-completed} retained numerical failures. Legacy 1934/1929 and normal Earth r39, world, biome and population fields remain unchanged. No new rainfall skill score, recalibration or physical adoption. Lower-cell dynamic resolution controls are the next separate experiment.</p>
<p><a href="data/extended_spinup.json" download>Download both frozen plans, all outcomes, daily budgets and fixed-window comparisons</a> · <a href="data/extended_spinup_fields.npz">All initial and daily state arrays</a> · <a href="../../reports/EXTENDED_SURFACE_SPINUP_20261029.md">Fourteen-day results and implications for calibration</a></p></section><!--extended-spinup-end-->'''
    page=ROOT/'atlases/climate_accuracy/index.html';text=page.read_text();start,end='<!--extended-spinup-start-->','<!--extended-spinup-end-->'
    if start in text:
        before,tail=text.split(start,1);_,after=tail.split(end,1);text=before+section+after
    else:text=text.replace('<!--research-list-start-->',section+'\n<!--research-list-start-->',1)
    page.write_text(text);print(json.dumps({k:v for k,v in result.items() if k not in ['analysis','first_three_day_reproduction']},indent=2))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--wet',type=Path,required=True);p.add_argument('--dry',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args();publish(a.wet,a.dry,a.out)
