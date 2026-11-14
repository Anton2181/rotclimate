"""Publish the reviewed crop-stage component and its source limitations."""
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
sys.path[:0]=[str(ROOT),str(ROOT/'scripts')]
from harvest.crop_stage import StageCurve
from settlement_locations_earth import sha,write

OUT=ROOT/'output/crop_stage_20261114'
PAGE=ROOT/'atlases/earth_evidence/crop_stage'


def main():
    r=json.loads((OUT/'reference.json').read_text());review=json.loads((OUT/'review.json').read_text())
    assert review['status']=='passed' and review['reference_sha256']==sha(OUT/'reference.json')
    assert review['reviewer_sha256']==sha(ROOT/'scripts/review_crop_stage.py')
    for name,digest in {**r['producers'],**r['unchanged_sha256']}.items():assert sha(ROOT/name)==digest,name
    for name,digest in review['fresh_byte_exact'].items():assert sha(OUT/name)==digest,name
    c=r['example30'];curve=StageCurve(tuple(c['stage_days']),*c['coefficients'])
    ages=np.linspace(0,100,1001);fig,ax=plt.subplots(figsize=(10,4.5),layout='constrained')
    for i,label in enumerate(['Initial','Development','Mid-season','Late season']):
        a,b=curve.edges_days[i:i+2];ax.axvspan(a,b,color='#387b7c',alpha=.07 if i%2 else .14)
        ax.text((a+b)/2,1.36,label,ha='center',fontsize=10)
    ax.plot(ages,curve.value(ages),color='#226f70',lw=2.5)
    for row in c['points']:
        ax.scatter(row['day'],row['value'],color='#ad6225',zorder=3)
        ax.annotate(f"Day {row['day']}: {row['published']}",(row['day'],row['value']),xytext=(0,12),textcoords='offset points',ha='center',fontsize=9)
    ax.set(xlim=(0,100),ylim=(0,1.48),xlabel='Days since planting in the supplied example',ylabel='Basal crop coefficient, Kcb',title='FAO56 Example 30 · dry beans, not a Nile cereal calibration')
    ax.grid(axis='y',alpha=.2)
    fig.supxlabel('Published stage lengths 25 / 25 / 30 / 20 days; supplied Kcb 0.15 / 1.14 / 0.25.\nExact integral 67.975 coefficient-days; mean 0.67975. Kcb includes residual soil diffusion.',fontsize=9)
    fig.savefig(OUT/'crop_stage.png',dpi=160);plt.close(fig)
    PAGE.mkdir(parents=True,exist_ok=True)
    for name in ['reference.json','review.json','intervals.csv','crop_stage.png']:shutil.copyfile(OUT/name,PAGE/name)
    shutil.copyfile(ROOT/'calibration/crop_stage_20261114/plan.json',PAGE/'plan.json')
    table11=''.join('<tr>'+''.join('<td>'+escape(str(v))+'</td>' for v in [row['crop'],' / '.join(map(str,row['stage_days'])),row['total_days'],row['planting'],row['region'] or 'Unspecified in row'])+'</tr>' for row in r['table11'])
    table17=''.join('<tr>'+''.join('<td>'+escape(str(v))+'</td>' for v in [row['crop'],row['kcb_initial_text']+(' (cereal heading)' if row['initial_inherited_from_cereals'] else ''),row['kcb_mid_text'],row['kcb_end_text']])+'</tr>' for row in r['table17'])
    points=''.join(f'<tr><td>{v["day"]}</td><td>{v["published"]}</td><td>{v["value"]:.6f}</td></tr>' for v in c['points'])
    links=' · '.join(f'<a href="{name}" download>{label}</a>' for name,label in [('plan.json','Declared scope'),('reference.json','Source facts and component values'),('review.json','Independent review'),('intervals.csv','277 exact intervals (CSV)')])
    html=f'''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Crop-stage component · Earth evidence</title>
<style>:root{{color-scheme:light dark;--paper:#eef1ee;--plate:#f9faf7;--ink:#21383a;--rule:#bdcbc4;--accent:#2b7168}}*{{box-sizing:border-box}}body{{margin:0;background:var(--paper);color:var(--ink);font:16px/1.6 system-ui,sans-serif}}main{{max-width:1100px;margin:auto;padding:24px 18px 70px}}h1{{font:600 clamp(2rem,5vw,3rem)/1.15 Georgia,serif}}h2{{font:600 1.6rem Georgia,serif}}a{{color:var(--accent);overflow-wrap:anywhere}}a:focus-visible,.table:focus-visible{{outline:3px solid var(--accent);outline-offset:4px}}section{{margin-top:32px}}p{{max-width:85ch}}figure{{margin:24px 0}}img{{display:block;width:100%;height:auto;background:white}}figcaption{{font-size:.9rem}}.status{{border-left:4px solid var(--accent);background:var(--plate);padding:12px 18px}}.table{{overflow:auto;border:1px solid var(--rule)}}table{{border-collapse:collapse;width:100%;background:var(--plate);font-size:14px}}th,td{{padding:10px;text-align:left;vertical-align:top;border-bottom:1px solid var(--rule)}}@media(prefers-color-scheme:dark){{:root{{--paper:#131d20;--plate:#1c292b;--ink:#e3ebe5;--rule:#435651;--accent:#8ed2b5}}}}</style>
<main><nav><a href="../">Earth evidence</a> · <a href="../../">Atlas hub</a> · <a href="../daily_fields/">Daily water maps</a> · <a href="../rain_timing/">Rain timing</a></nav>
<header><p>EARTH EVIDENCE · 14 NOVEMBER 2026</p><h1>Crop demand changes through four supplied growth stages</h1><p class="status">The mathematical curve and source extraction are verified. Local cereal stages, climatic adjustment and root uptake remain unqualified. This component does not change harvests or settlements.</p></header>
<section><h2>A published component check</h2><p>A supplied curve holds its initial coefficient, rises linearly during development, holds its mid-season value, then changes linearly to its final value. Exact interval integrals give a mean coefficient for each actual step duration, including steps crossing stage boundaries.</p><figure><a href="crop_stage.png" download><img src="crop_stage.png" width="1600" height="720" alt="Four-stage dry-bean curve from FAO56 Example 30, with published point checks at days 12, 37, 65 and 90. This is not an Earth cereal fit."></a><figcaption>Dry beans are the published arithmetic example. The curve is not adopted for Nile barley.</figcaption></figure><div class="table" tabindex="0" aria-label="Published point benchmark"><table id="points"><thead><tr><th scope="col">Day</th><th scope="col">FAO rounded value</th><th scope="col">Component value</th></tr></thead><tbody>{points}</tbody></table></div></section>
<section><h2>Basal ET is not pure root transpiration</h2><p>FAO56 defines Kcb × ETo as primarily transpiration, with residual diffusion from below the dry soil surface and beneath dense vegetation. The earlier water scenarios used legacy crop coefficients as supplied constant root-demand coefficients. A later stage curve needs an explicit decision about that residual flux and the crop uptake operator.</p><p>Table 17 assumes minimum relative humidity of 45% and wind speed of 2 m/s. FAO requires climatic adjustment of mid/end coefficients above 0.45 outside the reference conditions. These generic coefficients are source facts, not locally measured ancient crop parameters.</p><div class="table" tabindex="0" aria-label="FAO Table 17 cereal coefficients"><table id="coefficients"><thead><tr><th scope="col">Crop</th><th scope="col">Initial Kcb</th><th scope="col">Mid Kcb</th><th scope="col">End Kcb</th></tr></thead><tbody>{table17}</tbody></table></div><p>Winter-wheat initial values 0.15 and 0.5 refer to sparse ground cover and a fully covered, nonfrozen dormant winter period respectively. Its higher end value 0.3 is for hand harvesting. They are contextual alternatives, not unconstrained fitting ranges. Blank barley/spring initial cells inherit the cereal heading; they are not zero.</p></section>
<section><h2>Stage durations retain their original context</h2><p>FAO Table 11 gives these cereal examples for particular planting dates and climates. No row below establishes a Nile barley calendar. An unspecified source region is kept unspecified.</p><div class="table" tabindex="0" aria-label="FAO Table 11 cereal stage durations"><table id="stages"><thead><tr><th scope="col">Source crop group</th><th scope="col">Initial / development / mid / late days</th><th scope="col">Total days</th><th scope="col">Planting</th><th scope="col">Source region</th></tr></thead><tbody>{table11}</tbody></table></div><p>The California winter-wheat initial/development lengths carry footnote 2: these periods lengthen in frozen climates according to dormancy and days without growth potential. The 240-day Mediterranean winter-wheat example cannot silently replace a supplied four- or five-bin barley calendar.</p></section>
<section><h2>Checks and downloads</h2><p>137 controls pass, including 20 new component controls. Independent Decimal arithmetic checks the four published points and rounding, all 277 exported intervals, and 4,000 intervals over 100 synthetic curves. Two fresh numeric files reproduce byte for byte; all {review['protected_files']} protected files remain unchanged. This is published component agreement, not independent regional validation.</p><p>{links}</p><p>Primary sources: <a href="https://www.fao.org/4/x0490e/x0490e0b.htm">FAO56 Chapter 6, Table 11</a> and <a href="https://www.fao.org/4/x0490e/x0490e0c.htm">Chapter 7, Table 17 and Example 30</a>. Raw-source digests and context are retained in the downloads.</p></section>
<section><h2>Next dependency</h2><p>Qualify local phenology, reference evaporation and climatic adjustment, basal diffusion versus root uptake, canopy exposure, root development and inundation/drainage dates before declaring an Earth stage-curve comparison. Do not choose stage ratios because they improve Egypt. Tigris, independent regions and shared Earth/fantasy river flow remain open.</p><p>The release-3 settlement atlas and marketed share 0.3923 remain current; whole-empire Egypt calibration still fails.</p></section></main></html>'''
    (PAGE/'index.html').write_text(html)
    index=ROOT/'atlases/earth_evidence/index.html';s=index.read_text();s=re.sub(r'<section id="crop-stage-component">.*?</section>','',s,flags=re.S)
    panel='<section id="crop-stage-component"><h2>Crop-stage source constraints and exact curves</h2><p>Four-stage coefficient integration now reproduces the published FAO example. <a href="crop_stage/">See source contexts, checks and the limits on an Earth crop comparison →</a></p></section>'
    index.write_text(s.replace('</header>','</header>'+panel,1))
    write(OUT/'publication.json',dict(status='published',publisher_sha256=sha(Path(__file__)),reference_sha256=sha(OUT/'reference.json'),review_sha256=sha(OUT/'review.json'),files={str(p.relative_to(ROOT)):sha(p) for p in sorted(PAGE.iterdir()) if p.is_file()},evidence_index_sha256=sha(index)))
    print('Published',PAGE.relative_to(ROOT))


if __name__=='__main__':main()
