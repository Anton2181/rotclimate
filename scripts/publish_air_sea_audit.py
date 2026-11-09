"""Plot the completed development audit and add it to the local research page."""
from pathlib import Path
import json
import re
import shutil
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'scripts')]


def main():
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    import numpy as np
    from organize_climate_accuracy import organize
    from local_benchmark_protocol import file_hash, write_json
    source=ROOT/'output/air_sea_audit_20261109_operator_state';data=ROOT/'atlases/climate_accuracy/data'
    summary=json.loads((source/'summary.json').read_text());assert summary['status']=='passed'
    rows={(r['region'],r['config']):r for r in summary['rows']}
    names=['levant','japan','korea','h_top_end','h_new_guinea','h_ivory_coast']
    labels=['Levant','Japan','Korea','Top End','New Guinea','Ivory Coast']
    configs=['r44','failed_p8a_C3'];colors=['#246b84','#bd5a32'];legend=['r44','rejected P8a C3']
    assert set(rows)=={(r,c) for r in names for c in configs}
    metrics=[]
    for name,label in zip(names,labels):
        out=dict(region=name,label=label)
        for config in configs:
            r=rows[name,config];assert r['numerics']['all_checks_passed']
            m=r['monthly'];out[config]=dict(land_mae_c=float(np.mean(m['land_temperature_mae_c'])),
                marine_air_bias_c=float(np.mean(np.array(m['air_c'])-m['ncep_air_c'])),
                marine_monthly_curve_mae_c=float(np.mean(np.abs(np.array(m['air_c'])-m['ncep_air_c']))),
                sst_bias_c=float(np.mean(np.array(m['surface_c'])-m['woa_surface_c'])),
                sst_monthly_curve_mae_c=float(np.mean(np.abs(np.array(m['surface_c'])-m['woa_surface_c']))),
                cap_exceedance_cold=r['distributions']['nominal_cap_exceedance_fraction_cold'])
        metrics.append(out)
    fig,axes=plt.subplots(1,3,figsize=(13,4.9),layout='constrained',sharey=True)
    for ax,key,title in zip(axes,['land_mae_c','marine_air_bias_c','sst_bias_c'],
                           ['Land temperature MAE','Marine air bias vs NCEP sigma 0.995','SST bias vs WOA18']):
        for i,(config,color,label) in enumerate(zip(configs,colors,legend)):
            values=[r[config][key] for r in metrics]
            ax.barh(np.arange(6)+(i-.5)*.32,values,height=.3,color=color,label=label)
        ax.axvline(0,color='#555',lw=.7);ax.set_title(title,fontsize=10);ax.set_xlabel('°C')
        ax.grid(axis='x',alpha=.16);ax.set_axisbelow(True)
    axes[0].set_yticks(np.arange(6),labels);axes[0].invert_yaxis();axes[0].legend(fontsize=9)
    fig.suptitle('Coastal development audit · six already-seen regions · no new validation or adopted physics',fontsize=12)
    fig.savefig(source/'coastal_temperature_audit.png',dpi=150);plt.close(fig)
    fig,axes=plt.subplots(2,3,figsize=(12.5,7.2),layout='constrained',sharex=True,sharey=True)
    cap_flux=1.225*1004*1000*2/86400
    for ax,name,label in zip(axes.ravel(),names,labels):
        for config,color,title in zip(configs,colors,legend):
            ax.plot(np.arange(1,13),rows[name,config]['monthly']['flux_1000m_wm2'],color=color,label=title,lw=2)
        ax.axhline(0,color='#777',lw=.7);ax.axhline(cap_flux,color='#777',ls='--',lw=.8)
        ax.set_title(label);ax.set_xticks([1,4,7,10,12]);ax.grid(alpha=.14);ax.set_ylim(-75,80)
    axes[0,0].legend(fontsize=9);axes[0,0].set_ylabel('W/m² · assumed 1 km air slab');axes[1,0].set_ylabel('W/m² · assumed 1 km air slab')
    for ax in axes[1]:ax.set_xlabel('Model month · southern references shifted by 6')
    fig.suptitle('Actual surface relaxation, expressed as conditional slab flux\nDashed: nominal 2 K/day at 1 km; positive warms air. Excludes eddy/lateral terms and an ocean heat debit.',fontsize=11)
    fig.savefig(source/'surface_exchange_flux.png',dpi=145);plt.close(fig)
    write_json(source/'interpretation.json',dict(status='passed',metrics=metrics,
        depth_sensitivity=dict(depths_m=[250,500,1000,2000],flux_scalings_relative_1000m=[.25,.5,1,2]),
        scope='Development mechanism diagnosis only; NCEP sigma air and WOA SST have different periods/resolutions; no observed flux inferred.',
        source_sha256=file_hash(source/'summary.json')))
    for name in ['coastal_temperature_audit.png','surface_exchange_flux.png']:
        shutil.copyfile(source/name,data/name)
    shutil.copyfile(source/'interpretation.json',data/'air_sea_audit.json')
    page=ROOT/'atlases/climate_accuracy/index.html';html=page.read_text()
    japan_cap=rows['japan','failed_p8a_C3']['distributions']['nominal_cap_exceedance_fraction_cold']
    korea_cap=rows['korea','failed_p8a_C3']['distributions']['nominal_cap_exceedance_fraction_cold']
    section=f'''<!--air-sea-exchange-start--><h2>Surface heat exchange on r44 and rejected P8a</h2>
<p>Twelve verified runs revisit six <strong>already-seen development regions</strong>. The optional recorder leaves every model field bit-identical in tests. The adopted physics remains r44; this audit does not qualify a replacement.</p>
<figure><img src="data/coastal_temperature_audit.png" alt="Land error and separate marine-air and SST biases across six development regions"><figcaption>Land observations, NCEP sigma-0.995 air (1991–2020) and WOA18 sea temperature are separate references. NCEP is a sigma level, not fixed 995 hPa; differing periods, coarse grids and coastal interpolation limit their interpretation.</figcaption></figure>
<p>The nominal 2 K/day unstable cap retains r44's baseline exchange-rate floor. It is exceeded in {japan_cap:.1%} of eligible cold-air samples near Japan and {korea_cap:.1%} near Korea, evaluated at the recorded coefficient state to exclude fixed-point tolerance effects. This is the formula's intentional floor, not evidence for removing it. Faster coupling also worsens tropical transfer. Near the Top End the model sea is about 4.25 °C colder than WOA18; in the Levant, land error improves while marine-air agreement worsens. New Guinea's land and marine air move in opposite directions: a single local cooling explanation is insufficient.</p>
<figure><img src="data/surface_exchange_flux.png" alt="Monthly surface relaxation converted to flux for an explicitly assumed one-kilometre atmospheric slab"><figcaption>Conditional diagnostic: rho cp h lambda (SST − air), at h = 1 km. Flux scales by 0.25/0.5/2 at 250/500/2,000 m. It excludes eddy/lateral tendencies and does not debit heat from a prognostic ocean. No observed heat flux or inferred boundary-layer depth is claimed.</figcaption></figure>
<p>Next: diagnose shared modeled-SST errors and compensation before selecting another exchange scheme; then compare dispersed starts under fixed Earth forcing. No new blind pool was opened.</p>
<p><a href="data/air_sea_audit.json" download>Audit measurements and scope</a> · <a href="../../reports/AIR_SEA_AUDIT_20261109.md">Methods and next physics design</a></p><!--air-sea-exchange-end-->'''
    pattern=r'<!--air-sea-exchange-start-->[\s\S]*?<!--air-sea-exchange-end-->'
    if re.search(pattern,html):html=re.sub(pattern,lambda m:section,html)
    else:html=html.replace('</main>',section+'\n</main>')
    html,_=organize(html);assert organize(html)[0]==html;page.write_text(html)
    print('Published development-only surface-exchange audit; r44 unchanged')


if __name__=='__main__':main()
