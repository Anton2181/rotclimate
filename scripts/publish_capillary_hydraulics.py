"""Publish the reviewed stationary capillary example and source-context limits."""
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

OUT=ROOT/'output/capillary_hydraulics_20261114'
PAGE=ROOT/'atlases/earth_evidence/capillary'


def main():
    r=json.loads((OUT/'reference.json').read_text());v=json.loads((OUT/'review.json').read_text())
    assert v['status']=='passed' and v['reference_sha256']==sha(OUT/'reference.json')
    assert v['reviewer_sha256']==sha(ROOT/'scripts/review_capillary_hydraulics.py')
    assert r['controls_sha256']==sha(OUT/'controls.json')
    for name,digest in {**r['producers'],**r['unchanged_sha256']}.items():assert sha(ROOT/name)==digest,name
    for name,digest in v['fresh_byte_exact'].items():assert sha(OUT/name)==digest,name
    with (OUT/'benchmarks.csv').open() as file:rows=list(csv.DictReader(file))
    fig,ax=plt.subplots(figsize=(10,5.5),layout='constrained')
    for index,flux in enumerate(r['fluxes_mm_day']):
        values=[row for row in rows if float(row['flux_mm_day'])==flux];color=plt.cm.viridis(index/5)
        head=-np.array([float(row['suction_cm']) for row in values]);height=np.array([float(row['model_z_cm']) for row in values])
        ax.plot(head,height,color=color,lw=2,label=f'{flux:g} mm/day')
        ax.scatter(head,[float(row['source_z_cm']) for row in values],color=color,s=10,marker='o')
    ax.set(xlim=(-400,0),ylim=(0,410),xlabel='Pressure head h (cm; suction magnitude = −h)',ylabel='Height above water table z (cm)',title='FAO61 stationary capillary example · generic Dutch silty subsoil O8')
    ax.grid(alpha=.2);ax.legend(title='Prescribed upward flux',loc='upper right',fontsize=9)
    fig.supxlabel('Lines use the supplied hydraulic relation; dots are all 246 rounded published heights.\nThis relation creates no water. Local depth, soil, recharge and finite storage remain separate inputs.',fontsize=9)
    fig.savefig(OUT/'stationary_capillary.png',dpi=160);plt.close(fig)
    PAGE.mkdir(parents=True,exist_ok=True)
    for name in ['reference.json','review.json','controls.json','benchmarks.csv','hydraulic_functions.csv','stationary_capillary.png']:shutil.copyfile(OUT/name,PAGE/name)
    shutil.copyfile(ROOT/'calibration/capillary_hydraulics_20261114/plan.json',PAGE/'plan.json')
    summaries=[]
    for flux in r['fluxes_mm_day']:
        values=[row for row in rows if float(row['flux_mm_day'])==flux];last=values[-1]
        summaries.append([f'{flux:g}',last['source_z_text'],f"{float(last['model_z_cm']):.6f}",f"{float(last['error_cm']):+.6f}",str(sum(int(row['within_rounding']) for row in values))+' / 41'])
    endpoint=''.join('<tr>'+''.join('<td>'+escape(cell)+'</td>' for cell in row)+'</tr>' for row in summaries)
    soils=''.join('<tr>'+''.join('<td>'+escape(str(value))+'</td>' for value in [row['code'],*[row[key] for key in ['theta_residual','theta_saturated','ksat_cm_day','alpha_cm_inv','connectivity','n']]])+'</tr>' for row in r['soil_parameters_table_a5_4'])
    links=' · '.join(f'<a href="{name}" download>{label}</a>' for name,label in [('plan.json','Declared scope'),('reference.json','Source facts/parameters'),('review.json','Independent Decimal review'),('controls.json','208 controls'),('benchmarks.csv','All 246 profile checks (CSV)'),('hydraulic_functions.csv','All 448 hydraulic samples (CSV)')])
    html=f'''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Capillary hydraulics component · Earth evidence</title>
<style>:root{{color-scheme:light dark;--paper:#eef1ee;--plate:#f9faf7;--ink:#21383a;--rule:#bdcbc4;--accent:#2b7168}}*{{box-sizing:border-box}}body{{margin:0;background:var(--paper);color:var(--ink);font:16px/1.6 system-ui,sans-serif}}main{{max-width:1100px;margin:auto;padding:24px 18px 70px}}h1{{font:600 clamp(2rem,5vw,3rem)/1.15 Georgia,serif}}h2{{font:600 1.6rem Georgia,serif}}a{{color:var(--accent);overflow-wrap:anywhere}}a:focus-visible,.table:focus-visible{{outline:3px solid var(--accent);outline-offset:4px}}section{{margin-top:32px}}p{{max-width:85ch}}figure{{margin:24px 0}}img{{display:block;width:100%;height:auto;background:white}}figcaption{{font-size:.9rem}}.status{{border-left:4px solid var(--accent);background:var(--plate);padding:12px 18px}}.table{{overflow:auto;max-height:650px;border:1px solid var(--rule)}}table{{border-collapse:collapse;width:100%;background:var(--plate);font-size:14px}}th,td{{padding:10px;text-align:left;vertical-align:top;border-bottom:1px solid var(--rule)}}thead{{position:sticky;top:0;background:var(--plate)}}@media(prefers-color-scheme:dark){{:root{{--paper:#131d20;--plate:#1c292b;--ink:#e3ebe5;--rule:#435651;--accent:#8ed2b5}}}}</style>
<main><nav><a href="../">Earth evidence</a> · <a href="../../">Atlas hub</a> · <a href="../regional_forcing/">Regional water maps</a> · <a href="../crop_stage/">Crop-stage constraints</a></nav>
<header><p>EARTH EVIDENCE · 14 NOVEMBER 2026</p><h1>Capillary hydraulics matches the published example</h1><p class="status">All 246 published stationary profile heights agree within their printed rounding. This verifies a supplied-soil relation and source context. It supplies no groundwater, adds no root-zone storage and changes no field or settlement result.</p></header>
<section><h2>Flux, soil suction and height are distinct inputs</h2><p>The FAO61 example prescribes six upward fluxes and computes the pressure-head profile for generic Dutch silty subsoil O8. Van Genuchten conductivity and the midpoint Darcy recurrence determine the curves. The rate is not selected by a crop-water deficit, and the soil is not a measured Nile profile.</p><figure><a href="stationary_capillary.png" download><img src="stationary_capillary.png" width="1600" height="880" alt="Six stationary capillary curves for the supplied FAO61 O8 silty soil, with all published rounded profile points. No local groundwater availability is inferred."></a><figcaption>The zero-flux case is hydrostatic. Conductivity is cm/day while the prescribed flux is mm/day; conversion is explicit. Heights are above the water table, not measured depths below a Nile field.</figcaption></figure><div class="table" tabindex="0" aria-label="Published capillary endpoint checks"><table id="endpoints"><thead><tr>{''.join('<th scope="col">'+value+'</th>' for value in ['Flux mm/day','Published z at h=−400 cm','Model z cm','Model−published cm','Within rounding'])}</tr></thead><tbody>{endpoint}</tbody></table></div></section>
<section><h2>Historical support does not set a universal rate</h2><p>Butzer's 1976 discussion on printed page 19 uses Omo, Senegal and Chari–Logone floodplain analogies for prehistoric Nile ecology. Its capillary/high-water-table description is not an observation of Roman Nile groundwater flux. The summer water table of at least 3–4 m on printed page 90 is a summer description; it cannot be inserted as a winter depth.</p><p>Butzer 1984 describes high post-flood water tables qualitatively. FAO56 treats capillary input separately in the root-zone water budget and offers an approximate one-metre-below-root convention. Later FAO61 curves depend on soil and boundary conditions; that convention is not a universal hydraulic cutoff.</p><p>A field application still needs local hydraulic properties, water-table history, root suction and a finite water budget. Any recharge must come from the same paid river/field system. No unlimited capillary inflow, larger root-zone TAW or inferred crop gain follows from these curves.</p></section>
<section><h2>All source hydraulic parameter profiles</h2><p>FAO61 Table A5.4 supplies 28 Dutch topsoil/subsoil parameter sets. These are context-preserved source parameters, not defaults for Egypt. θ values are cm³/cm³; Ksat is cm/day; α is cm⁻¹; connectivity and n are dimensionless. Generated water-content/conductivity samples are evaluations of this model, not extra observations or an exact reproduction of the separate fitted Table A5.3.</p><div class="table" tabindex="0" aria-label="All FAO61 hydraulic source parameters"><table id="soils"><thead><tr>{''.join('<th scope="col">'+value+'</th>' for value in ['Code','θ residual','θ saturated','Ksat cm/day','α cm⁻¹','Connectivity','n'])}</tr></thead><tbody>{soils}</tbody></table></div></section>
<section><h2>Independent checks and downloads</h2><p>208 controls pass, including 26 new hydraulic controls. Two source-table parsing paths agree; a separate 50-digit Decimal implementation checks direct source-equation conductivity, water content and signed-head recurrence without importing the component or producer. It verifies 896 hydraulic sample cells and all 246 profile cells. Three fresh numeric exports reproduce byte for byte; all 932 protected files remain unchanged.</p><p>{links}</p><p>Primary sources: <a href="https://www.fao.org/4/y4263e/y4263e0i.htm">FAO61 Annex 5, Equations 4/6 and Tables A5.4/A5.5</a>, <a href="https://www.fao.org/4/x0490e/x0490e0e.htm">FAO56 Chapter 8</a>, and <a href="https://isac.uchicago.edu/publications/early-hydraulic-civilization-egypt-study-cultural-ecology">Butzer 1976, official publication and PDF</a>. Raw-source URLs/digests and page locators are retained in the downloads.</p></section>
<section><h2>Next dependency</h2><p>Declare finite paid groundwater recharge/storage and its transfer to the existing soil/river ledger before any new groundwater field experiment. Qualify depths, soil/root/canopy and drainage; preserve the forcing-period/grid limitations and all matched controls. Local phenology, Tigris, shared Earth/fantasy flow and independent regions remain open.</p><p>The regional forcing experiment and release-3 settlements remain unchanged. Marketed share 0.3923 remains adopted; whole-empire Egypt calibration still fails.</p></section></main></html>'''
    (PAGE/'index.html').write_text(html)
    index=ROOT/'atlases/earth_evidence/index.html';old=index.read_text();old=re.sub(r'<section id="capillary-hydraulics">.*?</section>','',old,flags=re.S)
    panel='<section id="capillary-hydraulics"><h2>Capillary source constraints and hydraulic curves</h2><p>The published stationary example is reproduced without granting groundwater. <a href="capillary/">Open the curves, 28 source profiles and historical-context checks →</a></p></section>'
    index.write_text(old.replace('</header>','</header>'+panel,1))
    write(OUT/'publication.json',dict(status='published',publisher_sha256=sha(Path(__file__)),reference_sha256=sha(OUT/'reference.json'),review_sha256=sha(OUT/'review.json'),files={str(p.relative_to(ROOT)):sha(p) for p in sorted(PAGE.iterdir()) if p.is_file()},evidence_index_sha256=sha(index)))
    print('Published',PAGE.relative_to(ROOT))


if __name__=='__main__':main()
