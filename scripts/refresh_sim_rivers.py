"""Simulated rivers of finished atlases from their stored monthly climate (rotclimate.routing, source resolution).

The atlas build computes them from the simulation itself (rotclimate.atlas.river_segments); atlases built before
8 Nov 2026 kept the climate grid's own network (14.7 km cells, cell centre to cell centre). This redraws them from the
atlas's monthly surface temperature and precipitation with the same runoff rule and routing.

    .venv/bin/python -I scripts/refresh_sim_rivers.py atlases/free_fit atlases/whittaker_fit
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
from scipy import ndimage as ndi

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "scripts")]


def refresh(atlas):
    from harvest.export import climate_arrays, surface_months
    from rotclimate import routing as R
    from rotclimate.geography import source_layers
    atlas = Path(atlas); data = atlas / "data"; meta = json.loads((data / "atlas.json").read_text())
    params = json.loads((atlas / "params.json").read_text())
    arrays = climate_arrays(data, meta)
    t, p, _, _ = surface_months(meta, arrays)                          # analysis grid (half source resolution)
    ro = R.runoff_from_months(t, p, params.get("year_days", 365) / 12.0)
    H, W = source_layers()["land"].shape
    land_a = ndi.zoom(source_layers()["land"].astype(float), (ro.shape[0] / H, ro.shape[1] / W), order=1) > 0.5
    _, (iy, ix) = ndi.distance_transform_edt(~land_a, return_indices=True)
    ro = ro[iy, ix]
    yy, xx = np.mgrid[0:H, 0:W].astype(float)
    ro_px = ndi.map_coordinates(ro, [(yy + 0.5) * ro.shape[0] / H - 0.5, (xx + 0.5) * ro.shape[1] / W - 0.5], order=1, mode="nearest")
    q, recv, land, _ = R.discharge(ro_px, params["tier_tops"], params.get("terrain_file", ""), params["map_width_mi"])
    meta["rivers_sim"] = R.segments(q, recv, land)
    meta["rivers_sim_note"] = "model runoff routed at the drawing's resolution (rotclimate/routing.py, refreshed from the atlas's monthly climate)"
    (data / "atlas.json").write_text(json.dumps(meta, ensure_ascii=False))
    print(atlas.name, len(meta["rivers_sim"]), "segments")


if __name__ == "__main__":
    for a in sys.argv[1:]:
        refresh(a)
