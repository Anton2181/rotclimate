"""Publish reviewed synthetic finite-storage water accounting."""
import csv
from html import escape
import json
from pathlib import Path
import re
import shutil
import sys

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
from settlement_locations_earth import sha,write

OUT=ROOT/'output/paid_groundwater_20261114'
PAGE=ROOT/'atlases/earth_evidence/groundwater_budget'
LABELS={'groundwater_disabled':'Groundwater disabled','stored_no_permission':'Stored, no upward permission','finite_groundwater':'Finite groundwater transfer'}
KEYS=['recharge_mm','capillary_mm','final_aquifer_mm','root_uptake_mm','root_potential_mm','river_delivered_m3']


def main():
    r=json.loads((OUT/'results.json').read_text());v=json.loads((OUT/'review.json').read_text())
    assert v['status']=='passed' and v['results_sha256']==sha(OUT/'results.json')
    assert v['reviewer_sha256']==sha(ROOT/'scripts/review_paid_groundwater.py')
    assert r['controls_sha256']==sha(OUT/'controls.json')
    for name,digest in {**r['producers'],**r['unchanged_sha256']}.items():assert sha(ROOT/name)==digest,name
    for name,digest in v['fresh_byte_exact'].items():assert sha(OUT/name)==digest,name
    with (OUT/'demonstrations.csv').open() as file:rows=list(csv.DictReader(file))
    fig,axes=plt.subplots(2,2,figsize=(12,8),layout='constrained',sharex=True)
    colors=['#455b75','#b57823','#247c65'];styles=['-','--','-']
    for index,case in enumerate(LABELS):
        values=[row for row in rows if row['case']==case]
        series=lambda name:np.array([float(row[name]) for row in values])
        x=np.r_[0,series('day_end')]
        data=[series('aquifer_mm'),series('top_mm')+series('deep_mm'),np.cumsum(series('root_uptake_mm')),np.cumsum(series('river_delivered_m3'))]
        for ax,y in zip(axes.flat,data):ax.plot(x,np.r_[0,y],color=colors[index],ls=styles[index],lw=2,label=LABELS[case])
    axes[1,0].plot(x,np.r_[0,np.cumsum(series('root_potential_mm'))],color='#303030',ls=':',lw=1.5,label='Potential root demand')
    for ax,title,unit in zip(axes.flat,['Accessible aquifer stock','Root-available soil stock','Cumulative root uptake','Cumulative paid river delivery'],['mm','mm','mm','m³']):
        ax.axvspan(0,20,color='#8eafc4',alpha=.15);ax.axvline(20,color='#71828d',ls=':',lw=1)
        ax.set(title=title,ylabel=unit,xlim=(0,60));ax.grid(alpha=.2)
    for ax in axes[1]:ax.set_xlabel('Elapsed day · flood 0–20, crop 20–60')
    axes[0,1].legend(fontsize=8,loc='lower left');axes[1,0].legend(fontsize=8,loc='upper left')
    fig.suptitle('Synthetic finite groundwater · empty first cycle, supplied permissions',fontsize=15)
    fig.supxlabel('Recharge comes from previously paid pond water. Transfer spends the same aquifer stock once.\nRates and capacities illustrate accounting; none is qualified for a Nile field or crop yield.',fontsize=10)
    fig.savefig(OUT/'finite_groundwater.png',dpi=160);plt.close(fig)
    PAGE.mkdir(parents=True,exist_ok=True)
    for name in ['results.json','review.json','controls.json','synthetic.npz','demonstrations.csv','finite_groundwater.png']:shutil.copyfile(OUT/name,PAGE/name)
    for name in ['plan.json','demo_spec.json']:shutil.copyfile(ROOT/'calibration/paid_groundwater_20261114'/name,PAGE/name)
    body=''.join('<tr><th scope="row">'+escape(LABELS[row['case']])+'</th>'+''.join('<td>'+format(row[key],'.3f')+'</td>' for key in KEYS)+'</tr>' for row in r['demonstrations'])
    links=' · '.join(f'<a href="{name}" download>{label}</a>' for name,label in [('plan.json','Declared scope'),('demo_spec.json','Fixed demonstrations'),('results.json','All results and source identities'),('review.json','Independent scalar review'),('controls.json','223 controls'),('demonstrations.csv','All 180 daily rows (CSV)'),('synthetic.npz','All synthetic inputs and histories (NPZ)')])
    html=f'''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Finite groundwater budget · Earth evidence</title>
<style>:root{{color-scheme:light dark;--paper:#eef1ee;--plate:#f9faf7;--ink:#21383a;--rule:#bdcbc4;--accent:#2b7168}}*{{box-sizing:border-box}}body{{margin:0;background:var(--paper);color:var(--ink);font:16px/1.6 system-ui,sans-serif}}main{{max-width:1100px;margin:auto;padding:24px 18px 70px}}h1{{font:600 clamp(2rem,5vw,3rem)/1.15 Georgia,serif}}h2{{font:600 1.6rem Georgia,serif}}a{{color:var(--accent);overflow-wrap:anywhere}}a:focus-visible,.table:focus-visible{{outline:3px solid var(--accent);outline-offset:4px}}section{{margin-top:32px}}p{{max-width:85ch}}figure{{margin:24px 0}}img{{display:block;width:100%;height:auto;background:white}}figcaption{{font-size:.9rem}}.status{{border-left:4px solid var(--accent);background:var(--plate);padding:12px 18px}}.table{{overflow:auto;border:1px solid var(--rule)}}table{{border-collapse:collapse;width:100%;background:var(--plate);font-size:14px}}th,td{{padding:10px;text-align:left;vertical-align:top;border-bottom:1px solid var(--rule)}}@media(prefers-color-scheme:dark){{:root{{--paper:#131d20;--plate:#1c292b;--ink:#e3ebe5;--rule:#435651;--accent:#8ed2b5}}}}</style>
<main><nav><a href="../">Earth evidence</a> · <a href="../../">Atlas hub</a> · <a href="../regional_forcing/">Regional water maps</a> · <a href="../capillary/">Hydraulic source checks</a></nav>
<header><p>EARTH EVIDENCE · 14 NOVEMBER 2026</p><h1>Groundwater transfer spends finite, paid storage</h1><p class="status">The five-stock water budget passes independent replay and exact legacy controls. These are synthetic demonstrations with supplied hydraulic permissions. No Earth groundwater fields are scored, and no yield or settlement change is adopted.</p></header>
<section><h2>Storage and upward permission both matter</h2><p>All three declared cases begin empty on the same 1,000 m² field. Twenty flood days precede forty crop days. Flood supply is 30 m³/day; crop river supply and all rain are zero. ETo is 4 mm/day, crop Kcb is 0.75, pond capacity is 40 mm and shared infiltration allowance is 20 mm/day. The illustrative soil has θFC 0.25, θWP 0.10 and a 1 m root zone. These values are synthetic inputs.</p><p>The two storage cases have 40 mm accessible aquifer capacity and a 5 mm/day recharge limit. One has no upward permission; the other permits at most 3 mm/day during the crop. Neither rate is inferred from a Nile water table or the Dutch hydraulic example.</p><figure><a href="finite_groundwater.png" download><img src="finite_groundwater.png" width="1920" height="1280" alt="Three empty-start synthetic cases compare aquifer and soil stocks, cumulative root uptake and paid river delivery. Finite groundwater recharges 40 mm then empties; stored water without upward permission provides no extra root uptake."></a><figcaption>Flood days are shaded. Empty initial stocks are included in the ledger. Separate repeated-cycle runs converge for all five stocks in two cycles; the displayed results are the empty first cycle.</figcaption></figure><div class="table" tabindex="0" aria-label="All fixed synthetic groundwater demonstrations"><table id="demos"><thead><tr>{''.join('<th scope="col">'+value+'</th>' for value in ['Case','Recharge mm','Upward transfer mm','Final aquifer mm','Root uptake mm','Root demand mm','River delivery m³'])}</tr></thead><tbody>{body}</tbody></table></div><p>Storing 40 mm costs 40 m³ of extra river delivery here. With upward permission, the aquifer empties and root uptake increases by 13.724 mm. Water stored without permission remains inaccessible. Upward transfer is internal redistribution, not an additional source in the joint river/field balance.</p></section>
<section><h2>One ledger for pond, aquifer and soil</h2><p>Each step first debits any supplied aquifer loss, then limits upward transfer by the supplied permission, remaining aquifer stock and soil deficit. Transfer fills deep available water, then the surface pool below wilting point, then top available water. Roots retain their existing restriction to available water.</p><p>Recharge draws only from the previous step's pond stock while pond and recharge permissions are open. It consumes the same infiltration allowance as soil wetting. Fresh river delivery can refill the pond but cannot recharge the aquifer until a later step. Exported percolation, overflow and pond release are not credited again or reused downstream.</p><p>The accessible aquifer store is measured above a supplied inaccessible floor. This budget does not infer water-table depth, hydraulic permission, root suction, transient flow, salinity or oxygen stress. Local soil/root and water-table evidence must qualify those inputs before regional application.</p></section>
<section><h2>Independent accounting checks</h2><p>223 controls pass. All 100 saved synthetic river forests and 4,680 field-steps agree with a separate scalar replay across 105,552 history values; the maximum difference is 1.60×10⁻¹³. All ten zero-groundwater cases reproduce every original field history exactly. Shared infiltration and aquifer capacity limits, all 180 demonstration rows and five-stock periodic states are checked. Three fresh numeric files reproduce byte for byte, and all 937 protected files remain unchanged.</p><p>{links}</p></section>
<section><h2>Next dependency</h2><p>Qualify local hydraulic profiles, root development and suction, seasonal water tables, recharge and drainage before declaring regional groundwater experiments. Keep high-water-table crop constraints, the weather period/grid mismatch, shared Earth/fantasy weather and river inputs, Tigris and independent regions in scope. Freeze harvest translation before testing Nile gain, Mesopotamian non-inflation and whole-empire supply.</p><p>The latest regional water maps and release-3 settlements remain unchanged. Marketed share 0.3923 remains adopted; Egypt calibration still fails.</p></section></main></html>'''
    (PAGE/'index.html').write_text(html)
    index=ROOT/'atlases/earth_evidence/index.html';old=index.read_text();old=re.sub(r'<section id="groundwater-budget">.*?</section>','',old,flags=re.S)
    panel='<section id="groundwater-budget"><h2>Finite groundwater uses the same paid water</h2><p>Independent synthetic replay verifies pond recharge, finite storage and upward transfer. <a href="groundwater_budget/">Open the accounting demonstration and controls →</a></p></section>'
    index.write_text(old.replace('</header>','</header>'+panel,1))
    write(OUT/'publication.json',dict(status='published',publisher_sha256=sha(Path(__file__)),results_sha256=sha(OUT/'results.json'),review_sha256=sha(OUT/'review.json'),files={str(p.relative_to(ROOT)):sha(p) for p in sorted(PAGE.iterdir()) if p.is_file()},evidence_index_sha256=sha(index)))
    print('Published',PAGE.relative_to(ROOT))


if __name__=='__main__':main()
