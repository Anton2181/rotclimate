"""Political reach layers for an atlas: control, days beyond the network, days
from the imperial capital, and who reaches where.

    python3 -I scripts/export_reach.py atlases/free_fit
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image

from .fields import CONTESTED_DAYS, HELD_DAYS, LAYERS, compute

ROOT = Path(__file__).resolve().parents[1]
CONTROL_RAMP = ['#4d1a17', '#8f3426', '#c8603a', '#e5a557', '#e8d98a', '#9fbf5f', '#4f8f4a', '#1f5f3a']
DAYS_RAMP = CONTROL_RAMP[::-1]
TRAVEL_NOTE = ('Days on foot for an official or a patrol: roads and river routes 30 km a day, ferry routes 40, '
               'otherwise Tobler\'s hiking speed over the terrain for 7 hours a day, slowed by Soule & Goldman '
               'terrain coefficients (forest 1.5, swamp 1.8, desert 1.6, snow 2.5) and quickened by footpaths where '
               'people farm. The countryside between the marked places holds unmarked seats, one per 40,000 '
               'people (the mean Han county of AD 2), as dense as the people. No open-sea shipping.')


def export(atlas):
    from harvest.export import color_image
    from rotclimate.geography import source_layers
    atlas = Path(atlas); data = atlas / 'data'
    meta = json.loads((data / 'atlas.json').read_text())
    r = compute(atlas)
    land, elev, f = r['land'], r['elev'], r['fields']
    coast = source_layers()['land']

    def save(rgb, filename):
        image = Image.fromarray((np.clip(rgb, 0, 1) * 255).astype(np.uint8))
        image = image.resize((meta['width'], meta['height']), Image.Resampling.NEAREST)
        pixels = np.array(image); pixels[~coast] = [214, 227, 240]
        Image.fromarray(pixels).save(data / filename, 'WEBP', quality=88, method=4)

    layers = []

    def ramp(lid, value, label, unit, lo, hi, stops, note):
        save(color_image(value, land, elev, stops, lo, hi), lid + '.webp')
        layers.append(dict(id=lid, file=lid + '.webp', label=label, kind='ramp', group='Political reach',
                           unit=unit, vmin=lo, vmax=hi, stops=stops, note=note, log=False))
    ramp('reach_control', 100 * r['control_open'], 'Effective control', '% · exp(−days / 1 day) from the nearest road, '
         'town, fort, monastery or unmarked seat, snow-free season', 0, 100, CONTROL_RAMP,
         'One day out and one day back is the reach a county seat or a fort holds directly; at two days a third of it '
         'remains. ' + TRAVEL_NOTE)
    ramp('reach_control_winter', 100 * r['control_winter'], 'Control in winter', '% · as above, with the months of '
         'lasting snow (soft snow 2.5× harder going)', 0, 100, CONTROL_RAMP, TRAVEL_NOTE)
    ramp('reach_days', np.minimum(f['days_open'], 6), 'Days beyond the roads', 'days on foot to the nearest road, '
         'town, fort, monastery or unmarked seat', 0, 6, DAYS_RAMP, TRAVEL_NOTE)
    ramp('reach_capital', np.minimum(f['capital_days_open'], 60), 'Days from the capital', 'days on foot from the '
         'imperial capital by road and track', 0, 60, DAYS_RAMP, TRAVEL_NOTE)

    # who reaches where
    best, best_days = f['polity_best'], f['polity_best_days']
    strength = np.clip(np.exp(-np.nan_to_num(best_days, nan=99, posinf=99)), 0, 1)
    rgb = np.ones(land.shape + (3,)) * np.array([.93, .91, .86])
    for k, name in enumerate(r['polity_names']):
        m = land & (best == k)
        col = np.array(r['polity_rgb'][name]) / 255.0
        rgb[m] = col * strength[m, None] + np.array([.93, .91, .86]) * (1 - strength[m, None])
    yy, xx = np.mgrid[:land.shape[0], :land.shape[1]]
    hatch = r['contested'] & ((xx + yy) % 5 == 0)
    rgb[hatch] = rgb[hatch] * .45
    gy, gx = np.gradient(elev)
    rgb = np.clip(rgb * np.clip(.96 - .00018 * gx + .00022 * gy, .78, 1.08)[..., None], 0, 1)
    rgb[~land] = [.84, .89, .94]
    save(rgb, 'reach_polities.webp')
    area = r['cell_km'] ** 2
    items = []
    for k, name in enumerate(r['polity_names']):
        held = float((r['held'] & (best == k)).sum() * area)
        if held > 0:
            items.append(dict(color='#%02x%02x%02x' % tuple(r['polity_rgb'][name]), label=f'{name} · {held / 1000:,.0f} k km² held'))
    layers.append(dict(id='reach_polities', file='reach_polities.webp', label='Who reaches where', kind='categories',
                       group='Political reach', items=items,
                       note=f'Each place takes the polity whose own roads, towns and unmarked seats are nearest in days; the '
                            f'colour fades with the days (exp(−days)). Hatched: contested, a rival within '
                            f'{CONTESTED_DAYS:g} day. Held = within {HELD_DAYS:g} days. ' + TRAVEL_NOTE))
    meta['layers'] = [l for l in meta['layers'] if not l['id'].startswith('reach_')] + layers
    manifest = json.loads((LAYERS / 'manifest.json').read_text())
    meta['reach'] = dict(source_sha256=manifest['source_sha256'], held_days=HELD_DAYS, contested_days=CONTESTED_DAYS)
    (data / 'atlas.json').write_text(json.dumps(meta, ensure_ascii=False))
    print('Political reach layers written to', data, flush=True)


if __name__ == '__main__':
    for path in sys.argv[1:]:
        export(path)
