"""Route the standard town placement to the published release-3 positions.

install() replaces polity.settle.place_towns (and the names already imported
from it) with a wrapper that recognises the published raw/corrected fantasy
density and returns the reviewed release-3 unmarked towns. Any other input is
refused, so nothing is silently placed by a different rule.
"""
import json
from pathlib import Path

import numpy as np
from scipy import ndimage as ndi

from . import settle

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'output/settlement_release3_20261113'


def _load():
    known = []
    for mode in ('raw', 'corrected'):
        with np.load(OUT / f'placed_{mode}_fields.npz') as f:
            density = f['density'].copy(); marked = {tuple(int(v) for v in m) for m in f['marked_cells']}
        sites = json.loads((OUT / f'placed_{mode}_sites.json').read_text())['sites']
        towns = [(s['row'], s['column']) for s in sites if not s['marked']]
        known.append((mode, density, marked, towns))
    return known


def install():
    known = _load(); used = []

    def place_towns(density, land, water_km, road, elev, cell_km, marked, allowed=None, **_):
        land = np.asarray(land, bool); given = np.where(land, np.asarray(density, float), 0.0)
        for mode, reference, anchors, towns in known:
            if given.shape == reference.shape and np.array_equal(given, reference):
                if {(int(y), int(x)) for y, x in marked} != anchors:
                    raise ValueError('Marked places differ from the release-3 build')
                coast_km = ndi.distance_transform_edt(land) * cell_km
                _, smooth = settle.site_score(density, land, water_km, coast_km, road, elev, cell_km)
                used.append(mode)
                return list(towns), coast_km, smooth
        raise ValueError('Unknown density: release-3 positions exist only for the published raw and corrected fantasy worlds')

    from . import fields, economic_world, administrative_world
    settle.place_towns = place_towns; fields.place_towns = place_towns
    for module in (economic_world, administrative_world):
        if hasattr(module, 'place_towns'):
            module.place_towns = place_towns
    return used
