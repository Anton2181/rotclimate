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
    coverage=data/'global_rain_coverage.png';plot(out,coverage)
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
    errors=data/'global_rain_regions.png';fig.savefig(errors,dpi=165);plt.close(fig)
    score_rows=[]
    for name,s in review['scores'].items():
        if not s.get('physical_admissible'):
            score_rows.append(f'<tr><td>{html.escape(name)}</td><td colspan="5">Physical/numerical rejection: {html.escape("; ".join(s["failures"]))}</td></tr>');continue
        score_rows.append(f'<tr><td>{name}</td><td>{s["objective"]:.4f}</td><td>{s["mean_rain_ratio"]:.4f}</td><td>{s["mean_temperature_ratio"]:.4f}</td><td>{s["worst_regional_combined_ratio"]:.4f}</td><td>{"Yes" if s["validation_ready"] else "No"}</td></tr>')
    metadata=dict(review,plan=p,records=progress['records'],history=progress['history'],
        source_protocol_sha256=file_hash(out/'protocol.json'),review_sha256=file_hash(out/'review.json'),
        publisher_sha256=file_hash(Path(__file__)),images_sha256={x.name:file_hash(x) for x in [coverage,errors]},
        old_policy_scope='Earlier strict regional acceptance rules and outcomes remain unchanged. This is a different prospective research objective.')
    write_json(data/'global_rain.json',metadata)
    figures=''
    for picture,alt in [(coverage,'Actual parameter coverage, separated global and local trials, and error progress'),(errors,'Regional combined errors for every completed global and local candidate')]:
        with Image.open(picture) as image:w,h=image.size
        figures+=f'<figure><a href="data/{picture.name}"><img src="data/{picture.name}" width="{w}" height="{h}" loading="lazy" alt="{alt}"></a></figure>\n'
    section=f'''<!--global-rain-start--><section aria-labelledby="global-rain-h"><h2 id="global-rain-h">Broader rainfall search and regional tradeoffs</h2>
<p>New research policy: numerical conservation, paired inputs, fixed Earth settings and declared actual parameters remain hard requirements. Rainfall, temperature, humidity, wind and sea-state prediction errors are explicit objectives. Modest regional regressions can accompany an average improvement; no individual prediction-error veto prunes the optimization path. Earlier acceptance decisions remain unchanged.</p>
<p>The frozen design covers 32 scrambled Sobol points over wider shared storm/rain-timescale/convective-RH ranges, then up to three separated starts with six bounded coordinate proposals each. Exact duplicate proposals reuse records. {review['actual_integrations']} actual integrations completed, {review['strictly_passed']} passed numerics and {review['failed_integrations']} failed. All 28 historical controls reproduce their saved fields exactly. This finite search does not certify a global optimum.</p>
{figures}<div class="table"><table><caption>All research candidates; objective includes explicit regret penalties</caption><thead><tr><th>Trial</th><th>Objective</th><th>Mean rain / r39</th><th>Mean T / r39</th><th>Worst region / r39</th><th>Broader-validation shortlist eligible</th></tr></thead><tbody>{''.join(score_rows)}</tbody></table></div>
<p>Non-dominated research candidates: {html.escape(', '.join(review['pareto_front']))}. At most two candidates may enter separately frozen broader validation: {html.escape(', '.join(review['validation_shortlist']) or 'none')}. A shortlist is not an adopted fit. No normal climate, foraging, farming, population packet or measured accuracy headline is replaced.</p>
<p class="note">Means use equal-region normalized errors. Reference-error floors are declared normalization choices, not measured observational uncertainties. Seven reused regions and small coastal samples cannot establish global skill. The prescribed environmental profile does not solve atmospheric radiation or latent-energy feedback.</p>
<p><a href="data/global_rain.json" download>Download complete search, tradeoffs, certificates and parameter histories</a> · <a href="../../reports/GLOBAL_RAIN_20261028.md">Design, objective and limitations</a></p></section><!--global-rain-end-->'''
    page=ROOT/'atlases/climate_accuracy/index.html';text=page.read_text();start='<!--global-rain-start-->';end='<!--global-rain-end-->'
    if start in text:
        before,tail=text.split(start,1);_,after=tail.split(end,1);text=before+section+after
    else:
        anchor='<!--joint-rain-start-->'
        if text.count(anchor)!=1:raise ValueError('Need unique preceding study')
        text=text.replace(anchor,section+'\n'+anchor)
    page.write_text(text)
    write_json(out/'publication.json',dict(status='published_research_only',page_sha256=file_hash(page),metadata_sha256=file_hash(data/'global_rain.json'),publisher_sha256=file_hash(Path(__file__)),physics_or_atlas_adoption=False))


if __name__=='__main__':
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--out',type=Path,required=True);publish(ap.parse_args().out.resolve())
