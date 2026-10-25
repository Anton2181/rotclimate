"""Write the entry page comparing the three completed atlas fits.

    python3 -I scripts/build_fit_hub.py                       # atlases/index.html, local links
    python3 -I scripts/build_fit_hub.py --artifact <dir>      # <dir>/index.html + img/, artifact links

The artifact version links each atlas by its URL in atlases/artifact_links.json
and carries its own small copies of the map images.
"""
import argparse
import datetime
from html import escape
import json
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
FITS = {
    'free_fit': ('Free fit', 'World and physics fitted to the seasonal painted zones.'),
    'earth_fit': ('Earth fit', 'World fitted with Earth r37 physics held fixed.'),
    'whittaker_fit': ('Whittaker fit', 'World and physics fitted to the proposed annual-biome targets.')}

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
.plates { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 20px; }
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
    a = ap.parse_args()
    artifact = a.artifact is not None
    links = json.loads((ROOT / 'atlases/artifact_links.json').read_text()) if artifact else {}
    if artifact:
        (a.artifact / 'img').mkdir(parents=True, exist_ok=True)
    plates, rows, population_rows, density_plates, cored, margins = [], [], [], [], [], []
    for name, (title, description) in FITS.items():
        folder = ROOT / 'atlases' / name
        summary = json.loads((folder / 'summary.json').read_text())
        metadata = json.loads((folder / 'data/atlas.json').read_text())
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
    updated = datetime.date.today().strftime('%-d %B %Y').upper()
    if artifact:
        compare = ('Each atlas opens with the same Population lab, so the same total can be tried in all three: '
                   'open the Population topic and set the population budget.')
        reports = ''
        head = '<meta charset="utf-8">\n'
    else:
        compare = ('Compare the same 50 million people: ' + ' · '.join(
            f'<a href="{n}/#layer=pop_density&amp;population=50000000&amp;pattern=markets">{FITS[n][0]}</a>' for n in FITS) + '.')
        reports = ('<p class="note"><a href="../reports/ITERATION_20261023.md">Population lab and latest milestones</a> · '
                   '<a href="../reports/HARVEST_MIGRATION_20261022.md">Food, disease and settlement models</a> · '
                   '<a href="../reports/THREE_FIT_20261022.md">Campaign report</a> · <a href="../docs/BIOMES.md">Biome methods</a></p>')
        head = '<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">\n'
    html = head + f'''<title>Rotclimate Atlases</title>
<meta name="claude:viewport-fit-sides" content="cover">
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Spectral+SC:wght@500;600&family=Alegreya+Sans:ital,wght@0,400;0,500;0,700;1,400&family=IBM+Plex+Mono:wght@400;500&display=swap">
<style>{STYLE}</style>
<div class="wrap">
<header><span class="eyebrow">Rotclimate · three calibration objectives · updated {updated}</span>
<h1>One world, three climate fits</h1>
<p class="lede">The seasonal map fit, the fit held to Earth physics, and the fit to proposed Whittaker biomes. Each atlas uses the mean climate over the same three layouts of the unknown surroundings.</p></header>
<section aria-label="The three atlases"><div class="plates">{''.join(plates)}</div></section>
<section aria-labelledby="measures-h"><h2 id="measures-h">The same measures</h2>
<div class="table"><table><thead><tr><th>Atlas</th><th>Seasonal zone objective</th><th>Whittaker objective</th><th>Exact zone agreement</th><th>Mean biome agreement</th><th>Land outside diagram</th><th>Med. dry</th><th>Med. Cs</th></tr></thead><tbody>{''.join(rows)}</tbody></table></div>
<div class="notes"><p class="note">Each target zone counts equally in mean biome agreement. Objective scores measure different definitions of a match and are not interchangeable. These figures classify the mean climate fields; calibration logs average scores across individual layouts.</p>
<p class="note">Med. dry and Med. Cs are the shares of the painted Mediterranean zone classified as Köppen dry climates and Mediterranean climates.</p>
<p class="note">The Whittaker atlas adds the proposed biome target map and a match layer. Annual temperature and rainfall do not decide Mediterranean summer drought or swamp hydrology, so those seasonal checks stay separate.</p></div></section>
<section aria-labelledby="people-h"><h2 id="people-h">Land and people around 200 AD</h2>
<p>Every atlas has ten map topics: Overview, Population, Political reach, Farming, Health and ecology, Temperature, Water, Air and sea, Month by month and Fit checks. {overview} Select any place for its climate chart, farming readouts and the real cities whose climate feels most alike.</p>
<p>Political reach measures how far each polity's hold extends beyond its roads, towns, forts and legions: days of travel over the terrain, month by month (snow, mud, heat and floods on land; ships by each month's winds, shut in the storm season; river boats), control fading by a factor of e per day and averaged over the year, the hardest month and what closes the roads then, and which polity's own network reaches each place first. The travel model was fitted on Han China in AD 2 and tested on the Roman empire of AD 150, on ancient sailing times and on Chinese county seats from AD 742 to 1820. De facto and de jure sets the held land against the painted claims, with a gap fill you choose (none, ½, 1 or 2 days) and the people each polity claims and holds; Trade routes prices goods as the Price Edict did (sea : river : road = 1 : 5 : 28) and routes a gravity model between towns. Every layer also comes as vector files (GeoJSON and a layered SVG in the source map's pixels) for making your own maps.</p>
<p>The Population topic is a lab: supply a total and choose even occupation, water and terrain, or market access. Six maps then show allocated residents, local pressure, spare food support, redistribution, walking to markets and settlement attraction, with province totals. {compare}</p>
<div class="plates">{''.join(density_plates)}</div>
<div class="table"><table><thead><tr><th>Atlas</th><th>Mixed food ceiling</th><th>Frontier scenario</th><th>Central scenario</th><th>Settled-core scenario</th></tr></thead><tbody>{''.join(population_rows)}</tbody></table></div>
<div class="notes"><p class="note">{harvest}; environmental malaria potential included. Occupation scenarios are historical analogues, not confidence intervals or reconstructed censuses. Each atlas can remove the malaria penalty. All three density maps share one colour scale.</p>{reports}</div></section>
</div>
'''
    out = (a.artifact if artifact else ROOT / 'atlases') / 'index.html'
    out.write_text(html)
    print('wrote', out)


if __name__ == '__main__':
    main()
