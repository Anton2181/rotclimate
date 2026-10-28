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
    for name,score in review['scores'].items():
        if evaluate(name,rows,p)!=score:raise ValueError('Changed score or physical certificate: '+name)
    if pareto_names(review['scores'])!=review['pareto_front']:raise ValueError('Changed tradeoff frontier')
    return protocol,progress,review


def publish(out):
    protocol,progress,review=verified(out);p=protocol['plan'];data=ROOT/'atlases/climate_accuracy/data'
    wind='wind_interaction' in p;stem='wind_interaction' if wind else 'global_rain';slug=stem.replace('_','-')
    title='Wind and rain-setting interactions' if wind else 'Broader rainfall search and regional tradeoffs'
    verification=json.loads((out/'scientific_verification.json').read_text())
    if (verification.get('status')!='passed' or verification.get('identity')!=identity(protocol)
            or verification.get('review_sha256')!=file_hash(out/'review.json')
            or verification.get('protocol_sha256')!=file_hash(out/'protocol.json')):
        raise ValueError('Need matching independent scientific verification before publication')
    coverage=data/f'{stem}_coverage.png'
    if wind:plot_wind_interaction(out,p,progress,review,coverage)
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
    fig.supxlabel('Global exploration and adaptive local proposals; all failures and regional regressions retained. These are reused development regions, not validation.\nNative humidity/wind and sea-state errors remain separate objective terms and downloadable diagnostics.',fontsize=9)
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
    source_hashes={r['name']+'/'+r['region']:file_hash(out/r['name']/(r['region']+'.json')) for r in progress['records']}
    metadata=dict(review,plan=p,records=[portable_record(r) for r in progress['records']],source_record_sha256=source_hashes,
        portable_record_scope='All prediction metrics and parameters; numerical summaries and compact per-step invariant checks. Full original runtime diagnostics remain in the hashed source-output JSON rows.',
        history=progress['history'],ranking_sensitivity=sensitivity,water_equation_diagnostic=water,local_basin_diagnostics=basins,
        scientific_verification_sha256=file_hash(out/'scientific_verification.json'),
        source_protocol_sha256=file_hash(out/'protocol.json'),review_sha256=file_hash(out/'review.json'),
        publisher_sha256=file_hash(Path(__file__)),images_sha256={x.name:file_hash(x) for x in pictures},
        old_policy_scope='Earlier strict regional acceptance rules and outcomes remain unchanged. This is a different prospective research objective.')
    write_json(data/f'{stem}.json',metadata)
    figures=''
    for picture in pictures:
        alt=('Signed water-equation comparisons for declared objective, mean-climate and native-error selections' if '_water' in picture.name else
             'Ranking sensitivity to alternative weights and omitted development regions' if 'sensitivity' in picture.name else
             'Actual parameter coverage, separated global and local trials, and error progress' if picture==coverage else
             'Regional combined errors for every completed global and local candidate')
        with Image.open(picture) as image:w,h=image.size
        figures+=f'<figure><a href="data/{picture.name}"><img src="data/{picture.name}" width="{w}" height="{h}" loading="lazy" alt="{alt}"></a></figure>\n'
    design_text=('The paired design tests three shared background westerly amplitudes (4.5, 6.0 and 8.5 m/s) at up to three separated rain settings selected from the completed parent search. Original 7.5 m/s results are archived comparisons, not additional integrations. No local refinement follows this bracket.' if wind else
        'The frozen design covers 32 scrambled Sobol points over wider shared storm/rain-timescale/convective-RH ranges, then up to three separated starts with six bounded coordinate proposals each. Exact duplicate proposals reuse records.')
    section=f'''<!--{slug}-start--><section aria-labelledby="{slug}-h"><h2 id="{slug}-h">{title}</h2>
<p>New research policy: numerical conservation, paired inputs, fixed Earth settings and declared actual parameters remain hard requirements. Rainfall, temperature, humidity, wind and sea-state prediction errors are explicit objectives. Modest regional regressions can accompany an average improvement; no individual prediction-error veto prunes the optimization path. Earlier acceptance decisions remain unchanged.</p>
<p>{design_text} {review['actual_integrations']} actual integrations completed, {review['strictly_passed']} passed numerics and {review['failed_integrations']} failed. All 28 historical controls reproduce their saved fields exactly. This finite search does not certify a global optimum.</p>
{figures}<div class="table"><table><caption>All research candidates; objective includes explicit regret penalties</caption><thead><tr><th>Trial</th><th>Objective</th><th>Mean rain / r39</th><th>Mean T / r39</th><th>Worst region / r39</th><th>Broader-validation shortlist eligible</th></tr></thead><tbody>{''.join(score_rows)}</tbody></table></div>
<p>Non-dominated research candidates: {html.escape(', '.join(review['pareto_front']))}. At most two candidates may enter separately frozen broader validation: {html.escape(', '.join(review['validation_shortlist']) or 'none')}. A shortlist is not an adopted fit. No normal climate, foraging, farming, population packet or measured accuracy headline is replaced.</p>
<p class="note">Means use equal-region normalized errors. Reference-error floors are declared normalization choices, not measured observational uncertainties. Seven reused regions and small coastal samples cannot establish global skill. The prescribed environmental profile does not solve atmospheric radiation or latent-energy feedback.</p>
<p><a href="data/{stem}.json" download>Download complete {title.lower()}, tradeoffs, certificates and parameter histories</a> · <a href="../../reports/{stem.upper()}_20261028.md">Design, objective and limitations</a></p></section><!--{slug}-end-->'''
    page=ROOT/'atlases/climate_accuracy/index.html';text=page.read_text();start=f'<!--{slug}-start-->';end=f'<!--{slug}-end-->'
    if start in text:
        before,tail=text.split(start,1);_,after=tail.split(end,1);text=before+section+after
    else:
        anchor='<!--global-rain-start-->' if wind else '<!--joint-rain-start-->'
        if text.count(anchor)!=1:raise ValueError('Need unique preceding study')
        text=text.replace(anchor,section+'\n'+anchor)
    page.write_text(text)
    write_json(out/'publication.json',dict(status='published_research_only',page_sha256=file_hash(page),metadata_sha256=file_hash(data/f'{stem}.json'),publisher_sha256=file_hash(Path(__file__)),physics_or_atlas_adoption=False))


if __name__=='__main__':
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--out',type=Path,required=True);publish(ap.parse_args().out.resolve())
