"""Publish the reviewed gauge timing preflight without changing map inputs."""
import calendar
import hashlib
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
OUT=ROOT/'output/flood_basin_seasonality_20261113'
PAGE=ROOT/'atlases/earth_evidence/flood_basin'


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    result=json.loads((OUT/'results.json').read_text());review=json.loads((OUT/'review.json').read_text())
    assert review['status']=='passed' and review['results_sha256']==sha(OUT/'results.json')
    assert review['reviewer_sha256']==sha(ROOT/'scripts/review_flood_basin_seasonality.py')
    for name,digest in {**result['producers'],**result['unchanged_atlas_sha256']}.items():assert sha(ROOT/name)==digest,name
    for name,digest in review['fresh_byte_exact'].items():assert sha(OUT/name)==digest,name
    PAGE.mkdir(parents=True,exist_ok=True)
    months=list(calendar.month_abbr)[1:];fig,axes=plt.subplots(2,2,figsize=(12,7.5),layout='constrained')
    labels={'aswan':'Nile · Aswan','hit':'Euphrates · Hit DS'}
    rows=[]
    for column,row in enumerate(result['rows'][:2]):
        mean=np.asarray(row['mean_monthly_flow_m3s']);ax=axes[0,column]
        ax.bar(range(12),mean,color='#337d8b');ax.axhline(mean.mean(),color='#925f26',ls='--',label='Mean across months')
        years=row['complete_years'];ax.set_title(f"{labels[row['id']]} · {years[0]}–{years[-1]} ({len(years)} complete years)",fontsize=11)
        ax.set_ylabel('Monthly mean discharge (m³/s)');ax.set_xticks(range(12),months,rotation=45);ax.legend(fontsize=8)
        phase=next(v for v in row['phase'] if v['crop_months']==5);ax=axes[1,column]
        ax.plot(range(12),phase['pre_sowing_excess_share'],label='Three months before sowing',color='#337d8b')
        ax.plot(range(12),phase['standing_crop_excess_share'],label='Five-month standing crop',color='#b16d25')
        ax.plot(range(12),phase['compatibility'],label='Compatibility: max(0, before − during)',color='#3f6e37',ls='--')
        ax.scatter([10],[phase['compatibility'][10]],color='#3f6e37',s=35,zorder=4)
        ax.set_xticks(range(12),months,rotation=45);ax.set_xlabel('Sowing month (all months retained)');ax.set_ylim(-.03,1.05);ax.set_ylabel('Share of above-mean discharge');ax.legend(fontsize=8,loc='upper left')
        for ax in axes[:,column]:ax.grid(axis='y',alpha=.18);ax.set_axisbelow(True)
        n=row['november_illustration']
        coverage='1871–1901' if row['id']=='aswan' else '1965–1967, 1969–1971'
        rows.append(f'<tr><th scope="row">{labels[row["id"]]}</th><td>{coverage}</td><td>{len(years)}</td><td>{months[row["peak_month"]-1]}</td><td>{n["compatibility"]:.3f}</td></tr>')
    fig.suptitle('Flood timing preflight · development gauges only',fontsize=15)
    fig.supxlabel('November / five-month illustration frozen before values. Indus unscored: no qualifying pre-1932 record.\nTiming is not water volume, irrigable area or a calibrated harvest increase.',fontsize=10)
    fig.savefig(OUT/'seasonality.png',dpi=160);plt.close(fig)
    files=['seasonality.png','results.json','review.json','controls.json','fields.npz','phase.csv','gauge_monthly.csv','sources.json']
    for name in files:shutil.copyfile(OUT/name,PAGE/name)
    shutil.copyfile(ROOT/'calibration/flood_basin_seasonality_20261113/plan.json',PAGE/'plan.json')
    links=' · '.join(f'<a href="{n}" download>{escape(n)}</a>' for n in ['plan.json','sources.json','review.json','controls.json','phase.csv','gauge_monthly.csv','fields.npz','results.json'])
    sources=json.loads((OUT/'sources.json').read_text());citations=''.join(f'<li><a href="{escape(s["url"])}">{escape(s["citation"])}</a> ({escape(s["license"])})</li>' for s in sources.values())
    html=f'''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Flood timing preflight · Earth evidence</title><style>
:root{{color-scheme:light dark;--paper:#eef1ee;--plate:#f9faf7;--ink:#21383a;--rule:#bdcbc4;--accent:#2b7168}}*{{box-sizing:border-box}}body{{margin:0;background:var(--paper);color:var(--ink);font:16px/1.6 system-ui,sans-serif}}main{{max-width:1100px;margin:auto;padding:24px 18px 70px}}h1{{font:600 clamp(2rem,5vw,3rem)/1.15 Georgia,serif}}h2{{font:600 1.6rem Georgia,serif}}a{{color:var(--accent);overflow-wrap:anywhere}}a:focus-visible{{outline:3px solid var(--accent);outline-offset:4px}}section{{margin-top:30px}}p{{max-width:85ch}}figure{{margin:24px 0}}img{{display:block;width:100%;height:auto;background:white}}figcaption{{font-size:.9rem}}.table{{overflow:auto;border:1px solid var(--rule)}}table{{width:100%;border-collapse:collapse;background:var(--plate)}}td,th{{text-align:left;vertical-align:top;padding:12px;border-bottom:1px solid var(--rule)}}.status{{border-left:4px solid var(--accent);padding:12px 18px;background:var(--plate)}}code{{overflow-wrap:anywhere}}@media(prefers-color-scheme:dark){{:root{{--paper:#131d20;--plate:#1c292b;--ink:#e3ebe5;--rule:#435651;--accent:#8ed2b5}}}}</style>
<main><nav><a href="../">Earth evidence</a> · <a href="../../">Atlas hub</a> · <a href="../../earth_fit/">Earth-calibrated settlement atlas</a></nav>
<header><p>EARTH EVIDENCE · 13 NOVEMBER 2026</p><h1>Can flood timing distinguish the Nile from Mesopotamia?</h1>
<p class="status">The development gauges show a strong seasonal distinction. The held-out Indus check is unscored. This is input preparation; the flood-basin irrigation rule has not been calibrated or adopted.</p></header>
<section><h2>Why this matters</h2><p>The current harvest model underproduces in Egypt. Low, nearby floodplain terrain identifies about 24,600 km² there, close to the historical cultivated area. The same terrain rule identifies 64,000 km² in Lower Mesopotamia, where the model already overproduces. Terrain alone cannot justify adding irrigation.</p>
<p>The Nile has high flow before winter sowing. The Euphrates peaks in May. This predeclared diagnostic measures how much above-mean flow occurs in the three months before sowing and how much overlaps the crop. It retains every sowing month and crop durations of three through nine months.</p></section>
<section><h2>Fixed November illustration</h2><p>For both development gauges, sowing in November and a five-month crop were declared before reading discharge values. Compatibility is max(0, pre-sowing excess share − standing-crop excess share): 0.944 for the Nile and 0.049 for the Euphrates. It is a dimensionless timing diagnostic, not a percentage of land irrigated.</p>
<div class="table"><table><thead><tr><th>Gauge</th><th>Retained years</th><th>Complete years</th><th>Peak month</th><th>Compatibility</th></tr></thead><tbody>{''.join(rows)}<tr><th scope="row">Indus · Kotri</th><td>1900–1931 requested</td><td>Unscored</td><td>Unscored</td><td>Unscored</td></tr></tbody></table></div>
<figure><a href="seasonality.png" download><img src="seasonality.png" width="1920" height="1200" alt="Monthly discharge and all twelve sowing-month timing diagnostics for Nile Aswan and Euphrates Hit. Nile peaks in September, Euphrates in May. November compatibility is 0.944 for Nile and 0.049 for Euphrates."></a><figcaption>Equal-weight means of complete years; units m³/s. Earlier local water management is not assumed absent. The Indus series starts in 1936, after the declared pre-Sukkur cutoff, so no regulated substitute is scored.</figcaption></figure></section>
<section><h2>Source quality and independent checks</h2><p>Aswan retains 1871–1901 before the first Aswan dam. Its incomplete 1869 and 1870 are excluded. Hit retains 1965–1967 and 1969–1971 before major Tabqa/Keban impoundment; every excluded year is listed in the results. These observations establish timing inputs, not ancient discharge or flood reliability.</p>
<p>Fifteen controls passed before output. Independent raw-HTML parsing, Decimal means and scalar cyclic arithmetic checked 1,469 observations, 168 season combinations and 504 phase values. Five rebuilt output files match byte for byte; 904 existing Earth atlas files remain unchanged.</p><p>{links}</p></section>
<section><h2>What is still needed for the map</h2><p>A water budget, flood delivery and travel times, drainage constraints, and defensible crop calendars. Fully watered crop seasons can tie in the current optimizer, so simply choosing the best timing window would introduce a hidden selection rule. A field rule and independent test regions must be declared before scoring irrigated areas or population capacity.</p><p>The published release-3 settlements and adopted marketed share 0.3923 remain current. The whole-empire supply calibration still fails because of Egypt. This preflight does not change those results.</p></section>
<section><h2>Sources and attribution</h2><ul>{citations}</ul><p>Historical calendar context: <a href="https://sites.utexas.edu/butzer/wp-content/uploads/sites/6106/2017/07/Butzer-1984-LongTermNile.pdf">Butzer (1984), long-term Nile flood discharge and basin agriculture</a>. Numeric input hashes, publisher representations and licenses are in the source manifest.</p></section></main></html>'''
    (PAGE/'index.html').write_text(html)
    evidence=ROOT/'atlases/earth_evidence/index.html';old=evidence.read_text()
    section='<section id="flood-basin-preflight"><h2>Flood-basin irrigation: timing inputs</h2><p>Nile and Euphrates gauge timing checked; Indus remains unscored. No new irrigated area or harvest adoption. <a href="flood_basin/">Open the source audit, season spectra and numeric downloads →</a></p></section>'
    old=re.sub(r'<section id="flood-basin-preflight">.*?</section>','',old,flags=re.S)
    evidence.write_text(old.replace('</header>','</header>'+section,1))
    receipt=dict(status='published',publisher_sha256=sha(Path(__file__)),results_sha256=sha(OUT/'results.json'),review_sha256=sha(OUT/'review.json'),files={str(p.relative_to(ROOT)):sha(p) for p in sorted(PAGE.iterdir()) if p.is_file()},evidence_index_sha256=sha(evidence))
    (OUT/'publication.json').write_text(json.dumps(receipt,indent=2)+'\n')
    print('Published',PAGE.relative_to(ROOT))


if __name__=='__main__':main()
