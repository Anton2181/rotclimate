"""Monthly mean surface winds of an atlas's simulation, for the polity model's sailing.

    python3 -I scripts/export_winds12.py --checkpoint output/atlas_r37/earth_publication.pkl --atlas atlases/earth_fit

Reads a self-generated simulation checkpoint (scripts/build_atlas_variant.py
--checkpoint), checks that it is the atlas's own run (same parameters), bins
the winds into the twelve solstice-aligned months of the atlas's T12 / P12
(rotclimate.analogs.model_bins) and crops them to the same coarse map grid.
Writes <atlas>/data/winds12.npz: U12, V12 (m/s, east / north on the map's
grid), float16.
"""
from __future__ import annotations

import argparse
import json
import pickle
import sys
from dataclasses import asdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import numpy as np  # noqa: E402


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--checkpoint", help="the atlas's saved simulation; without it, --simulate")
    ap.add_argument("--simulate", action="store_true",
                    help="re-run the atlas's simulation from its recorded parameters and seeds")
    ap.add_argument("--workers", type=int, default=1)
    ap.add_argument("--atlas", required=True)
    a = ap.parse_args()
    from rotclimate.analogs import model_bins
    atlas = Path(a.atlas)
    sim = json.loads((atlas / "data/build_provenance.json").read_text())["simulation"]
    if a.simulate:
        from rotclimate.config import Params
        from rotclimate.model import run_ensemble
        p = Params(**{k: (tuple(v) if isinstance(v, list) else v) for k, v in sim["params"].items()
                      if k in Params.__dataclass_fields__})
        r = run_ensemble(p, sim["seeds"], workers=a.workers)
    else:
        with open(a.checkpoint, "rb") as f:
            r = pickle.load(f)["result"]
    p = r.params
    prov = sim["params"]
    mine = json.loads(json.dumps(asdict(p)))
    differ = [k for k in prov if k != "downsample" and prov[k] != mine.get(k)]
    if differ:
        raise SystemExit(f"checkpoint is not this atlas's run: {differ[:6]}")
    meta = json.loads((atlas / "data/atlas.json").read_text())
    nt, ny_m, nx_m = meta["arrays"]["T12"]["shape"]
    g = r.grid
    sl = (slice(g.pad, g.pad + ny_m), slice(g.pad, g.pad + nx_m))
    U12, _ = model_bins(r.u, np.zeros_like(r.u), r.days, p.winter_solstice_day, p.year_days)
    V12, _ = model_bins(r.v, np.zeros_like(r.v), r.days, p.winter_solstice_day, p.year_days)
    U12, V12 = U12[(slice(None),) + sl], V12[(slice(None),) + sl]
    if U12.shape != (nt, ny_m, nx_m):
        raise SystemExit(f"shape {U12.shape} != T12 {(nt, ny_m, nx_m)}")
    np.savez_compressed(atlas / "data/winds12.npz", U12=U12.astype(np.float16), V12=V12.astype(np.float16))
    sp = np.hypot(U12, V12)
    print(atlas.name, "winds12", U12.shape, "mean speed by month", np.round(sp.mean((1, 2)), 2).tolist())


if __name__ == "__main__":
    main()
