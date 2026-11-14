"""Publish the reviewed rain-timing sensitivity as a normal Earth-evidence page."""
import json, re, shutil, sys
from html import escape
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT / 'scripts'))
from settlement_locations_earth import sha, write

OUT = ROOT / 'output/rain_timing_20261114'; PAGE = ROOT / 'atlases/earth_evidence/rain_timing'
PATTERNS = ['uniform', 'events1', 'events2', 'events4']; NAMES = {'uniform': 'Uniform', 'events1': '1 event', 'events2': '2 events', 'events4': '4 events'}
REGION = {'nile': 'Nile', 'mesopotamia_euphrates_only': 'Mesopotamia · Euphrates only'}


def main():
    r = json.loads((OUT / 'results.json').read_text()); review = json.loads((OUT / 'review.json').read_text())
    assert review['status'] == 'passed' and review['results_sha256'] == sha(OUT / 'results.json') and review['reviewer_sha256'] == sha(ROOT / 'scripts/review_rain_timing_fields.py')
    for name, digest in {**r['producers'], **r['unchanged_sha256']}.items(): assert sha(ROOT / name) == digest, name
    for name, digest in review['fresh_byte_exact'].items(): assert sha(OUT / name) == digest, name
    rows = r['rows']; get = lambda region, calendar, capture, pattern: next(v for v in rows if v['region'] == region and v['calendar'] == calendar and v['capture'] == capture and v['rain_pattern'] == pattern)
    fig, axes = plt.subplots(1, 2, figsize=(12, 4.6), layout='constrained')
    for ax, capture, title in ((axes[0], True, 'River capture'), (axes[1], False, 'Rain only')):
        for region, color in (('nile', '#266e84'), ('mesopotamia_euphrates_only', '#a66b27')):
            for calendar, style in (('old', '-o'), ('fractional', '--s')):
                ax.plot(range(4), [100 * get(region, calendar, capture, p)['root_coverage'] for p in PATTERNS], style, color=color, label=f"{REGION[region]} · {'5-bin' if calendar == 'old' else '4-bin fractional'}")
        ax.set_xticks(range(4), [NAMES[p] + ('\nper month' if p != 'uniform' else '\nwithin month') for p in PATTERNS]); ax.set_title(title); ax.set_ylabel('Root water demand met (%)'); ax.grid(alpha=.2)
        if capture: ax.set_ylim(0, 100)
    axes[1].legend(fontsize=8)
    fig.suptitle('Rain timing inside the month hardly changes root-water coverage · totals conserved', fontsize=12)
    fig.supxlabel('Same monthly rain on every field, delivered uniformly or as 1, 2 or 4 one-day events. Fixed illustration: barley, 1.5 m roots, bare coefficient 0.15, pond 200 mm, efficiency 1.\nSynthetic sensitivity: events are synchronized scenarios, not observed storms; no pattern is preferred or adopted.', fontsize=9)
    fig.savefig(OUT / 'rain_timing.png', dpi=160); plt.close(fig)
    PAGE.mkdir(parents=True, exist_ok=True)
    for name in ['results.json', 'review.json', 'fields.npz', 'rain_timing.png']: shutil.copyfile(OUT / name, PAGE / name)
    shutil.copyfile(ROOT / 'calibration/rain_timing_20261114/plan.json', PAGE / 'plan.json')
    pct = lambda v: f'{100 * v:.2f}%'; km3 = lambda v: f'{v / 1e9:.3f}'
    cells = lambda v: [REGION[v['region']], '5-bin' if v['calendar'] == 'old' else '4-bin fractional', 'River capture' if v['capture'] else 'Rain only', NAMES[v['rain_pattern']],
                       pct(v['root_coverage']), f"{v['adequate_root_area_km2']:,.0f}", km3(v['rain_m3']), km3(v['surface_evap_m3']), km3(v['root_uptake_m3']), str(v['spinup_years'])]
    table = ''.join(f'<tr data-region="{v["region"]}" data-access="{int(v["capture"])}">' + ''.join('<td>' + escape(x) + '</td>' for x in cells(v)) + '</tr>' for v in rows)
    headers = ['Region', 'Calendar', 'Access', 'Rain pattern', 'Root demand met', '≥95% root km²', 'Rain km³', 'Surface evaporation km³', 'Root uptake km³', 'Spin-up years']
    spread = review['coverage_by_pattern']; biggest = max(spread.values(), key=lambda v: v['range']); nile = [v for k, v in spread.items() if k.startswith('nile') and k.endswith('_c1')]
    links = ' · '.join(f'<a href="{name}" download>{label}</a>' for name, label in [('plan.json', 'Protocol'), ('results.json', 'All results/provenance'), ('review.json', 'Independent review/replay'), ('fields.npz', 'Field states/monthly ledgers (NPZ)')])
    html = f'''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Rain timing sensitivity · Earth evidence</title>
<style>:root{{color-scheme:light dark;--paper:#eef1ee;--plate:#f9faf7;--ink:#21383a;--rule:#bdcbc4;--accent:#2b7168}}*{{box-sizing:border-box}}body{{margin:0;background:var(--paper);color:var(--ink);font:16px/1.6 system-ui,sans-serif}}main{{max-width:1250px;margin:auto;padding:24px 18px 70px}}h1{{font:600 clamp(2rem,5vw,3rem)/1.15 Georgia,serif}}h2{{font:600 1.6rem Georgia,serif}}a{{color:var(--accent);overflow-wrap:anywhere}}a:focus-visible,select:focus-visible{{outline:3px solid var(--accent);outline-offset:4px}}section{{margin-top:32px}}p{{max-width:85ch}}figure{{margin:24px 0}}img{{display:block;width:100%;height:auto;background:white}}figcaption{{font-size:.9rem}}.status{{border-left:4px solid var(--accent);background:var(--plate);padding:12px 18px}}.table{{overflow:auto;max-height:650px;border:1px solid var(--rule)}}table{{border-collapse:collapse;width:100%;background:var(--plate);font-size:14px}}th,td{{padding:10px;text-align:left;vertical-align:top;border-bottom:1px solid var(--rule)}}thead{{position:sticky;top:0;background:var(--plate)}}.filters{{display:flex;flex-wrap:wrap;gap:18px;margin:18px 0}}label{{display:flex;flex-direction:column;min-width:0;max-width:100%}}select{{font:inherit;padding:8px;max-width:100%}}@media(prefers-color-scheme:dark){{:root{{--paper:#131d20;--plate:#1c292b;--ink:#e3ebe5;--rule:#435651;--accent:#8ed2b5}}}}</style>
<main><nav><a href="../">Earth evidence</a> · <a href="../../">Atlas hub</a> · <a href="../daily_fields/">Daily river-to-field water</a> · <a href="../../earth_fit/">Current settlement atlas</a></nav>
<header><p>EARTH EVIDENCE · 14 NOVEMBER 2026</p><h1>When rain falls inside the month hardly matters here</h1><p class="status">A declared sensitivity on the eight mapped illustrations. With every field's monthly rain conserved exactly, delivering it as one, two or four one-day events instead of uniformly changes root-water coverage by at most {100 * biggest['range']:.2f} percentage points. With river capture on the Nile the change is at most {100 * max(v['range'] for v in nile):.2f} points. Uniform rain is therefore not what limits these results. No pattern is preferred or adopted.</p></header>
<section><h2>The question</h2><p>The daily coupling spreads monthly rain evenly inside each month. Light daily rain can evaporate from the surface while the same amount in a storm might soak in, so uniform rain could have understated crop water. This experiment holds everything else fixed and changes only the timing.</p><figure><a href="rain_timing.png" download><img src="rain_timing.png" width="1920" height="736" alt="Two panels show root water demand met for four rain timing patterns. With river capture the Nile lines stay flat near 65 and 79 percent and the Euphrates lines near 4 to 5 percent. With rain only all lines stay below 6 percent."></a><figcaption>Root transpiration actual/potential, area-weighted over crop-eligible candidate fields. It is not crop yield, irrigated area or residents.</figcaption></figure></section>
<section><h2>All 32 cases</h2><div class="filters"><label>Region<select id="region"><option value="">Both regions</option><option value="nile">Nile</option><option value="mesopotamia_euphrates_only">Mesopotamia · Euphrates only</option></select></label><label>Access<select id="access"><option value="">Capture and rain only</option><option value="1">River capture</option><option value="0">Rain only</option></select></label></div><p id="count" role="status">32 scenarios</p><div class="table" tabindex="0" aria-label="Rain timing scenario table, horizontally scrollable"><table><thead><tr>{''.join('<th scope="col">' + h + '</th>' for h in headers)}</tr></thead><tbody>{table}</tbody></table></div></section>
<section><h2>Clock control</h2><p>All four patterns run on one common clock that contains every event boundary, so they differ only in rain. That clock is finer than the original one. Uniform rain on the common clock reproduces the archived original-clock coverage to within {100 * review['max_clock_control_coverage_difference']:.3f} percentage points; that difference is a step-size effect and is reported separately from rain timing.</p></section>
<section><h2>Independent checks</h2><p>Twelve preflight controls passed before any Earth output, including exact bin and field totals on arbitrary clocks and a decimal overlap reference. The review rebuilds the pulse rain from first principles, reuses the previously reviewed scalar river, pond and soil ledger, and compares {review['field_steps']:,} field-steps: eligibility, annual field stocks and fluxes, monthly basin ledgers and daily basin stocks. Largest annual field difference {review['max_annual_field_difference_mm']:.1e} mm. A fresh run reproduces both numeric files byte for byte, and every protected earlier file is unchanged.</p><p>{links}</p></section>
<section><h2>What this does and does not show</h2><p>It removes one suspected cause: within-month rain timing does not explain the low rain-only coverage or the Nile shortfall. It does not model storm runoff or deeper infiltration from intense rain, which the plan excluded, and the events are synchronized across all fields, unlike real storms. Soil profiles, root development, crop coefficients, pond access and drainage dates remain unqualified, Mesopotamia still lacks the Tigris, and no harvest rule follows from these water diagnostics.</p></section></main>
<script>function filter(){{let n=0;const ids=['region','access'];for(const row of document.querySelectorAll('tbody tr')){{row.hidden=ids.some(id=>{{const v=document.getElementById(id).value;return v&&row.dataset[id]!==v;}});if(!row.hidden)n++;}}document.getElementById('count').textContent=n+' scenarios';}}for(const id of ['region','access'])document.getElementById(id).addEventListener('change',filter);</script></html>'''
    (PAGE / 'index.html').write_text(html)
    evidence = ROOT / 'atlases/earth_evidence/index.html'; old = re.sub(r'<section id="rain-timing">.*?</section>', '', evidence.read_text(), flags=re.S)
    panel = '<section id="rain-timing"><h2>Rain timing inside the month hardly matters</h2><p>32 conserved-total cases: one, two or four rain events per month instead of uniform rain change root-water coverage by under one percentage point. <a href="rain_timing/">Open all cases, the chart and the independent review →</a></p></section>'
    evidence.write_text(old.replace('</header>', '</header>' + panel, 1))
    write(OUT / 'publication.json', dict(status='published', publisher_sha256=sha(Path(__file__)), results_sha256=sha(OUT / 'results.json'), review_sha256=sha(OUT / 'review.json'),
        files={str(p.relative_to(ROOT)): sha(p) for p in sorted(PAGE.iterdir()) if p.is_file()}, evidence_index_sha256=sha(evidence)))
    print('Published', PAGE.relative_to(ROOT), 'largest pattern range', round(100 * biggest['range'], 3), 'points')


if __name__ == '__main__':
    main()
