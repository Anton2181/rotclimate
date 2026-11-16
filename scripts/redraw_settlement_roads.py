"""Redraw the published release-4 Settlements images with the map's main roads (owner, 16 Nov 2026: "tiny roads that lead to
nowhere" — 89 of 186 minor-track ends meet a drawn main road, which these images did not show). Only the drawing changes:
towns, sizes and tracks are the published release-4 data. Updates the images' sha256 and legend in settlement_release3.json.

    .venv/bin/python -I scripts/redraw_settlement_roads.py
"""
import json, sys
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parents[1]; sys.path[:0] = [str(ROOT), str(ROOT / 'scripts')]
from settlement_locations_earth import sha, write
from publish_settlement_release2 import render, main_roads
from publish_settlement_release3 import ROADS_ITEM

R4 = ROOT / 'output/settlement_release4_20261116/release3'; SUP = ROOT / 'output/settlement_release4_20261116/supply'; DATA = ROOT / 'atlases/earth_fit/data'


def main():
    meta = json.loads((DATA / 'atlas.json').read_text()); man = json.loads((DATA / 'settlement_release3.json').read_text())
    for mode in ('raw', 'corrected'):
        model = json.loads((R4 / f'placed_{mode}_sites.json').read_text()); f = dict(np.load(R4 / f'placed_{mode}_fields.npz'))
        z = np.load(SUP / f'supply_{mode}.npz'); roads = main_roads(f['land'].shape)
        for o in man['packets'][mode]['options']['reach_towns']:
            scenario = {'release3_central': 'central', 'release3_low': 'low'}.get(o['value'])
            if scenario is None:
                continue
            # white centre = fed including imports, exactly as the release-4 supply step drew it (central 34 %, low 14 %)
            g = dict(f); g['local_support_share_' + scenario] = z[{'central': 'central_x34', 'low': 'low_x14'}[scenario] + '_fed_share']
            file = DATA / o['file']
            render(mode, scenario, model['sites'], model['actors'], g, meta, roads=roads).save(file, lossless=True)
            o['file_sha256'] = sha(file)
            if ROADS_ITEM not in o['items']:
                i = next(k for k, it in enumerate(o['items']) if it['label'].startswith('Brown lines')) + 1
                o['items'].insert(i, ROADS_ITEM)
            print(mode, scenario, file.relative_to(DATA))
    write(DATA / 'settlement_release3.json', man)


if __name__ == '__main__':
    main()
