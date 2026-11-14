"""Publish the reviewed reference-method comparison and complete weather inputs."""
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

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from settlement_locations_earth import sha,write

OUT=ROOT/'output/reference_eto_20261114'
PAGE=ROOT/'atlases/earth_evidence/reference_eto'
LABELS={'cairo':'Cairo','aswan':'Aswan','hit':'Hit · Euphrates'}


def summary_cells(row):
    return [LABELS[row['site']],f"{row['pm_mean_annual_mm']:,.0f}",f"{row['hargreaves_mean_annual_mm']:,.0f}",f"{row['atlas_style_mean_annual_mm']:,.0f}",f"{100*row['hargreaves_over_pm']:.1f}%",f"{100*row['nov_mar']['hargreaves_over_pm']:.1f}%",str(row['valid_days']),str(row['cloud_ratio_clipped_days'])]


def month_cells(row):
    return [LABELS[row['site']],str(row['month']),*[f'{row[name]:.3f}' for name in ['pm_mean_mm_day','hargreaves_mean_mm_day','atlas_style_hargreaves_mm_day','bias_mm_day','aggregation_effect_mm_day','geometry_effect_mm_day']]]


def main():
    r=json.loads((OUT/'results.json').read_text());v=json.loads((OUT/'review.json').read_text())
    assert v['status']=='passed' and v['results_sha256']==sha(OUT/'results.json')
    assert v['reviewer_sha256']==sha(ROOT/'scripts/review_reference_eto_weather.py')
    for name,digest in {**r['producers'],**r['sources'],**r['unchanged_sha256']}.items():assert sha(ROOT/name)==digest,name
    for name,digest in v['fresh_byte_exact'].items():assert sha(OUT/name)==digest,name
    fig,axes=plt.subplots(2,3,figsize=(13,7),layout='constrained')
    for col,(site,label) in enumerate(LABELS.items()):
        rows=[row for row in r['climatology'] if row['site']==site]
        month=[row['month'] for row in rows];top,bottom=axes[:,col]
        for key,title,color,style in [('pm_mean_mm_day','FAO Penman–Monteith','#226f70','-'),('hargreaves_mean_mm_day','Daily Hargreaves','#b06825','-'),('atlas_style_hargreaves_mm_day','Atlas-style monthly','#5d6d7e',':')]:
            top.plot(month,[row[key] for row in rows],label=title,color=color,ls=style,lw=2)
        top.set_title(label);top.set_ylabel('Reference ETo (mm/day)');top.set_ylim(bottom=0)
        for key,title,color,style in [('bias_mm_day','Daily Hargreaves − PM','#b06825','-'),('aggregation_effect_mm_day','Monthly aggregation effect','#3a7b9b','--'),('geometry_effect_mm_day','Legacy solar geometry effect','#5d6d7e',':')]:
            bottom.plot(month,[row[key] for row in rows],label=title,color=color,ls=style,lw=2)
        bottom.axhline(0,color='#555',lw=.7);bottom.set_ylabel('Difference (mm/day)');bottom.set_xlabel('Gregorian calendar month')
        for ax in (top,bottom):ax.set_xticks([1,3,5,7,9,11]);ax.grid(alpha=.18)
        if col==0:top.legend(fontsize=8);bottom.legend(fontsize=7)
    fig.suptitle('Reference methods diverge on the same 2020–2024 gridded weather',fontsize=15)
    fig.supxlabel('NASA POWER development locations; neither curve is observed crop ET.\nAtlas-style uses the same monthly weather with the unchanged equal-bin solar approximation; no field forcing is replaced.',fontsize=9)
    fig.savefig(OUT/'reference_eto.png',dpi=160);plt.close(fig)
    PAGE.mkdir(parents=True,exist_ok=True)
    for name in ['results.json','review.json','daily.csv','reference_eto.png']:shutil.copyfile(OUT/name,PAGE/name)
    shutil.copyfile(ROOT/'calibration/reference_eto_20261114/plan.json',PAGE/'plan.json')
    shutil.copyfile(ROOT/'data/source/reference_eto_20261114/sources.json',PAGE/'sources.json')
    shutil.copyfile(OUT/'core/review.json',PAGE/'core_review.json')
    for site in LABELS:shutil.copyfile(ROOT/f'data/source/reference_eto_20261114/{site}.json',PAGE/f'source_{site}.json')
    yearly=''.join('<tr>'+''.join('<td>'+escape(cell)+'</td>' for cell in summary_cells(row))+'</tr>' for row in r['summaries'])
    months=''.join(f'<tr data-site="{row["site"]}" data-month="{row["month"]}">'+''.join('<td>'+escape(cell)+'</td>' for cell in month_cells(row))+'</tr>' for row in r['climatology'])
    downloads=[('plan.json','Declared protocol'),('sources.json','Frozen source receipt'),('core_review.json','Preflight controls'),('results.json','Results and all aggregates'),('review.json','Independent review/replay'),('daily.csv','All 5,481 daily rows (CSV)'),('source_cairo.json','Raw Cairo weather'),('source_aswan.json','Raw Aswan weather'),('source_hit.json','Raw Hit weather')]
    links=' · '.join(f'<a href="{name}" download>{label}</a>' for name,label in downloads)
    clipped=sum(row['cloud_ratio_clipped_days'] for row in r['summaries'])
    html=f'''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Reference evaporation audit · Earth evidence</title>
<style>:root{{color-scheme:light dark;--paper:#eef1ee;--plate:#f9faf7;--ink:#21383a;--rule:#bdcbc4;--accent:#2b7168}}*{{box-sizing:border-box}}body{{margin:0;background:var(--paper);color:var(--ink);font:16px/1.6 system-ui,sans-serif}}main{{max-width:1250px;margin:auto;padding:24px 18px 70px}}h1{{font:600 clamp(2rem,5vw,3rem)/1.15 Georgia,serif}}h2{{font:600 1.6rem Georgia,serif}}a{{color:var(--accent);overflow-wrap:anywhere}}a:focus-visible,select:focus-visible,.table:focus-visible{{outline:3px solid var(--accent);outline-offset:4px}}section{{margin-top:32px}}p{{max-width:85ch}}figure{{margin:24px 0}}img{{display:block;width:100%;height:auto;background:white}}figcaption{{font-size:.9rem}}.status{{border-left:4px solid var(--accent);background:var(--plate);padding:12px 18px}}.table{{overflow:auto;max-height:650px;border:1px solid var(--rule)}}table{{border-collapse:collapse;width:100%;background:var(--plate);font-size:14px}}th,td{{padding:10px;text-align:left;vertical-align:top;border-bottom:1px solid var(--rule)}}thead{{position:sticky;top:0;background:var(--plate)}}.filters{{display:flex;flex-wrap:wrap;gap:18px;margin:18px 0}}label{{display:flex;flex-direction:column;max-width:100%}}select{{font:inherit;padding:8px;max-width:100%}}@media(prefers-color-scheme:dark){{:root{{--paper:#131d20;--plate:#1c292b;--ink:#e3ebe5;--rule:#435651;--accent:#8ed2b5}}}}</style>
<main><nav><a href="../">Earth evidence</a> · <a href="../../">Atlas hub</a> · <a href="../crop_stage/">Crop-stage constraints</a> · <a href="../daily_fields/">Daily water maps</a></nav>
<header><p>EARTH EVIDENCE · 14 NOVEMBER 2026</p><h1>Two reference methods diverge on the same weather</h1><p class="status">On the declared 2020–2024 NASA POWER gridded weather, daily Hargreaves totals are 19–30% below FAO56 Penman–Monteith. This identifies a material forcing uncertainty. It is a reference-method comparison, not observed field evaporation or a calibrated harvest update.</p></header>
<section><h2>Same weather, separate method and geometry effects</h2><p>Both daily methods receive identical temperatures and FAO solar geometry at Cairo, Aswan and Hit. Penman–Monteith additionally uses supplied solar radiation, 2 m wind, pressure and dewpoint. All 5,481 requested dates pass the declared source checks; no dates are imputed or discarded.</p><figure><a href="reference_eto.png" download><img src="reference_eto.png" width="2080" height="1120" alt="Six panels compare three reference-evaporation calculations and separate method, monthly aggregation and solar geometry differences at Cairo, Aswan and Hit on fixed 2020–2024 gridded weather."></a><figcaption>The atlas-style line applies the unchanged monthly formula and solar approximation to the same modern monthly weather. It does not show the archived WorldClim field forcing and does not replace it. Bottom panels separate method, aggregation and solar geometry effects.</figcaption></figure></section>
<section><h2>Five-year average annual totals</h2><p>Totals are millimetres per year averaged across 2020–2024, including leap days. November–March ratios pool those Gregorian months; they are not the earlier equal-bin crop calendars. PM denotes the declared Penman–Monteith reference equation.</p><div class="table" tabindex="0" aria-label="Annual reference-method summary"><table id="annual"><thead><tr>{''.join('<th scope="col">'+value+'</th>' for value in ['Location','PM mm/year','Daily Hargreaves mm/year','Atlas-style mm/year','Daily Hargreaves / PM','Nov–Mar Hargreaves / PM','Valid days','Cloud-ratio clamp days'])}</tr></thead><tbody>{yearly}</tbody></table></div></section>
<section><h2>Every climatological month</h2><p>Values below are mm/day. The method difference is daily Hargreaves minus PM. The aggregation effect compares Hargreaves on monthly mean weather with the average of daily Hargreaves; the geometry effect then applies the existing atlas solar approximation. Scroll horizontally for all values.</p><div class="filters"><label>Location<select id="site"><option value="">All locations</option>{''.join(f'<option value="{key}">{label}</option>' for key,label in LABELS.items())}</select></label><label>Month<select id="month"><option value="">All months</option>{''.join(f'<option value="{month}">{month}</option>' for month in range(1,13))}</select></label></div><p id="count" role="status">36 location-months</p><div class="table" tabindex="0" aria-label="Monthly reference-method comparisons"><table id="climate"><thead><tr>{''.join('<th scope="col">'+value+'</th>' for value in ['Location','Month','PM','Daily Hargreaves','Atlas-style','Method difference','Aggregation effect','Geometry effect'])}</tr></thead><tbody>{months}</tbody></table></div></section>
<section><h2>Inputs and approximation limits</h2><p>NASA POWER provides MERRA2/SYN1DEG/POWER gridded products, not station observations or ancient weather. Grid elevations are 135.44 m at Cairo, 253.64 m at Aswan and 79.59 m at Hit. API coordinates name development locations; they are not surveyed station elevations. The API returns solar radiation in MJ/m²/day here, so no kWh conversion is applied.</p><p>The daily grass-reference calculation uses albedo 0.23 and soil heat flux zero. Actual vapour pressure comes from daily mean dewpoint. Its empirical longwave cloud ratio is bounded to 0.3–1; {clipped} days trigger that declared bound, including 156 at Aswan. No negative raw daily ETo occurs. All intermediates and raw source values are retained.</p><p>The current atlas solar function uses equal climate-bin midpoints and a circular-orbit approximation, without the Earth–Sun distance factor in FAO geometry. Its difference also includes the phase/bin convention. This audit quantifies the combined geometry effect and leaves the existing function unchanged.</p><p>Daily mean relative humidity is not daily minimum relative humidity. It cannot directly supply FAO Equation 70's crop-coefficient climate adjustment. The audit does not qualify local phenology, basal diffusion versus root uptake, canopy/root development or drainage.</p></section>
<section><h2>Independent checks and complete inputs</h2><p>159 controls pass. Before weather ETo was calculated, FAO Example 18 reproduced its rounded 3.9 mm/day, Example 8 its 32.2 MJ/m²/day, and 1,000 synthetic weather days agreed with an independent scalar/Decimal reference. The weather review checks all 98,658 daily numeric cells, 180 site-year-month rows, 15 annual rows and 36 climatological rows. Two fresh numeric exports reproduce byte for byte; 920 protected files remain unchanged.</p><p>{links}</p><p>Source methods: <a href="https://www.fao.org/4/x0490e/x0490e06.htm">FAO56 Chapter 2, Equation 6</a>, <a href="https://www.fao.org/4/x0490e/x0490e07.htm">Chapter 3, weather inputs and Equation 52</a>, <a href="https://www.fao.org/4/x0490e/x0490e08.htm">Chapter 4, Example 18</a>, and <a href="https://power.larc.nasa.gov/">NASA POWER</a>. The frozen protocol's Equation 52 chapter locator is corrected in the results metadata; both chapters were pinned from the outset.</p></section>
<section><h2>What this changes in the work queue</h2><p>The earlier water-adequacy results remain conditional on their evaporation forcing. Neither a site multiplier nor a preferred crop calendar is adopted. A later regional forcing comparison needs a declared spatial weather/reference policy and qualification of humidity, wind, radiation, period and grid representativeness, followed by matched field controls and independent evidence.</p><p>All three locations are development. This comparison does not demonstrate ancient reference evaporation, measured crop ET, regional harvest non-inflation or whole-empire calibration. Tigris/shared Earth-fantasy flow and independent regions remain open. Release-3 settlements and marketed share 0.3923 remain current; Egypt calibration still fails.</p></section></main>
<script>function filter(){{let n=0;for(const row of document.querySelectorAll('#climate tbody tr')){{row.hidden=['site','month'].some(key=>{{const v=document.getElementById(key).value;return v&&row.dataset[key]!==v;}});if(!row.hidden)n++;}}document.getElementById('count').textContent=n+' location-months';}}for(const key of ['site','month'])document.getElementById(key).addEventListener('change',filter);</script></html>'''
    (PAGE/'index.html').write_text(html)
    index=ROOT/'atlases/earth_evidence/index.html';old=index.read_text();old=re.sub(r'<section id="reference-eto-audit">.*?</section>','',old,flags=re.S)
    panel='<section id="reference-eto-audit"><h2>Reference evaporation remains a material input uncertainty</h2><p>Three fixed locations and 5,481 matched-weather days compare Hargreaves with FAO reference evaporation. <a href="reference_eto/">Open every monthly comparison, raw weather and independent checks →</a></p></section>'
    index.write_text(old.replace('</header>','</header>'+panel,1))
    write(OUT/'publication.json',dict(status='published',publisher_sha256=sha(Path(__file__)),results_sha256=sha(OUT/'results.json'),review_sha256=sha(OUT/'review.json'),files={str(p.relative_to(ROOT)):sha(p) for p in sorted(PAGE.iterdir()) if p.is_file()},evidence_index_sha256=sha(index)))
    print('Published',PAGE.relative_to(ROOT))


if __name__=='__main__':main()
