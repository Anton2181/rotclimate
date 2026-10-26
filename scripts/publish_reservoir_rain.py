"""Publish a frozen nonlinear manufactured experiment, never a climate fit."""
from pathlib import Path
import json,sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from local_benchmark_protocol import file_hash,write_json


def main():
    out=ROOT/'output/reservoir_rain_20261026';protocol=json.loads((out/'protocol.json').read_text());review=json.loads((out/'review.json').read_text())
    if not review['complete'] or not review['all_numerical_checks_passed'] or review['physics_or_atlas_adoption']:raise ValueError('Need verified research-only results')
    for name,digest in protocol['sources'].items():
        if file_hash(ROOT/name)!=digest:raise ValueError('Changed nonlinear source epoch: '+name)
    for name,row in review['records'].items():
        if json.loads((out/f'{name}.json').read_text())!=row or row['status']!='passed':raise ValueError('Changed nonlinear record')
    data=ROOT/'atlases/climate_accuracy/data';image=data/'reservoir_rain.png'
    fig,axes=plt.subplots(2,2,figsize=(12,8),constrained_layout=True)
    labels={'fixed_ratio':'Imposed ratio0.2','separate_no_mix':'Separate, no vertical mixing','separate_mix5':'Separate,5-day mixing'}
    colors=['#a25b6d','#b28b41','#398f8b'];styles=['--','-','-']
    for name,color,style in zip(protocol['plan']['profiles'],colors,styles):
        profile=review['profiles'][name];x=profile['x_km']
        for ax,key,title,ylabel in [(axes[0,0],'rain_mm_day','Existing nonlinear column rainfall law','Rain (mm/day)'),
             (axes[0,1],'water_mm','Total water is solved independently','Column water (mm)'),
             (axes[1,0],'upper_lower_q_ratio','Upper air moistens under vertical transport','Upper/lower mixing-ratio ratio')]:
            ax.plot(x,profile[key],color=color,ls=style,label=labels[name]);ax.set(title=title,ylabel=ylabel,xlabel='Synthetic domain x (km)')
            ax.grid(alpha=.15);ax.legend(frameon=False,fontsize=8)
    names=list(protocol['plan']['profiles']);values=[review['records'][name]['scaled_residual'] for name in names]
    axes[1,1].bar(np.arange(len(names)),values,color=colors)
    axes[1,1].set(xticks=np.arange(len(names)),xticklabels=['Imposed\nratio','Separate\nno mix','Separate\n5-day mix'],
        yscale='log',ylabel='Largest scaled local equation residual',title='Actual nonlinear water balance checked',ylim=(1e-12,1e-6))
    axes[1,1].axhline(protocol['plan']['numerics']['moisture_residual_tol'],color='#444',ls='--',lw=1,label='Required tolerance')
    axes[1,1].legend(frameon=False,fontsize=8)
    axes[1,1].grid(axis='y',alpha=.15)
    fig.suptitle('Nonlinear reservoir prototype · synthetic mechanism test',fontsize=16)
    fig.supxlabel('Same opposing winds, supply, layer boundaries,40mm column capacity and r39 rain law, including convection/subcloud evaporation.\n'
        'No Earth geography or observed rainfall is scored. Upper humidity near unity exposes the remaining need for vertical thermodynamics/cloud physics.',fontsize=9)
    fig.savefig(image,dpi=145);plt.close(fig)
    summary=dict(review,source_epoch='0e55984',protocol_sha256=file_hash(out/'protocol.json'),review_sha256=file_hash(out/'review.json'),
        image_sha256=file_hash(image),publisher_sha256=file_hash(Path(__file__)),
        interpretation='The convergence peak weakens in this synthetic nonlinear system, but upper/lower humidity ratios0.81–0.97 are not evidence of a realistic Earth vertical profile. Column rain is removed proportionally, without independent vertical saturation or cloud formation. No climate accuracy/adoption claim.')
    write_json(data/'reservoir_rain.json',summary)
    section='''<!--reservoir-rain-start--><section aria-labelledby="reservoir-rain-h"><h2 id="reservoir-rain-h">Nonlinear rain with separate moisture reservoirs</h2>
<p><strong>Synthetic mechanism test, not an Earth accuracy gain.</strong> This follow-up uses the unchanged r39 nonlinear rainfall law, including its convective and subcloud terms, with identical prescribed winds, surface supply and both layer boundaries. Separate lower and upper water fields reduce a sharp convergence peak, both without vertical mixing and with5-day mixing.</p>
<figure><a href="data/reservoir_rain.png"><img src="data/reservoir_rain.png" width="1740" height="1160" loading="lazy" alt="Nonlinear synthetic rainfall, total water, solved layer humidity and strict residuals: separate reservoirs reduce a peak but upper air becomes nearly as humid as lower air"></a><figcaption>All three predeclared systems pass their actual nonlinear equations; each independent reservoir is checked separately. Rain is removed in proportion to current layer water. The near-uniform vertical humidity is a remaining physical limitation, not a validated Earth result.</figcaption></figure>
<p>The imposed-ratio peak is46.2mm/day; separate fields give about1.1mm/day in this manufactured case. Upper/lower specific-humidity ratios reach0.97, so vertical saturation and cloud formation still require explicit treatment. There is no seasonal thermal feedback, ocean exchange, storm transport or new climate calibration. Published atlas climates and headline scores remain unchanged.</p>
<p><a href="data/reservoir_rain.json" download>Download nonlinear reservoir diagnostics</a> · <a href="../../reports/RESERVOIR_RAIN_20261026.md">Equations, controls and physical limitations</a></p></section><!--reservoir-rain-end-->'''
    page=ROOT/'atlases/climate_accuracy/index.html';content=page.read_text();start='<!--reservoir-rain-start-->';end='<!--reservoir-rain-end-->'
    if start in content:
        before,rest=content.split(start,1);_,after=rest.split(end,1);content=before+section+after
    else:content=content.replace('</main>',section+'\n</main>')
    page.write_text(content)
    write_json(out/'publication.json',dict(scope='Research-only; no climate adoption',metadata_sha256=file_hash(data/'reservoir_rain.json'),
        page_sha256=file_hash(page),publisher_sha256=file_hash(Path(__file__)),image_sha256=file_hash(image)))


if __name__=='__main__':main()
