"""Publish the exact-control moisture-equation diagnosis without fitting physics."""
from pathlib import Path
import json
import re
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'scripts')]
from local_benchmark_protocol import file_hash,write_json
from organize_climate_accuracy import organize


def main():
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    import numpy as np
    source=ROOT/'output/r44_rainfall_sources_20261110';data=ROOT/'atlases/climate_accuracy/data'
    summary=json.loads((source/'summary.json').read_text())
    assert summary['status']=='passed' and len(summary['rows'])==4
    rows={r['region']:r for r in summary['rows']}
    names=['japan','bengal','north_queensland','patagonia']
    labels=['Japan','Bengal','North Queensland','Patagonia']
    terms=['evaporation','advection','diffusion','storm_exchange','convergence_import','column_drying']
    captions=['Land evaporation','Net advection','Net diffusion','Net storm exchange',
              'Parameterized convergence','Column drying']
    colors=['#558758','#367b9d','#78acbb','#9c80b4','#d6ab35','#bd6745']
    annual={}
    for name,row in rows.items():
        if not row['exact_climate_control'] or not row['numerics']['all_checks_passed']:
            raise ValueError('Failed observer control: '+name)
        if file_hash(source/(name+'.npz'))!=row['arrays_sha256']:
            raise ValueError('Changed diagnostic arrays: '+name)
        m=row['summaries']['all_land']['monthly']
        annual[name]={key:float(sum(values)) for key,values in m.items()}
        if abs(sum(annual[name][t] for t in terms)-annual[name]['simulated']-annual[name]['residual'])>1e-3:
            raise ValueError('Annual equation does not close')
    fig,ax=plt.subplots(figsize=(12.2,6),layout='constrained')
    for i,(term,caption,color) in enumerate(zip(terms,captions,colors)):
        values=np.array([annual[n][term] for n in names]);pos=np.zeros(4);neg=np.zeros(4)
        for before in terms[:i]:
            a=np.array([annual[n][before] for n in names]);pos+=np.maximum(a,0);neg+=np.minimum(a,0)
        ax.barh(range(4),values,left=np.where(values>=0,pos,neg),color=color,height=.5,label=caption)
    ax.scatter([annual[n]['simulated'] for n in names],range(4),s=85,marker='D',
               color='#222',edgecolor='white',linewidth=.7,zorder=4,label='Modeled rain = net terms − residual')
    ax.scatter([annual[n]['observed'] for n in names],range(4),s=85,marker='o',
               facecolor='white',edgecolor='#222',linewidth=1.5,zorder=4,label='Observed rain (comparison only)')
    ax.axvline(0,color='#555',lw=1);ax.grid(axis='x',alpha=.2)
    ax.set(yticks=range(4),yticklabels=labels,xlabel='Signed annual-equivalent contribution · mm/year',
           title='r44 moisture equation · all four observer runs reproduce the saved climate exactly')
    ax.invert_yaxis();ax.legend(loc='upper center',bbox_to_anchor=(.5,-.12),ncol=3,fontsize=8)
    fig.supxlabel('Regional means · parameterized convergence and storm exchange are explicit\n'
                  'Equation closure is not a globally conserved water or energy budget.',fontsize=9)
    fig.savefig(data/'r44_rainfall_sources.png',dpi=150);plt.close(fig)
    fig,axes=plt.subplots(1,2,figsize=(11.6,6.3),layout='constrained')
    for ax,name,label in zip(axes,['bengal','north_queensland'],['Bengal','North Queensland']):
        with np.load(source/(name+'.npz')) as archive:
            a=dict(archive)
        valid=a['valid'] & (a['observed'].sum(0)>=50)
        ratio=a['simulated'].sum(0)/np.maximum(a['observed'].sum(0),1e-30)
        values=np.ma.array(np.log2(np.maximum(ratio,1e-12)),mask=~valid)
        lat=-a['lat'] if name=='north_queensland' else a['lat']
        picture=ax.pcolormesh(a['lon'],lat,values,cmap='BrBG',vmin=-3,vmax=3,shading='auto',rasterized=True)
        ax.contour(a['lon'],lat,a['valid'].astype(float),levels=[.5],colors=['#333'],linewidths=.5)
        ax.set(title=label,xlabel='Longitude · °E',ylabel='Latitude · °N')
        ax.set_aspect(1/np.cos(np.radians(float(lat.mean()))))
    bar=fig.colorbar(picture,ax=axes,orientation='horizontal',fraction=.08,pad=.04,
        ticks=[-3,-2,-1,0,1,2,3],extend='both')
    bar.ax.set_xticklabels(['⅛ ×','¼ ×','½ ×','1 ×','2 ×','4 ×','8 ×'])
    bar.set_label('Modeled / observed annual rainfall · wet scored land only (observed ≥50 mm/year)')
    fig.suptitle('Current r44 spatial rainfall errors · 56 km · no new fit or physics change',fontsize=12)
    fig.savefig(data/'r44_rainfall_error_maps.png',dpi=150);plt.close(fig)
    public=dict(status='passed',annual=annual,runs=summary,
        source_sha256=file_hash(source/'summary.json'),independent_validation=False,adopted='r44')
    write_json(data/'r44_rainfall_sources.json',public)
    table=''.join(f'<tr><th>{label}</th><td>{annual[n]["observed"]:.0f}</td><td>{annual[n]["simulated"]:.0f}</td>'
                  f'<td>{annual[n]["advection"]:+.0f}</td><td>{annual[n]["convergence_import"]:+.0f}</td>'
                  f'<td>{annual[n]["column_drying"]:+.0f}</td></tr>' for n,label in zip(names,labels))
    section=f'''<!--r44-rainfall-sources-start--><h2>Current rainfall failures: exact-control moisture diagnosis</h2>
<p>Four unchanged r44 observer runs reproduce the archived monthly climate and observation arrays bit for bit. Actual input hashes match, all solver checks pass, and the exported signed terms reconstruct the equation residual. These are reused development cases, separate from the joint refit's fixed candidate budget.</p>
<figure><img src="data/r44_rainfall_sources.png" alt="Signed moisture-equation contributions in Japan, Bengal, North Queensland and Patagonia"><figcaption>Bengal has weak net advective supply and substantial column drying; North Queensland has strong parameterized convergence import. This describes the current equation, not the rainfall change obtained by turning a term off. Monsoon drying is a subset of column drying and is not counted twice.</figcaption></figure>
<div class="table"><table><thead><tr><th>Region</th><th>Observed rain</th><th>Model rain</th><th>Net advection</th><th>Parameterized convergence</th><th>Column drying</th></tr></thead><tbody>{table}</tbody></table></div>
<p>Table units are annual-equivalent mm/year, averaged over scored land. Regional-mean integrated absolute equation residuals are below 0.6 mm/year; this is much smaller than the climate errors. Equation convergence does not establish correct processes or globally conserved water/energy. The legacy column-water/saturation ratio is a model proxy, not observed surface relative humidity.</p>
<figure><img src="data/r44_rainfall_error_maps.png" alt="Annual rain-ratio maps show Bengal too dry and North Queensland with strong spatial errors"><figcaption>Wet scored land only; colors saturate below one eighth and above eight times observed annual rain. The 56-km maps are baseline diagnostics, not new climate predictions.</figcaption></figure>
<p>Next hypotheses should distinguish circulation delivery, parameterized sources/sinks and condensation. No coefficient or adoption changes here. <a href="data/r44_rainfall_sources.json" download>All source terms, controls and numerical receipts</a> · <a href="../../reports/R44_RAINFALL_SOURCES_20261110.md">Methods and limits</a> · <a href="../../reports/CALIBRATION_STRATEGY_20261110.md">Literature-based calibration alternatives</a></p><!--r44-rainfall-sources-end-->'''
    page=ROOT/'atlases/climate_accuracy/index.html';html=page.read_text()
    pattern=r'<!--r44-rainfall-sources-start-->[\s\S]*?<!--r44-rainfall-sources-end-->'
    html=re.sub(pattern,lambda m:section,html) if re.search(pattern,html) else html.replace('</main>',section+'\n</main>')
    html,_=organize(html);assert organize(html)[0]==html;page.write_text(html)
    report=ROOT/'reports/R44_RAINFALL_SOURCES_20261110.md'
    report.write_text('''# r44 rainfall-source diagnosis — 10 November 2026

All four existing equation observers pass exact archived monthly-array controls, actual input hashes,
strict numerical checks and signed-source reconstruction. This is a read-only baseline audit, separate
from the P8d 51-candidate campaign: no coefficients, objective, finalist, independent pool or physics
adoption changed. The four cases are reused development data.

![Signed equation terms](../atlases/climate_accuracy/data/r44_rainfall_sources.png)

![Current spatial errors](../atlases/climate_accuracy/data/r44_rainfall_error_maps.png)

Bengal's annual rain is 444 mm versus 2143 observed. Its net advection contributes −32 mm, parameterized
convergence +319, storm exchange +516, evaporation +284, diffusion +90 and column drying −732 mm/year.
North Queensland has 1707 mm versus 874 observed; parameterized convergence supplies +1183 mm/year,
net advection +744, with drying −944. These are the present equation terms, not counterfactual causal
effects: removing one term would alter water, rain, recycling, temperatures and winds.

Japan's summer moisture shortage and excessive winter rain remain visible in the monthly series.
Patagonia's regional annual total is near observations, while local errors remain large. The maps
show annual modeled/observed rainfall on scored wet land (observed ≥50 mm/year), clipping colors at
one eighth/eight times. Southern coordinates are restored to actual Earth latitude.

The maximum reconstruction gap is below 0.000023 mm/month. Regional-mean annual integrated absolute
equation residuals are below 0.6 mm/year, much smaller than the climate errors. These checks establish
the recorded discrete equation and solver control, not physical correctness or a globally conserved
water/energy budget. The active transport equation is the legacy concentration form; convergence import
and storm exchange are parameterized, and monsoon drying is already included in column drying.
The legacy column water/saturation ratio is not measured surface relative humidity.

Frozen inputs: `calibration/r44_rainfall_sources_20261110/plan.json`; output protocol, numerical receipts,
monthly source arrays and summaries: `output/r44_rainfall_sources_20261110/`. The wrapper reuses the
existing `check_moisture_sources.audit_one` observer without editing model/scoring code. Monthly archives
use the model's existing equal-month calendar; source contributions are converted from mm/day with
the same year/12 factor used by the climate export. Plots of regional means conceal local cancellation;
canonical rainfall loss continues to score every cell and month.

See [the calibration-method proposal](CALIBRATION_STRATEGY_20261110.md) for verified academic approaches
to separating parameter uncertainty, process constraints and model limitations. That proposal does not
change the current campaign or provide new independent validation.
''')
    register=ROOT/'calibration/earth_components_20261105/dataset_usage.json'
    exposure=json.loads(register.read_text());exposure['date']='2026-11-10'
    entry=dict(id='r44_rainfall_sources_20261110',status='reused_development_diagnostic',
        evidence='reports/R44_RAINFALL_SOURCES_20261110.md',
        note='Japan, Bengal, North Queensland and Patagonia, unchanged r44 observer controls. No fresh validation, fit or adoption.')
    exposure['datasets']=[r for r in exposure['datasets'] if r['id']!=entry['id']]+[entry]
    write_json(register,exposure)
    (ROOT/'atlases/earth_evidence/data/dataset_usage.json').write_bytes(register.read_bytes())
    print(json.dumps(annual,indent=2))


if __name__=='__main__':main()
