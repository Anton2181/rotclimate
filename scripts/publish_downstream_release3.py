"""Publish reach and trade layers rebuilt on release-3 towns as the displayed version.

    publish_downstream_release3.py <raw staging atlas> <corrected staging atlas> <raw control cache> <corrected control cache>

The staged layers come from scripts/export_reach_release3.py. Published
atlas.json, release.json and every earlier layer file stay byte-identical; the
page swaps these layers in through data/release3_layers.json.
"""
import json, re, shutil, sys
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parents[1]; sys.path[:0] = [str(ROOT), str(ROOT / 'scripts')]
from settlement_locations_earth import sha, write

DATA = ROOT / 'atlases/earth_fit/data'; OUT = ROOT / 'output/settlement_downstream_20261113'
KEEP_OUT = ('reach_towns', 'reach_defacto')        # owned by the settlements panel; see stage 3
PREFIX = 'Rebuilt on the release-3 towns and tracks (same rule, only the unmarked towns changed). '


def relocate(value, staging, legacy_dir, target, rel, changed):
    if isinstance(value, dict):
        return {k: relocate(v, staging, legacy_dir, target, rel, changed) for k, v in value.items()}
    if isinstance(value, list):
        return [relocate(v, staging, legacy_dir, target, rel, changed) for v in value]
    if isinstance(value, str) and re.fullmatch(r'[\w.-]+\.(webp|png|csv|json|gif)', value) and (staging / value).is_file():
        old = legacy_dir / value
        if not old.is_file() or old.read_bytes() != (staging / value).read_bytes():
            changed.append(value)
        shutil.copyfile(staging / value, target / value)
        return f'{rel}/{value}'
    return value


def stats(cache):
    with np.load(cache) as z:
        land = z['land']; claim = z['claim']; held = z['held_by_00']; towns = z['towns']; mass = z['t_mass']
        claimed = land & (claim >= 0)
        return dict(towns=int(len(towns)), claimed_cells=int(claimed.sum()),
            claimed_held_share=float(((held >= 0) & claimed).sum() / claimed.sum()),
            held_by_claimant_share=float(((held == claim) & claimed).sum() / claimed.sum()),
            largest_market_share=float(mass.max() / mass.sum()), top10_market_share=float(np.sort(mass)[-10:].sum() / mass.sum()))


def main(raw_staging, corrected_staging, raw_control, corrected_control):
    meta = json.loads((DATA / 'atlas.json').read_text()); parent = json.loads((DATA / 'settled_reach.json').read_text())
    preserved = {str(p.relative_to(ROOT)): sha(p) for p in (DATA / 'atlas.json', ROOT / 'atlases/release.json')}
    packets = {}; OUT.mkdir(parents=True, exist_ok=True)
    for mode, staging, control in (('raw', Path(raw_staging), raw_control), ('corrected', Path(corrected_staging), corrected_control)):
        sdata = staging / 'data'; smeta = json.loads((sdata / 'atlas.json').read_text())
        legacy_dir = DATA / ('corrected' if mode == 'corrected' else '')
        legacy_layers = {l['id']: l for l in (meta['corrected_climate']['layers'] if mode == 'corrected' else meta['layers'])}
        target = DATA / 'release3' / mode; target.mkdir(parents=True, exist_ok=True); layers = []; unchanged = []; report = {}
        for layer in smeta['layers']:
            if not layer['id'].startswith('reach_') or layer['id'] in KEEP_OUT:
                continue
            changed = []
            new = relocate(layer, sdata, legacy_dir, target, f'release3/{mode}', changed)
            if not changed:
                unchanged.append(layer['id']); continue
            if 'note' in new:
                new['note'] = PREFIX + new['note']
            for option in (new.get('variants') or {}).get('options', []):
                if 'note' in option: option['note'] = PREFIX + option['note']
            if set(new) != set(legacy_layers[layer['id']]) - {'evidence'} and set(new) != set(legacy_layers[layer['id']]):
                report[layer['id']] = sorted(set(new) ^ set(legacy_layers[layer['id']]))
            layers.append(new)
        downloads = {}
        for name in ('polities.csv', 'market_hinterlands.csv'):
            shutil.copyfile(sdata / name, target / name); downloads[name] = dict(file=f'release3/{mode}/{name}', sha256=sha(target / name))
        for stale in target.iterdir():          # only files a layer or download references
            if not any(stale.name in json.dumps(l) for l in layers) and stale.name not in downloads: stale.unlink()
        cache = ROOT / 'output/polity_map' / f'{staging.name}.npz'
        packets[mode] = dict(layers=layers, unchanged_layers=unchanged, key_differences=report, downloads=downloads,
            files={p.name: sha(p) for p in sorted(target.iterdir())},
            expected_harvest_fingerprint=parent['packets'][mode]['expected_harvest_fingerprint'],
            statistics=dict(earlier_towns=stats(control), release3_towns=stats(cache)))
    for path, digest in preserved.items():
        if sha(ROOT / path) != digest: raise ValueError('Published metadata modified: ' + path)
    write(DATA / 'release3_layers.json', dict(version=1, status='reach_and_trade_rebuilt_on_release3_towns', packets=packets,
        publisher_sha256=sha(Path(__file__)), declaration='calibration/settlement_downstream_20261113/plan.json'))
    write(OUT / 'reach_trade.json', dict(status='published', manifest_sha256=sha(DATA / 'release3_layers.json'), preserved=preserved,
        controls=dict(raw='unmodified exporter reproduced every published raw reach/trade image byte for byte',
                      corrected='unmodified exporter reproduced every published corrected reach/trade image byte for byte'),
        packets={m: dict(layers=[l['id'] for l in p['layers']], unchanged=p['unchanged_layers'], statistics=p['statistics']) for m, p in packets.items()}))
    for m, p in packets.items():
        print(m, [l['id'] for l in p['layers']], 'unchanged', p['unchanged_layers'], p['key_differences'], len(p['files']), 'files'); print(' ', p['statistics'])


if __name__ == '__main__':
    main(*sys.argv[1:5])
