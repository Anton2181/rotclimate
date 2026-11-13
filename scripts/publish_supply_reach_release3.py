"""Publish the supply-supported reach (control v2 / v2.1) rebuilt on release-3 town positions."""
import json, re, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]; sys.path[:0] = [str(ROOT), str(ROOT / 'scripts')]
from settlement_locations_earth import sha, write

DATA = ROOT / 'atlases/earth_fit/data'; OUT = ROOT / 'output/settlement_downstream_20261113'
NOTE = ('Rebuilt on the release-3 town POSITIONS: market hinterlands, joint food budget, field work, soil fertility and the control rule were '
        'rerun unchanged. Town requests keep the chain\'s original 7.5% of served people, because that request is part of the rule that was '
        'blind-tested on Earth; the release-2 calibrated residents are not fed in. The place-by-place food ledger below the map is not rebuilt '
        'for this version. ')


def main():
    parent = json.loads((DATA / 'settled_reach.json').read_text()); packets = {}
    for mode in ('raw', 'corrected'):
        old = parent['packets'][mode]; legacy = {o['value']: o for o in old['options']['reach_defacto']}; options = []; compare = {}
        for case, label in (('v21_joint365', 'Control v2.1'), ('v2_joint365', 'Control v2')):
            file = DATA / 'release3/reach' / ('corrected' if mode == 'corrected' else '') / f'settled_control_{case}.webp'
            base = legacy[case]
            options.append(dict(value='release3_' + case.split('_')[0], label=f'Release 3 towns · {label}', note=NOTE + base.get('note', ''),
                integrated_support=False, release3=True, file=str(file.relative_to(DATA)), file_sha256=sha(file),
                items=base.get('items', []), caption=base.get('caption', '')))
            tag = 'control_v21' if case.startswith('v21') else 'control_v2'
            pa = ROOT / f'output/{tag}_20261107/earth_fit_{mode}/summary.json'; pb = ROOT / f'output/{tag}_release3_20261113/earth_fit_{mode}/summary.json'
            if not (pa.is_file() and pb.is_file()):
                continue          # the earlier v2 run kept no per-climate summary in this checkout
            a = json.loads(pa.read_text()); b = json.loads(pb.read_text())
            compare[case] = {k: dict(earlier=a[k], release3=b[k]) for k in a if isinstance(a[k], (int, float)) and not isinstance(a[k], bool) and k in b}
        packets[mode] = dict(shape=old['shape'], parent_payload_sha256=old['payload_sha256'],
            expected_harvest_fingerprint=old['expected_harvest_fingerprint'], options=dict(reach_defacto=options), comparison=compare)
    write(DATA / 'release3_reach.json', dict(version=1, status='supply_supported_reach_rebuilt_on_release3_positions', default_option='release3_v21',
        packets=packets, publisher_sha256=sha(Path(__file__)), declaration='calibration/settlement_downstream_20261113/plan.json'))
    page = DATA.parent / 'index.html'; html = page.read_text()
    tag = re.search(r'<script src="settled-reach\.js"[^>]*></script>', html).group(0)
    if 'data-release3-reach-enabled' not in tag:
        page.write_text(html.replace(tag, tag.replace('></script>', ' data-release3-reach-enabled></script>')))
    write(OUT / 'supply_reach.json', dict(status='published', manifest_sha256=sha(DATA / 'release3_reach.json'),
        chain=['review_settlement_integration', 'extend_settlement_labour', 'extend_settlement_fertility', 'build_control_v2', 'build_control_v21'],
        fertility_factor_cache='regenerated with scripts/fertility_integration.py maps; tracked map_factors.json summary reproduced unchanged',
        comparison={m: p['comparison'] for m, p in packets.items()}))
    print({m: {c: {k: (round(v['earlier'], 4), round(v['release3'], 4)) for k, v in d.items() if 'share' in k or k == 'staffed'} for c, d in p['comparison'].items()} for m, p in packets.items()})


if __name__ == '__main__':
    main()
