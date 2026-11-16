"""WP3 confluence screen (calibration/wp3_site_factors_20261116/plan.json)."""
import json, sys
from pathlib import Path
import numpy as np
from scipy import ndimage as ndi
ROOT = Path(__file__).resolve().parents[1]; sys.path[:0] = [str(ROOT), str(ROOT / 'scripts')]
from polity.settlement_locations import prior_tiling_sites
from settlement_locations_earth import metrics
IN = ROOT / 'output/settlement_locations_20261110'; OUT = ROOT / 'output/wp3_site_factors_20261116'


def confluence(d, R=15.0):
    river = d['water_km'] <= 1e-6
    nb = ndi.convolve(river.astype(int), np.ones((3, 3), int), mode='constant') - river
    junc = ndi.binary_dilation(river & (nb >= 3))
    cell = float(d['cell_km']); dist = ndi.distance_transform_edt(~junc) * cell
    return np.exp(-(dist / R) ** 2), int(junc.sum())


def run(d, prior, target):
    f = lambda sp: prior_tiling_sites(d['density'], d['land'], d['water_km'], d['road'], d['elev'], float(d['cell_km']), prior=prior,
                                      allowed=d['allowed'], aridity=d['aridity'], seat_people=sp)
    lo, hi = 2e3, 1e6
    for _ in range(22):
        sp = np.sqrt(lo * hi); n = len(f(sp))
        if n > target: lo = sp
        else: hi = sp
    return f(np.sqrt(lo * hi))


def main():
    OUT.mkdir(parents=True, exist_ok=True); res = {}
    for pool in ('han', 'rome'):
        d = dict(np.load(IN / f'{pool}_inputs.npz')); target = int(d['allowed'].ravel()[d['real']].sum())
        c, nj = confluence(d)
        for k in (0.0, 0.5, 1.0):
            t = run(d, d['history'] * (1 + k * c), target); m = metrics(d, t)
            res[f'{pool}_k{k}'] = dict(junction_cells=nj, **{x: m[x] for x in ('composite', 'F1', 'recall', 'precision', 'M1', 'M3', 'n_model', 'n_real')})
            print(pool, k, json.dumps(res[f'{pool}_k{k}']), flush=True)
    (OUT / 'results.json').write_text(json.dumps(res, indent=1) + '\n')


if __name__ == '__main__':
    main()
