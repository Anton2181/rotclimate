"""Publish the frozen r5 settlement/annual-grain cohort; preserve r4 references."""
import hashlib
import json
from pathlib import Path
import re
import shutil
import sys

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / 'scripts')]
from publish_settlement_release2 import render, main_roads
from publish_wide_supply_release3 import supply_map, COLORS
from render_urban_hierarchy_candidate import TEMPLATE

OUT = ROOT / 'output/settlement_provisional_release5_20261117'
BASE = ROOT / 'output/urban_hierarchy_candidate_20261116'
SUPPLY = ROOT / 'output/urban_candidate_supply_20261116'
SEEDS = ROOT / 'output/urban_candidate_seeds_20261116'
DATA = ROOT / 'atlases/earth_fit/data'
PLAN = ROOT / 'calibration/settlement_provisional_release5_20261117.json'


def sha(p):
    with p.open('rb') as f:
        return hashlib.file_digest(f, 'sha256').hexdigest()


def read(p):
    return json.loads(p.read_text())


def write(p, value):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(value, indent=2, allow_nan=False) + '\n')


def check_frozen():
    baseline = read(OUT / 'baseline.json')
    assert baseline['plan_sha256'] == sha(PLAN)
    allowed = read(PLAN)['historical_live_files_allowed_to_change']
    for name, digest in baseline['protected_science_sha256'].items():
        p = OUT / 'baseline' / name if name in allowed else ROOT / name
        assert sha(p) == digest, name
    for name, digest in baseline['archived_live_sha256'].items():
        assert sha(OUT / 'baseline' / name) == digest, name
    for folder in [BASE, SUPPLY, SEEDS]:
        result, review = read(folder / 'results.json'), read(folder / 'review.json')
        assert review['status'] == 'passed'
        assert review['results_sha256'] == sha(folder / 'results.json')
        for name, digest in result['files_sha256'].items():
            assert sha(folder / name) == digest, name
        assert result['adopt'] is False
    return baseline


def check_replay():
    checks = {}
    for label, source in [('candidate', BASE), ('supply', SUPPLY)]:
        replay = OUT / ('replay_' + label)
        original = read(source / 'results.json')
        names = list(original['files_sha256'])
        for name in names:
            # Candidate fit and maps must be byte exact. Supply scientific files
            # are exact; the top receipt additionally enumerates later modules.
            assert sha(source / name) == sha(replay / name), (label, name)
        checks[label] = dict(files=len(names), files_byte_exact=True,
                             replay_results_sha256=sha(replay / 'results.json'))
    checks['scope'] = 'Unchanged recipes replayed; fresh freight network, exact released controls and candidate scientific outputs. Later unused modules may appear in the supply source inventory.'
    write(OUT / 'replay_review.json', checks)


def comparison_view(supply):
    target = DATA.parent / 'provisional'
    target.mkdir(exist_ok=True)
    payload = read(BASE / 'viewer_data.json')
    grain = np.load(SUPPLY / 'town_model.npz')
    for mode, data in payload['modes'].items():
        for reading, key in [('central', 'central_x34'), ('low', 'low_x14')]:
            old = supply['variants']['control']['climates'][mode]['scenarios'][key]
            new = supply['variants']['candidate']['climates'][mode]['scenarios'][key]
            data['summary'][reading].update(old_grain=old['fed_share_of_residents'], new_grain=new['fed_share_of_residents'], old_short=old['short_towns'], new_short=new['short_towns'])
            for i, town in enumerate(data['towns']):
                town['old_grain_' + reading] = float(grain[f'control__{mode}__{key}_fed_share'][i])
                town['new_grain_' + reading] = float(grain[f'candidate__{mode}__{key}_fed_share'][i])
    text = TEMPLATE.replace('<title>Settlement hierarchy candidate</title>', '<title>Rotclimate — provisional settlement atlas r5</title>')
    text = text.replace('Development preview · not an adopted release', 'Provisional release 5 · 17 November 2026')
    text = text.replace('<h1>Settlement hierarchy candidate</h1>', '<h1>Settlement atlas · provisional release 5</h1>')
    text = text.replace('Existing map and refreshed Earth fit.', 'Release 4 and the refreshed Earth development fit.')
    text = text.replace('<h2>Published map</h2>', '<h2>Release 4 reference</h2>').replace('<h2>Candidate</h2>', '<h2>Provisional release 5</h2>')
    text = text.replace('<option value="change">Area change</option>', '<option value="change">Area change</option><option value="grain">Annual grain support</option>')
    text = text.replace('<th>Published</th><th>Candidate</th>', '<th>Release 4</th><th>Provisional 5</th>')
    text = text.replace('</tbody></table></section>', '<tr><td>Annual grain need met · work-limited supply</td><td class="num" id="old-grain"></td><td class="num" id="new-grain"></td></tr></tbody></table></section>')
    text = text.replace("$('old-area').textContent=", "$('old-grain').textContent=fmt(100*t['old_grain_'+state.reading],2)+'%';$('new-grain').textContent=fmt(100*t['new_grain_'+state.reading],2)+'%';$('old-area').textContent=")
    text = text.replace("if(panel&&state.display==='change'){", "if(state.display==='grain'){const g=t[(panel?'new':'old')+'_grain_'+state.reading];c.style.fill='hsl('+Math.round(120*g)+',55%,42%)';c.style.fillOpacity='.95';}if(panel&&state.display==='change'){")
    text = text.replace("$('change-legend').hidden=state.display!=='change';", "$('old-summary').textContent+=' · '+fmt(100*s.old_grain,2)+'% annual grain need met · '+s.old_short+' towns short';$('new-summary').textContent+=' · '+fmt(100*s.new_grain,2)+'% annual grain need met · '+s.new_short+' towns short';$('grain-legend').hidden=state.display!=='grain';$('change-legend').hidden=state.display!=='change';")
    text = text.replace('<div class="legend">', '<div class="legend"><span id="grain-legend" hidden>Annual grain: red = none; yellow = half; green = all need met</span>')
    text = text.replace('People are conserved in the annual ledger. Seasonal source food, labour and imported supply remain to be qualified. Climate r44 is retained.', 'People are conserved. Annual grain supply uses each model’s own remaining rural population and field work (600 hours/worker/year; extraction 33.719% central or 14.049% low). Grain support is a ration equivalent, not a new population count. Seasonal food/work feasibility, warehouse capacity, handling staff and complete diets remain unresolved. Earth comparisons use exposed development data; this is not independent validation. Climate r44 is retained. Existing reach, trade and administration belong to release 4 or older labelled scenarios.')
    text = text.replace('Candidate towns CSV', 'Provisional towns CSV').replace('Published control CSV', 'Release 4 towns CSV')
    text = text.replace('</nav>', '<a href="town_intervals.csv" download>Five-seed size sensitivity</a><a href="grain_comparison.csv" download>Annual grain scenarios</a><a id="grain-download" href="supply/corrected.csv" download>Provisional grain CSV · central density</a><a href="comparison_corrected.png">Corrected comparison image</a><a href="comparison_raw.png">Raw comparison image</a><a href="../#layer=reach_towns">Full atlas</a></nav>')
    text = text.replace("$('control-download').href='control/placed_'+state.mode+'_towns.csv';", "$('control-download').href='control/placed_'+state.mode+'_towns.csv';$('grain-download').href='supply/'+state.mode+'.csv';")
    text = text.replace('Circle size scales with settlement area', 'Circle size scales with settlement area · fixed seed 1')
    text = text.replace('Candidate colours', 'Map colours')
    text = text.replace('Earth comparisons use exposed development data; this is not independent validation.', 'Earth comparisons use exposed development data; this is not independent validation. The earlier pipeline failed its southern Mesopotamia blind check; this refreshed fit has no new blind qualification.')
    text = text.replace('</main>', '<p class="note">Five seeds (1, 7, 19, 43, 97) describe scenario sensitivity, not calibrated uncertainty. Individual town changes can be large. The full atlas retains release-4 reference options. <a href="release.json">Release assumptions and provenance</a>.</p></main>')
    encoded = json.dumps(payload, separators=(',', ':'), allow_nan=False).replace('<', '\\u003c')
    (target / 'index.html').write_text(text.replace('__PAYLOAD__', encoded))
    write(OUT / 'viewer_data.json', payload)
    for label in ['candidate', 'control']:
        (target / label).mkdir(exist_ok=True)
        for mode in ['raw', 'corrected']:
            shutil.copyfile(BASE / label / f'placed_{mode}_towns.csv', target / label / f'placed_{mode}_towns.csv')
    (target / 'supply').mkdir(exist_ok=True)
    for mode in ['raw', 'corrected']:
        shutil.copyfile(SUPPLY / 'candidate' / f'supply_{mode}_towns.csv', target / 'supply' / f'{mode}.csv')
    for source, name in [(BASE / 'town_changes.csv', 'town_changes.csv'), (BASE / 'comparison.csv', 'comparison.csv'), (SEEDS / 'town_intervals.csv', 'town_intervals.csv'), (SUPPLY / 'comparison.csv', 'grain_comparison.csv')]:
        shutil.copyfile(source, target / name)
    write(target / 'release.json', dict(release=5, status='provisional', plan=read(PLAN), candidate_results_sha256=sha(BASE/'results.json'), supply_results_sha256=sha(SUPPLY/'results.json'), historical_scientific_adoption=False))
    # New publication figures, retaining all old scientific presentation artifacts.
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from PIL import Image
    terrain = np.asarray(Image.open(BASE / 'terrain.png'))
    for mode, data in payload['modes'].items():
        fig, axes = plt.subplots(2, 2, figsize=(15, 8), layout='constrained')
        towns = data['towns']
        for row in range(2):
            for col, label in enumerate(['old', 'new']):
                ax = axes[row, col]; ax.imshow(terrain)
                area = np.array([t[label + '_area'] for t in towns])
                kwargs = dict(c='#294f70') if row == 0 else dict(c=[t[label+'_grain_central'] for t in towns], cmap='RdYlGn', vmin=0, vmax=1)
                dots = ax.scatter([t['x'] for t in towns], [t['y'] for t in towns], s=3+.1*area, linewidths=.15, edgecolors='#263a40', **kwargs)
                ax.set(xlim=(0,1000), ylim=(463,0)); ax.axis('off')
                s = data['summary']['central']
                ax.set_title(('Release 4' if col == 0 else 'Provisional 5') + (f" · {s[label+'_res']/1e6:.2f} M residents" if row == 0 else f" · {s[label+'_grain']:.2%} annual grain need met; {s[label+'_short']} towns short"))
        fig.colorbar(dots, ax=list(axes[1]), fraction=.025, pad=.01, label='Annual grain need met')
        fig.suptitle(f'{mode.capitalize()} climate · provisional settlement atlas r5 · fixed seed 1', fontsize=16)
        fig.supxlabel('Circle size scales with built-up area. Central density; 600 field hours/worker/year. Seasonal food/work remains unqualified.', fontsize=10)
        fig.savefig(target / f'comparison_{mode}.png', dpi=150); plt.close(fig)


def main():
    baseline = check_frozen(); check_replay()
    meta, parent = read(DATA / 'atlas.json'), read(DATA / 'settled_reach.json')
    results, supply = read(BASE / 'results.json'), read(SUPPLY / 'results.json')
    target = DATA / 'settlement_provisional'; packets = {}
    for mode in ['raw', 'corrected']:
        folder = target / mode; folder.mkdir(parents=True, exist_ok=True)
        model = read(BASE / 'candidate' / f'placed_{mode}_sites.json')
        f = dict(np.load(BASE / 'candidate' / f'placed_{mode}_fields.npz'))
        z = dict(np.load(SUPPLY / 'candidate' / f'supply_{mode}.npz'))
        csvfile = folder / 'towns.csv'; shutil.copyfile(BASE / 'candidate' / f'placed_{mode}_towns.csv', csvfile)
        graincsv = folder / 'grain_central.csv'; shutil.copyfile(SUPPLY / 'candidate' / f'supply_{mode}_towns.csv', graincsv)
        options = []
        for reading, key, label in [('central', 'central_x34', '100–500 people/ha'), ('low', 'low_x14', '100 people/ha')]:
            s = supply['variants']['candidate']['climates'][mode]['scenarios'][key]
            c = next(x for x in results['comparison'] if x['mode']==mode and x['reading']==reading)
            note = (f"Provisional release 5 · fixed seed 1 · {label}. Refreshed hierarchy fitted on exposed Earth development data; no independent validation claim. "
                    f"{c['candidate_allocated_residents']/1e6:.2f} M town residents, drawn from rural cells with total population conserved. Town locations and climate r44 are unchanged. "
                    f"Annual work-limited grain meets {s['fed_share_of_residents']:.2%} of town need; {s['short_towns']} towns remain short. "
                    "600 field hours/worker/year; extraction 33.719% central or 14.049% low, with existing freight assumptions. Seasonal food/work, warehouse capacity, handling staff and complete diets remain unresolved. "
                    "Reach, trade, administration and recurrence layers use release-4 or older labelled populations. Open the before/after comparison for both cohorts and downloads.")
            adjusted = dict(f); adjusted['local_support_share_'+reading] = np.where(z[key+'_fed_share'] >= 1-1e-6, 1., 0.)
            file = folder / f'towns_{reading}.webp'
            render(mode, reading, model['sites'], model['actors'], adjusted, meta, roads=main_roads(f['land'].shape)).save(file, lossless=True)
            options.append(dict(value='provisional_'+reading, label='Provisional 5 · settlements · '+label, note=note, integrated_support=False, file=str(file.relative_to(DATA)), file_sha256=sha(file), download=str(csvfile.relative_to(DATA)), items=[dict(color='#59636b', label='Circle area scales with residents; colour identifies actor'), dict(color='#ffffff', label='White centre: annual grain need met including imports'), dict(color='#1d1d1d', label='Dark outline: marked campaign place'), dict(color='#a8382b',label='Red: painted main roads; brown: fixed rebuilt tracks')], caption='Provisional development scenario; seed 1. Seasonal feasibility remains unqualified.'))
            file = folder / f'grain_{reading}.webp'
            supply_map(model['sites'], f, z, key, f['residents_'+reading], meta).save(file, lossless=True)
            options.append(dict(value='provisional_supply_'+reading, label='Provisional 5 · annual grain · '+label, note=note, integrated_support=False, file=str(file.relative_to(DATA)), file_sha256=sha(file), download='../provisional/grain_comparison.csv', items=[dict(color=COLORS['self'],label='Annual need met from own freight hinterland'),dict(color=COLORS['imports'],label='Annual need met with imports'),dict(color=COLORS['short'],label='Annual grain need unmet'),dict(color='#5a6f8a',label='400 largest annual grain shipments')],caption='Annual ration equivalents; residents are unchanged.'))
        p = parent['packets'][mode]
        packets[mode] = dict(shape=list(f['land'].shape),parent_payload_sha256=p['payload_sha256'],expected_harvest_fingerprint=p['expected_harvest_fingerprint'],options=dict(reach_towns=options),population_budget=c['world_people'])
    write(DATA / 'settlement_provisional.json', dict(version=1,release=5,status='provisional_settlement_and_annual_grain_default',default_option='provisional_central',scientific_adoption=False,packets=packets,plan_sha256=sha(PLAN),candidate_results_sha256=sha(BASE/'results.json'),supply_results_sha256=sha(SUPPLY/'results.json')))
    comparison_view(supply)
    page = DATA.parent / 'index.html'; text = page.read_text()
    text = text.replace('data-settlement-release3-enabled', 'data-settlement-release3-enabled data-settlement-provisional-enabled') if 'data-settlement-provisional-enabled' not in text else text
    banner = '<aside id="provisional-release" style="padding:12px 20px;background:#f1dfba;color:#40351f">Provisional settlement atlas r5 · <a href="provisional/">Before/after maps and downloads</a>. New settlements and annual grain only; reach, trade and administration retain release-4 or older labelled scenarios. Seasonal food/work remains unresolved.</aside>'
    if 'id="provisional-release"' not in text:
        if re.search(r'<body[^>]*>', text):
            text = re.sub(r'(<body[^>]*>)', lambda m:m[0]+banner, text, count=1)
        else:
            # The legacy atlas relies on the browser's implicit head/body tags.
            text = text.replace('</style>', '</style>'+banner, 1)
    page.write_text(text)
    for name in ['settled-reach.js','evidence.js']:
        shutil.copyfile(ROOT/'atlas'/name, DATA.parent/name)
    release = read(ROOT/'atlases/release.json')
    release['settlement_provisional'] = dict(release=5,status='provisional',manifest_sha256=sha(DATA/'settlement_provisional.json'),comparison='earth_fit/provisional/',climate='r44 unchanged',derived_layers='release-4 or older labelled cohorts',scientific_adoption=False)
    write(ROOT/'atlases/release.json',release)
    check_frozen()
    files = [p for directory in [target,DATA.parent/'provisional'] for p in directory.rglob('*') if p.is_file()]
    files += [DATA/'settlement_provisional.json',page,DATA.parent/'settled-reach.js',DATA.parent/'evidence.js',ROOT/'atlases/release.json']
    write(OUT/'publication.json',dict(status='built_provisional_release5',publisher_sha256=sha(Path(__file__)),plan_sha256=sha(PLAN),files_sha256={str(p.relative_to(ROOT)):sha(p) for p in files},baseline_sha256=sha(OUT/'baseline.json'),frozen_input_count=len(baseline['protected_science_sha256']),historical_scientific_adoption=False))
    print('Built provisional default settlement maps, own-cohort grain maps and comparison atlas')


if __name__ == '__main__':
    main()
