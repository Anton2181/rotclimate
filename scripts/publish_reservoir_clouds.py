"""Append verified layer-capacity results to the nonlinear research section."""
from pathlib import Path
import json,sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from local_benchmark_protocol import file_hash,write_json


def main():
    out=ROOT/'output/reservoir_clouds_20261026';protocol=json.loads((out/'protocol.json').read_text());review=json.loads((out/'review.json').read_text())
    if not review['complete'] or not review['all_numerical_checks_passed'] or review['physics_or_atlas_adoption']:raise ValueError('Need completed research-only experiment')
    for name,digest in protocol['sources'].items():
        if file_hash(ROOT/name)!=digest:raise ValueError('Changed cloud experiment epoch: '+name)
    for name,row in review['records'].items():
        if row['status']!='passed' or json.loads((out/f'{name}.json').read_text())!=row:raise ValueError('Changed layer record')
    parent=ROOT/protocol['plan']['parent'];prior=json.loads((parent/'review.json').read_text())
    if file_hash(parent/'review.json')!=review['verified_parent_review_sha256']:raise ValueError('Changed prior nonlinear example')
    data=ROOT/'atlases/climate_accuracy/data';picture=data/'reservoir_clouds.png'
    fig,axes=plt.subplots(2,2,figsize=(12,8),constrained_layout=True)
    shown=[('Imposed ratio0.2',prior['profiles']['fixed_ratio'],'#a25b6d','--'),
           ('Column rain, separate water (5-day mix)',prior['profiles']['separate_mix5'],'#398f8b','-'),
           ('Layer rain, separate water (5-day mix)',review['profiles']['layer_mix5'],'#3e6ca4','-')]
    for label,profile,color,style in shown:
        for ax,key,title,ylabel in [(axes[0,0],'rain_mm_day','Same forcing; different condensation placement','Rain (mm/day)'),
             (axes[0,1],'upper_lower_q_ratio','Layer capacity only partly changes humidity','Upper/lower mixing-ratio ratio'),
             (axes[1,0],'water_mm','Total column water','Water (mm)')]:
            ax.plot(profile['x_km'],profile[key],label=label,color=color,ls=style)
            ax.set(title=title,ylabel=ylabel,xlabel='Synthetic domain x (km)');ax.grid(alpha=.15);ax.legend(frameon=False,fontsize=8)
    profile=review['profiles']['layer_mix5']
    axes[1,1].plot(profile['x_km'],profile['lower_rain_mm_day'],label='Lower-layer rain',color='#b28b41')
    axes[1,1].plot(profile['x_km'],profile['upper_rain_mm_day'],label='Upper-layer rain',color='#3e6ca4')
    axes[1,1].set(title='Layer rain,5-day mixing',ylabel='Rain (mm/day)',xlabel='Synthetic domain x (km)')
    axes[1,1].legend(frameon=False,fontsize=8);axes[1,1].grid(alpha=.15)
    fig.suptitle('Independent layer condensation · manufactured capacity profile',fontsize=16)
    fig.supxlabel('Prior capacity split0.625/0.375 is prescribed; actual humidity is solved. All original rain-law coefficients stay fixed.\n'
        'Both zero/5-day mixing cases pass. The fixed5-day examples above were not selected by accuracy; all outcomes are in the download. No Earth score.',fontsize=9)
    fig.savefig(picture,dpi=145);plt.close(fig)
    summary=dict(review,verified_parent_results=prior,source_epoch=protocol['source_commit'],
        protocol_sha256=file_hash(out/'protocol.json'),review_sha256=file_hash(out/'review.json'),image_sha256=file_hash(picture),publisher_sha256=file_hash(Path(__file__)),
        interpretation='Layer-specific capacity reduces upper humidity somewhat but is still a prescribed approximation, not independently solved vertical thermodynamics or observed Earth accuracy. No physics or atlas adoption.')
    write_json(data/'reservoir_clouds.json',summary)
    addition='''<!--reservoir-clouds-start--><div><h3>Condensation within each layer</h3>
<p>A further fixed experiment assigns0.625/0.375 of the same column saturation capacity to the lower/upper layers. Actual water remains independently solved. Each layer uses the old rain law at its equivalent column amount; this exactly recovers the original law when the old humidity shape is imposed, including the convective numerical water floor.</p>
<figure><a href="data/reservoir_clouds.png"><img src="data/reservoir_clouds.png" width="1740" height="1160" loading="lazy" alt="Synthetic independent layer condensation: changed rain placement and moderately lower upper humidity, with original rain law recovered under the fixed profile"></a><figcaption>Shown: fixed5-day mixing comparisons, with both zero/5-day outcomes retained in the download. Layer rain reduces upper humidity somewhat, but ratios still reach0.91. The imposed capacity split is an approximation, not independent layer temperatures or an observed Earth result.</figcaption></figure>
<p>Both new systems pass strict per-layer nonlinear residuals. Six new closure/analytic/equilibrium checks bring the focused reservoir suite to21 passing tests. Neither this example nor the preceding proportional-column example supplies a new Earth accuracy score or changes the normal atlas climate.</p>
<p><a href="data/reservoir_clouds.json" download>Download layer-condensation results and verified parent controls</a> · <a href="../../reports/RESERVOIR_CLOUDS_20261026.md">Capacity partition, tests and remaining limitations</a></p></div><!--reservoir-clouds-end-->'''
    page=ROOT/'atlases/climate_accuracy/index.html';content=page.read_text();start='<!--reservoir-clouds-start-->';end='<!--reservoir-clouds-end-->'
    if start in content:
        before,rest=content.split(start,1);_,after=rest.split(end,1);content=before+addition+after
    else:content=content.replace('</section><!--reservoir-rain-end-->',addition+'</section><!--reservoir-rain-end-->')
    if start not in content:raise ValueError('Missing nonlinear research section')
    page.write_text(content)
    write_json(out/'publication.json',dict(scope='Research only; no climate adoption',metadata_sha256=file_hash(data/'reservoir_clouds.json'),
        page_sha256=file_hash(page),image_sha256=file_hash(picture),publisher_sha256=file_hash(Path(__file__))))


if __name__=='__main__':main()
