"""Publish a verified completed tradeoff search, without adopting any climate."""
from pathlib import Path
import argparse,html,json,shutil,sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT));sys.path.insert(0,str(ROOT/'scripts'))
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from PIL import Image
from local_benchmark_protocol import file_hash,identity,write_json
from tradeoff_search import evaluate,pareto_names
from plot_tradeoff_progress import plot


def portable_record(row):
    """Keep all skill metrics, numerical summaries and compact invariant steps."""
    def summaries(value):
        if isinstance(value,dict):return {k:summaries(v) for k,v in value.items() if k!='steps'}
        if isinstance(value,list):return [summaries(v) for v in value]
        return value
    result={k:v for k,v in row.items() if k!='numerics'}
    if 'numerics' not in row:return result
    result['numerics']=summaries(row['numerics'])
    water=row['numerics'].get('moisture_reservoirs',{}).get('steps',[])
    branches=row['numerics'].get('two_layer_transport',{}).get('steps',[])
    if water:
        steps=[]
        for w,b in zip(water,branches,strict=True):
            if w['day']!=b['day']:raise ValueError('Unpaired invariant step times')
            steps.append({**{k:w[k] for k in ['day','all_layer_checks_passed','max_scaled_layer_residual','max_scaled_column_residual','max_scaled_dry_column_residual','maximum_internal_precipitation_transfer_residual_mm_day','partition_temperature_profile','partition_lapse_k_km','rain_scheme']},
                **{k:v for k,v in w.items() if k.startswith(('ocean_','minimum_ocean_','maximum_ocean_'))},
                **{k:b[k] for k in ['maximum_branch_speed_ms','p95_branch_speed_ms']}})
        result['numerics']['invariant_steps']=steps
    return result


def plot_wind_interaction(out,p,progress,review,target):
    """Paired wind curves, with the original 7.5m/s anchors clearly archived."""
    interaction=p['wind_interaction'];parent=ROOT/interaction['parent']
    old=json.loads((parent/'review.json').read_text())
    rows={(r['name'],r['region']):r for r in progress['records']}
    fig,axes=plt.subplots(2,2,figsize=(13,9),constrained_layout=True)
    for basin,anchor in enumerate(interaction['anchors']):
        color=plt.get_cmap('tab10')(basin);points=[]
        oldrow=json.loads((parent/anchor/'pacific_nw.json').read_text())
        points.append((oldrow['params']['westerly_speed'],old['scores'][anchor],oldrow,True))
        for item in interaction['grid']:
            if item['parent_profile']!=anchor:continue
            n=item['name'];s=review['scores'][n]
            if s.get('physical_admissible'):points.append((item['westerly_speed'],s,rows[n,'pacific_nw'],False))
        points.sort(key=lambda x:x[0])
        ys=[[x[1]['objective'] for x in points],[x[1]['mean_rain_ratio'] for x in points],
            [x[2]['extra_circulation']['scores']['q925_300']['ocean']['vector_rmse_ms'] for x in points],
            [sum(x[2]['monthly_rain']['simulated']) for x in points]]
        for ax,values in zip(axes.flat,ys):
            ax.plot([x[0] for x in points],values,'o-',color=color,label=f'Rain setting {basin+1}: {anchor}')
            for i,x in enumerate(points):
                if x[3]:ax.scatter([x[0]],[values[i]],marker='D',color=color,edgecolors='black',s=80,zorder=4)
    obs=sum(rows['reference','pacific_nw']['monthly_rain']['observed'])
    axes[0,1].axhline(1,color='#555',ls=':',label='r39 rain-error ratio')
    axes[1,1].axhline(obs,color='#555',ls=':',label='Observed regional rainfall')
    titles=['Penalized research objective','Mean regional rain error / r39','PNW native ocean wind-vector RMSE','PNW full-score annual rainfall']
    units=['Objective · lower is better','Normalized error · lower is better','m/s · lower is better','mm/year']
    for ax,title,unit in zip(axes.flat,titles,units):
        ax.set(title=title,xlabel='Shared background westerly amplitude (m/s)',ylabel=unit,xticks=[4.5,6,7.5,8.5]);ax.grid(alpha=.15);ax.legend(frameon=False,fontsize=7)
    fig.suptitle('Wind/rain interactions · fixed paired bracket at separated rain settings',fontsize=16)
    fig.supxlabel('Circles are fresh wind experiments; black-edged diamonds are archived 7.5m/s anchors (no new integration).\nAll other coefficients at each rain setting stay fixed. These are reused development regions; no global-optimum or adoption claim.',fontsize=9)
    fig.savefig(target,dpi=145);plt.close(fig)


def plot_drying_ablation(out,p,progress,review,target):
    ablation=p['drying_ablation'];parent=ROOT/ablation['parent']
    old=json.loads((parent/'review.json').read_text())
    rows={(r['name'],r['region']):r for r in progress['records']}
    fig,axes=plt.subplots(2,2,figsize=(13,9),constrained_layout=True)
    variants=['retained','subsidence_off','monsoon_off','both_off']
    count=len(ablation['anchors']);width=.8/count
    for index,anchor in enumerate(ablation['anchors']):
        cases=[(old['scores'][anchor],json.loads((parent/anchor/'pacific_nw.json').read_text()),
                json.loads((parent/anchor/'north_india.json').read_text()))]
        for variant in variants[1:]:
            name=next(g['name'] for g in ablation['grid'] if g['parent_profile']==anchor and g['variant']==variant)
            score=review['scores'][name]
            cases.append((score,rows[name,'pacific_nw'],rows[name,'north_india']))
        values=[[c[0].get('objective',float('nan')) for c in cases],
                [c[0].get('mean_rain_ratio',float('nan')) for c in cases],
                [sum(c[1]['monthly_rain']['simulated']) if c[1]['status']=='passed' else float('nan') for c in cases],
                [sum(c[2]['monthly_rain']['simulated']) if c[2]['status']=='passed' else float('nan') for c in cases]]
        for ax,y in zip(axes.flat,values):
            bars=ax.bar(np.arange(4)+(index-(count-1)/2)*width,y,width=width,label=f'Anchor {index+1}: {anchor}')
            bars[0].set_hatch('//');bars[0].set_edgecolor('black')
    axes[0,1].axhline(1,color='#555',ls=':',label='r39 rain-error ratio')
    for ax,region in [(axes[1,0],'pacific_nw'),(axes[1,1],'north_india')]:
        ax.axhline(sum(rows['reference',region]['monthly_rain']['observed']),color='#555',ls=':',label='Observed rainfall')
    for ax,title,unit in zip(axes.flat,['Penalized research objective','Mean regional rain error / r39',
            'PNW full-score annual rainfall','North India full-score annual rainfall'],['Objective','Normalized error','mm/year','mm/year']):
        ax.set(title=title,ylabel=unit,xticks=range(4),xticklabels=['Retained','Subsidence off','Monsoon off','Both off'])
        ax.legend(frameon=False,fontsize=8);ax.grid(axis='y',alpha=.15)
    fig.suptitle('Do legacy column sinks overlap explicit donor transport?',fontsize=16)
    fig.supxlabel('Hatched bars are archived parent anchors; other bars are fresh paired ablations. Planet and other coefficients stay fixed.\n'
                  'Whole-column removal is tested separately for each closure and jointly; changed rainfall does not by itself prove double counting.\n'
                  'Development-region ablation, not independent validation, global optimization or an adopted climate.',fontsize=9)
    fig.savefig(target,dpi=145);plt.close(fig)


def plot_ocean_pilot(out,p,progress,review,target):
    rows={(r['name'],r['region']):r for r in progress['records']}
    fig,axes=plt.subplots(2,2,figsize=(13,9),constrained_layout=True)
    modes=['legacy','hydrostatic_uniform','hydrostatic_half']
    for index,wind in enumerate([4.5,3.5]):
        names=[next(g['name'] for g in p['ocean_profile_pilot']['grid'] if g['westerly_speed']==wind and g['mode']==mode) for mode in modes]
        values=[[review['scores'][n].get('objective',float('nan')) for n in names],
                [review['scores'][n].get('mean_rain_ratio',float('nan')) for n in names]]
        for region in ['north_india','pacific_nw']:
            values.append([sum(rows[n,region]['monthly_rain']['simulated']) if rows[n,region]['status']=='passed' else float('nan') for n in names])
        for ax,y in zip(axes.flat,values):
            positions=np.arange(3)+(index-.5)*.38
            ax.bar(positions,y,width=.38,label=f'Background wind {wind:g} m/s')
            for x,value in zip(positions,y):
                if not np.isfinite(value):ax.text(x,0,'FAIL',ha='center',fontsize=8,color='#a22')
    axes[0,1].axhline(1,color='#555',ls=':',label='r39 rain-error ratio')
    for ax,region in [(axes[1,0],'north_india'),(axes[1,1],'pacific_nw')]:
        ax.axhline(sum(rows['reference',region]['monthly_rain']['observed']),color='#555',ls=':',label='Observed rainfall')
    for ax,title,unit in zip(axes.flat,['Penalized research objective','Mean regional rain error / r39','North India full-score annual rain','PNW full-score annual rain'],['Objective','Normalized error','mm/year','mm/year']):
        ax.set(title=title,ylabel=unit,xticks=range(3),xticklabels=['Legacy target','Hydrostatic uniform','Hydrostatic half taper']);ax.legend(frameon=False,fontsize=8);ax.grid(axis='y',alpha=.15)
    fig.suptitle('Ocean water amount and RH shape · fixed coupled pilot',fontsize=16)
    fig.supxlabel('All bars are fresh integrations. Hydrostatic uniform isolates a changed total-water law; half taper also changes vertical RH and total water.\n'
        'Actual surface-RH coefficient and other physics stay fixed; independently solved interior humidity is never reset.\n'
        'Matched legacy control, explicit source transition, same numerical/skill policy and fixed Earth properties; no automatic adoption.',fontsize=9)
    fig.savefig(target,dpi=145);plt.close(fig)


def verified(out):
    protocol=json.loads((out/'protocol.json').read_text());progress=json.loads((out/'progress.json').read_text());review=json.loads((out/'review.json').read_text())
    run_id=identity(protocol);p=protocol['plan'];rows=progress['records']
    if not review['complete'] or not progress['complete'] or review['identity']!=run_id or progress['identity']!=run_id or review['physics_or_atlas_adoption'] is not False:
        raise ValueError('Need completed frozen research search')
    for name,sha in protocol['sources'].items():
        if file_hash(ROOT/name)!=sha:raise ValueError('Scientific source changed: '+name)
    if len(rows)!=review['actual_integrations'] or len({(r['name'],r['region']) for r in rows})!=len(rows):raise ValueError('Missing/duplicate actual integrations')
    for row in rows:
        path=out/row['name']/(row['region']+'.json');raw=path.with_suffix('.npz')
        if row!=json.loads(path.read_text()) or row['identity']!=run_id:raise ValueError('Changed raw row identity')
        if row['status']=='passed':
            if file_hash(raw)!=row['arrays_sha256']:raise ValueError('Changed main raw climate packet')
            if row['region'] in p['extra_circulation_regions']:
                if file_hash(path.with_name(row['region']+'_extra.npz'))!=row['extra_circulation_arrays_sha256']:raise ValueError('Changed native companion')
        if row['name'] in p['control_names']:
            if row['status']!='passed' or row.get('physical_control_exact') is not True:raise ValueError('Control failed')
            with np.load(raw) as a,np.load(ROOT/p['profile_control_archives'][row['name']]/raw.name) as b:
                if set(a.files)!=set(b.files) or any(not np.array_equal(a[k],b[k],equal_nan=True) for k in a.files):raise ValueError('Historical control is not exact')
    evaluator=evaluate
    if 'ocean_profile_pilot' in p:
        from ocean_profile_pilot import evaluate_ocean
        evaluator=evaluate_ocean
    for name,score in review['scores'].items():
        if evaluator(name,rows,p)!=score:raise ValueError('Changed score or physical certificate: '+name)
    if pareto_names(review['scores'])!=review['pareto_front']:raise ValueError('Changed tradeoff frontier')
    return protocol,progress,review


def publish(out):
    protocol,progress,review=verified(out);p=protocol['plan'];data=ROOT/'atlases/climate_accuracy/data'
    wind='wind_interaction' in p;ablation='drying_ablation' in p;ocean='ocean_profile_pilot' in p
    stem=p.get('publication_stem','global_rain');slug=stem.replace('_','-')
    title=p.get('publication_title','Wind and rain-setting interactions' if wind else 'Broader rainfall search and regional tradeoffs')
    verification=json.loads((out/'scientific_verification.json').read_text())
    if (verification.get('status')!='passed' or verification.get('identity')!=identity(protocol)
            or verification.get('review_sha256')!=file_hash(out/'review.json')
            or verification.get('protocol_sha256')!=file_hash(out/'protocol.json')):
        raise ValueError('Need matching independent scientific verification before publication')
    coverage=data/f'{stem}_coverage.png'
    if ocean:plot_ocean_pilot(out,p,progress,review,coverage)
    elif ablation:plot_drying_ablation(out,p,progress,review,coverage)
    elif wind:plot_wind_interaction(out,p,progress,review,coverage)
    else:plot(out,coverage)
    names=list(review['scores']);regions=p['regions'];ref={r['region']:r for r in progress['records'] if r['name']=='reference'}
    rows={(r['name'],r['region']):r for r in progress['records']}
    matrix=np.full((len(regions),len(names)),np.nan)
    for j,name in enumerate(names):
        for i,region in enumerate(regions):
            row=rows[name,region];base=ref[region]
            if row['status']=='passed':matrix[i,j]=.5*(row['rain']['loss']/base['rain']['loss']+row['temperature']['monthly_mae_C']/base['temperature']['monthly_mae_C'])
    fig,ax=plt.subplots(figsize=(max(13,len(names)*.3),5.7),constrained_layout=True)
    limit=max(.1,float(np.nanmax(abs(np.log10(matrix)))))
    im=ax.imshow(np.log10(matrix),cmap='RdBu_r',vmin=-limit,vmax=limit,aspect='auto')
    for i,j in np.ndindex(matrix.shape):ax.text(j,i,'FAIL' if not np.isfinite(matrix[i,j]) else f'{matrix[i,j]:.2f}',ha='center',va='center',fontsize=5)
    ax.set(xticks=range(len(names)),xticklabels=[n.replace('global','g').replace('local','l') for n in names],yticks=range(len(regions)),yticklabels=[r.replace('_',' ').title() for r in regions],title='Every completed candidate · regional combined error / r39')
    ax.tick_params(axis='x',rotation=90,labelsize=7);fig.colorbar(im,ax=ax,label='Log10 combined error ratio · lower is better')
    trial_scope='Global exploration and adaptive local proposals' if p['design']['local_poll_order'] else 'Fixed paired experiments; no local refinement'
    fig.supxlabel(trial_scope+'; all failures and regional regressions retained. These are reused development regions, not validation.\nNative humidity/wind and sea-state errors remain separate objective terms and downloadable diagnostics.',fontsize=9)
    errors=data/f'{stem}_regions.png';fig.savefig(errors,dpi=165);plt.close(fig)
    score_rows=[]
    for name,s in review['scores'].items():
        if not s.get('physical_admissible'):
            score_rows.append(f'<tr><td>{html.escape(name)}</td><td colspan="5">Physical/numerical rejection: {html.escape("; ".join(s["failures"]))}</td></tr>');continue
        score_rows.append(f'<tr><td>{name}</td><td>{s["objective"]:.4f}</td><td>{s["mean_rain_ratio"]:.4f}</td><td>{s["mean_temperature_ratio"]:.4f}</td><td>{s["worst_regional_combined_ratio"]:.4f}</td><td>{"Yes" if s["validation_ready"] else "No"}</td></tr>')
    pictures=[coverage,errors];sensitivity=None
    sensitivity_path=out/'ranking_sensitivity.json'
    if sensitivity_path.exists():
        sensitivity=json.loads(sensitivity_path.read_text());source_image=out/'ranking_sensitivity.png'
        if (sensitivity['review_sha256']!=file_hash(out/'review.json')
                or sensitivity['protocol_sha256']!=file_hash(out/'protocol.json')
                or sensitivity['new_earth_integrations']!=0
                or sensitivity['image_sha256']!=file_hash(source_image)):
            raise ValueError('Changed post-search sensitivity diagnostic')
        target=data/f'{stem}_sensitivity.png';shutil.copyfile(source_image,target);pictures.append(target)
    basins=verification['local_basin_diagnostics']
    water=None;water_path=out/'water_tradeoffs.json'
    if water_path.exists():
        water=json.loads(water_path.read_text());source_image=out/'water_tradeoffs.png'
        if (water['review_sha256']!=file_hash(out/'review.json') or water['protocol_sha256']!=file_hash(out/'protocol.json')
                or water['image_sha256']!=file_hash(source_image) or water['new_earth_integrations']!=0):raise ValueError('Changed water-equation diagnostic')
        for key,sha in water['raw_arrays_sha256'].items():
            name,region=key.split('/')
            if file_hash(out/name/(region+'.npz'))!=sha:raise ValueError('Changed diagnostic raw climate')
        target=data/f'{stem}_water.png';shutil.copyfile(source_image,target);pictures.append(target)
    seasons=None;seasons_path=out/'rainfall_seasons.json'
    if seasons_path.exists():
        seasons=json.loads(seasons_path.read_text());source_image=out/'rainfall_seasons.png'
        if (seasons['review_sha256']!=file_hash(out/'review.json') or seasons['protocol_sha256']!=file_hash(out/'protocol.json')
                or seasons['image_sha256']!=file_hash(source_image) or seasons['new_earth_integrations']!=0):raise ValueError('Changed seasonal rainfall diagnostic')
        for key,sha in seasons['row_sha256'].items():
            name,region=key.split('/')
            if file_hash(out/name/(region+'.json'))!=sha:raise ValueError('Changed seasonal rainfall source')
        target=data/f'{stem}_seasons.png';shutil.copyfile(source_image,target);pictures.append(target)
    humidity=None;humidity_path=out/'humidity_seasons.json'
    if humidity_path.exists():
        humidity=json.loads(humidity_path.read_text());source_image=out/'humidity_seasons.png'
        if (humidity['review_sha256']!=file_hash(out/'review.json') or humidity['protocol_sha256']!=file_hash(out/'protocol.json')
                or humidity['image_sha256']!=file_hash(source_image) or humidity['new_earth_integrations']!=0):raise ValueError('Changed native humidity diagnostic')
        for key,sha in humidity['row_sha256'].items():
            name,region=key.split('/')
            if file_hash(out/name/(region+'.json'))!=sha:raise ValueError('Changed native humidity source')
        target=data/f'{stem}_humidity.png';shutil.copyfile(source_image,target);pictures.append(target)
    source_hashes={r['name']+'/'+r['region']:file_hash(out/r['name']/(r['region']+'.json')) for r in progress['records']}
    background_scope=None;scope_path=out/'background_input_scope.json'
    if scope_path.exists():
        background_scope=json.loads(scope_path.read_text())
        if background_scope.get('literal_plan_unchanged') is not True or background_scope.get('actual_inputs_or_parameters_changed') is not False or background_scope.get('climate_integrations_added')!=0:raise ValueError('Unexpected background-input scope note')
    metadata=dict(review,plan=p,records=[portable_record(r) for r in progress['records']],source_record_sha256=source_hashes,
        background_input_scope=background_scope,
        portable_record_scope='All prediction metrics and parameters; numerical summaries and compact per-step invariant checks. Full original runtime diagnostics remain in the hashed source-output JSON rows.',
        history=progress['history'],ranking_sensitivity=sensitivity,water_equation_diagnostic=water,rainfall_seasons=seasons,native_humidity_seasons=humidity,local_basin_diagnostics=basins,
        scientific_verification_sha256=file_hash(out/'scientific_verification.json'),
        source_transition=protocol.get('source_transition'),reference_refresh=protocol.get('reference_refresh'),
        declaration_metadata_issues=verification.get('declaration_metadata_issues',[]),
        source_protocol_sha256=file_hash(out/'protocol.json'),review_sha256=file_hash(out/'review.json'),
        publisher_sha256=file_hash(Path(__file__)),images_sha256={x.name:file_hash(x) for x in pictures},
        old_policy_scope='Earlier strict regional acceptance rules and outcomes remain unchanged. This is a different prospective research objective.')
    write_json(data/f'{stem}.json',metadata)
    figures=''
    for picture in pictures:
        alt=('Native seasonal partial-column water and upper-to-lower humidity shape on the original scored footprints' if '_humidity' in picture.name else
             'Monthly regional rainfall on the complete scored masks, compared with observations and previous controls' if '_seasons' in picture.name else
             'Signed water-equation comparisons for declared objective, mean-climate and native-error selections' if '_water' in picture.name else
             'Ranking sensitivity to alternative weights and omitted development regions' if 'sensitivity' in picture.name else
             ('Paired hydrostatic ocean-target laws, winds and coupled rainfall comparisons' if ocean else
              'Paired legacy-drying ablations and archived parent rainfall and score comparisons' if ablation else
              'Wind-amplitude interactions with separated parent rain settings' if wind else
              'Actual parameter coverage, separated global and local trials, and error progress') if picture==coverage else
             'Regional combined errors for every completed global and local candidate')
        with Image.open(picture) as image:w,h=image.size
        figures+=f'<figure><a href="data/{picture.name}"><img src="data/{picture.name}" width="{w}" height="{h}" loading="lazy" alt="{alt}"></a></figure>\n'
    design_text=('The paired design switches off subsidence drying, monsoon drying, and both, at up to two separated retained wind/rain settings. Explicit conservative donor transport stays active. Parent anchors are archived comparisons, not new integrations. This tests a possible overlap, without assuming that removing a closure corrects the physics. No local refinement follows.' if ablation else
        'The paired design tests three shared background westerly amplitudes (4.5, 6.0 and 8.5 m/s) at up to three separated rain settings selected from the completed parent search. Original 7.5 m/s results are archived comparisons, not additional integrations. No local refinement follows this bracket.' if wind else
        'The frozen design covers 32 scrambled Sobol points over wider shared storm/rain-timescale/convective-RH ranges, then up to three separated starts with six bounded coordinate proposals each. Exact duplicate proposals reuse records.')
    design_text=p.get('publication_design_text',design_text)
    metadata_note=('<p class="note">The original declaration retains an anchor-selection bounds metadata error from a shallow copy. The literal trial grid was frozen before execution; verification reconstructs selection in the committed parent space. Runs, parameters and scores are unchanged. See the report and downloadable verification notes.</p>'
                   if verification.get('declaration_metadata_issues') else '')
    if background_scope:
        metadata_note+='<p class="note">The inherited regional setup retains observation-derived latitude/month cloud and remote monsoon-descent backgrounds, fixed across these comparisons. The new ocean target uses modeled SST and prescribed RH, without observed profile forcing. These are conditional regional tests, not independent global forecasts; the original declaration and inputs remain unchanged.</p>'
    if ocean:
        diagnosis=ROOT/'output/rainfall_diagnosis_20261028/archived_budgets.json'
        if diagnosis.exists():
            diagnostic=json.loads(diagnosis.read_text())
            if (diagnostic['source_protocol_sha256']!=file_hash(out/'protocol.json') or diagnostic['source_review_sha256']!=file_hash(out/'review.json')
                    or diagnostic['new_earth_integrations']!=0 or diagnostic['new_fit'] is not False):raise ValueError('Changed exploratory rainfall diagnosis')
            for key,hashes in diagnostic['source_records'].items():
                name,region=key.split('/')
                if file_hash(out/name/(region+'.json'))!=hashes['row_sha256'] or file_hash(out/name/(region+'.npz'))!=hashes['arrays_sha256']:raise ValueError('Changed exploratory water-budget input')
            shutil.copyfile(diagnosis,data/'ocean_profile_diagnosis.json')
            metadata_note+='<p>The next milestone diagnoses seasonal transport in North India, Mexico and PNW before another broad parameter search. <a href="../../reports/RAINFALL_RECOVERY_PLAN_20261028.md">Rainfall recovery plan</a> · <a href="data/ocean_profile_diagnosis.json" download>Download exploratory seasonal water budgets</a>. These archived budgets add zero model runs and do not change acceptance decisions.</p>'
    section=f'''<!--{slug}-start--><section aria-labelledby="{slug}-h"><h2 id="{slug}-h">{title}</h2>
<p>New research policy: numerical conservation, paired inputs, fixed Earth settings and declared actual parameters remain hard requirements. Rainfall, temperature, humidity, wind and sea-state prediction errors are explicit objectives. Modest regional regressions can accompany an average improvement; no individual prediction-error veto prunes the optimization path. Earlier acceptance decisions remain unchanged.</p>
<p>{design_text} {review['actual_integrations']} actual integrations completed, {review['strictly_passed']} passed numerics and {review['failed_integrations']} failed. All 28 historical controls reproduce their saved fields exactly. This finite search does not certify a global optimum.</p>
{metadata_note}
{figures}<div class="table"><table><caption>All research candidates; objective includes explicit regret penalties</caption><thead><tr><th>Trial</th><th>Objective</th><th>Mean rain / r39</th><th>Mean T / r39</th><th>Worst region / r39</th><th>Broader-validation shortlist eligible</th></tr></thead><tbody>{''.join(score_rows)}</tbody></table></div>
<p>Non-dominated research candidates: {html.escape(', '.join(review['pareto_front']))}. At most two candidates may enter separately frozen broader validation: {html.escape(', '.join(review['validation_shortlist']) or 'none')}. A shortlist is not an adopted fit. No normal climate, foraging, farming, population packet or measured accuracy headline is replaced.</p>
<p class="note">Means use equal-region normalized errors. Reference-error floors are declared normalization choices, not measured observational uncertainties. Seven reused regions and small coastal samples cannot establish global skill. The prescribed environmental profile does not solve atmospheric radiation or latent-energy feedback.</p>
<p><a href="data/{stem}.json" download>Download complete {title.lower()}, tradeoffs, certificates and parameter histories</a> · <a href="../../reports/{stem.upper()}_20261028.md">Design, objective and limitations</a></p></section><!--{slug}-end-->'''
    page=ROOT/'atlases/climate_accuracy/index.html';text=page.read_text();start=f'<!--{slug}-start-->';end=f'<!--{slug}-end-->'
    if start in text:
        before,tail=text.split(start,1);_,after=tail.split(end,1);text=before+section+after
    else:
        anchor=('<!--'+p['previous_study_slug']+'-start-->') if 'previous_study_slug' in p else '<!--wind-interaction-start-->' if ablation else '<!--global-rain-start-->' if wind else '<!--joint-rain-start-->'
        if text.count(anchor)!=1:raise ValueError('Need unique preceding study')
        text=text.replace(anchor,section+'\n'+anchor)
    page.write_text(text)
    write_json(out/'publication.json',dict(status='published_research_only',page_sha256=file_hash(page),metadata_sha256=file_hash(data/f'{stem}.json'),publisher_sha256=file_hash(Path(__file__)),physics_or_atlas_adoption=False))


if __name__=='__main__':
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--out',type=Path,required=True);publish(ap.parse_args().out.resolve())
