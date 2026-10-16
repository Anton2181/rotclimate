"""Verify and diagnose completed cloud-bound cases using saved fields only."""
from __future__ import annotations
import argparse
from dataclasses import asdict
import json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import numpy as np
from scripts import check_v10_cloud_mixing as run,review_v10_storm_delivery as RESPONSE
from rotclimate_v10.earth import atomic_json,atomic_npz,sha256
WINTER=RESPONSE.WINTER.copy();SUMMER=RESPONSE.SUMMER.copy()


def load_verified(source):
    protocol,inputs,setting,anchors,tables=run.prepare()
    state=json.loads((source/'state.json').read_text())
    if json.loads((source/'manifest.json').read_text())!=protocol or state['status']!='complete':raise ValueError('Need the unchanged completed cloud experiment.')
    if set(state['cases'])!={j['key'] for j in protocol['jobs']}:raise ValueError('Cloud case set differs from protocol.')
    records={};seconds=0.;cycles=0;errors=[];dose_errors=[]
    for job in protocol['jobs']:
        folder=source/'cases'/job['key'];row=state['cases'][job['key']]
        run.previous.verify_completed(folder,row)
        identity={**job,'code_sha256':protocol['code_sha256'],'settings':asdict(setting)}
        if json.loads((folder/'config.json').read_text())!=identity:raise ValueError('Cloud case config changed.')
        n=row['years'];evidence={f'year{year}.{ext}' for year in range(1,n+1) for ext in ('json','npz')}
        if set(row['evidence_sha256'])!=evidence or (n!=1 if job['phase']=='control' else not 3<=n<=6):raise ValueError('Incomplete cloud annual evidence.')
        case,p,g,air,c=inputs[job['region']];anchor=anchors[job['anchor']]
        initial=anchor['initial'] if job['phase']=='control' else anchor['record'][0]
        last=None;check={'passed':False};elapsed=0.
        target=tables[(job['seed'],job['region'])]['monthly_import_target_mm']
        for year in range(1,n+1):
            record=run.run.parent.read_checkpoint(folder,year,case.domain.land.shape,completed=True)
            if record is None:raise ValueError('Missing saved cloud year.')
            run.run.validate_control_record(record,target)
            errors.append(run.run.review.verify_annual(record,initial,case))
            changes=np.array(record[-1]['diagnostics']['temperature_changes_scored_land_c']).sum(axis=(0,1))
            t0=run.model.base.temperature(initial.energy,g.mass,initial.water,g.height_m)
            t1=run.model.base.temperature(record[0].energy,g.mass,record[0].water,g.height_m)
            if not np.allclose(changes,(t1-t0)[:,case.score_mask].mean(1),atol=1e-8,rtol=0):raise ValueError('Cloud signed thermal ledger disagrees with states.')
            parcel=np.array(record[-1]['parcel_rain_scored_land_mm'])
            layer=np.array(record[-1]['diagnostics']['layer_rain_scored_land_mm'])
            if parcel.shape!=layer.shape or not np.isfinite(parcel).all() or (parcel<0).any() or (parcel-layer>1e-8).any():raise ValueError('Invalid cloud/total layer rain split.')
            if job['mode']=='bulk' and parcel.any():raise ValueError('Bulk case contains parcel condensation.')
            if job['mode']=='parcel_lower' and parcel[:,-1].any():raise ValueError('Lower-interface case contains highest-layer parcel rain.')
            if last is not None:check=run.run.parent.settling(last,record,case,g)
            if year<n and year>=3 and check['passed']:raise ValueError('Cloud case ran beyond its first settling point.')
            initial=record[0];last=record;elapsed+=record[-1]['elapsed_seconds'];cycles+=1
            dose_errors.append(float(abs(np.array(record[-1]['diagnostics']['monthly_boundary_import_gross_mm'])-target).max()))
        if job['phase']=='control':
            run.previous.replay.verify_physical(record,anchor['record']);check=anchor['row']['settling']
        computed=run.summary(record,case,check,n,anchor)
        computed.update(physical_control_exact=job['phase']=='control',elapsed_seconds=elapsed,
            case_config_sha256=sha256(folder/'config.json'),evidence_sha256={name:sha256(folder/name) for name in sorted(evidence)})
        if computed!=row:raise ValueError('Cloud summary disagrees with reconstructed saved fields.')
        seconds+=elapsed;records[job['key']]=record
    if run.source_id()!=protocol['code_sha256']:raise ValueError('Cloud sources changed during review.')
    return protocol,state,inputs,setting,anchors,records,seconds,cycles,errors,dose_errors


def groups_for(case,target):
    codes=np.array(run.run.koppen_maps.koppen.CODES);mask=case.score_mask
    med=mask&np.isin(target,[i for i,c in enumerate(codes) if c in ('Csa','Csb','Csc')])
    arid=mask&np.isin(target,[i for i,c in enumerate(codes) if c.startswith('B')])
    return {'coast':mask&(case.coast_distance_km<150.),'interior':mask&(case.coast_distance_km>300.),
        'reference_mediterranean':med,'reference_arid':arid,'other_reference_land':mask&~med&~arid}


def placement(old,new,observed,mask,groups):
    gain=abs(old-observed)-abs(new-observed);rows={};denominator=12*mask.sum()
    for name,selected in groups.items():
        if not selected.any():continue
        a,b,o=old[:,selected],new[:,selected],observed[:,selected]
        rows[name]={'cells':int(selected.sum()),'old_winter_mm':float(a[WINTER].sum(0).mean()),
            'new_winter_mm':float(b[WINTER].sum(0).mean()),'reference_winter_mm':float(o[WINTER].sum(0).mean()),
            'old_summer_mm':float(a[SUMMER].sum(0).mean()),'new_summer_mm':float(b[SUMMER].sum(0).mean()),
            'reference_summer_mm':float(o[SUMMER].sum(0).mean()),
            'monthly_mae_gain_mm':float(gain[:,selected].mean()),
            'overall_mae_gain_contribution_mm':float(gain[:,selected].sum()/denominator),
            'winter_overall_mae_gain_contribution_mm':float(gain[WINTER][:,selected].sum()/denominator),
            'summer_overall_mae_gain_contribution_mm':float(gain[SUMMER][:,selected].sum()/denominator)}
    return rows


def numerical_difference(coarse,fine,mask,coarse_bulk=None,fine_bulk=None):
    a,b=coarse[1],fine[1];classes=run.run.koppen_maps
    result={'monthly_rain_difference_p95_mm':float(np.percentile(abs(b-a)[:,mask],95)),
        'annual_rain_difference_p95_mm':float(np.percentile(abs((b-a).sum(0))[mask],95)),
        'temperature_difference_p95_c':float(np.percentile(abs(fine[2]-coarse[2])[:,:,mask],95)),
        'fine_over_coarse_step_ratio':fine[-1]['steps']/coarse[-1]['steps']}
    if coarse_bulk is not None:
        result['treatment_gain_change_monthly_p95_mm']=float(np.percentile(abs((b-fine_bulk[1])-(a-coarse_bulk[1]))[:,mask],95))
    return result


def analyse(source):
    protocol,state,inputs,setting,anchors,records,seconds,cycles,errors,dose=load_verified(source)
    cases={};numerics={};aggregate={};arrays={};fields={};maps=run.run.koppen_maps
    for region,(case,p,g,air,c) in inputs.items():
        target=maps.classify_months(case.domain.temperature_c,case.observed_rain_mm,case.score_mask)
        groups=groups_for(case,target);fields[region]=(case,target)
        arrays[region+'_target']=target;arrays[region+'_mask']=case.score_mask
        arrays[region+'_longitude']=case.longitude;arrays[region+'_latitude']=case.domain.latitude
        for job in (j for j in protocol['jobs'] if j['region']==region):
            key=job['key'];record=records[key];anchor=anchors[job['anchor']];row=state['cases'][key]
            cases[key]={'response':row['response'],'baseline_response':row['baseline_response'],
                'coastal_winter_gain_mm':row['coastal_winter_gain_mm'],'monthly_mae_change_mm':row['monthly_mae_change_mm'],
                'koppen':row['koppen_fixed_surface_temperature'],'settled':row['settling']['passed'],
                'temperature_guards_pass':row['guards']['lower_temperature'] and row['guards']['upper_temperature'],
                'placement':placement(anchor['record'][1],record[1],case.observed_rain_mm,case.score_mask,groups),
                'water_accounting_difference':run.previous.replay.review.atmospheric_budget_difference(anchor['row']['budget'],row['budget']),
                'annual_layer_rain_mm':np.array(record[-1]['diagnostics']['layer_rain_scored_land_mm']).sum(0).tolist(),
                'annual_parcel_layer_rain_mm':row['annual_subgrid_rain_scored_land_by_layer_mm']}
            if not np.isclose(cases[key]['placement']['coast']['new_winter_mm'],row['response']['coast_winter_mm'],atol=1e-10,rtol=0):raise ValueError('Seasonal placement disagrees with the frozen response convention.')
            if job['phase']=='numerics':
                coarse=anchor['record'] if job['mode']=='bulk' else records[key.replace('numerics_','repeat_').replace('_dt0.5','_dt1')]
                fine_bulk=records[key.replace('_'+job['mode']+'_','_bulk_')]
                result=numerical_difference(coarse,record,case.score_mask,anchor['record'],fine_bulk)
                coarse_response=anchor['row']['response'] if job['mode']=='bulk' else state['cases'][key.replace('numerics_','repeat_').replace('_dt0.5','_dt1')]['response']
                result['coastal_winter_change_mm']=row['response']['coast_winter_mm']-coarse_response['coast_winter_mm']
                result['koppen_changed_fraction']=float((maps.classify_months(case.domain.temperature_c,record[1],case.score_mask)[case.score_mask]!=maps.classify_months(case.domain.temperature_c,coarse[1],case.score_mask)[case.score_mask]).mean())
                numerics[key]=result
        for amplitude,timing in run.LIFTING:
            for mode in ('parcel_lower','parcel_all'):
                rows=[state['cases'][f'repeat_{run.label(seed,region,amplitude,timing)}_{mode}_dt1'] for seed in run.SEEDS]
                aggregate[f'{region}_lift{amplitude:g}_{mode}']={k:{'mean':float(np.mean(v)),'min':float(np.min(v)),'max':float(np.max(v))} for k,v in {
                    'coastal_winter_mm':[r['response']['coast_winter_mm'] for r in rows],
                    'coastal_winter_gain_mm':[r['coastal_winter_gain_mm'] for r in rows],
                    'monthly_mae_change_mm':[r['monthly_mae_change_mm'] for r in rows],
                    'mediterranean_to_arid_fraction':[r['koppen_fixed_surface_temperature']['target_mediterranean_to_arid'] for r in rows]}.items()}
        # Fixed seed67, strong-lifting/linked forcing; no best-case selection.
        anchor=anchors[run.label(67,region,16.,'aligned')]
        for name,record in [('bulk',anchor['record']),('lower',records[f'repeat_s67_{region}_lift16_aligned_parcel_lower_dt1']),('all',records[f'repeat_s67_{region}_lift16_aligned_parcel_all_dt1'])]:
            arrays[region+'_'+name+'_koppen']=maps.classify_months(case.domain.temperature_c,record[1],case.score_mask)
            arrays[region+'_'+name+'_rain_mm']=record[1]
        arrays[region+'_reference_rain_mm']=case.observed_rain_mm
    data={'source_code_sha256':protocol['code_sha256'],'source_manifest_sha256':sha256(source/'manifest.json'),
        'source_state_sha256':sha256(source/'state.json'),'analysis_script_sha256':sha256(Path(__file__)),
        'sources_verified':True,'completed_cases':len(cases),'cycles':cycles,'integration_minutes':seconds/60,
        'all_settled':all(r['settled'] for r in cases.values()),'all_temperature_guards_pass':all(r['temperature_guards_pass'] for r in cases.values()),
        'exact_physical_controls':sum(j['phase']=='control' and state['cases'][j['key']]['physical_control_exact'] for j in protocol['jobs']),
        'maximum_recomputed_errors':{k:max(abs(e[k]) for e in errors) for k in errors[0]},
        'maximum_monthly_gross_import_error_mm':max(dose),'cases':cases,'numerics':numerics,'aggregate':aggregate,
        'seasons':'Frozen response winter October–March, summer April–September; Koppen uses April–September warmer half-year. Earlier prose describing response winter as November–April was incorrect; frozen numerical response fields are unchanged.',
        'geography':'Regional domains include neighboring land; the Iberia interior mask includes North Africa. Regime masks use reference climate classes, not country borders.',
        'interpretation':'Unmixed ascending-parcel/instant-liquid-fallout sensitivity. Reused synthetic seeds, not observed climate uncertainty. Shared observed surface temperature for Koppen; no predicted 2m T.',
        'new_climate_integrations':0,'atlas_updated':False}
    return data,fields,arrays


def markdown(data):
    lines=['# Completed cloud-mixing review','',f"{data['completed_cases']}/52 cases; {data['cycles']} saved years; {data['integration_minutes']:.1f} integration minutes. Four exact controls; settling, water, energy, thermal ledgers and monthly incoming-water checks verified.",'',
        '| Region, stronger-lifting/linked case | Coastal winter rain across four catalogues | Added rain, lower-interface cloud bound | Reference | Mediterranean still arid |',
        '|---|---:|---:|---:|---:|']
    for region in ('california','iberia'):
        r=data['aggregate'][region+'_lift16_parcel_lower'];rain=r['coastal_winter_mm'];gain=r['coastal_winter_gain_mm'];arid=r['mediterranean_to_arid_fraction']
        ref=data['cases'][f'screen_s41_{region}_lift16_aligned_parcel_lower_dt1']['response']['coast_winter_reference_mm']
        lines.append(f'| {region} | {rain["min"]:.1f}–{rain["max"]:.1f} mm | +{gain["min"]:.1f}–{gain["max"]:.1f} mm | {ref:.1f} mm | {arid["min"]:.1%}–{arid["max"]:.1%} |')
    maximum=max(abs(r['coastal_winter_change_mm']) for r in data['numerics'].values())
    lines+=['',f'Halving the permitted time step changes coastal winter rain by at most {maximum:.3f} mm over twelve checks. This supports time-step stability for this tested refinement and seed; it does not establish vertical or horizontal resolution convergence.', '',
        '## Why the Iberia headline gain does not improve the whole climate', '',
        '| Reference regime / location, seed67 stronger lift | Winter: bulk → cloud / reference | Summer: bulk → cloud / reference | Contribution to overall monthly-MAE improvement |',
        '|---|---:|---:|---:|']
    key='repeat_s67_iberia_lift16_aligned_parcel_lower_dt1'
    for group in ('coast','interior','reference_mediterranean','reference_arid','other_reference_land'):
        r=data['cases'][key]['placement'][group]
        lines.append(f'| {group} | {r["old_winter_mm"]:.1f} → {r["new_winter_mm"]:.1f} / {r["reference_winter_mm"]:.1f} mm | {r["old_summer_mm"]:.1f} → {r["new_summer_mm"]:.1f} / {r["reference_summer_mm"]:.1f} mm | {r["overall_mae_gain_contribution_mm"]:+.3f} mm |')
    lines+=['', 'Coast/interior masks overlap the reference-regime partition and must not be added to it. The three reference-regime contributions sum to the overall improvement. Positive values improve error. Interior includes North African land, not just the Iberian peninsula.', '',
        'The primary lower-interface gain repeats in every fixed paired comparison, without highest-layer parcel condensation. Adding the highest interface increases rain further but generally worsens Iberia monthly MAE; it does not earn selection. The parcel limit lacks entrainment, cloud memory, ice and rain re-evaporation. No atlas promotion.', '',
        '![Monthly rainfall](rainfall_comparison.png)', '', '![Fixed-temperature Koppen comparison](koppen_comparison.png)', '',
        'Maps use the predeclared seed67 stronger-lifting/linked case, identical observed surface temperatures, Gregorian monthly rainfall and shared score masks. Target is the project classification of WorldClim rain/T, not an external published Koppen raster. All four catalogue comparisons are retained in review.json.', '',
        'Next priority is the origin and season of the misplaced rain, especially in reference-arid land. Diagnose ocean/boundary supply versus local land recycling with passive tags before adding another wetting mechanism. Do not treat more total rain as a successful Mediterranean fix.', '',
        'Reproduce this saved-data review:', '', '```sh','.venv/bin/python scripts/review_v10_cloud_mixing.py --write','```']
    return '\n'.join(lines)+'\n'


def plot(data,fields,a,out):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.patches import Patch
    maps=run.run.koppen_maps
    fig,axes=plt.subplots(2,2,figsize=(12.5,8),constrained_layout=True)
    for row,(region,(case,target)) in enumerate(fields.items()):
        for col,(name,mask) in enumerate((('Coast <150km',case.score_mask&(case.coast_distance_km<150.)),('Interior >300km',case.score_mask&(case.coast_distance_km>300.)))):
            ax=axes[row,col];x=np.arange(1,13)
            for key,label,color,style in [('reference','Reference','#223b43','o-'),('bulk','Bulk saturation','#888888','--'),('lower','Cloud bound · lower interfaces','#127f9c','-'),('all','Cloud bound · all interfaces','#b05f47',':')]:
                ax.plot(x,a[region+'_'+key+'_rain_mm'][:,mask].mean(1),style,color=color,label=label,lw=1.9)
            ax.set(title=region.title()+' · '+name,ylabel='Rain (mm / month)',xticks=x,ylim=(0,None));ax.grid(alpha=.2);ax.legend(frameon=False,fontsize=8)
    fig.suptitle('Cloud formation before mixing helps winter rain; seasonal and spatial errors remain',fontsize=13)
    for ext in ('png','svg'):fig.savefig(out/('rainfall_comparison.'+ext),dpi=170,facecolor='#fbfcfc')
    plt.close(fig)
    fig,axes=plt.subplots(2,3,figsize=(15.4,11.8));fig.subplots_adjust(left=.055,right=.99,top=.875,bottom=.22,wspace=.16,hspace=.28)
    fig.suptitle('Cloud-bound experiment: Mediterranean climate remains too dry',y=.975,fontsize=19,fontweight='bold')
    fig.text(.52,.94,'Shared observed surface temperature · same stronger-lifting/linked forcing · fixed seed67',ha='center',fontsize=11)
    fig.text(.52,.917,'Reference rain versus bulk saturation and lower-interface cloud bound · 60km cells',ha='center',fontsize=10)
    present=set()
    for row,(region,(case,target)) in enumerate(fields.items()):
        mask=case.score_mask;land=case.domain.land;lon=case.longitude[0];lat=case.domain.latitude[:,0]
        dx=float(np.diff(lon).mean());dy=float(abs(np.diff(lat).mean()));extent=(lon[0]-dx/2,lon[-1]+dx/2,lat[-1]-dy/2,lat[0]+dy/2)
        for col,(name,title) in enumerate((('target','Earth target'),('bulk','Bulk saturation'),('lower','Cloud bound · lower interfaces'))):
            classes=target if name=='target' else a[region+'_'+name+'_koppen'];image=np.full(land.shape+(3,),[226/255,239/255,243/255]);image[land]=np.array([222,226,226])/255
            image[mask]=np.array([maps.koppen.COLORS[maps.koppen.CODES[i]] for i in classes[mask]])/255;present.update(maps.koppen.CODES[i] for i in classes[mask])
            ax=axes[row,col];ax.imshow(image,extent=extent,origin='upper',interpolation='nearest');ax.contour(case.longitude,case.domain.latitude,land.astype(float),levels=[.5],colors=['#52676d'],linewidths=.45)
            ax.set(title=title,xlim=(case.longitude[mask].min()-1.7*dx,case.longitude[mask].max()+1.7*dx),ylim=(case.domain.latitude[mask].min()-1.1*dy,case.domain.latitude[mask].max()+1.1*dy));ax.set_aspect(1/np.cos(np.deg2rad(case.domain.latitude[mask].mean())))
            for city,x,y in maps.LANDMARKS[region]:ax.plot(x,y,'o',ms=2.5,color='#14232a');ax.annotate(city,(x,y),xytext=(4,4),textcoords='offset points',fontsize=7,bbox=dict(facecolor='white',alpha=.75,edgecolor='none',pad=1))
            if name=='target':caption=f'{case.observed_rain_mm.sum(0)[mask].mean():.0f} mm/year · observed rain'
            else:
                k=maps.comparison(target,classes,mask);rain=a[region+'_'+name+'_rain_mm'].sum(0)[mask].mean();caption=f'{rain:.0f} mm/year · {k["exact_class_agreement"]:.0%} match · {k["target_mediterranean_to_arid"]:.0%} Cs → arid'
            ax.set_xlabel(caption,fontsize=9,labelpad=8);ax.tick_params(labelsize=8)
        axes[row,0].set_ylabel(maps.REGION_NAMES[region],fontsize=11,fontweight='semibold',labelpad=14)
    handles=[Patch(facecolor=np.array(maps.koppen.COLORS[c])/255,label=c+' · '+maps.koppen.DESCRIPTIONS[c]) for c in maps.koppen.CODES if c in present]
    handles.append(Patch(facecolor='#dee2e2',label='Gray · outside evaluation mask'))
    fig.legend(handles=handles,loc='lower center',bbox_to_anchor=(.52,.047),ncol=4,frameon=False,fontsize=8.3)
    fig.text(.52,.022,'WorldClim 1970–2000 target · final settled synthetic year · unmixed liquid-cloud limit · atlas unchanged',ha='center',fontsize=9)
    for ext in ('png','svg'):fig.savefig(out/('koppen_comparison.'+ext),dpi=170,facecolor='#fbfcfc')
    plt.close(fig)


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source',type=Path,default=ROOT/'output/v10_cloud_mixing');p.add_argument('--out',type=Path,default=ROOT/'output/v10_cloud_review');p.add_argument('--write',action='store_true');args=p.parse_args(argv)
    data,fields,arrays=analyse(args.source)
    if args.write:
        a,b=args.out.resolve(),args.source.resolve()
        if a==b or a in b.parents or b in a.parents:raise ValueError('Preserve original cloud experiment output.')
        atomic_json(args.out/'review.json',data);atomic_npz(args.out/'map_fields.npz',**arrays);(args.out/'review.md').write_text(markdown(data));plot(data,fields,arrays,args.out)
    print(markdown(data));return 0


if __name__=='__main__':raise SystemExit(main())
