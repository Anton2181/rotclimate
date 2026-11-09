"""Report every predeclared SST direction without adopting a new climate."""
from pathlib import Path
import json
import re
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'scripts')]


def main():
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    import numpy as np
    from organize_climate_accuracy import organize
    from local_benchmark_protocol import file_hash,write_json
    source=ROOT/'output/shared_sst_screen_20261109';data=ROOT/'atlases/climate_accuracy/data'
    plan=json.loads((ROOT/'calibration/shared_sst_screen_20261109/plan.json').read_text())
    full=json.loads((source/'summary.json').read_text());assert full['status']=='passed'
    rows={(r['region'],r['config']):r for r in full['rows']}
    assert set(rows)=={(r,c) for r in plan['regions'] for c in plan['configs']}
    allowed={'sst_offset','current_strength','ocean_tau_stable','ocean_tau_unstable','ocean_unstable_cap'}
    for region in plan['regions']:
        ref=rows[region,'r44']
        for config in plan['configs']:
            r=rows[region,config];assert r['numerics']['all_checks_passed']
            assert r['case_sha256']==ref['case_sha256']
            assert {k for k,v in r['params'].items() if v!=ref['params'][k]} <= allowed
    metrics=[]
    for config in plan['configs']:
        selected=[rows[r,config] for r in plan['regions']]
        m=dict(config=config,T_mae_c=float(np.mean([r['land_metrics']['temperature_mae_c'] for r in selected])),
            P_loss=float(np.mean([r['land_metrics']['rain_loss'] for r in selected])),
            sst_monthly_curve_mae_c=float(np.mean([np.abs(np.array(r['monthly']['surface_c'])-r['monthly']['woa_surface_c']).mean() for r in selected])),
            marine_air_monthly_curve_mae_c=float(np.mean([np.abs(np.array(r['monthly']['air_c'])-r['monthly']['ncep_air_c']).mean() for r in selected])))
        if not metrics: ref=m
        m.update(S6=.5*m['T_mae_c']/ref['T_mae_c']+.5*m['P_loss']/ref['P_loss'],
            T_change=m['T_mae_c']/ref['T_mae_c']-1,P_change=m['P_loss']/ref['P_loss']-1,
            sst_change=m['sst_monthly_curve_mae_c']/ref['sst_monthly_curve_mae_c']-1)
        m['screen_pass']=bool(m['S6']<=.995 and m['T_change']<=.01 and m['P_change']<=.01)
        metrics.append(m)
    assert not any(m['screen_pass'] for m in metrics)
    result=dict(status='passed',verified_runs=len(rows),all_geographies_and_fixed_parameters_match=True,
        metrics=metrics,adopted='r44',scope='Six selected seen/spent regions, development screen only; no new independent validation or multi-start optimization.',
        source_sha256=file_hash(source/'summary.json'))
    write_json(source/'comparison.json',result);write_json(data/'shared_sst_screen.json',result)
    labels=['r44','Rejected C3','SST/current ±1.5 K','±1.5 K + C3','SST/current ±3 K','±3 K + C3']
    colors=['#3a5260','#777777','#287b95','#bb5835','#287b95','#bb5835']
    fig,axes=plt.subplots(1,2,figsize=(11.8,4.9),layout='constrained',sharey=True)
    for ax,key,title in zip(axes,['S6','sst_monthly_curve_mae_c'],['Land temperature + rainfall · S6','Coastal SST monthly-curve MAE · °C']):
        ax.scatter([m[key] for m in metrics],np.arange(6),c=colors,s=75,zorder=3)
        for i,m in enumerate(metrics):ax.annotate(f'{m[key]:.3f}',(m[key],i),xytext=(8,3),textcoords='offset points',fontsize=9)
        ax.axvline(metrics[0][key],color='#777',ls='--',lw=1);ax.grid(axis='x',alpha=.2)
        ax.set_title(title,fontsize=11);ax.margins(x=.2);ax.set_xlabel('Lower is better')
    axes[0].set_yticks(np.arange(6),labels);axes[0].invert_yaxis()
    fig.suptitle('Shared ocean-parameter screen · all 36 runs verified · no new physics adopted',fontsize=12)
    fig.savefig(data/'shared_sst_screen.png',dpi=155);plt.close(fig)
    table=''.join(f"<tr><th>{label}</th><td>{m['T_mae_c']:.3f}</td><td>{m['P_loss']:.5f}</td><td>{m['S6']:.4f}</td><td>{m['sst_monthly_curve_mae_c']:.3f}</td></tr>" for label,m in zip(labels,metrics))
    section=f'''<!--shared-sst-screen-start--><h2>Shared SST/current screen: compensation persists</h2>
<p>Four predeclared global parameter directions raised the existing SST offset by 1.5 or 3 K while lowering current-anomaly strength by the same amount, with r44 or C3 exchange. Earth forcing/geography, modeled SST/winds and numerical tolerances stayed fixed. All 36 runs passed; these are six selected <strong>already-seen</strong> development regions, not a new independent test or a multi-start optimum.</p>
<figure><img src="data/shared_sst_screen.png" alt="Every shared SST candidate improves the coastal SST metric but worsens the combined land-climate score"><figcaption>The four new directions reduce coastal SST monthly-curve MAE by 23–29%, but their S6 scores worsen 1.9–8.0%. Parameters are existing phenomenological responses, not a resolved ocean heat budget. Neither a gain nor a global optimum is established.</figcaption></figure>
<div class="table"><table><thead><tr><th>Configuration</th><th>Land T MAE, °C</th><th>Rain loss</th><th>S6</th><th>SST curve MAE, °C</th></tr></thead><tbody>{table}</tbody></table></div>
<p>C3's S6 is slightly lower, but temperature worsens more than the screen's 1% component guard; its earlier independent test already failed. None advances as an improvement. The next informative search needs a joint ocean/land-response refit from dispersed starts, retaining broad development and finer-grid checks. r44 remains adopted.</p>
<p><a href="data/shared_sst_screen.json" download>All screen measurements</a> · <a href="../../reports/SHARED_SST_SCREEN_20261109.md">Frozen directions, methods and limits</a></p><!--shared-sst-screen-end-->'''
    page=ROOT/'atlases/climate_accuracy/index.html';html=page.read_text();pattern=r'<!--shared-sst-screen-start-->[\s\S]*?<!--shared-sst-screen-end-->'
    html=re.sub(pattern,lambda m:section,html) if re.search(pattern,html) else html.replace('</main>',section+'\n</main>')
    html,_=organize(html);assert organize(html)[0]==html;page.write_text(html)
    print(json.dumps(metrics,indent=2))


if __name__=='__main__':main()
