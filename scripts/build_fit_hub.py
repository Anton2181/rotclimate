"""Write the active atlas entry page, retaining links to retired snapshots.

    python3 -I scripts/build_fit_hub.py                       # atlases/index.html, local links
    python3 -I scripts/build_fit_hub.py --artifact <dir>      # <dir>/index.html + img/, artifact links

The artifact version links each atlas by its URL in atlases/artifact_links.json
and carries its own small copies of the map images.
"""
import argparse
import datetime
from html import escape
import json
import re
import sys
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from atlas_set import ACTIVE, RETIRED

ALL_FITS = {
    'free_fit': ('Free fit', 'World and physics fitted to the seasonal painted zones.'),
    'earth_fit': ('Earth fit', "Adopted Earth r42 physics, checked on 49 development regions, finer grids and a separately reserved region set, on the published world's geometry."),
    'whittaker_fit': ('Whittaker fit', 'World and physics fitted to the proposed annual-biome targets.')}
FITS = {name: ALL_FITS[name] for name in ACTIVE}

STYLE = '''
/* Layout: an atlas title page; three plates side by side, then the shared measures. Same tokens as the atlases. */
:root {
  --paper: #eef1f1; --plate: #f8faf9; --ink: #1b262c; --ink-soft: #4b5a62; --rule: #c9d2d4;
  --brass: #94641a; --chip: #e2e8e9; --good: #2f7a52;
  --font-display: "Spectral SC", "Iowan Old Style", Georgia, serif;
  --font-body: "Alegreya Sans", "Gill Sans", "Segoe UI", system-ui, sans-serif;
  --font-data: "IBM Plex Mono", ui-monospace, "SFMono-Regular", Menlo, monospace;
  --step--1: 0.84rem; --step-0: 1rem; --step-1: 1.2rem; --step-2: 1.55rem; --step-3: clamp(2rem, 5vw, 3rem);
}
@media (prefers-color-scheme: dark) {
  :root:not([data-theme="light"]) {
    --paper: #12191d; --plate: #182126; --ink: #e3e9eb; --ink-soft: #9fb0b7; --rule: #2c3a41;
    --brass: #d7a64b; --chip: #22303a; --good: #6cc495; color-scheme: dark;
  }
}
:root[data-theme="dark"] {
  --paper: #12191d; --plate: #182126; --ink: #e3e9eb; --ink-soft: #9fb0b7; --rule: #2c3a41;
  --brass: #d7a64b; --chip: #22303a; --good: #6cc495; color-scheme: dark;
}
* { box-sizing: border-box; }
body { margin: 0; background: var(--paper); color: var(--ink); font-family: var(--font-body);
  font-size: var(--step-0); line-height: 1.55; }
.wrap { max-width: 1240px; margin: 0 auto; display: grid; gap: 44px;
  padding-left: max(16px, env(safe-area-inset-left, 0px)); padding-right: max(16px, env(safe-area-inset-right, 0px));
  padding-block: 32px 72px; }
header, section { display: grid; gap: 14px; min-width: 0; }
header { max-width: 72ch; gap: 10px; }
.eyebrow { font-family: var(--font-data); font-size: var(--step--1); letter-spacing: 0.08em; text-transform: uppercase; color: var(--brass); }
h1, h2 { font-family: var(--font-display); font-weight: 600; letter-spacing: 0.01em; text-wrap: balance; margin: 0; }
h1 { font-size: var(--step-3); line-height: 1.08; }
h2 { font-size: var(--step-2); line-height: 1.2; }
h3 { font-size: var(--step-1); margin: 0; }
p { margin: 0; max-width: 75ch; }
.lede { font-size: var(--step-1); color: var(--ink-soft); }
.note { font-size: var(--step--1); color: var(--ink-soft); }
a { color: var(--brass); text-underline-offset: 3px; }
a:focus-visible { outline: 2px solid var(--brass); outline-offset: 3px; border-radius: 2px; }
.plates { display: grid; grid-template-columns: repeat(auto-fit, minmax(min(100%, 320px), 1fr)); gap: 20px; }
@media (max-width: 900px) { .plates { grid-template-columns: minmax(0, 1fr); } }
.plate { display: grid; grid-template-rows: auto 1fr; background: var(--plate); border: 1px solid var(--rule);
  border-radius: 6px; overflow: hidden; min-width: 0; color: inherit; text-decoration: none; }
.plate:hover { border-color: var(--brass); }
.plate img { display: block; width: 100%; max-width: 100%; aspect-ratio: 2000 / 926; object-fit: cover; background: var(--chip); }
.plate .body { display: grid; gap: 8px; padding: 14px 16px 18px; align-content: start; }
.plate .open { font-family: var(--font-data); font-size: var(--step--1); color: var(--brass); }
.status { font-family: var(--font-data); font-size: 0.78rem; color: var(--good); }
.table { overflow-x: auto; border: 1px solid var(--rule); border-radius: 6px; background: var(--plate); }
table { width: 100%; border-collapse: collapse; font-variant-numeric: tabular-nums; }
th, td { text-align: left; padding: 11px 14px; border-bottom: 1px solid var(--rule); white-space: nowrap; }
tbody tr:last-child > * { border-bottom: 0; }
thead th { font-family: var(--font-data); font-weight: 500; font-size: 0.75rem; letter-spacing: 0.04em;
  text-transform: uppercase; color: var(--ink-soft); }
td { font-family: var(--font-data); font-size: 0.9rem; }
.notes { display: grid; gap: 6px; }
'''


def thumbnail(src: Path, dst: Path, width=1200):
    with Image.open(src) as im:
        im.resize((width, round(im.height * width / im.width)), Image.LANCZOS).save(dst, 'WEBP', quality=82)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--artifact', type=Path, help='write the artifact version into this folder')
    ap.add_argument('--date', type=datetime.date.fromisoformat, help='publication date YYYY-MM-DD; overrides the build host date')
    a = ap.parse_args()
    artifact = a.artifact is not None
    links = json.loads((ROOT / 'atlases/artifact_links.json').read_text()) if artifact else {}
    if artifact:
        (a.artifact / 'img').mkdir(parents=True, exist_ok=True)
    plates, rows, population_rows, density_plates, cored, margins = [], [], [], [], [], []
    has_sensitivity = False
    corrected = None
    earth_profile, earth_report = 'r42', 'reports/R42_20261101.md'
    foraging_fits, foraging_rows = [], []
    for name, (title, description) in FITS.items():
        folder = ROOT / 'atlases' / name
        summary = json.loads((folder / 'summary.json').read_text())
        metadata = json.loads((folder / 'data/atlas.json').read_text())
        if name == 'earth_fit':
            if re.fullmatch(r'r\d+', metadata.get('physics_profile', '')):
                earth_profile = metadata['physics_profile']
                earth_report = metadata['physics_report']
                description = re.sub(r'Earth r\d+ physics', f'Earth {earth_profile} physics', description)
            has_sensitivity = bool(metadata.get('surroundings_sensitivity'))
            corrected = metadata.get('earth_correction')
        verified = bool(summary.get('observed_numerics', {}).get('all_checks_passed'))
        strict = summary['whittaker']['strict']
        outside = metadata['biomes'][0]['share']
        if summary.get('fit_objective') == 'whittaker-covered':
            description += ' A coverage guard limits land outside the original biome diagram.'
        h = summary['harvest']; pop = h['population']['endemic']
        if any(L['id'] == 'land_density_cores' for L in metadata['layers']):
            cored.append(title)
        if json.loads((folder / 'data/harvest_model.json').read_text()).get('margin_reliability'):
            margins.append(title)
        if metadata.get('foraging'):
            foraging_fits.append(title)
            forage = json.loads((folder / 'data' / metadata['foraging']['metadata']).read_text()).get('summary', {})
            foraging_rows.append(f'<tr><th scope="row">{escape(title)}</th><td>{forage.get("total_scenario_people", float("nan")) / 1e6:.2f} M</td>'
                                 f'<td>{forage.get("mean_foraging_hours_day", float("nan")):.1f} h</td>'
                                 f'<td>{forage.get("mean_scarcity_days_year", float("nan")):.0f} days</td>'
                                 f'<td>{forage.get("mean_meat_fraction", float("nan")):.0%}</td>'
                                 + (f'<td>{forage["mean_fish_share"]:.0%}</td>' if forage.get("mean_fish_share") is not None else '<td>—</td>')
                                 + '</tr>')
        if artifact:
            href = links.get(name, '')
            biome_img, density_img = f'img/{name}_whittaker.webp', f'img/{name}_density.webp'
            thumbnail(folder / 'data/whittaker.webp', a.artifact / biome_img)
            thumbnail(folder / 'data/land_density_central_endemic.webp', a.artifact / density_img)
            density_href = href
        else:
            href = f'{name}/'
            biome_img, density_img = f'{name}/data/whittaker.webp', f'{name}/data/land_density_central_endemic.webp'
            density_href = f'{name}/#layer=land_density&amp;occupation=central&amp;disease=endemic'
        t = escape(title)
        plates.append(f'<a class="plate" href="{href}"><img src="{biome_img}" alt="{t}: potential Whittaker biomes" loading="lazy">'
                      f'<div class="body"><h3>{t}</h3><p>{escape(description)}</p>'
                      f'<p class="status">Numerical checks {"passed" if verified else "unverified"} · {outside:.2%} of land outside the diagram</p>'
                      f'<span class="open">Open the atlas →</span></div></a>')
        density_plates.append(f'<a class="plate" href="{density_href}"><img src="{density_img}" alt="{t}: central population density scenario" loading="lazy">'
                              f'<div class="body"><h3>{t}</h3><p class="note">{pop["central"] / 1e6:.1f} M people in the central scenario</p></div></a>')
        rows.append(f'<tr><th scope="row"><a href="{href}">{t}</a></th><td>{summary["zonefit"]:.4f}</td><td>{strict["score"]:.4f}</td>'
                    f'<td>{summary["strict_accuracy"]:.1%}</td><td>{strict["macro_hard"]:.1%}</td><td>{outside:.2%}</td>'
                    f'<td>{summary["mediterranean"]["dry_share"]:.1%}</td><td>{summary["mediterranean"]["cs_share"]:.1%}</td></tr>')
        population_rows.append(f'<tr><th scope="row">{t}</th><td>{h["food_capacity"] / 1e6:.1f} M</td><td>{pop["frontier"] / 1e6:.1f} M</td>'
                               f'<td>{pop["central"] / 1e6:.1f} M</td><td>{pop["core"] / 1e6:.1f} M</td></tr>')
    def who(names):
        names = [n.replace(' ', '-') for n in names]
        return ' and '.join([', '.join(names[:-1]), names[-1]] if len(names) > 1 else names)
    if len(cored) == len(FITS):
        overview = 'Overview holds the biome map, settlement potential, expected density and density around the old heartlands named in the campaign lore.'
    else:
        overview = 'Overview holds the biome map, settlement potential and expected density' + (
            f'; the {who(cored)} atlas{"es" if len(cored) > 1 else ""} also map{"" if len(cored) > 1 else "s"} density around the old heartlands named in the campaign lore.' if cored else '.')
    if len(margins) == len(FITS):
        harvest = 'Low-input Han, Roman and Parthian technology, with poor-year limits on cold and dry margins'
    else:
        harvest = 'Low-input Han, Roman and Parthian technology' + (
            f' (the {who(margins)} atlas{"es" if len(margins) > 1 else ""} add{"" if len(margins) > 1 else "s"} poor-year limits on cold and dry margins)' if margins else '')
    topics = ['Overview', 'Population', 'Political reach', 'Farming', 'Health and ecology', 'Temperature', 'Water',
              'Air and sea', 'Month by month', 'Fit checks']
    if len(foraging_fits) == len(FITS):
        topics.insert(2, 'Foraging')
    work_maps=all((ROOT/'atlases'/name/'data/farm_work.json').exists() for name in FITS)
    if work_maps:topics.insert(topics.index('Farming')+1,'Food and work')
    administrative_maps=all((ROOT/'atlases'/name/'data/administrative_access.json').exists() for name in FITS)
    hierarchy_maps=all((ROOT/'atlases'/name/'data/administrative_hierarchy.json').exists() for name in FITS)
    pasture_maps=all((ROOT/'atlases'/name/'data/pasture.json').exists() for name in FITS)
    if pasture_maps:topics.insert(topics.index('Foraging')+1 if 'Foraging' in topics else 2,'Livelihoods')
    if administrative_maps:topics.insert(topics.index('Political reach')+1,'Administration')
    topic_text = f'Map topics include {", ".join(topics[:-1])} and {topics[-1]}.'
    if corrected:
        fit = corrected['zone_fit']
        topic_text += (' The Earth atlas opens on its Earth-corrected climate: every climate map, the station card, farming, '
                       'population, foraging and political reach use the simulation after the corrections learned from the 31 '
                       'Earth regions, with the raw simulation one switch away and maps of the changes under Fit checks '
                       f'(exact zone agreement {100 * fit["raw"]["strict_accuracy"]:.1f} % raw, '
                       f'{100 * fit["corrected"]["strict_accuracy"]:.1f} % corrected).')
    if work_maps:
        topic_text+=(' Food and work adds partial cereal field-work hours, cropped land per food target, '
            'reaping staffing for supplied harvest windows and calendar alternatives. These use the current crop model '
            'and Columella’s listed tasks, with explicit assumptions; they do not estimate total survival work or population. '
            'Choose the map view inside that topic. ')
    if administrative_maps:
        topic_text+=(' Administration compares seasonal two-day access from documented commandery seats, '
            'marked places, proposed towns, tracks, roads and military markers, with a separate three-seed settlement comparison. '
            'The workbook-backed inventory retains disputed seats. These scenarios measure access, not allegiance or military strength. ')
    if hierarchy_maps:
        topic_text+=(' Administrative links adds six schematic views of directed seasonal communication through 19 recorded provincial capitals, '
            'comparing marked interchanges with proposed transport. Reply budgets are adjustable scenarios, not limits that establish political control. ')
    if pasture_maps:
        topic_text+=(' Livelihoods adds worldwide usable forage, seasonal feed reserves and mapped water proximity, including land outside state claims. '
            'These are dry-matter resource scenarios, not herd or human carrying capacities; the zero-loss reserve experiment uses explicitly stated demand. ')
    coverage_maps=all((ROOT/'atlases'/name/'data/coverage.json').exists() for name in FITS)
    if coverage_maps:
        topic_text+=(' Political reach adds Coverage audit: six views for all 18 mapped actors, comparing linked, claim-assigned and generated sites. '
            'Select an actor and travel budget to inspect seasonal same-site return access, overlap and missing evidence; this does not assign sovereignty. ')
    presence_maps=all((ROOT/'atlases'/name/'data/presence_mobility.json').exists() for name in FITS)
    if presence_maps:
        topic_text+=(' Sustained presence tests cereal provisioning, origin/destination stores and freight interruptions at all 151 verified marked sites. '
            'Livelihoods adds Seasonal circuits: four independent resource landscapes with a single closed herd route, finite carried feed and water-proximity sensitivity. '
            'Local and regional extents retain the same grazing footprint and travel budget, with nested candidate bases, an all-land fixed-base control and an optimistic resource bound. '
            'Origin storage and collection sensitivities expose food-support assumptions. These are explicit scenarios, not actual garrisons, camps, nutrition or control. ')
    foraging_section = ('' if not foraging_rows else
        '<p>The Foraging topic runs a hunter-gatherer scenario on each climate, adapted from the FORGE human model '
        '(published equations, with climate-based productivity and seasonal resource proxies in place of its ORCHIDEE vegetation), '
        'with coastal and freshwater fish as a third food. Its terrestrial and aquatic food scales were fitted on Binford\'s North '
        'American hunter-gatherers and tested on the rest of the world (density error a factor 1.8, rank correlation 0.74, and which '
        'groups fished, 0.78). Five maps show scenario density, daily food-procurement hours, days of food shortfall a year, the share '
        'of food from animals and the share from fish; select any place for its readouts. It is separate from the farming model and both draw on the same land.</p>'
        '<div class="table"><table><thead><tr><th>Atlas</th><th>Foraging scenario people</th><th>Procurement per day</th>'
        '<th>Shortfall per year</th><th>Animal share</th><th>Fish share</th></tr></thead><tbody>' + ''.join(foraging_rows) + '</tbody></table></div>'
        '<div class="notes"><p class="note">Finite-horizon scenarios, not validated carrying capacities or censuses. Means are weighted by scenario people. '
        'Food shortfall includes ordinary reserve drawdown; it is not famine mortality.</p></div>')
    settled_maps=all((ROOT/'atlases'/name/'data/settled_reach.json').exists() for name in FITS)
    if settled_maps:
        topic_text+=(' Settlements and supply-supported reach now share one seasonal food ledger: local cereal caps civilian requests and available institutional cohorts, then changes which sites emit reach. A transport-matched unconstrained reference and legacy maps remain available. Three listed-field-work scenarios also cap cereal by annual/reaping budgets while keeping rural meals fixed. These are conditional scenarios, not validated populations or sovereignty. ')
    updated = (a.date or datetime.date.today()).strftime('%-d %B %Y').upper()
    sensitivity_note = ('<p class="note">The Earth atlas also offers Rain sensitivity and Temperature sensitivity under Fit checks, with grid values to download. These show spread across nine hypothetical surroundings at the screening resolution; they are conditional boundary sensitivities, not weather variability or measured climate error.</p>'
                        if has_sensitivity and not artifact else '')
    if artifact:
        compare = 'Open the Population topic and set the population budget.'
        reports = ''
        head = '<meta charset="utf-8">\n'
    else:
        compare = ('Compare the same 50 million people: ' + ' · '.join(
            f'<a href="{n}/#layer=pop_density&amp;population=50000000&amp;pattern=markets">{FITS[n][0]}</a>' for n in FITS) + '.')
        reports = ('<p class="note"><a href="climate_accuracy/">Climate accuracy and joint fit</a> · '
                   '<a href="earth_evidence/rain_timing/">Rain timing sensitivity</a> · '
                   '<a href="earth_evidence/daily_fields/">Daily river-to-field water</a> · '
                   '<a href="earth_evidence/soil_drying/">Soil drying and supplied daily clock</a> · '
                   '<a href="earth_evidence/flood_storage/">Flood storage and winter crop water</a> · '
                   '<a href="earth_evidence/flood_basin/">Flood-basin timing inputs</a> · '
                   '<a href="../reports/SEASONAL_CYCLE_20261026.md">Seasonal settling checks</a> · '
                   f'<a href="../{escape(earth_report)}">Earth {earth_profile} calibration</a> · '
                   '<a href="../reports/R40_WORLD_20261031.md">World refit (r40, kept)</a> · '
                   '<a href="../reports/FORAGING_20261027.md">Foraging scenarios</a> · '
                   '<a href="../reports/FORAGING_EARTH_20261031.md">Foraging against Binford\'s hunter-gatherers</a> · '
                   '<a href="../reports/ITERATION_20261023.md">Population lab</a> · '
                   '<a href="../reports/HARVEST_MIGRATION_20261022.md">Food, disease and settlement models</a> · '
                   '<a href="../reports/THREE_FIT_20261022.md">Campaign report</a> · <a href="../docs/BIOMES.md">Biome methods</a></p>')
        head = '<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">\n'
    html = head + f'''<title>Rotclimate Atlases</title>
<meta name="claude:viewport-fit-sides" content="cover">
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Spectral+SC:wght@500;600&family=Alegreya+Sans:ital,wght@0,400;0,500;0,700;1,400&family=IBM+Plex+Mono:wght@400;500&display=swap">
<style>{STYLE}</style>
<div class="wrap">
<header><span class="eyebrow">Rotclimate · Earth-fit atlas · updated {updated}</span>
<h1>Climate, land and people</h1>
<p class="lede">Explore the active Earth fit: climate checked against Earth observations, with farming, settlement and control models around 200 AD. The climate averages three layouts of the unknown surroundings. Each model retains its stated evidence and scenario limits.</p></header>
{'' if artifact else '<p><a href="climate_accuracy/">Climate accuracy and joint fit →</a> · Earth measurements and rainfall-source maps.<br><a href="economy_lab/">Food, farming and society →</a> · c.200 AD proposals and seasonal budgets.<br><a href="earth_evidence/">Earth calibration evidence →</a> · component ledger, independent tests and remaining assumptions.</p>'}
<section aria-label="Active atlas"><div class="plates">{''.join(plates)}</div></section>
{'' if artifact else '<section aria-labelledby="archive-h"><h2 id="archive-h">Retired snapshots</h2><p>The free and Whittaker fits stopped receiving updates on 8 November 2026. Their last snapshots remain available: <a href="free_fit/">Free fit archive</a> · <a href="whittaker_fit/">Whittaker fit archive</a>.</p></section>'}
<section aria-labelledby="measures-h"><h2 id="measures-h">Atlas measures</h2>
<div class="table"><table><thead><tr><th>Atlas</th><th>Seasonal zone objective</th><th>Whittaker objective</th><th>Exact zone agreement</th><th>Mean biome agreement</th><th>Land outside diagram</th><th>Med. dry</th><th>Med. Cs</th></tr></thead><tbody>{''.join(rows)}</tbody></table></div>
<div class="notes"><p class="note">Each target zone counts equally in mean biome agreement. Objective scores measure different definitions of a match and are not interchangeable. These figures classify the mean climate fields; calibration logs average scores across individual layouts.</p>
<p class="note">Med. dry and Med. Cs are the shares of the painted Mediterranean zone classified as Köppen dry climates and Mediterranean climates.</p>
<p class="note">Annual temperature and rainfall do not decide Mediterranean summer drought or swamp hydrology, so those seasonal checks stay separate.</p></div></section>
{sensitivity_note}
<section aria-labelledby="people-h"><h2 id="people-h">Land and people around 200 AD</h2>
<p>{topic_text} {overview} Select any place for its climate chart, farming readouts and the real cities whose climate feels most alike.</p>
<p>Political reach now offers supply-supported scenarios: one grain budget supports requested civilians and institutional residents, and only available affiliated cohorts emit seasonal outward-and-return reach. Three listed-field-work cases also constrain the grain. These coupled scenarios remain uncalibrated for actual settlement sizes and sovereignty. Legacy views retain earlier source/reach rules and their historical Han/Roman comparisons; those tests do not validate the newer coupling. Trade routes bulk goods separately in each direction, with inbound hinterlands reporting people served rather than town inhabitants. The earlier Roman test did not establish that market access predicts town size. See the Earth evidence ledger for the distinction between measured inputs, empirical fits, literature relationships and scenario choices.</p>
<p>The Population topic is a lab: supply a total and choose even occupation, water and terrain, or market access. Six maps then show allocated residents, local pressure, spare food support, redistribution, walking to markets and settlement attraction, with province totals. {compare}</p>
<div class="plates">{''.join(density_plates)}</div>
<div class="table"><table><thead><tr><th>Atlas</th><th>Mixed food ceiling</th><th>Frontier scenario</th><th>Central scenario</th><th>Settled-core scenario</th></tr></thead><tbody>{''.join(population_rows)}</tbody></table></div>
<div class="notes"><p class="note">{harvest}; environmental malaria potential included. Occupation scenarios are historical analogues, not confidence intervals or reconstructed censuses. The atlas can remove the malaria penalty.</p></div>
{foraging_section}
<div class="notes">{reports}</div></section>
</div>
'''
    out = (a.artifact if artifact else ROOT / 'atlases') / 'index.html'
    out.write_text(html)
    if not artifact:
        import hashlib
        release = dict(
            earth_physics=earth_profile,
            active_atlases=list(ACTIVE), retired_atlases=list(RETIRED),
            published_branch='claude/friendly-turing-43ygeu',
            hub_sha256=hashlib.sha256(out.read_text(encoding='utf-8').encode('utf-8')).hexdigest(),
            metadata_sha256={name: hashlib.sha256((ROOT / 'atlases' / name / 'data/atlas.json').read_bytes()).hexdigest()
                             for name in ALL_FITS})
        if work_maps:
            release['cereal_work_sha256']={name:hashlib.sha256((ROOT/'atlases'/name/'data/farm_work.json').read_bytes()).hexdigest() for name in FITS}
        if administrative_maps:
            release['administrative_access_sha256']={name:hashlib.sha256((ROOT/'atlases'/name/'data/administrative_access.json').read_bytes()).hexdigest() for name in FITS}
        if hierarchy_maps:
            release['administrative_hierarchy_sha256']={name:hashlib.sha256((ROOT/'atlases'/name/'data/administrative_hierarchy.json').read_bytes()).hexdigest() for name in FITS}
        if pasture_maps:
            release['pasture_sha256']={name:hashlib.sha256((ROOT/'atlases'/name/'data/pasture.json').read_bytes()).hexdigest() for name in FITS}
        if coverage_maps:
            release['coverage_sha256']={name:hashlib.sha256((ROOT/'atlases'/name/'data/coverage.json').read_bytes()).hexdigest() for name in FITS}
        if presence_maps:
            release['presence_mobility_sha256']={name:hashlib.sha256((ROOT/'atlases'/name/'data/presence_mobility.json').read_bytes()).hexdigest() for name in FITS}
        if settled_maps:
            release['settled_reach_sha256']={name:hashlib.sha256((ROOT/'atlases'/name/'data/settled_reach.json').read_bytes()).hexdigest() for name in FITS}
        evidence=ROOT/'atlases/earth_evidence'
        if evidence.exists():
            release['earth_evidence_sha256']={str(p.relative_to(evidence)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(evidence.rglob('*')) if p.is_file()}
        accuracy=ROOT/'atlases/climate_accuracy'
        if accuracy.exists():
            release['climate_accuracy_sha256']={str(p.relative_to(accuracy)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(accuracy.rglob('*')) if p.is_file()}
        (ROOT / 'atlases/release.json').write_text(json.dumps(release, indent=2) + '\n')
    print('wrote', out)


if __name__ == '__main__':
    main()
