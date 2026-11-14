"""Publish one Earth-evidence page stating what each layer of the default settlement map is calibrated against."""
import json, re, shutil, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT / 'scripts'))
from settlement_locations_earth import sha, write

PAGE = ROOT / 'atlases/earth_evidence/settlement_calibration'; O = ROOT / 'output'
FIGS = {'settlement_release2_20261113.png': (2100, 644), 'settlement_release3_20261113.png': (1820, 616),
        'settlement_supply_calibration_20261113.png': (1820, 630), 'vidarbha_release3_20261114.png': (1760, 572),
        'floodplain_rule_20261114.png': None, 'greek_walls_20261114.png': None, 'fantasy_floodplain_20261114.png': None}


def load(path):
    return json.loads((O / path).read_text())


def main():
    PAGE.mkdir(parents=True, exist_ok=True)
    r2 = load('settlement_release2_20261113/results.json'); b = load('settlement_placement_iteration_20261113/family_b/results.json')
    s = load('settlement_supply_calibration_20261113/without_egypt/results.json'); sv = load('settlement_supply_calibration_20261113/without_egypt/review.json')
    whole = load('settlement_supply_calibration_20261113/results.json'); fz = load('settlement_supply_calibration_20261113/without_egypt/fantasy_at_calibrated_share.json')
    v = load('vidarbha_release3_20261114/results.json'); vr = load('vidarbha_release3_20261114/review.json')
    assert vr['status'] == 'passed' and vr['results_sha256'] == sha(O / 'vidarbha_release3_20261114/results.json')
    assert sv['status'] == 'passed' and b['passed'] and v['guard']['guard_pass']
    gw = load('greek_walls_20261114/results.json'); gwr = load('greek_walls_20261114/review.json'); sg = load('sizes_greek_walls_20261114/results.json')
    sup = load('sizes_greek_walls_20261114/supply/results.json'); assert gwr['status'] == 'passed' and gw['primary_pass'] and sg['sizes']['primary']['gate']['passed']
    gwd = gw['variants']['greece']['decision']; m1g = sg['sizes']['primary']['models']['M1']; s34 = sup['climates']['corrected']['scenarios'][f"central_x{int(round(sup['marketed_share'] * 100)):02d}"]
    copies_extra = {'greek_walls__results.json': 'greek_walls_20261114/results.json', 'greek_walls__review.json': 'greek_walls_20261114/review.json',
                    'sizes_greek_walls__results.json': 'sizes_greek_walls_20261114/results.json', 'floodplain_rule__results.json': 'floodplain_rule_20261114/results.json',
                    'floodplain_rule__review.json': 'floodplain_rule_20261114/review.json'}
    m1 = r2['sizes']['primary']['models']['M1']; res = r2['residents']; d = s['decision']; g = v['guard']; x39 = fz['central_x39']
    copies = {'release2__results.json': 'settlement_release2_20261113/results.json', 'placement_family_b__results.json': 'settlement_placement_iteration_20261113/family_b/results.json',
              'supply_without_egypt__results.json': 'settlement_supply_calibration_20261113/without_egypt/results.json', 'supply_without_egypt__review.json': 'settlement_supply_calibration_20261113/without_egypt/review.json',
              'supply_fantasy_at_calibrated_share.json': 'settlement_supply_calibration_20261113/without_egypt/fantasy_at_calibrated_share.json',
              'vidarbha_release3__results.json': 'vidarbha_release3_20261114/results.json', 'vidarbha_release3__review.json': 'vidarbha_release3_20261114/review.json'}
    bl = load('geography_control_20261107/blind.json')['pools']
    copies.update(copies_extra)
    for target, source in copies.items(): shutil.copyfile(O / source, PAGE / target)
    for name in FIGS: shutil.copyfile(ROOT / 'reports/figures' / name, PAGE / name)
    w270 = whole['surface']['270']['all']['fed_share']; shares = whole['surface'] and json.loads((ROOT / 'calibration/settlement_supply_calibration_20261113/plan.json').read_text())['parameters']['marketed_share_e']
    whole_third = w270[[round(e, 4) for e in shares].index(0.3333)]
    rows = [
        ('Town count', 'Earth-fitted', 'people<sup>0.7</sup>×area<sup>0.3</sup>, one seat per 40,000 people; total error 1.6–2.3% on Han and Rome', 'Kept: a better exponent gained only 1.9%', 'SETTLEMENT_RELEASE2_20261113.md'),
        ('Town positions', 'Earth-fitted, cross-pool', f'Catchment tiling with a heartland prior exp(−D/800 km), chosen on one pool and scored on the other: {b["quadrant_wins"]}/8 quadrants better than production', 'Passed. Vidarbha (exposed, not blind): no loss against production', 'SETTLEMENT_RELEASE3_20261113.md'),
        ('Town sizes (area)', 'Earth-fitted, held-out', f'Hanson 2016 official areas, Greek wall circuits at their inhabited share (Hansen 2008), province-blocked folds: lnA = {m1g["full_coefficients"][0]:.3f} + {m1g["full_coefficients"][1]:.3f} lnH, held-out σ {m1g["heldout_sigma"]:.2f}', f'Passed (KS {sg["sizes"]["primary"]["gate"]["mean_ks"]:.3f}). Size barely depends on local people: mostly scatter', 'SIZES_GREEK_WALLS_20261114.md'),
        ('Residents', 'Literature relationship', f'Sliding 100→500 people/ha (Hanson). Roman check: {res["central_total_all_885_official_areas"] / 1e6:.1f} M in 885 towns vs published {res["published_reference_range"][0] / 1e6:.1f}–{res["published_reference_range"][1] / 1e6:.1f} M', 'Inside the published range; owner choice of reading', 'SETTLEMENT_RELEASE2_20261113.md'),
        ('Lore ranking', 'Owner rule', 'Marked places keep their lore order on final size', 'Binding; not an Earth test', 'SETTLEMENT_RELEASE2_20261113.md'),
        ('Grain supply', 'Earth-fitted, whole empire (development)', f'Whole Roman empire with Egypt, on real harvests with a floodplain rule for the Nile, heartland people at Frier\'s 61.4 M and Greek wall circuits at their inhabited share: 95% of residents fed at a marketed share of {gwd["e95_all_at_L_used"]:.3f} with the cited 270 km haul; west/east settings feed each other {100 * gwd["transfer"]["west_setting_feeds_east"]:.0f}% / {100 * gwd["transfer"]["east_setting_feeds_west"]:.0f}%', f'Passed (development: each fix followed a failure). Without Egypt, the original test gives {d["e95_all_at_L_used"]:.2f}', 'GREEK_WALLS_20261114.md'),
        ('Floodplain land', 'Earth rule (development)', 'Low land by a river whose flood ends Jul-Oct with little flood-season rain: full water, yearly winter cereal, 95% farmed', 'Egypt capacity 2.3 → 5.8 M, no other census region changes; no fantasy river qualifies (all flood in winter)', 'FLOODPLAIN_RULE_20261114.md'),
        ('Fantasy supply', 'Earth value applied', f'Marketed share {sup["marketed_share"]:.3f}: {100 * s34["fed_share_of_residents"]:.0f}% of residents fed, {s34["short_towns"]} towns short (corrected climate)', 'Published default', 'SIZES_GREEK_WALLS_20261114.md'),
        ('Political reach', 'Earth-tested blind (rule)', f'Control rule v2.1 (held + enclosed land) scored once on unseen pools: CHGIS seats of 1080 BA {bl["T1"]["F"]["ba"]:.3f} vs {bl["T1"]["v2"]["ba"]:.3f} for v2; Pleiades AD 550 {bl["T2"]["F"]["ba"]:.3f} vs {bl["T2"]["v2"]["ba"]:.3f}', 'Passed and adopted. The map staffs every affiliated town from its supply-fed residents (the blind runs staffed 99% / 84%)', 'GEOGRAPHY_CONTROL_PLAN_20261107.md'),
        ('Population pattern', 'Earth-tested blind (pattern)', 'Heartland occupancy, capacity × exp(−D/800 km): Domesday England 1086 block rank 0.63 (20 km); Han commanderies 0.82 in development', 'Pattern passed; level not predicted (supplied)', 'POPULATION_LEDGER_20261108.md'),
        ('Trade, administration', 'Rebuilt, not calibrated', 'Run on the release-3 towns and supply-fed residents', 'No Earth test of their own', 'SETTLEMENT_DOWNSTREAM_20261113.md'),
    ]
    trs = ''.join(f'<tr><th scope="row">{a}</th><td><span class="tag">{t}</span></td><td>{m}</td><td>{o}</td><td><a href="../../../reports/{rep}">report</a></td></tr>' for a, t, m, o, rep in rows)
    links = ' · '.join(f'<a href="{n}" download>{n}</a>' for n in sorted(copies))
    css = (':root{color-scheme:light dark;--paper:#eef1ee;--plate:#f9faf7;--ink:#21383a;--rule:#bdcbc4;--accent:#2b7168;--tag:#dfe9e4}*{box-sizing:border-box}body{margin:0;background:var(--paper);color:var(--ink);font:16px/1.6 system-ui,sans-serif}'
           'main{max-width:1250px;margin:auto;padding:24px 16px 70px}h1{font:600 clamp(2rem,5vw,3rem)/1.15 Georgia,serif}h2{font:600 1.6rem Georgia,serif}a{color:var(--accent);overflow-wrap:anywhere}a:focus-visible{outline:3px solid var(--accent);outline-offset:4px}'
           'section{margin-top:32px}p{max-width:85ch}figure{margin:24px 0}img{display:block;width:100%;height:auto;background:white}figcaption{font-size:.9rem}.status{border-left:4px solid var(--accent);background:var(--plate);padding:12px 18px}'
           '.table{overflow:auto;border:1px solid var(--rule)}table{border-collapse:collapse;width:100%;min-width:760px;background:var(--plate);font-size:14px}th,td{padding:9px;text-align:left;vertical-align:top;border-bottom:1px solid var(--rule)}'
           '.tag{display:inline-block;background:var(--tag);border-radius:4px;padding:1px 6px;white-space:nowrap}@media(prefers-color-scheme:dark){:root{--paper:#131d20;--plate:#1c292b;--ink:#e3ebe5;--rule:#435651;--accent:#8ed2b5;--tag:#2c3d3f}}')
    html = f'''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Settlement calibration · Earth evidence</title><style>{css}</style>
<main><nav><a href="../">Earth evidence</a> · <a href="../../">Atlas hub</a> · <a href="../../earth_fit/">Current settlement atlas</a></nav>
<header><p>EARTH EVIDENCE · 14 NOVEMBER 2026</p><h1>What the settlement map is calibrated against</h1><p class="status">The default Settlements map (release 3, sliding density, marketed share 0.34) stacks several layers. Count, positions, sizes and grain supply are each fitted on Earth data and scored on held-out folds, quadrants or halves. These are development tests on exposed pools, not blind validation. Since 14 November the grain supply passes on the whole Roman Empire, Egypt included. That needed a floodplain rule for the Nile, a people level from Frier and Greek wall circuits read as inhabited area; each was introduced after a failure and is disclosed.</p></header>
<section><h2>Layer by layer</h2><div class="table" tabindex="0" aria-label="Calibration status of each settlement layer"><table><thead><tr><th>Layer</th><th>Kind</th><th>Rule and Earth evidence</th><th>Outcome</th><th></th></tr></thead><tbody>{trs}</tbody></table></div></section>
<section><h2>Positions</h2><p>Production tiling under-filled the old heartlands; a heartland prior chosen on Han and scored on Rome (and the reverse) beat production in all eight quadrants. On Vidarbha in India, a survey region the rule was not tuned on, it neither helps nor hurts: 10 km capture {g["capture_delta_release3_vs_production"]:+.3f}, percentile {g["rank_delta_release3_vs_production"]:+.3f} against environment only. With about 53 surveyed site cells, those percentiles are within noise of chance.</p>
<figure><a href="settlement_release3_20261113.png" download><img src="settlement_release3_20261113.png" width="1820" height="616" alt="Placement quality in eight Han and Roman quadrants. Left: fixed 18 km spacing with a heartland pull beats the earlier rule in 5 of 8 and fails. Right: density-adaptive spacing with the heartland pull, setting chosen on the other pool, beats it in all 8."></a><figcaption>Right panel is the adopted rule (family B). The left panel shows the rule that failed.</figcaption></figure>
<figure><a href="vidarbha_release3_20261114.png" download><img src="vidarbha_release3_20261114.png" width="1760" height="572" alt="Vidarbha check: release 3 has the same 10 km capture as production, 0.121, and a slightly higher site percentile than environment only; a map shows release-3 and production towns."></a></figure></section>
<section><h2>Sizes</h2><p>Town areas follow the official Hanson 2016 table. Local people density explains almost none of the spread, so sizes are mostly a calibrated scatter around a weak trend. That is honest but limits what a map can predict about any single town.</p>
<figure><a href="settlement_release2_20261113.png" download><img src="settlement_release2_20261113.png" width="2100" height="644" alt="Left: an earlier placement rule that won 5 of 8 quadrants and was superseded. Middle: cumulative distribution of built-up area for observed Roman cities, the model on held-out provinces and fantasy towns, which nearly coincide (held-out distance 0.058, limit 0.10). Right: fantasy town residents by rank under earlier sizes, release 2 at 100 people per hectare, and the sliding 100 to 500 per hectare reading."></a><figcaption>Middle panel is the size test. The left panel shows the superseded placement finalist (see the figure above).</figcaption></figure></section>
<section><h2>Grain supply</h2><p>The same production, freight network and allocation code runs on the Roman empire with real harvests. Without Egypt the cited 270 km haul limit holds and west and east agree. With Egypt it fails, and the cause is upstream: field-water work shows the Nile is now limited by the crop model's rain-fed constants (yield, farmed share, fallow), not by water.</p>
<figure><a href="settlement_supply_calibration_20261113.png" download><img src="settlement_supply_calibration_20261113.png" width="1820" height="630" alt="Fed share of Roman city residents by marketed share and haul limit, for the whole empire and without Egypt."></a></figure></section>
<section><h2>Egypt and the whole empire</h2><p>The harvest model first gave Egypt half its historical people. A floodplain rule fixed capacity (2.3 → 5.8 M) without moving any other census region. Two more fixes were needed for the supply test to pass: a people level anchored on Frier's 61.4 M, and Greek wall circuits read as their inhabited share (Hansen 2008). The fantasy map has no Nile-type river, so the floodplain rule does not change it.</p>
<figure><a href="floodplain_rule_20261114.png" download><img src="floodplain_rule_20261114.png" alt="Qualifying Nile flood-basin land, Egypt capacity rising into its historical range with no other region changing, and the whole-empire supply test before and after."></a></figure>
<figure><a href="greek_walls_20261114.png" download><img src="greek_walls_20261114.png" alt="The share of grain that must be marketed to feed 95% of west and east city residents at each step of the day: the east goes from never fed to agreeing with the west at 0.34."></a></figure>
<figure><a href="fantasy_floodplain_20261114.png" download><img src="fantasy_floodplain_20261114.png" alt="All fantasy rivers flood in winter, while the Nile in the same model floods in late summer."></a></figure></section>
<section><h2>Not yet calibrated</h2><p>Trade and administration are rebuilt on the calibrated towns but have no Earth test of their own. Town positions and sizes have only been checked on development pools (cross-pool quadrants, province folds, Vidarbha); the reach rule and the population pattern have each passed one blind test.</p><p>{links}</p></section></main></html>'''
    (PAGE / 'index.html').write_text(html)
    evidence = ROOT / 'atlases/earth_evidence/index.html'; old = re.sub(r'<section id="settlement-calibration">.*?</section>', '', evidence.read_text(), flags=re.S)
    panel = '<section id="settlement-calibration"><h2>What the settlement map is calibrated against</h2><p>Count, positions, sizes and grain supply of the default Settlements map, each with its Earth test and outcome; Egypt remains the open gap. <a href="settlement_calibration/">Open the calibration status →</a></p></section>'
    evidence.write_text(old.replace('</header>', '</header>' + panel, 1))
    files = {str(p.relative_to(ROOT)): sha(p) for p in sorted(PAGE.iterdir()) if p.is_file()}
    write(O / 'vidarbha_release3_20261114/publication.json', dict(status='published', page='atlases/earth_evidence/settlement_calibration/', files=files, publisher_sha256=sha(Path(__file__)), evidence_index_sha256=sha(evidence)))
    print('published', len(files), 'files')


if __name__ == '__main__':
    main()
