"""Publish the complete rejected shear pilot without changing atlas climates."""
from pathlib import Path
import json
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from local_benchmark_protocol import file_hash, write_json


def main():
    out = ROOT/'output/column_shear_20261026'
    review = json.loads((out/'review.json').read_text())
    protocol = json.loads((out/'protocol.json').read_text())
    advance = json.loads((out/'advance/review.json').read_text())
    if (not review['complete'] or not review['all_per_step_checks_passed'] or review['development_finalists']
            or advance['eligible_for_earth_adoption']):
        raise ValueError('This exporter requires the complete, rejected pilot')
    for name, expected in protocol['sources'].items():
        if file_hash(ROOT/name) != expected:
            raise ValueError('Pilot sources changed: '+name)
    names = ['reference',*protocol['plan']['candidates']]
    records = {}
    for name in names:
        records[name] = {}
        for region in protocol['plan']['regions']:
            row = json.loads((out/name/f'{region}.json').read_text())
            if (row['identity'] != review['identity'] or row['status'] != 'passed'
                    or not row['numerics']['all_checks_passed'] or (name == 'reference' and not row['legacy_exact'])
                    or file_hash(out/name/f'{region}.npz') != row['arrays_sha256']):
                raise ValueError('Changed or unverified shear run')
            records[name][region] = row
    data = ROOT/'atlases/climate_accuracy/data'
    fig, axes = plt.subplots(1,3,figsize=(13.6,4.8),constrained_layout=True,
                             gridspec_kw=dict(width_ratios=[1.2,1.2,1.4]))
    colors = ['#285c80','#4d9b91','#ce8848','#9c4665']
    ax = axes[0]
    observed = records['reference']['north_india']['monthly_rain']['observed']
    ax.plot(observed,color='#20272d',lw=2.5,label='Observed')
    for name, color in zip(names,colors):
        row = records[name]['north_india']
        ax.plot(row['monthly_rain']['simulated'],color=color,lw=1.8,label=f'Drag ratio {row["ratio"]:g}')
    ax.set(title='North India: less column drag loses rain',ylabel='Rain (mm / equal model month)',
           xticks=np.arange(12),xticklabels=list('JFMAMJJASOND'))
    ax.legend(frameon=False,fontsize=8)
    ax.grid(axis='y',alpha=.15)
    ax = axes[1]
    fields = ['convergence_import','evaporation','advection','storm_exchange']
    labels = ['Convergence import','Evaporation','Mean-wind transport','Storm exchange']
    for key,label,color in zip(fields,labels,['#285c80','#4d9b91','#ce8848','#9c4665']):
        values=[]
        for name in names:
            with np.load(out/name/'north_india.npz') as z:
                values.append(float(z[key][6,z['valid']].mean()))
        ax.plot(np.arange(4),values,marker='o',color=color,label=label)
    ax.axhline(0,color='#555555',lw=.6)
    ax.set(title='July: inflow and recycling shrink',ylabel='Signed source (mm / model month)',
           xticks=np.arange(4),xticklabels=['1','.75','.5','.25'],xlabel='Column / surface Rayleigh drag')
    ax.legend(frameon=False,fontsize=8)
    ax.grid(axis='y',alpha=.15)
    ax = axes[2]
    regions=protocol['plan']['regions']
    labels=['North India','Iran plateau','Iberia','Japan','Mexico','East Australia','Pacific NW']
    x=np.arange(len(regions))
    for i,name in enumerate(names[1:]):
        ax.barh(x+(i-1)*.22,[100*(review['screen'][name]['regions'][r]['rain']-1) for r in regions],
                height=.2,color=colors[i+1],label=f'Drag ratio {protocol["plan"]["candidates"][name]:g}')
    ax.axvline(0,color='#555555',lw=.7)
    ax.set(title='Regional rainfall loss',yticks=x,yticklabels=labels,xlabel='Change from r39 (%) · lower is better')
    ax.invert_yaxis()
    ax.legend(frameon=False,fontsize=8)
    fig.suptitle('Pressure-driven column shear: physically motivated, rejected on accuracy',fontsize=15)
    fig.supxlabel('All 28 runs passed their per-step solves; all seven legacy controls reproduce exactly. No finalist, physics adoption or atlas-climate replacement.\n'
                  'Planet/geography unchanged; observed remote forcing retained. These are reused regional development tests.',fontsize=9)
    figure=data/'column_shear.png'
    fig.savefig(figure,dpi=150)
    plt.close(fig)
    summary=dict(complete=True,decision='Rejected; retain r39',exact_controls=7,numerically_verified_runs=28,
        screening=review['screen'],scope=protocol['plan']['interpretation'],
        integrated_sst_reference={region:records['reference'][region]['sst'] for region in regions},
        north_india_annual_rain_mm={name:records[name]['north_india']['rain']['sim_mean_annual_mm'] for name in names},
        provenance=dict(protocol_sha256=file_hash(out/'protocol.json'),review_sha256=file_hash(out/'review.json'),
                        plotter_sha256=file_hash(Path(__file__)),figure_sha256=file_hash(figure)))
    write_json(data/'column_shear.json',summary)
    page=ROOT/'atlases/climate_accuracy/index.html'
    content=page.read_text()
    start,end='<!--column-shear-start-->','<!--column-shear-end-->'
    section='''<!--column-shear-start--><section aria-labelledby="shear-h"><h2 id="shear-h">Latest experiment: turning the moisture-column wind</h2>
<p>Lower friction above the surface changes the direction of pressure-driven flow, as well as its speed. Three fixed drag ratios were tested with the current Earth physics and unchanged planetary inputs. All 28 runs converged, and seven default controls reproduced their archived climate exactly.</p>
<p><strong>All three candidates were rejected.</strong> North India's annual rain fell from 256 mm to 203, 130 and 75 mm, against 761 mm observed. Japan and the Pacific Northwest improved slightly, but India and eastern Australia worsened. No candidate advanced to the finer-grid or established-region stages.</p>
<figure><a href="data/column_shear.png"><img src="data/column_shear.png" width="2040" height="720" loading="lazy" alt="Rejected shear experiment: Indian rain and convergence import fall as column drag decreases, with mixed regional rainfall errors"></a><figcaption>Reducing drag weakened cross-isobar moisture inflow in India. Faster or more geostrophic flow alone does not supply its missing monsoon. Default physics and every atlas climate remain unchanged.</figcaption></figure>
<p class="note">This screen also used actual simulated sea-surface temperatures, including wind-dependent upwelling, against the restored twelve-month WOA18 climatology. The candidates passed the ocean-error and wind-speed limits; they failed land-rainfall accuracy. This seven-region ocean check differs from the older static 19-region SST benchmark.</p>
<p><a href="data/column_shear.json" download>Download shear experiment measurements</a> · <a href="../../reports/COLUMN_SHEAR_20261026.md">Experiment record</a></p></section><!--column-shear-end-->'''
    if start in content:
        before,rest=content.split(start,1)
        _,after=rest.split(end,1)
        content=before+section+after
    else:
        content=content.replace('</main>',section+'\n</main>')
    page.write_text(content)
    write_json(out/'publication.json',dict(status='published_rejected_diagnostic',
        image_sha256=file_hash(figure),metadata_sha256=file_hash(data/'column_shear.json'),
        page_sha256=file_hash(page),physics_or_atlas_climate_adoption=False))


if __name__=='__main__':
    main()
