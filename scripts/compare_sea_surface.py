"""Compare the model's monthly sea surface with WOA18 over each region's seas.

    python -I scripts/compare_sea_surface.py --params calibration/local_accuracy_20261023/r40_params.json \
        --regions anatolia levant central_asia iberia --out output/sea_20261031/sst_r40.json

Runs each region once at 56 km, records the sea-surface temperature the
model uses at every step (ClimateModel.sst plus upwelling, as the step
applies them), and sets its monthly means beside WOA18 (grid.obs_sst) over
the region's sea cells, split into enclosed seas (the model's own enclosure
share above one half) and open sea. Diagnostic only.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from multiprocessing import Pool
from pathlib import Path

os.environ.setdefault("OMP_NUM_THREADS", "1")
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / "scripts"))
import numpy as np  # noqa: E402

from benchmark_local import DEV12_SPECS  # noqa: E402
from earth_benchmark import load_params  # noqa: E402
from rotclimate import earth  # noqa: E402
from rotclimate.koppen import monthly_weights  # noqa: E402
from rotclimate.model import ClimateModel  # noqa: E402


def one(job):
    region, params_path, changes = job
    earth.REGIONS.update(json.loads(DEV12_SPECS.read_text()))
    case = earth.region_case(region, 56.0)
    g = case.grid
    p = earth.earth_params(load_params(params_path), case)
    if changes:
        p = p.replace(**changes)
    model = ClimateModel(p, g)
    record = {}
    raw = model.sst

    def sst(day, To, Tl):
        out = raw(day, To, Tl)
        record[round(float(day), 6)] = out.copy()
        return out
    model.sst = sst
    res = model.run()
    days = np.asarray(res.days, float)
    S = np.stack([record[round(float(d), 6)] for d in days])
    W = monthly_weights(days, p.year_days)
    Sm = (W @ S.reshape(len(days), -1)).reshape((12,) + S.shape[1:])
    obs = g.obs_sst
    sea = ~g.land & np.isfinite(obs).all(0) & g.inmap if hasattr(g, 'inmap') else ~g.land & np.isfinite(obs).all(0)
    enclosed = model.enclosure > 0.5
    out = dict(region=region, sea_cells=int(sea.sum()))
    for name, m in (('enclosed', sea & enclosed), ('open', sea & ~enclosed)):
        if m.sum() < 3:
            continue
        out[name] = dict(cells=int(m.sum()), model=Sm[:, m].mean(1).round(2).tolist(), woa=obs[:, m].mean(1).round(2).tolist(),
                         bias=(Sm[:, m] - obs[:, m]).mean(1).round(2).tolist())
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--params', required=True); ap.add_argument('--regions', nargs='+', required=True)
    ap.add_argument('--set', default='{}', help='JSON parameter changes'); ap.add_argument('--workers', type=int, default=4)
    ap.add_argument('--out', required=True)
    a = ap.parse_args()
    changes = json.loads(a.set)
    with Pool(a.workers) as pool:
        rows = pool.map(one, [(r, a.params, changes) for r in a.regions])
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    Path(a.out).write_text(json.dumps(dict(params=a.params, changes=changes, regions=rows), indent=1))
    for r in rows:
        for k in ('enclosed', 'open'):
            if k in r:
                print(f"{r['region']:15s} {k:8s} n{r[k]['cells']:4d} bias " + " ".join(f"{x:+5.1f}" for x in r[k]['bias'])
                      + f" | model Jan {r[k]['model'][0]:.1f} Jul {r[k]['model'][6]:.1f} woa Jan {r[k]['woa'][0]:.1f} Jul {r[k]['woa'][6]:.1f}")


if __name__ == '__main__':
    main()
