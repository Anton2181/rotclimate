"""Publish all available complete months, withholding an incomplete pooled score."""
from pathlib import Path
import argparse,json,shutil,sys
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patheffects as pe
from PIL import Image
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'scripts')]
from local_benchmark_protocol import file_hash,write_json
from analyze_regional_rainfall import analyze


def publish(source,out):
    source=source.resolve();out=out.resolve();out.mkdir(parents=True,exist_ok=True);analyze(source,out/'analysis');a=json.loads((out/'analysis/analysis.json').read_text());plan=json.loads((source/'frozen_protocol.json').read_text());regions=['north_india','mexico','pacific_nw']
    complete={name:r for name,r in a['trials'].items() if r.get('complete_scored_month')};assert complete,'Publish only after at least one complete, budget-qualified month'
    with np.load(out/'analysis/evaluation_fields.npz') as f:fields={k:f[k] for k in f.files}
    fig,axes=plt.subplots(1,2,figsize=(13,5));x=np.arange(3);colors=['#a96a3b','#207fa5','#cf9438'];table=[]
    for j,(profile,color,offset) in enumerate(zip(['r39','wet','dry'],colors,[-.24,0,.24])):
        for i,region in enumerate(regions):
            record=a['baselines'][region] if profile=='r39' else a['trials'][region+'_'+profile+'_900'];metrics=record.get('metrics')
            if metrics:
                for ax,key in zip(axes,['mae_mm_day','predicted_mean_mm_day']):ax.bar(i+offset,metrics[key],.23,color=color,label=profile if i==0 else None)
            else:
                for ax in axes:ax.text(i+offset,.03,'pending',rotation=90,ha='center',va='bottom',fontsize=8,transform=ax.get_xaxis_transform(),color=color)
    for i,region in enumerate(regions):
        metrics=a['baselines'][region]['metrics'];axes[1].plot([i-.36,i+.36],[metrics['observed_mean_mm_day']]*2,color='#28794e',lw=2,label='WorldClim' if i==0 else None)
        for profile in ['r39','wet','dry']:
            r=a['baselines'][region] if profile=='r39' else a['trials'][region+'_'+profile+'_900'];m=r.get('metrics');table.append(dict(region=region,profile=profile,month=7 if region!='mexico' else 8,status=r['status'],mae_mm_day=m['mae_mm_day'] if m else None,mean_mm_day=m['predicted_mean_mm_day'] if m else None,bias_mm_day=m['bias_mm_day'] if m else None,observed_mean_mm_day=metrics['observed_mean_mm_day']))
    for ax,title in zip(axes,['Area-weighted absolute rainfall error','Mean rainfall on identical scoring footprints']):ax.set_title(title);ax.set_xticks(x,['India / July','Mexico / August','PNW / July']);ax.set_ylabel('mm/day');ax.set_xlim(-.6,2.6);ax.grid(axis='y',alpha=.2);ax.legend(fontsize=9)
    extra=a['trials']['mexico_wet_450'];m=extra.get('metrics');table.append(dict(region='mexico',profile='wet450 (numerical)',month=8,status=extra['status'],mae_mm_day=m['mae_mm_day'] if m else None,mean_mm_day=m['predicted_mean_mm_day'] if m else None,bias_mm_day=m['bias_mm_day'] if m else None,observed_mean_mm_day=a['baselines']['mexico']['metrics']['observed_mean_mm_day']))
    comparison_notes=[]
    for region in regions:
        wet=a['trials'][region+'_wet_900'].get('metrics');dry=a['trials'][region+'_dry_900'].get('metrics');control=a['baselines'][region]['metrics']
        if wet and dry:comparison_notes.append(f'{region.replace("_"," ")}: wet/dry MAE {wet["mae_mm_day"]:.3f}/{dry["mae_mm_day"]:.3f} mm/day versus r39 {control["mae_mm_day"]:.3f}; mean wet/dry rainfall {wet["predicted_mean_mm_day"]:.3f}/{dry["predicted_mean_mm_day"]:.3f} versus observed {control["observed_mean_mm_day"]:.3f}.')
    title='Complete monthly rainfall comparison' if a['primary_comparison_available'] else 'Available complete months — pooled comparison withheld'
    fig.suptitle(title,fontsize=14);fig.text(.5,.01,'31 evaluation days after a14-day prelude • every complete wet/dry branch shown • pending is never zero • reused regional development tests',ha='center',fontsize=9);fig.tight_layout(rect=(0,.04,1,.94));fig.savefig(out/'regional_rainfall_results.png',dpi=160);plt.close(fig)
    maps,axes=plt.subplots(3,6,figsize=(19,10),squeeze=False)
    for row,region in enumerate(regions):
        geo={k[len(region+'_reference_'):]:v for k,v in fields.items() if k.startswith(region+'_reference_')};mask=geo['score_mask'];month=7 if region!='mexico' else 8;obs=geo['observed_monthly_rain'][month-1]/31;control=fields[region+'_r39_rate'];wet=fields.get(region+'_wet_900_rain_rate');dry=fields.get(region+'_dry_900_rain_rate')
        data=[obs,control,wet,dry,None if wet is None else wet-obs,None if dry is None else dry-obs];titles=['Observed normal','r39','Wet start','Dry start','Wet − observed','Dry − observed'];limit=max(float(v[mask].max()) for v in data[:4] if v is not None);bias_limit=max([float(abs(v[mask]).max()) for v in data[4:] if v is not None]+[.01])
        lon,lat=geo['longitude'],geo['latitude'];dx=max(float(np.ptp(lon[mask])),1.)*.18;dy=max(float(np.ptp(lat[mask])),1.)*.18
        for col,(value,name) in enumerate(zip(data,titles)):
            ax=axes[row,col];ax.set_title(region.replace('_',' ')+': '+name,fontsize=9)
            if value is None:ax.text(.5,.5,'Month pending',transform=ax.transAxes,ha='center');ax.set_axis_off();continue
            signed=col>=4;image=ax.pcolormesh(lon,lat,np.where(mask,value,np.nan),shading='nearest',cmap='RdBu_r' if signed else 'YlGnBu',vmin=-bias_limit if signed else 0,vmax=bias_limit if signed else max(limit,.01));coast=ax.contour(lon,lat,geo['land'].astype(float),levels=[.5],colors='#203d4a',linewidths=.9);coast.set_path_effects([pe.withStroke(linewidth=2.5,foreground='white')]);ax.set_xlim(lon[mask].min()-dx,lon[mask].max()+dx);ax.set_ylim(lat[mask].min()-dy,lat[mask].max()+dy);maps.colorbar(image,ax=ax,shrink=.65,label='mm/day');ax.tick_params(labelsize=7)
    maps.suptitle('Observed and complete simulated months on the same frozen land footprints',fontsize=14);maps.text(.5,.01,'Only valid scoring cells shown • common rate and error scales within each region • no interpolation of missing trial months',ha='center',fontsize=9);maps.tight_layout(rect=(0,.03,1,.95));maps.savefig(out/'regional_rainfall_maps.png',dpi=145);plt.close(maps)
    known=[r['metrics']['mae_mm_day'] for r in a['trials'].values() if r.get('primary') and r.get('complete_scored_month')]
    control_mean=float(np.mean([r['metrics']['mae_mm_day'] for r in a['baselines'].values()]))
    lower_bound=dict(known_complete_primary_cases=len(known),remaining_primary_cases=6-len(known),candidate_mae_lower_bound_mm_day=float(sum(known)/6),r39_equal_region_mae_mm_day=control_mean,scope='Nonnegative-loss lower bound, not a completed pooled score; no unfinished month is scored or substituted.')
    bound_note=''
    if not a['primary_comparison_available'] and sum(known)/6>control_mean:
        bound_note=f'Even if every remaining primary case had zero MAE, the candidate mean would be at least {sum(known)/6:.3f} mm/day versus r39 {control_mean:.3f}. This configuration therefore cannot beat the declared objective. This is a mathematical bound, not its completed pooled score; all planned cases continue.'
    result=dict(status=a['status'],complete_month_cases=list(complete),primary=a['primary'],primary_comparison_available=a['primary_comparison_available'],table=table,analysis=a,primary_lower_bound=lower_bound,figure_sha256={name:file_hash(out/name) for name in ['regional_rainfall_results.png','regional_rainfall_maps.png']},publisher_sha256=file_hash(Path(__file__)),new_integrations_started=0,physical_adoption=False,recalibration=False,scope='Every available complete31-day candidate month, under the precommitted objective/calendar/masks. Missing primary months withhold pooled score. Reused conditional regional tests are not annual/global validation.')
    write_json(out/'publication.json',result);dest=ROOT/'atlases/climate_accuracy/data'
    for name in ['regional_rainfall_results.png','regional_rainfall_maps.png']:shutil.copyfile(out/name,dest/name)
    shutil.copyfile(out/'analysis/evaluation_fields.npz',dest/'regional_rainfall_results_fields.npz');write_json(dest/'regional_rainfall_results.json',dict(protocol=plan,publication=result))
    rows=[]
    for row in table:
        f=lambda key:'pending' if row[key] is None else f'{row[key]:.3f}'
        rows.append(f'<tr><td>{row["region"].replace("_"," ")}</td><td>{row["profile"]}</td><td>{f("observed_mean_mm_day")}</td><td>{f("mean_mm_day")}</td><td>{f("mae_mm_day")}</td><td>{f("bias_mm_day")}</td></tr>')
    pooled='Pooled primary score is withheld until all six primary wet/dry months complete and pass saved-state budgets.'
    if a['primary_comparison_available']:
        p=a['primary'];pooled=f'The declared mean of six independently scored region/initialization losses is {p["candidate_equal_region_and_scenario_mae_mm_day"]:.3f} mm/day, versus r39 {p["r39_equal_region_mae_mm_day"]:.3f}. The signed relative MAE gain is {100*p["relative_mae_gain_fraction"]:.1f}%. Regional tradeoffs are allowed; no favorable initial state is selected.'
    figures=''
    for name,caption in [('regional_rainfall_results.png','Only complete calendar months are scored. Pending branches are explicitly marked.'),('regional_rainfall_maps.png','The same valid land cells, Gregorian month and projection-area weights score every branch. Scales are shared within each region.')]:
        with Image.open(out/name) as im:w,h=im.size
        figures+=f'<figure><a href="data/{name}"><img src="data/{name}" width="{w}" height="{h}" loading="lazy" alt="{caption}"></a><figcaption>{caption}</figcaption></figure>'
    water_rows=''
    for name,r in a['trials'].items():
        budget=r.get('monthly_column_water_budget')
        if budget and r['primary']:
            water_rows+='<tr><td>'+name.replace('_',' ')+'</td>'+''.join(f'<td>{budget[k]:.3f}</td>' for k in ['rain_mm_day','net_evaporation_mm_day','net_horizontal_water_import_mm_day','vapor_storage_change_mm_day','surface_storage_change_mm_day'])+'</tr>'
    water_table='<div class="table"><table><caption>Complete-month modeled water supply on the same scoring footprints, mm/day</caption><thead><tr><th>Case</th><th>Rain</th><th>Net evaporation</th><th>Net horizontal import</th><th>Vapor change</th><th>Soil change</th></tr></thead><tbody>'+water_rows+'</tbody></table></div><p>Rain = evaporation + net import − vapor storage change. These are conserved-store model identities, not observed evaporation or independent water-origin tracers. They diagnose moisture delivery and reliance on the initial surface store; they do not uniquely identify the cause or establish bistability.</p>'
    section=f'''<!--regional-rainfall-results-start--><section aria-labelledby="regional-rainfall-results-h"><h2 id="regional-rainfall-results-h">Complete-month rainfall results</h2><p>{len(complete)} of7 candidate months are complete and saved-state budget-qualified. These are conditional regional development tests using simulated initial/lateral states, with observed WorldClim monthly normals reserved for scoring.</p><p><strong>{pooled}</strong></p><p>{bound_note}</p><p>{" ".join(comparison_notes)}</p>{figures}<div class="table"><table><caption>All available complete months; rates and MAE in mm/day</caption><thead><tr><th>Region</th><th>Profile</th><th>Observed</th><th>Model</th><th>MAE</th><th>Bias</th></tr></thead><tbody>{''.join(rows)}</tbody></table></div>{water_table}<p>A14-day prelude is not assumed to remove initial soil-water memory. Both initializations are reported separately. Mexico wet450s is a separate numerical sensitivity control, excluded from the six-case primary objective. Conservation and completed integration are numerical qualifications, not claims of rainfall skill. This does not adopt new physics or change the normal atlas climates.</p><p><a href="data/regional_rainfall_results.json">Protocol, all available scores, geographic attributions and daily budget checks</a> · <a href="data/regional_rainfall_results_fields.npz">Saved evaluation fields</a> · <a href="../../reports/REGIONAL_RAINFALL_RESULTS_20261029.md">Results and limitations</a></p></section><!--regional-rainfall-results-end-->'''
    page=ROOT/'atlases/climate_accuracy/index.html';text=page.read_text();start,end='<!--regional-rainfall-results-start-->','<!--regional-rainfall-results-end-->'
    if start in text:before,tail=text.split(start,1);_,after=tail.split(end,1);text=before+section+after
    else:text=text.replace('<!--research-list-start-->',section+'\n<!--research-list-start-->',1)
    page.write_text(text)
    report='# Regional complete-month rainfall results\n\n'+pooled+'\n\n'+'\n\n'.join(comparison_notes)+'\n\n'+bound_note+'\n\n'+f'{len(complete)} of7 candidate months are complete. All complete fields are scored; no incomplete-month loss is substituted.\n\n'
    report+='| Region | Profile | Observed | Model | MAE | Bias |\n|---|---|---:|---:|---:|---:|\n'
    for row in table:
        values=[row['region'],row['profile']]+['pending' if row[k] is None else f'{row[k]:.4f}' for k in ['observed_mean_mm_day','mean_mm_day','mae_mm_day','bias_mm_day']];report+='| '+' | '.join(values)+' |\n'
    report+='\nThe primary objective and masks were committed before prediction. Scores are area-weighted per case, then averaged equally across three regions and two initializations. Mexico wet450s is excluded from that primary mean. Geographic bins, wet/dry differences, numerical sensitivity and cold-liquid diagnostics are retained in the downloadable JSON.\n\nThe reference controls exactly reproduce archived r39 monthly float32 fields and pass strict checks. Raw annual r39 output is reaggregated by Gregorian overlap; observed normals and all model predictions use identical centered224-km footprints.\n\nThese are reused summer region/month pairs under fixed simulated lateral reservoirs, not independent global forecasts, held-out tests or annual validation. Flat terrain, missing nonlinear momentum, liquid-only physics and a partial380-hPa atmosphere remain limitations. No calibration or physics adoption. Checkpoint continuation after an environment interruption retained the daily prefix and independently reproduced a complete subsequent day byte exactly for both India branches. Original per-step histories before interruption were not flushed and are not fabricated.\n'
    report+='\nComplete-month modeled water identities on the frozen footprints, all rates mm/day. These are inferred model stores/fluxes, not observed evaporation or water-origin tracers. P=E+net import−vapor storage change.\n\n| Case | Rain | Net evaporation | Net import | Vapor change | Soil change |\n|---|---:|---:|---:|---:|---:|\n'
    for name,r in a['trials'].items():
        b=r.get('monthly_column_water_budget')
        if b and r['primary']:report+='| '+name+' | '+' | '.join(f'{b[k]:.5f}' for k in ['rain_mm_day','net_evaporation_mm_day','net_horizontal_water_import_mm_day','vapor_storage_change_mm_day','surface_storage_change_mm_day'])+' |\n'
    (ROOT/'reports/REGIONAL_RAINFALL_RESULTS_20261029.md').write_text(report)
    print(json.dumps(dict(complete=list(complete),primary=a['primary']),indent=2))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args();publish(a.source,a.out)
