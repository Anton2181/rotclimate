"""How well does a simulated climate reproduce the painted target zones?

Each painted zone is turned into a *fuzzy rule* on physically meaningful
climate statistics (coldest / warmest month, Koppen aridity ratio, summer
drought...).  A cell's membership is in [0, 1]; a zone's score is the mean
membership over its land cells; the total is the mean over zones (so small
zones count as much as big ones).
"""
from __future__ import annotations

import numpy as np

from .geography import TARGET_CLASSES, TARGET_KEYS
from .koppen import climate_indices, monthly_stats


def sig(x):
    return 1.0 / (1.0 + np.exp(-np.clip(x, -30, 30)))


# Human-readable versions of the rules, used in the docs and plots.
RULES = {
    "cold_wet": "coldest month < ~1 C  AND  humid (precip >= 1.8x Koppen dry threshold)",
    "cold_dry": "coldest month < ~1 C  AND  semi-arid/arid (precip < 1.3x Koppen threshold)",
    "warm_wet": "coldest month > ~1 C, warmest > ~20 C  AND  humid (>= 1.8x)  AND  no summer drought",
    "med": "warmest month > ~22 C, coldest > ~0 C, dry summer + wet winter (Koppen 's'), not desert",
    "swamp": "warmest month > ~25 C, coldest > ~4 C  AND  very wet (>= 2.3x threshold)",
    "tree": "coldest month > ~2 C  AND  humid enough for forest (>= 1.6x threshold)",
    "hot_dry": "mean annual T > ~17 C  AND  arid/semi-arid (< 1.0x threshold)",
}


def memberships(ix: dict) -> dict:
    Tc, Th, MAT, ar = ix["Tcold"], ix["Thot"], ix["MAT"], ix["aridity"]
    lar = np.log(np.maximum(ar, 1e-3))
    humid = lambda a: sig((lar - np.log(a)) / 0.18)
    arid = lambda a: sig((np.log(a) - lar) / 0.18)
    summer_dry = sig((40 - ix["Psdry"]) / 8) * sig((ix["Pwwet"] / 3 - ix["Psdry"]) / 8)
    cold = sig((1.0 - Tc) / 2.0)
    return {
        "cold_wet": cold * humid(1.8),
        "cold_dry": cold * arid(1.3),
        "warm_wet": sig((Tc - 1.0) / 2.0) * sig((Th - 20) / 1.5) * humid(1.8) * (1 - summer_dry),
        "med": sig((Th - 22) / 1.2) * sig((Tc - 0.0) / 2.0) * summer_dry * humid(1.0),
        "swamp": sig((Th - 25) / 1.2) * sig((Tc - 4) / 2.0) * humid(2.3),
        "tree": sig((Tc - 2) / 2.0) * humid(1.6),
        "hot_dry": sig((MAT - 17) / 1.2) * arid(1.0),
    }


def evaluate(result, land_only=True):
    g = result.grid
    p = result.params
    st = monthly_stats(result.T, result.P, result.days, p.year_days,
                       summer_solstice=p.winter_solstice_day + p.year_days / 2)
    ix = climate_indices(st["Tm"], st["Pm"], st["summer"])
    mem = memberships(ix)
    valid = g.inmap & (g.land if land_only else True)
    per = {}
    for cid, key, label, _ in TARGET_CLASSES:
        m = valid & (g.target == cid)
        per[key] = float(mem[key][m].mean()) if m.any() else np.nan
    total = float(np.nanmean(list(per.values())))
    # hard confusion: best-matching zone per painted cell
    keys = [c[1] for c in TARGET_CLASSES]
    stack = np.stack([mem[k] for k in keys])
    pred = stack.argmax(0) + 1
    pred[stack.max(0) < 0.3] = 0
    conf = np.zeros((7, 8), int)
    for cid in range(1, 8):
        m = valid & (g.target == cid)
        conf[cid - 1] = np.bincount(pred[m], minlength=8)
    painted = valid & (g.target > 0)
    acc = float((pred[painted] == g.target[painted]).mean())
    return dict(total=total, per_class=per, accuracy=acc, confusion=conf,
                indices=ix, memberships=mem, monthly=st, predicted=pred)


def format_report(ev) -> str:
    lines = [f"score {ev['total']:.3f}   hard accuracy {ev['accuracy']:.3f}"]
    for k, v in ev["per_class"].items():
        lines.append(f"  {k:9s} {v:.3f}")
    return "\n".join(lines)


__all__ = ["evaluate", "memberships", "format_report", "RULES", "TARGET_KEYS"]
