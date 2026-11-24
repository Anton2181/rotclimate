"""Batch calibration: a perturbed-parameter ensemble, Gaussian-process emulators of every region's score terms, and
waves of emulator-chosen candidates (history-matching style). Replaces one-knob-at-a-time coordinate descent.

    python3 -I scripts/ppe.py design   PLAN.json      # space-filling (scrambled Sobol) design -> OUT/design.json
    python3 -I scripts/ppe.py run      PLAN.json      # evaluate every pending point (resumable) -> OUT/results.jsonl
    python3 -I scripts/ppe.py fit      PLAN.json      # fit emulators, leave-one-out check, sensitivities -> OUT/emulator.json
    python3 -I scripts/ppe.py propose  PLAN.json K    # K new points from the emulator (best feasible + spread) -> design
    python3 -I scripts/ppe.py report   PLAN.json      # evaluated points ranked by the v4 objective
    python3 -I scripts/ppe.py import   PLAN.json      # copy an earlier ensemble's results, re-referenced (plan import_from)

Each evaluation runs the candidate on the development parts (refit_e75.evaluate, paired with the plan's reference).
The emulators predict, for every region, the candidate's temperature MAE and rain loss; S55, S49, T and P are then
computed from the predicted regions exactly as the gate computes them, so constraints apply to the emulated gate.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import refit_e75 as R  # noqa: E402
from gate_v3 import paired  # noqa: E402


def load_plan(path):
    plan = json.loads(Path(path).read_text())
    out = ROOT / plan["out"]
    out.mkdir(parents=True, exist_ok=True)
    R.OUT = out / "runs"
    R.REF = ROOT / plan["reference"]
    R.REF_NAME = plan["reference_name"]
    R.PARTS.update(plan.get("extra_parts", {}))
    return plan, out


def to_unit(plan, x):
    u = []
    for k, (lo, hi, sc) in plan["knobs"].items():
        v = x[k]
        u.append((np.log(v) - np.log(lo)) / (np.log(hi) - np.log(lo)) if sc == "log" else (v - lo) / (hi - lo))
    return np.array(u)


def from_unit(plan, u):
    x = {}
    for (k, (lo, hi, sc)), v in zip(plan["knobs"].items(), u):
        x[k] = float(np.exp(np.log(lo) + v * (np.log(hi) - np.log(lo)))) if sc == "log" else float(lo + v * (hi - lo))
    return x


def base_params(plan):
    p = json.loads((ROOT / plan["base"]).read_text())
    p.update(plan.get("base_set", {}))
    return p


def read_design(out):
    f = out / "design.json"
    return json.loads(f.read_text()) if f.exists() else []


def read_results(out):
    f = out / "results.jsonl"
    return [json.loads(l) for l in f.read_text().splitlines() if l.strip()] if f.exists() else []


def design(plan, out):
    from scipy.stats import qmc
    if read_design(out):
        raise SystemExit("design exists")
    d = len(plan["knobs"])
    u = qmc.Sobol(d, scramble=True, seed=plan["seed"]).random(plan["wave1"])
    pts = [dict(name=f"w1_{i:03d}", wave=1, x=from_unit(plan, ui)) for i, ui in enumerate(u)]
    if plan.get("include_base", True):
        b = base_params(plan)
        pts.insert(0, dict(name="w1_base", wave=1, x={k: b[k] for k in plan["knobs"]}))
    (out / "design.json").write_text(json.dumps(pts, indent=1) + "\n")
    print(len(pts), "points")


def region_values(name):
    d = R.OUT / name
    Rr, Cc = paired(d, R.REF_NAME, None, list(R.PARTS))
    return {n: [Cc[n]["temperature"]["monthly_mae_C"], Cc[n]["rain"]["loss"],
                Rr[n]["temperature"]["monthly_mae_C"], Rr[n]["rain"]["loss"]] for n in Rr}


def run(plan, out):
    done = {r["name"] for r in read_results(out)}
    base = base_params(plan)
    for pt in read_design(out):
        if pt["name"] in done:
            continue
        p = dict(base)
        p.update(pt["x"])
        try:
            R.evaluate(pt["name"], p)
            rec = dict(name=pt["name"], wave=pt["wave"], x=pt["x"], regions=region_values(pt["name"]), ok=True)
        except Exception as e:  # a failed numerical check is data too: infeasible
            rec = dict(name=pt["name"], wave=pt["wave"], x=pt["x"], ok=False, error=repr(e)[:300])
        with (out / "results.jsonl").open("a") as f:
            f.write(json.dumps(rec) + "\n")
        print(pt["name"], "ok" if rec["ok"] else "FAILED", flush=True)


def gate_terms(C, Rf, names, t_names):
    """C: candidate [n, 2] (T, P) in region order `names`; Rf: reference [n, 2]. Returns S55, T, P, S49."""
    def S(idx):
        c, r = C[..., idx, :].mean(-2), Rf[idx].mean(0)
        return 0.5 * c[..., 0] / r[0] + 0.5 * c[..., 1] / r[1], c[..., 0] / r[0] - 1, c[..., 1] / r[1] - 1
    allx = np.arange(len(names))
    s55, t, p = S(allx)
    if isinstance(t_names, dict):
        # policy v6: the guard term is the worst regime's S (regimes_v2.json), in place of S49
        groups = {}
        for i, n in enumerate(names):
            groups.setdefault(t_names.get(n, "untagged"), []).append(i)
        s49 = np.max(np.stack([S(np.array(ix))[0] for ix in groups.values()]), axis=0)
        return s55, t, p, s49
    s49, _, _ = S(np.array([i for i, n in enumerate(names) if n not in t_names]))
    return s55, t, p, s49


def objective(plan, s55, t, p, s49):
    guard = 1.02 if plan.get("policy") == "v6" else 1.0     # v6: worst regime S <= 1.02; v5: S49 <= 1
    pen = 10.0 * (np.maximum(s49 - guard, 0) + np.maximum(t - 0.01, 0) + np.maximum(p - 0.01, 0))
    return s55 + pen


def training(plan, out):
    res = [r for r in read_results(out) if r.get("ok")]
    names = sorted(res[0]["regions"])
    X = np.array([to_unit(plan, r["x"]) for r in res])
    Y = np.array([[[r["regions"][n][0], r["regions"][n][1]] for n in names] for r in res])     # [m, n, 2]
    Rf = np.array([[res[0]["regions"][n][2], res[0]["regions"][n][3]] for n in names])
    return res, names, X, Y, Rf


def fit_gps(X, Y):
    from sklearn.gaussian_process import GaussianProcessRegressor
    from sklearn.gaussian_process.kernels import RBF, ConstantKernel, WhiteKernel
    d = X.shape[1]
    gps = []
    for j in range(Y.shape[1]):
        row = []
        for q in range(2):
            y = np.log(Y[:, j, q])
            k = ConstantKernel(1.0, (1e-3, 1e2)) * RBF(np.full(d, 0.5), (0.03, 30.0)) + WhiteKernel(1e-4, (1e-8, 1e-1))
            gp = GaussianProcessRegressor(k, normalize_y=True, n_restarts_optimizer=1, random_state=0).fit(X, y)
            row.append(gp)
        gps.append(row)
    return gps


def predict(gps, U):
    out = np.empty((len(U), len(gps), 2))
    for j, row in enumerate(gps):
        for q, gp in enumerate(row):
            out[:, j, q] = np.exp(gp.predict(U))
    return out


def t_names_of(plan):
    if plan.get("policy") == "v6":
        return json.loads((ROOT / "calibration/regimes_20261124/regimes_v2.json").read_text())["regimes"]
    t = []
    for part, spec in plan.get("extra_parts", {}).items():
        t += list(json.loads((ROOT / spec).read_text()))
    return set(t)


def fit(plan, out):
    res, names, X, Y, Rf = training(plan, out)
    tn = t_names_of(plan)
    gps = fit_gps(X, Y)
    # leave-one-out check of the emulated objective on up to 20 points
    from sklearn.base import clone
    m = len(X)
    idx = np.linspace(0, m - 1, min(m, 20)).astype(int)
    truth, pred = [], []
    for i in idx:
        keep = np.arange(m) != i
        g2 = []
        for j, row in enumerate(gps):
            g2.append([clone(gp).set_params(kernel=gp.kernel_, optimizer=None).fit(X[keep], np.log(Y[keep, j, q]))
                       for q, gp in enumerate(row)])
        pc = predict(g2, X[i:i + 1])
        truth.append(float(gate_terms(Y[i:i + 1], Rf, names, tn)[0][0]))
        pred.append(float(gate_terms(pc, Rf, names, tn)[0][0]))
    truth, pred = np.array(truth), np.array(pred)
    # sensitivity: mean inverse length scale of the S55-weighted terms across regions
    inv = np.zeros(X.shape[1])
    for row in gps:
        for gp in row:
            inv += 1.0 / np.asarray(gp.kernel_.k1.k2.length_scale)
    sens = dict(sorted(zip(plan["knobs"], (inv / inv.sum()).round(3).tolist()), key=lambda kv: -kv[1]))
    rep = dict(points=m, loo_rmse_S55=float(np.sqrt(np.mean((truth - pred) ** 2))),
               loo_corr=float(np.corrcoef(truth, pred)[0, 1]), loo=list(zip(truth.round(4).tolist(), pred.round(4).tolist())),
               sensitivity=sens)
    (out / "emulator.json").write_text(json.dumps(rep, indent=1) + "\n")
    print(json.dumps({k: rep[k] for k in ("points", "loo_rmse_S55", "loo_corr", "sensitivity")}, indent=1))
    return gps, names, Rf, tn


def propose(plan, out, k):
    gps, names, Rf, tn = fit(plan, out)
    from scipy.stats import qmc
    d = len(plan["knobs"])
    rng = np.random.default_rng(plan["seed"] + len(read_design(out)))
    U = qmc.Sobol(d, scramble=True, seed=int(rng.integers(1 << 30))).random(2 ** 15)
    # also local samples around the best evaluated points
    res, _, X, Y, _ = training(plan, out)
    s55, t, p, s49 = gate_terms(Y, Rf, names, tn)
    best = X[np.argsort(objective(plan, s55, t, p, s49))[:5]]
    loc = np.clip(np.repeat(best, 2000, 0) + rng.normal(0, 0.06, (5 * 2000, d)), 0, 1)
    U = np.vstack([U, loc])
    pred = np.vstack([predict(gps, U[i:i + 4096]) for i in range(0, len(U), 4096)])
    obj = objective(plan, *gate_terms(pred, Rf, names, tn))
    order = np.argsort(obj)
    pick = []
    for i in order:                                     # best first, at least 0.12 apart in the unit cube
        if all(np.linalg.norm(U[i] - U[j]) > 0.12 for j in pick):
            pick.append(i)
        if len(pick) == k:
            break
    pts = read_design(out)
    wave = max(p_["wave"] for p_ in pts) + 1
    new = [dict(name=f"w{wave}_{n:03d}", wave=wave, x=from_unit(plan, U[i]), predicted_objective=float(obj[i])) for n, i in enumerate(pick)]
    (out / "design.json").write_text(json.dumps(pts + new, indent=1) + "\n")
    for n_ in new:
        print(n_["name"], round(n_["predicted_objective"], 4))


def import_results(plan, out):
    """Absolute per-region errors do not depend on the reference: copy an earlier ensemble's evaluations and replace
    their reference columns with the plan reference's values (read from a run of that reference, e.g. its finalist)."""
    spec = plan["import_from"]
    if any(r["name"].startswith(spec["prefix"]) for r in read_results(out)):
        raise SystemExit("already imported")
    ref = region_values_at(ROOT / spec["reference_run"])
    base = base_params(plan)
    n = 0
    with (out / "results.jsonl").open("a") as f:
        for r in (json.loads(l) for l in (ROOT / spec["results"]).read_text().splitlines() if l.strip()):
            if not r.get("ok"):
                continue
            x = {k: r["x"].get(k, base[k]) for k in plan["knobs"]}
            regs = {k: v[:2] + ref[k] for k, v in r["regions"].items()}
            f.write(json.dumps(dict(name=spec["prefix"] + r["name"], wave=0, x=x, regions=regs, ok=True, imported=True)) + "\n")
            n += 1
    print(n, "imported")


def region_values_at(d):
    Rr, Cc = paired(d, R.REF_NAME if (d / f"{R.REF_NAME}_dev31").exists() else "r51", None, list(R.PARTS))
    return {n: [Cc[n]["temperature"]["monthly_mae_C"], Cc[n]["rain"]["loss"]] for n in Rr}


def report(plan, out):
    res, names, X, Y, Rf = training(plan, out)
    tn = t_names_of(plan)
    s55, t, p, s49 = gate_terms(Y, Rf, names, tn)
    obj = objective(plan, s55, t, p, s49)
    for i in np.argsort(obj)[:15]:
        print(f"{res[i]['name']:10s} obj {obj[i]:.4f}  S55 {s55[i]:.4f} T {t[i]:+.3f} P {p[i]:+.3f} S49 {s49[i]:.4f}")
    print(len(res), "evaluated;", sum(1 for r in read_results(out) if not r.get("ok")), "failed")


def main():
    cmd, plan_path = sys.argv[1], sys.argv[2]
    plan, out = load_plan(plan_path)
    if cmd == "design":
        design(plan, out)
    elif cmd == "run":
        run(plan, out)
    elif cmd == "fit":
        fit(plan, out)
    elif cmd == "propose":
        propose(plan, out, int(sys.argv[3]))
    elif cmd == "import":
        import_results(plan, out)
    elif cmd == "report":
        report(plan, out)
    else:
        raise SystemExit(__doc__)


if __name__ == "__main__":
    main()
