"""Settlement hierarchy A4: two-parameter centre model (selection strength phi, centre shift c), fitted on training folds,
scored on held-out folds (calibration/settlement_hierarchy_20261115/plan.json A4)."""
import json, subprocess, sys
from pathlib import Path
import numpy as np
from scipy.stats import ks_2samp
ROOT = Path(__file__).resolve().parents[1]; sys.path[:0] = [str(ROOT), str(ROOT / 'scripts')]
import settlement_hierarchy as SH
from polity import settlement_sizes as Z
from polity.survey_transfer import sphere_distance
from settlement_locations_earth import sha, write

PHI = [0.0, 0.25, 0.5, 0.75, 1.0]; CS = [round(0.1 * k, 1) for k in range(14)]; SEEDS = SH.SEEDS


def generate(pred, sig, cap, centre, C, phi, c, seed, members_order):
    e = Z.draws(len(pred), seed).copy(); mean = pred + c * cap
    for k in C:
        mem = members_order[k]; take = mem[:int(round(phi * len(mem)))]; pool = np.r_[k, take]
        j = pool[np.argmax(e[pool])]; e[k], e[j] = e[j], e[k]
    return np.exp(mean + sig * e)


def stats(gen, sub, centre, cap, pred, mask=None):
    s = sub if mask is None else sub & mask; cp = cap if mask is None else cap & mask
    return (float(np.mean(gen[s] > gen[centre[s]])), float(np.median(gen[s] / gen[centre[s]])), float(np.exp(np.mean(np.log(gen[cp]) - pred[cp]))))


def main():
    if subprocess.check_output(['git', 'show', 'HEAD:' + str(SH.PLAN.relative_to(ROOT))], cwd=ROOT) != SH.PLAN.read_bytes():
        raise ValueError('Commit the exact declaration first')
    rows, lat, lon, cap = SH.cohort(); n = len(rows)
    y = np.log([r['area'] for r in rows]); lnH = np.array([r['lnH'] for r in rows]); fold = np.array([Z.province_fold(r['province']) for r in rows])
    C = np.flatnonzero(cap); centre = np.full(n, -1)
    for i in np.flatnonzero(~cap):
        d = sphere_distance(lat[C], lon[C], lat[i], lon[i]); j = int(np.argmin(d))
        if d[j] <= SH.RADIUS: centre[i] = C[j]
    sub = centre >= 0; area = np.exp(y); capf = cap.astype(float)
    rng = np.random.default_rng(2026); order = {k: rng.permutation(np.flatnonzero(centre == k)) for k in C}
    pred = np.empty(n)
    for f in range(4):
        tr, te = fold != f, fold == f; c = Z.fit({'lnH': lnH[tr]}, ('lnH',), y[tr]); pred[te] = c[0] + c[1] * lnH[te]
    sig = float(np.std(y - pred))
    def observed(mask): s = sub & mask; cp = cap & mask; return (float(np.mean(area[s] > area[centre[s]])), float(np.median(area[s] / area[centre[s]])), float(np.exp(np.mean(y[cp] - pred[cp]))))
    chosen = {}; held = {s: np.empty(n) for s in SEEDS}
    for f in range(4):
        tr = fold != f; obs = observed(tr); best = None
        for phi in PHI:
            for c in CS:
                vals = np.mean([stats(generate(pred, sig, capf, centre, C, phi, c, s, order), sub, centre, cap, pred, tr) for s in SEEDS], 0)
                loss = (vals[0] - obs[0]) ** 2 + np.log(vals[1] / obs[1]) ** 2 + np.log(vals[2] / obs[2]) ** 2
                if best is None or loss < best[0]: best = (loss, phi, c)
        chosen[f] = dict(phi=best[1], c=best[2], train_loss=float(best[0]))
        for s in SEEDS:
            g = generate(pred, sig, capf, centre, C, best[1], best[2], s, order); held[s][fold == f] = g[fold == f]
    runs = []
    for s in SEEDS:
        g = np.clip(held[s], area.min(), area.max()); sh, mr, cf = stats(g, sub, centre, cap, pred)
        runs.append(dict(seed=s, ks=float(ks_2samp(g, area).statistic), total_ratio=float(g.sum() / area.sum()), share_sub_larger=sh, median_ratio=mr, implied_capital_factor=cf))
    obs = observed(np.ones(n, bool)); m = lambda k: float(np.mean([r[k] for r in runs]))
    gate = dict(ks=m('ks'), total_ratio=m('total_ratio'), share_sub_larger=m('share_sub_larger'), median_ratio=m('median_ratio'), implied_capital_factor=m('implied_capital_factor'))
    passed = bool(gate['ks'] <= .10 and .80 <= gate['total_ratio'] <= 1.25 and abs(gate['share_sub_larger'] - obs[0]) <= .05
                  and abs(np.log(gate['median_ratio'] / obs[1])) <= np.log(1.25) and abs(np.log(gate['implied_capital_factor'] / obs[2])) <= np.log(1.25))
    # full-data fit for the map
    fullobs = obs; best = None
    for phi in PHI:
        for c in CS:
            vals = np.mean([stats(generate(pred, sig, capf, centre, C, phi, c, s, order), sub, centre, cap, pred) for s in SEEDS], 0)
            loss = (vals[0] - fullobs[0]) ** 2 + np.log(vals[1] / fullobs[1]) ** 2 + np.log(vals[2] / fullobs[2]) ** 2
            if best is None or loss < best[0]: best = (loss, phi, c)
    full_m1 = Z.fit({'lnH': lnH}, ('lnH',), y)
    out = dict(status='settlement_hierarchy_soft_selection_development', plan_sha256=sha(SH.PLAN), producer_sha256=sha(Path(__file__)), observed=dict(share_sub_larger=obs[0], median_ratio=obs[1], capital_factor=obs[2]),
               fold_choices=chosen, runs=runs, gate=gate, passed=passed, full_fit=dict(phi=best[1], c=best[2], loss=float(best[0]), m1_coefficients=[float(v) for v in full_m1], sigma=sig))
    write(SH.OUT / 'results_soft.json', out); print(json.dumps({k: v for k, v in out.items() if k != 'runs'}, indent=1))


if __name__ == '__main__':
    main()
