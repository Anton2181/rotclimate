"""Publish reviewed soil-drying components and a supplied fractional clock."""
import csv,json,re,shutil
from html import escape
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
ROOT=Path(__file__).resolve().parents[1]
import sys
sys.path.insert(0,str(ROOT/'scripts'))
from settlement_locations_earth import sha,write
OUT=ROOT/'output/soil_drying_20261114';PAGE=ROOT/'atlases/earth_evidence/soil_drying'


def main():
    r=json.loads((OUT/'results.json').read_text());review=json.loads((OUT/'review.json').read_text())
    assert review['status']=='passed' and review['results_sha256']==sha(OUT/'results.json')
    assert review['reviewer_sha256']==sha(ROOT/'scripts/review_soil_drying.py')
    for name,digest in {**r['producers'],**r['unchanged_sha256']}.items():assert sha(ROOT/name)==digest,name
    for name,digest in review['fresh_byte_exact'].items():assert sha(OUT/name)==digest,name
    with (OUT/'benchmarks.csv').open() as f:checks=list(csv.DictReader(f))
    fig,axes=plt.subplots(1,2,figsize=(11,4.4),layout='constrained')
    tables=[]
    for ax,example,column,label in [(axes[0],31,5,'Surface evaporation (mm/day)'),(axes[1],37,6,'Actual crop ET (mm/day)')]:
        data=[v for v in checks if int(v['example'])==example and int(v['column'])==column]
        days=[int(v['day']) for v in data];printed=[float(v['published_value']) for v in data];model=[float(v['model_value']) for v in data]
        ax.plot(days,model,color='#266e84',label='Unrounded model')
        ax.errorbar(days,printed,yerr=[float(v['tolerance']) for v in data],color='#a66b27',fmt='o',ms=4,capsize=3,label='FAO printed value ± rounding')
        ax.set_title('FAO-56 Example '+str(example));ax.set_xlabel('Drying day');ax.set_ylabel(label);ax.grid(alpha=.2);ax.legend(fontsize=8)
        rows=''.join('<tr>'+''.join(f'<td>{escape(value)}</td>' for value in [str(int(v['day'])),v['source_text'],f'{float(v["model_value"]):.6f}',f'{float(v["tolerance"]):.3g}'])+'</tr>' for v in data)
        tables.append(f'<article><h3>Example {example}</h3><p>{label}</p><div class="table"><table><thead><tr><th>Day</th><th>FAO printed</th><th>Model</th><th>Rounding tolerance</th></tr></thead><tbody>{rows}</tbody></table></div></article>')
    fig.suptitle('Published component checks · all 140 numeric cells match printed precision',fontsize=12)
    fig.supxlabel('Example 31 checks surface drying; Example 37 checks root stress for a tomato profile.\nThese checks do not validate combined uptake allocation or Nile soil parameters.',fontsize=9)
    fig.savefig(OUT/'component_checks.png',dpi=160);plt.close(fig)
    with np.load(OUT/'fields.npz') as z:
        fig,axes=plt.subplots(1,2,figsize=(11,4.4),layout='constrained')
        for label,color,title in [('bare','#a66b27','Bare surface'),('crop','#266e84','Active crop')]:
            top=np.r_[z[label+'__initial_top_mm'],z[label+'__top_mm']];deep=np.r_[z[label+'__initial_deep_mm'],z[label+'__deep_mm']];bound=np.r_[z[label+'__initial_bound_mm'],z[label+'__bound_mm']]
            axes[0].plot(range(61),top+bound,label=title,color=color)
            axes[1].plot(range(61),top+deep,label=title,color=color)
        for ax in axes:ax.set_xlabel('Day without new water');ax.grid(alpha=.2);ax.legend(fontsize=9)
        axes[0].set_title('Surface water · TEW capacity 20 mm');axes[0].set_ylabel('Top available + surface below-WP pool (mm)')
        axes[1].set_title('Root-available water · TAW capacity 150 mm');axes[1].set_ylabel('Top available + deeper available (mm)')
        fig.suptitle('Two depth layers, three physical pools · the shared top pool is counted once',fontsize=12)
        fig.supxlabel('Declared synthetic profile: FC 0.25, WP 0.10, root depth 1 m, surface depth 0.10 m, REW 9 mm.\nInitial wet stock 155 mm counted. Bare Kcb=0 omits deeper diffusive evaporation; no local soil or harvest fit.',fontsize=9)
        fig.savefig(OUT/'synthetic_drying.png',dpi=160);plt.close(fig)
    PAGE.mkdir(parents=True,exist_ok=True)
    for name in ('results.json','review.json','controls.json','benchmarks.csv','fields.npz','component_checks.png','synthetic_drying.png'):shutil.copyfile(OUT/name,PAGE/name)
    for name in ('plan.json','clock_amendment.json'):shutil.copyfile(ROOT/'calibration/soil_drying_20261114'/name,PAGE/name)
    downloads=' · '.join(f'<a href="{name}" download>{label}</a>' for name,label in [('plan.json','Original declaration'),('clock_amendment.json','Clock declaration'),('benchmarks.csv','All 140 printed/model checks (CSV)'),('fields.npz','Daily states, forcing and clock (NPZ)'),('results.json','Results and provenance'),('review.json','Independent review and replay'),('controls.json','90 controls')])
    clock=r['clock']
    html=f'''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Soil drying and exact supplied calendar · Earth evidence</title>
<style>:root{{color-scheme:light dark;--paper:#eef1ee;--plate:#f9faf7;--ink:#21383a;--rule:#bdcbc4;--accent:#2b7168}}*{{box-sizing:border-box}}body{{margin:0;background:var(--paper);color:var(--ink);font:16px/1.6 system-ui,sans-serif}}main{{max-width:1150px;margin:auto;padding:24px 18px 70px}}h1{{font:600 clamp(2rem,5vw,3rem)/1.15 Georgia,serif}}h2{{font:600 1.6rem Georgia,serif}}a{{color:var(--accent);overflow-wrap:anywhere}}a:focus-visible{{outline:3px solid var(--accent);outline-offset:4px}}p{{max-width:85ch}}section{{margin-top:32px}}figure{{margin:24px 0}}img{{display:block;width:100%;height:auto;background:white}}figcaption{{font-size:.9rem}}.status{{border-left:4px solid var(--accent);padding:12px 18px;background:var(--plate)}}.grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(100%,420px),1fr));gap:20px}}article{{min-width:0}}.table{{overflow:auto;border:1px solid var(--rule)}}table{{width:100%;border-collapse:collapse;background:var(--plate);font-size:14px}}td,th{{text-align:left;vertical-align:top;padding:10px;border-bottom:1px solid var(--rule)}}@media(prefers-color-scheme:dark){{:root{{--paper:#131d20;--plate:#1c292b;--ink:#e3ebe5;--rule:#435651;--accent:#8ed2b5}}}}</style>
<main><nav><a href="../">Earth evidence</a> · <a href="../../">Atlas hub</a> · <a href="../flood_storage/">Earlier field-water maps</a> · <a href="../../earth_fit/">Current settlement atlas</a></nav>
<header><p>EARTH EVIDENCE · 14 NOVEMBER 2026</p><h1>Surface drying and root water share a finite supply</h1><p class="status">Separate soil drying and root-stress components now match the published FAO examples. The combined physical ledger and exact supplied calendar pass independent checks. No new Earth field, yield or population score has been computed.</p></header>
<section><h2>The same water cannot sit in two independent stores</h2><p>Surface evaporable water and root-available water overlap in the shallow soil. The model partitions physical water into top plant-available water, deeper plant-available water and surface water below wilting point that evaporation can remove but roots cannot use. The top pool contributes to both diagnostics and is stored once.</p><p>Supplied water refills the pools and pays drainage explicitly. Evaporation uses only surface water, then root uptake draws proportionally from remaining plant-available water. Initial wet stocks, delivered inputs, both ET fluxes and drainage close the same ledger. This operator and uptake allocation remain declared approximations.</p></section>
<section><h2>Published component checks</h2><p>Example 31 tests surface drying for ten days. Example 37 tests root stress on a tomato profile for ten days; it does not set cereal or Nile parameters. All 140 printed numeric cells agree within half of their last displayed decimal. The independent review uses the original source rows and 40-digit Decimal arithmetic.</p><figure><a href="component_checks.png" download><img src="component_checks.png" width="1760" height="704" alt="Two FAO drying curves compare printed values and rounding tolerance with unrounded model values. Surface evaporation declines as the upper soil dries; root-zone stress reduces crop ET."></a><figcaption>Full source/model values for every column are in the CSV. Passing component equations does not validate the combined model's uptake or drainage assumptions.</figcaption></figure><div class="grid">{''.join(tables)}</div></section>
<section><h2>Combined water accounting</h2><p>Independent scalar simulations check 36,000 profile-days and 108,000 compartment states across 200 synthetic columns. Every physical pool stays bounded; surface and root losses spend the same water. Maximum observed model daily closure error is {review['max_model_daily_mass_residual_mm']:.2g} mm, a numerical precision check rather than a measure of physical accuracy.</p><figure><a href="synthetic_drying.png" download><img src="synthetic_drying.png" width="1760" height="704" alt="A declared sixty-day no-water example compares surface and root water in bare and cropped columns. The bare surface cannot evaporate directly from the deep root store."></a><figcaption>Synthetic profile and initial water are supplied explicitly. The pure-bare case sets Kcb=0 and omits deeper diffusive evaporation, leaving its deeper 135 mm store unchanged by policy. This is not evidence of indefinite deep-water retention in real soils or an Earth harvest prediction.</figcaption></figure></section>
<section><h2>A clock that retains supplied event boundaries</h2><p>The clock splits at climate-bin, daily and supplied event boundaries. Monthly totals are distributed by duration; rates and temperatures are repeated without duration scaling. Every resulting step is at most one day, and soil fluxes receive its actual duration.</p><p>The declared mathematical example has {clock['steps']} segments in 365 days. Its supplied capture window spans {clock['capture_days']:.6f} days and its wrapping crop window {clock['crop_days']:.6f} days, with no overlap. Decimal integration independently recovers all twelve source-bin totals for both example columns. Dates and uniform within-bin forcing remain unqualified for actual fields.</p></section>
<section><h2>Evidence and remaining work</h2><p>Ninety controls pass. Three fresh numeric files reproduce byte for byte. All 904 Earth-fit assets and the three numeric files for all 96 earlier field-water cases remain unchanged.</p><p>{downloads}</p><p>Sources: <a href="https://www.fao.org/4/x0490e/x0490e0c.htm">FAO-56 Chapter 7, equations 71/74 and Example 31</a>; <a href="https://www.fao.org/4/x0490e/x0490e0e.htm">Chapter 8, equation 84 and Example 37</a>.</p><p>Next is a declared daily river-to-field adapter with paid transfers and pond/drainage rules, qualified soil and crop calendars, and independent region evidence. Root development, groundwater recharge, Tigris coverage and flood access remain open. The current settlement atlas and whole-empire Egypt calibration failure are unchanged.</p></section></main></html>'''
    (PAGE/'index.html').write_text(html)
    evidence=ROOT/'atlases/earth_evidence/index.html';old=evidence.read_text();old=re.sub(r'<section id="soil-drying-components">.*?</section>','',old,flags=re.S)
    panel='<section id="soil-drying-components"><h2>Surface drying, root stress and a supplied daily clock</h2><p>Published FAO component checks and shared-pool water balances pass; no new Earth harvest or settlement adoption. <a href="soil_drying/">Open source checks, physical drydowns and numeric downloads →</a></p></section>'
    evidence.write_text(old.replace('</header>','</header>'+panel,1))
    write(OUT/'publication.json',dict(status='published',publisher_sha256=sha(Path(__file__)),results_sha256=sha(OUT/'results.json'),review_sha256=sha(OUT/'review.json'),files={str(p.relative_to(ROOT)):sha(p) for p in sorted(PAGE.iterdir()) if p.is_file()},evidence_index_sha256=sha(evidence)))
    print('Published',PAGE.relative_to(ROOT))


if __name__=='__main__':main()
