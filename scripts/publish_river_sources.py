"""Publish the Tigris, capture-season and base-flow steps as one Earth-evidence page."""
import json, re, shutil, sys
from html import escape
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT / 'scripts'))
from settlement_locations_earth import sha, write

PAGE = ROOT / 'atlases/earth_evidence/river_sources'; M = 'mesopotamia_euphrates_only'
STEPS = [('tigris_gauge_20261114', 'review_tigris_gauge.py', 'tigris_gauge.png'), ('tigris_fields_20261114', 'review_tigris_fields.py', 'tigris_fields.png'),
         ('capture_season_20261114', 'review_capture_season_fields.py', 'capture_season.png'), ('base_flow_20261114', 'review_base_flow_fields.py', 'base_flow.png')]
RL = {'flood_excess': 'Flood water above mean', '0.10': '10% of total flow', '0.25': '25% of total flow', '0.50': '50% of total flow'}
WL = {'pre_sowing': 'Pre-sowing (Aug–Oct)', 'in_crop': 'In-crop canal', 'both': 'Both windows'}


def main():
    PAGE.mkdir(parents=True, exist_ok=True); files = {}
    for folder, reviewer, figure in STEPS:
        out = ROOT / 'output' / folder; r = json.loads((out / 'results.json').read_text()); v = json.loads((out / 'review.json').read_text())
        assert v['status'] == 'passed' and v['results_sha256'] == sha(out / 'results.json') and v['reviewer_sha256'] == sha(ROOT / 'scripts' / reviewer), folder
        for name, digest in v['fresh_byte_exact'].items(): assert sha(out / name) == digest, name
        stem = folder.rsplit('_', 1)[0]
        for name in ('results.json', 'review.json', figure): shutil.copyfile(out / name, PAGE / f'{stem}__{name}' if name != figure else PAGE / figure)
    for name in ('calibration/tigris_gauge_20261114/plan.json', 'calibration/tigris_gauge_20261114/field_plan.json', 'calibration/capture_season_20261114/plan.json', 'calibration/base_flow_20261114/plan.json'):
        target = name.split('/')[1].rsplit('_', 1)[0] + '__' + Path(name).name; shutil.copyfile(ROOT / name, PAGE / target)
    shutil.copyfile(ROOT / 'output/tigris_gauge_20261114/gauge_monthly.csv', PAGE / 'tigris_gauge_monthly.csv')
    g = json.loads((ROOT / 'output/tigris_gauge_20261114/results.json').read_text())['comparison']
    cap = json.loads((ROOT / 'output/capture_season_20261114/results.json').read_text())['rows']
    base = json.loads((ROOT / 'output/base_flow_20261114/results.json').read_text())
    pct = lambda x: f'{100 * x:.2f}%'
    cap_rows = ''.join(f'<tr data-region="{x["region"]}"><td>{"Nile" if x["region"] == "nile" else "Mesopotamia"}</td><td>{"5-bin" if x["calendar"] == "old" else "4-bin fractional"}</td><td>{"Hargreaves" if x["method"] == "hargreaves" else "Penman-Monteith"}</td><td>{WL[x["window"]]}</td><td>{pct(x["root_coverage"])}</td><td>{x["delivered_m3"] / 1e9:.2f}</td></tr>' for x in cap)
    base_rows = ''.join(f'<tr data-region="{x["region"]}"><td>{"Nile" if x["region"] == "nile" else "Mesopotamia"}</td><td>{"5-bin" if x["calendar"] == "old" else "4-bin fractional"}</td><td>{"Hargreaves" if x["method"] == "hargreaves" else "Penman-Monteith"}</td><td>{RL[x["source_rule"]]}</td><td>{pct(x["root_coverage"])}</td><td>{x["root_coverage"] * x["eligible_area_km2"]:,.0f}</td><td>{x["delivered_m3"] / 1e9:.2f}</td></tr>' for x in base['rows'])
    downloads = sorted(p.name for p in PAGE.iterdir() if p.suffix in ('.json', '.csv'))
    links = ' · '.join(f'<a href="{n}" download>{escape(n)}</a>' for n in downloads)
    css = (':root{color-scheme:light dark;--paper:#eef1ee;--plate:#f9faf7;--ink:#21383a;--rule:#bdcbc4;--accent:#2b7168}*{box-sizing:border-box}body{margin:0;background:var(--paper);color:var(--ink);font:16px/1.6 system-ui,sans-serif}'
           'main{max-width:1250px;margin:auto;padding:24px 18px 70px}h1{font:600 clamp(2rem,5vw,3rem)/1.15 Georgia,serif}h2{font:600 1.6rem Georgia,serif}a{color:var(--accent);overflow-wrap:anywhere}a:focus-visible,select:focus-visible{outline:3px solid var(--accent);outline-offset:4px}'
           'section{margin-top:32px}p{max-width:85ch}figure{margin:24px 0}img{display:block;width:100%;height:auto;background:white}figcaption{font-size:.9rem}.status{border-left:4px solid var(--accent);background:var(--plate);padding:12px 18px}'
           '.table{overflow:auto;max-height:560px;border:1px solid var(--rule)}table{border-collapse:collapse;width:100%;background:var(--plate);font-size:14px}th,td{padding:9px;text-align:left;border-bottom:1px solid var(--rule)}thead{position:sticky;top:0;background:var(--plate)}'
           'label{display:flex;flex-direction:column;max-width:100%}select{font:inherit;padding:8px;max-width:100%}@media(prefers-color-scheme:dark){:root{--paper:#131d20;--plate:#1c292b;--ink:#e3ebe5;--rule:#435651;--accent:#8ed2b5}}')
    html = f'''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>River sources and capture rules · Earth evidence</title><style>{css}</style>
<main><nav><a href="../">Earth evidence</a> · <a href="../../">Atlas hub</a> · <a href="../matched_weather/">Matched-weather field water</a> · <a href="../../earth_fit/">Current settlement atlas</a></nav>
<header><p>EARTH EVIDENCE · 14 NOVEMBER 2026</p><h1>Tigris, capture season and base flow</h1><p class="status">Three declared development steps on the field-water model. The Tigris is added to Mesopotamia; then the season in which fields may draw river water; then whether they may divert base flow. Only the last moves Mesopotamia much, and the Nile stays the better-watered region throughout. Water diagnostics only: no harvest, population or settlement change.</p></header>
<section><h2>1. The Tigris joins the flood inputs</h2><p>RivDIS Tigris at Mosul qualifies on the Euphrates gauge rules: the same six complete years (1965–67, 1969–71), a May peak, and {g['common_years']['mosul']['positive_excess_km3']:.2f} km³/yr of flood water above its mean. Pooled with the Euphrates: {g['common_years']['hit_plus_mosul']['positive_excess_km3']:.2f} km³/yr against {g['common_years']['hit']['positive_excess_km3']:.2f}. Baghdad has only three complete years and stays unscored. Mosul lies above the Zab, Adhaim and Diyala, so the Tigris is understated; nothing is scaled.</p>
<figure><a href="tigris_gauge.png" download><img src="tigris_gauge.png" width="1950" height="690" alt="Monthly flows of the Nile at Aswan, Euphrates at Hit and Tigris at Mosul; the Tigris and Euphrates peak in May while the Nile peaks in late summer. Bars compare flood water above the annual mean."></a></figure>
<figure><a href="tigris_fields.png" download><img src="tigris_fields.png" width="1950" height="690" alt="With the Tigris added, flood water by month rises but falls outside the August to October capture window; delivered water rises slightly and root-water coverage is unchanged."></a><figcaption>In the field run root water does not change: both rivers flood in spring, after the declared capture window, so the extra water flows past or evaporates before sowing.</figcaption></figure></section>
<section><h2>2. When fields may draw river water</h2><p>Capture before sowing (current), during the standing crop (canal-style refilling of the root zone), or both. The Nile gains 3–6 points; Mesopotamia at most about one. No capture season inflates Mesopotamia.</p>
<figure><a href="capture_season.png" download><img src="capture_season.png" width="1950" height="720" alt="Root-water coverage by capture window: Nile lines between about 50 and 85 percent rise slightly with both windows; Mesopotamia lines stay below 4 percent."></a></figure>
<div class="table" tabindex="0" aria-label="Capture-season runs"><table><thead><tr><th>Region</th><th>Calendar</th><th>Reference ET</th><th>Capture window</th><th>Root water met</th><th>Delivered km³</th></tr></thead><tbody>{cap_rows}</tbody></table></div></section>
<section><h2>3. Whether fields may divert base flow</h2><p>The river source is either flood water above the annual mean (current) or a fixed share of total monthly flow. This is the first change that moves Mesopotamia substantially, up to 18–29% at half the flow, but the Nile saturates first. The grey band in the right panel is the historical Egypt/Mesopotamia population ratio, shown only for orientation.</p>
<figure><a href="base_flow.png" download><img src="base_flow.png" width="2400" height="720" alt="Root water by source rule for the Nile and Mesopotamia, and the Nile to Mesopotamia ratio of fully-watered equivalent area, which falls from about 8 to 22 with flood water only to about 1.3 to 3.4 with base-flow shares."></a></figure>
<p><label>Region<select id="region"><option value="">Both regions</option><option value="nile">Nile</option><option value="{M}">Mesopotamia</option></select></label></p><p id="count" role="status">{len(base['rows'])} base-flow runs</p>
<div class="table" tabindex="0" aria-label="Base-flow runs"><table id="base"><thead><tr><th>Region</th><th>Calendar</th><th>Reference ET</th><th>Source rule</th><th>Root water met</th><th>Fully-watered equivalent km²</th><th>Delivered km³</th></tr></thead><tbody>{base_rows}</tbody></table></div></section>
<section><h2>Checks and limits</h2><p>Each step was declared before its outputs. Every new field run reuses the previously reviewed scalar river, soil and pond reference, with the capture mask separated from the pond mask by declared substitutions and every source rebuilt from the raw gauge pages; fresh runs reproduce all files byte for byte, and the runs that recreate earlier ones reproduce the archived arrays exactly. Limits: Mosul understates the lower Tigris; one ideal pool per region ignores canal command areas, salinity and drainage; modern flows; root water is not grain, area or residents.</p><p>{links}</p></section></main>
<script>document.getElementById('region').addEventListener('change',e=>{{let n=0;for(const row of document.querySelectorAll('#base tbody tr')){{row.hidden=!!e.target.value&&row.dataset.region!==e.target.value;if(!row.hidden)n++;}}document.getElementById('count').textContent=n+' base-flow runs';}});</script></html>'''
    (PAGE / 'index.html').write_text(html)
    evidence = ROOT / 'atlases/earth_evidence/index.html'; old = re.sub(r'<section id="river-sources">.*?</section>', '', evidence.read_text(), flags=re.S)
    panel = '<section id="river-sources"><h2>Tigris, capture season and base flow</h2><p>The Tigris is added to Mesopotamia, then the season and share of river water fields may take. Only base-flow diversion moves Mesopotamia much; the Nile stays better watered. <a href="river_sources/">Open the three steps, charts and all runs →</a></p></section>'
    evidence.write_text(old.replace('</header>', '</header>' + panel, 1))
    files = {str(p.relative_to(ROOT)): sha(p) for p in sorted(PAGE.iterdir()) if p.is_file()}
    write(ROOT / 'output/base_flow_20261114/publication.json', dict(status='published', page='atlases/earth_evidence/river_sources/', files=files, publisher_sha256=sha(Path(__file__)), evidence_index_sha256=sha(evidence)))
    print('published', len(files), 'files')


if __name__ == '__main__':
    main()
