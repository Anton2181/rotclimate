"""Publish all four completed mechanism-isolation outcomes and matched curves."""
from pathlib import Path
import html
import json
import re
import shutil
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'scripts')]
from local_benchmark_protocol import file_hash,write_json
from validate_r42_multistart import paired_score
from organize_climate_accuracy import organize


def main():
    import numpy as np
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    folder=ROOT/'output/r42_storm_factorial_20261102'
    plan=json.loads((folder/'plan.json').read_text());result=json.loads((folder/'results.json').read_text())
    reference=ROOT/plan['reference'];ref=json.loads((reference/'summary.json').read_text())
    if not ref.get('complete') or result['adoption'] or result['sealed_run']:raise ValueError('Invalid factorial scope')
    names=plan['regions'];curves={};packets={};regional={};scores={}
    for label in ['reference',*plan['profiles']]:
        base=reference if label=='reference' else folder/label
        summary=json.loads((base/'summary.json').read_text())
        if not summary.get('complete') or set(summary['regions'])!=set(names):raise ValueError('Incomplete profile')
        score=paired_score(ref['regions'],summary['regions'],names)
        if label!='reference' and score!=result['profiles'][label]['score']:raise ValueError('Changed score')
        scores[label]=score;curves[label]={};regional[label]={}
        for name in names:
            path=base/'cells'/(name+'.npz');row=summary['regions'][name]
            if file_hash(path)!=row['cells_sha256']:raise ValueError('Changed packet')
            packets[str(path.relative_to(ROOT))]=file_hash(path)
            with np.load(path) as z,np.load(reference/'cells'/(name+'.npz')) as r:
                for key in ['i','j','To','Po','lat','lon','elev','elev_max','coast_km']:
                    if not np.array_equal(z[key],r[key]):raise ValueError('Unpaired inputs')
                curves[label][name]=dict(prediction=z['Ps'].mean(1),observed=z['Po'].mean(1))
            regional[label][name]=dict(T=row['temperature']['monthly_mae_C'],P=row['rain']['loss'])
    out=ROOT/'output/storm_factorial_review_20261103';out.mkdir(exist_ok=True)
    fig,axes=plt.subplots(2,4,figsize=(16,7.5),layout='constrained')
    for ax,name in zip(axes.flat,names):
        ax.plot(range(1,13),curves['reference'][name]['observed'],'--',color='#222',lw=2,label='Observed')
        for label,title,color in [('reference','r42 control','#377ab2'),('storm_exchange_only','Conservative storms only','#24814b')]:
            ax.plot(range(1,13),curves[label][name]['prediction'],color=color,lw=2,label=title)
        ax.set_title(name.replace('_',' ').title(),loc='left',fontsize=11)
        ax.set_xticks([1,4,7,10],['Jan','Apr','Jul','Oct']);ax.set_ylabel('mm/month');ax.set_ylim(bottom=0)
        ax.grid(alpha=.2);ax.spines[['top','right']].set_visible(False)
    fig.suptitle('Conservative storm exchange alone: rain loss −4.36%, temperature error −1.06%\nEight reused development regions · unchanged strengths and strict numerical criteria',fontsize=14)
    fig.legend(*axes[0,0].get_legend_handles_labels(),loc='outside lower center',ncol=3,frameon=False)
    image=out/'storm_only_monthly.png';fig.savefig(image,dpi=135);plt.close(fig)
    review=dict(adoption=False,sealed_run=False,scores=scores,regional=regional,
        packets_sha256=packets,figure_sha256=file_hash(image),plan_sha256=file_hash(folder/'plan.json'),
        result_sha256=file_hash(folder/'results.json'),publisher_sha256=file_hash(Path(__file__)),
        scope='Four complete fixed mechanism-isolation profiles. Eight reused development regions, not unseen evidence. Full 61-region/fine/f qualification is separately declared.')
    write_json(out/'review.json',review)
    destination=ROOT/'atlases/climate_accuracy/data';shutil.copyfile(image,destination/'storm_factorial_monthly.png')
    write_json(destination/'storm_factorial.json',review)
    rows=[]
    for name in plan['profiles']:
        score=scores[name]
        rows.append(f'<tr><td>{html.escape(name.replace("_"," "))}</td><td>{score["S"]:.6f}</td><td>{100*score["T"]:+.2f}%</td><td>{100*score["P"]:+.2f}%</td></tr>')
    commit=subprocess.check_output(['git','log','-1','--format=%H','--',str((folder/'results.json').relative_to(ROOT))],cwd=ROOT,text=True).strip()
    if not commit:raise ValueError('Commit source results first')
    section=f'''<!--storm-factorial-start--><section aria-labelledby="storm-factorial-h">
<h2 id="storm-factorial-h">Isolating the mechanisms: conservative storms help on the eight-region screen</h2>
<p>All four fixed profiles are complete. Conservative storm exchange alone improves combined error by 2.71%, rain loss by 4.36% and temperature MAE by 1.06% on these reused development regions. Switching mean-wind vapor transport to flux form creates most of the large wet bias. Accounted crest condensation also worsens the aggregate under inherited strengths. None is adopted from this screen.</p>
<div class="table"><table><caption>Versus the same verified damped r42 control; combined ratio below 1 improves</caption><thead><tr><th>Fixed profile</th><th>Combined ratio</th><th>Temperature</th><th>Rain loss</th></tr></thead><tbody>{''.join(rows)}</tbody></table></div>
<figure><a href="data/storm_factorial_monthly.png"><img src="data/storm_factorial_monthly.png" width="2160" height="1012" loading="lazy" alt="Observed, r42 and conservative-storm monthly rainfall in all eight development regions"></a><figcaption>Seasonal rainfall under the promising storm-only change. The aggregate can improve despite individual seasonal and regional regressions; the full raw packets and per-region errors remain available.</figcaption></figure>
<p>The baseline has crest rainout disabled. The accounted-condensation profiles explicitly add a local-saturation cap; they do not inherit an active cap. Conservative storms retain legacy concentration-form mean-wind transport, so this is not a globally conservative atmosphere. Planet/orbit and model wind/SST settings are unchanged.</p>
<p>A separate prospective study compares storm-only exchange at both r42 and r43 strengths over 61 development regions, including spent d/e; historical S49 remains separate. Both candidates finish before selection, then at most one frozen finalist reaches paired finer grids and the unopened f regions. No region/group veto or post-result threshold change is introduced.</p>
<p><a href="data/storm_factorial.json" download>All profile scores, regional errors and verified source hashes</a> · <a href="https://github.com/Anton2181/rotclimate/tree/{commit}/output/r42_storm_factorial_20261102">All 32 verified raw case packets and numerical records at the result commit</a> · <a href="../../reports/TRANSPORT_FACTORS_20261102.md">Physical interpretation</a></p>
</section><!--storm-factorial-end-->'''
    page=ROOT/'atlases/climate_accuracy/index.html';text=re.sub(r'<!--storm-factorial-start-->[\s\S]*?<!--storm-factorial-end-->','',page.read_text())
    text=text.replace('</main>',section+'\n</main>');text,studies=organize(text)
    if organize(text)[0]!=text:raise ValueError('Research navigation is not idempotent')
    page.write_text(text);write_json(out/'publication.json',dict(status='passed',studies=studies[:3],page_sha256=file_hash(page)))
    print('Published all four complete factorial profiles')


if __name__=='__main__':main()
