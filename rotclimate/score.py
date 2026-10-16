"""How well does a simulated climate reproduce the painted target zones?

Each painted zone is turned into a *fuzzy rule* on physically meaningful
climate statistics (coldest / warmest month, Koppen aridity ratio, summer
drought...).  A cell's membership is in [0, 1]; a zone's score is the mean
membership over its land cells; the total is the mean over zones (so small
zones count as much as big ones).
"""
from __future__ import annotations

import numpy as np
from functools import reduce

from .geography import TARGET_CLASSES, TARGET_KEYS
from .koppen import climate_indices, monthly_stats


def sig(x):
    return 1.0 / (1.0 + np.exp(-np.clip(x, -30, 30)))


# Human-readable versions of the rules, used in the docs and plots.
RULES = {
    "cold_wet": "coldest month < ~1 C  AND  humid (precip >= 1.8x Koppen dry threshold)",
    "cold_dry": "mean annual T < ~18 C AND arid/semi-arid (precip < Koppen dry threshold)",
    "warm_wet": "coldest month > ~1 C, warmest > ~20 C  AND  humid (>= 1.8x)  AND  no summer drought",
    "med": "warmest month > ~10 C, coldest > ~0 C, dry summer + wet winter (Koppen Cs), not desert",
    "swamp": "warmest month > ~25 C, coldest > ~4 C, annual mean > ~21 C AND very wet (>= 2.0x threshold) AND flat (slope < ~1.5 per mille)",
    "tree": "coldest month > ~2 C  AND  humid enough for forest (>= 1.6x threshold)",
    "hot_dry": "mean annual T > ~18 C  AND  arid/semi-arid (< 1.0x threshold)",
}


# Swamps are wet climates on flat ground, where water cannot drain away. Your
# painted swamp is ~5x flatter than the equally rainy warm-wet coast and the
# forested hills (median slope 0.7 vs 3.4 per mille), so flatness is what sets
# it apart. Slope is measured on a fixed ~15 km scale (grid independent).
SWAMP_HUMID = 2.0                # flat ground waterlogs with less rain than slopes
# "Hot and wet, swampy" vs "Warm and wet": the painted swamp is set apart
# from look-alike wet lowland by heat (mean annual temperature, AUC 0.96),
# not by drainage or wetness; ~21 C keeps it in Earth's range (Miami,
# Tampa, Guangzhou inside; Houston on the edge; New Orleans just below)
SWAMP_MAT = 21.0
                                 # (Everglades ~1,400 mm, Pantanal ~1,200 mm)
FLAT_SCALE_KM = 15.0


def terrain_slope(g) -> np.ndarray:
    """Ground slope (per mille) on the model grid, smoothed over ~15 km."""
    from scipy import ndimage as ndi

    e = ndi.gaussian_filter(g.elev, FLAT_SCALE_KM / g.cell_km)
    gy, gx = np.gradient(e, g.cell_km * 1000.0)
    return np.hypot(gy, gx) * 1000.0


def flatness(slope):
    """~1 on plains (slope under ~1 per mille), ~0 on hills (over ~3)."""
    return sig((np.log(1.5) - np.log(np.maximum(slope, 1e-3))) / 0.35)


def membership_factors(ix: dict, floodplain=None, slope=None) -> dict:
    """Named factors in the existing rules, ordered as in the original products."""
    Tc, Th, MAT, ar = ix["Tcold"], ix["Thot"], ix["MAT"], ix["aridity"]
    lar = np.log(np.maximum(ar, 1e-3))
    humid = lambda a: sig((lar - np.log(a)) / 0.18)
    arid = lambda a: sig((np.log(a) - lar) / 0.18)
    summer_dry = sig((40 - ix["Psdry"]) / 8) * sig((ix["Pwwet"] / 3 - ix["Psdry"]) / 8)
    return {
        "cold_wet": dict(cold_winter=sig((1.0 - Tc) / 2.0), humidity=humid(1.8)),
        "cold_dry": dict(cool_year=sig((18.0 - MAT) / 1.2), aridity=arid(1.0)),
        "warm_wet": dict(mild_winter=sig((Tc - 1.0) / 2.0), warm_summer=sig((Th - 20) / 1.5),
                         humidity=humid(1.8), summer_moisture=1 - summer_dry),
        "med": dict(warm_summer=sig((Th - 10) / 1.2), mild_winter=sig(Tc / 2.0),
                    summer_drought=summer_dry, nonarid=humid(1.0)),
        "swamp": dict(hot_summer=sig((Th - 25) / 1.2), mild_winter=sig((Tc - 4) / 2.0),
                      humidity=humid(SWAMP_HUMID) if floodplain is None else
                      np.maximum(humid(SWAMP_HUMID), floodplain * humid(1.2)),
                      flat_ground=np.ones_like(Tc, dtype=float) if slope is None else flatness(slope),
                      hot_year=sig((MAT - SWAMP_MAT) / 0.6)),
        "tree": dict(mild_winter=sig((Tc - 2) / 2.0), humidity=humid(1.6)),
        "hot_dry": dict(hot_year=sig((MAT - 18.0) / 1.2), aridity=arid(1.0)),
    }


def memberships(ix: dict, floodplain=None, slope=None) -> dict:
    return {key: reduce(np.multiply, factors.values())
            for key, factors in membership_factors(ix, floodplain, slope).items()}


# The Koppen classes each painted zone may be labelled on: the soft rules give
# partial credit across Koppen's lines (fair for scoring), but a map label must
# never contradict the Koppen map - e.g. dry-summer continental Dsa is neither
# "cold and dry" (not a dry climate) nor "Mediterranean" (cold winters).
ZONE_KOPPEN = {
    "cold_wet": lambda c: c[0] in "DE",
    "cold_dry": lambda c: c in ("BSk", "BWk"),
    "warm_wet": lambda c: c[0] == "A" or (c[0] == "C" and c[1] != "s"),
    "med": lambda c: c.startswith("Cs"),
    "swamp": lambda c: c[0] in "CA",
    "tree": lambda c: c[0] in "CA",
    "hot_dry": lambda c: c in ("BSh", "BWh"),
}


def best_zone(mem: dict, threshold=0.3, weights=None, koppen=None) -> np.ndarray:
    """Single best-fitting painted zone per cell (0 = none above threshold).
    The swamp rule is the narrowest - every swamp also meets the warm-wet
    and forest rules - so where it is met (>= 0.5) the cell is a swamp.
    With `koppen` (class indices from koppen.classify) a zone is only
    labelled on its own Koppen classes (ZONE_KOPPEN)."""
    keys = [c[1] for c in TARGET_CLASSES]
    w = np.ones(len(keys)) if weights is None else np.array([weights.get(k, 1.0) for k in keys])
    stack = np.stack([mem[k] for k in keys]) * w.reshape((-1,) + (1,) * np.ndim(mem[keys[0]]))
    allowed = np.ones(stack.shape, bool)
    if koppen is not None:
        from .koppen import CODES

        for i, k in enumerate(keys):
            ok = np.array([ZONE_KOPPEN[k](c) for c in CODES] + [False])     # index -1 = unclassified
            allowed[i] = ok[np.asarray(koppen)]
        stack = np.where(allowed, stack, 0.0)
    z = stack.argmax(0) + 1
    z[stack.max(0) < threshold] = 0
    z[(mem["swamp"] >= 0.5) & allowed[keys.index("swamp")]] = keys.index("swamp") + 1
    return z


def display_zones(mem, land, threshold=0.3, ix=None, elev=None, koppen=None):
    """Atlas labels, including mountain/grassland/transitional display types."""
    z = best_zone(mem, threshold=threshold, weights={"tree": 0.75}, koppen=koppen).astype(np.int8)
    if ix is not None and elev is not None:
        z[(elev > 2200.0) | (ix["Thot"] < 15.0)] = 8
        left = z == 0
        z[left & (ix["aridity"] < 1.8)] = 9
        z[left & (ix["aridity"] >= 1.8)] = 10
    z[~land] = -1
    return z


# A zone's rule may also hold where a narrower zone is painted: every swampy
# place is also warm-and-wet and forested, and warm-and-wet places forested.
BROADER = {"tree": ("swamp", "warm_wet"), "warm_wet": ("swamp",)}


def precision_f1(mem, target, valid, coverage, elev=None, high=1500.0):
    """Per zone: precision = the share of the rule's membership (summed over
    painted land) that falls inside its own painted zone, or inside a
    narrower zone it contains; F1 = harmonic mean with coverage (the zone
    score). Coverage alone never penalises a rule spilling into areas painted
    as something else. Ground above `high` m is not counted as spill: ridges
    inside a broadly painted zone are rightly colder and wetter."""
    prec, f1 = {}, {}
    for cid, key, _, _ in TARGET_CLASSES:
        ok_ids = [cid] + [c for c, k, _, _ in TARGET_CLASSES if k in BROADER.get(key, ())]
        elsewhere = valid & (target > 0) & ~np.isin(target, ok_ids)
        if elev is not None:
            elsewhere &= elev <= high
        own = valid & (target == cid)
        a = float(mem[key][own].sum())
        b = float(mem[key][elsewhere].sum())
        prec[key] = a / (a + b) if a + b > 0 else 0.0
        s = coverage[key]
        f1[key] = 2 * s * prec[key] / (s + prec[key]) if s + prec[key] > 0 else 0.0
    return prec, f1


def evaluate(result, land_only=True):
    g = result.grid
    p = result.params
    st = monthly_stats(result.T, result.P, result.days, p.year_days,
                       summer_solstice=p.winter_solstice_day + p.year_days / 2)
    ix = climate_indices(st["Tm"], st["Pm"], st["summer"])
    from .hydrology import analyse

    hyd = analyse(result)
    # (a river-floodplain route to "swampy" was tested and rejected: in the
    # model the painted swamp coast is no more river-fed than other lowland,
    # so it would only loosen the rule - see docs/ITERATIONS.md)
    mem = memberships(ix, slope=terrain_slope(g))
    valid = g.inmap & (g.land if land_only else True)
    per = {}
    for cid, key, label, _ in TARGET_CLASSES:
        m = valid & (g.target == cid)
        per[key] = float(mem[key][m].mean()) if m.any() else np.nan
    total = float(np.nanmean(list(per.values())))
    prec, f1 = precision_f1(mem, g.target, valid, per, elev=g.elev)
    # hard confusion: best-matching zone per painted cell
    from .koppen import classify
    kop = classify(st["Tm"], st["Pm"], st["summer"])
    pred = best_zone(mem, koppen=kop)
    conf = np.zeros((7, 8), int)
    for cid in range(1, 8):
        m = valid & (g.target == cid)
        conf[cid - 1] = np.bincount(pred[m], minlength=8)
    painted = valid & (g.target > 0)
    acc = float((pred[painted] == g.target[painted]).mean())
    recall = {key: float(conf[cid - 1, cid] / conf[cid - 1].sum())
              if conf[cid - 1].sum() else np.nan for cid, key, _, _ in TARGET_CLASSES}
    displayed = display_zones(mem, g.land, ix=ix, elev=g.elev, koppen=kop)
    policy_audit = dict(
        grid="model_grid",
        strict_accuracy=acc,
        display_accuracy=float((displayed[painted] == g.target[painted]).mean()),
        note="Same model fields under two label policies; full-resolution map interpolation can differ.",
        per_zone={key: dict(
            strict_recall=float((pred[valid & (g.target == cid)] == cid).mean()),
            display_recall=float((displayed[valid & (g.target == cid)] == cid).mean()))
            for cid, key, _, _ in TARGET_CLASSES if (valid & (g.target == cid)).any()})
    MAP = ix["MAP"][valid]
    realism = dict(map_median=float(np.median(MAP)), map_p95=float(np.percentile(MAP, 95)),
                   share_over_3500=float((MAP > 3500).mean()), **summer_heat(st["Tm"], st["Pm"], g, valid))
    return dict(total=total, per_class=per, precision=prec, f1=f1, recall=recall,
                accuracy=acc, confusion=conf,
                indices=ix, memberships=mem, monthly=st, predicted=pred, label_policy_audit=policy_audit,
                rivers={**river_check(result, ix), **river_network_check(g, hyd)},
                realism=realism, hydrology=hyd)


def river_network_check(g, hyd, q_min=20.0):
    """Do the simulated big rivers (discharge > q_min m3/s) run where rivers
    are drawn?  recall = share of drawn-river cells within one cell of a
    simulated river; precision = the converse."""
    from scipy import ndimage as ndi

    land = g.inmap & g.land
    drawn = (g.rivers > 0.002) & land
    sim = (hyd["discharge"] > q_min) & land
    if not drawn.any() or not sim.any():
        return dict(net_recall=np.nan, net_precision=np.nan)
    k = np.ones((3, 3), bool)
    recall = float((drawn & ndi.binary_dilation(sim, k)).sum() / drawn.sum())
    precision = float((sim & ndi.binary_dilation(drawn, k)).sum() / sim.sum())
    return dict(net_recall=recall, net_precision=precision)


# Earth (WorldClim 2.1 lowland below 500 m, 20-50 deg, area-weighted): where
# the warmest month brings >= 80 mm of rain it passes 30 C on only 2.8% of
# the land (>= 120 mm: 0.4%) - wet ground and cloud cap humid summers
WET_SUMMER_MM = 80.0
WET_SUMMER_HOT_C = 30.0
EARTH_WET_SUMMER_HOT = 0.028


def summer_heat(Tm, Pm, g, valid) -> dict:
    """Share of the map's lowland whose warmest month is wet (>= 80 mm) and
    hotter than 30 C; Earth: 2.8%."""
    m = valid & (g.elev < 500)
    T, P = Tm[:, m], Pm[:, m]
    if T.shape[1] == 0:
        return dict(wet_summer_share=0.0, wet_summer_hot=0.0)
    iw = T.argmax(0)
    Pw = P[iw, np.arange(T.shape[1])]
    wet = Pw >= WET_SUMMER_MM
    hot = wet & (T.max(0) > WET_SUMMER_HOT_C)
    return dict(wet_summer_share=float(wet.mean()),
                wet_summer_hot=float(hot.sum() / max(wet.sum(), 1)))


def objective(ev, mode="mean"):
    """Number the calibrator maximises.

    'mean'      plain mean of the zone scores (rounds 1-2)
    'balanced'  half mean, half soft-minimum of the zone scores (so no zone
                can be sacrificed), minus penalties for implausible rainfall
                (land median above 1300 mm/yr, 95th percentile above 3500).
    'f1'        as 'balanced' but on each zone's F1 (coverage and precision),
                so a zone's rule also has to stay out of other painted zones.
    'f1r'       as 'f1', and humid summers must be no hotter than Earth's:
                penalised when more than twice Earth's share (2.8%) of the
                wet-summer lowland passes 30 C in its warmest month.
    'zonefit'   equal weight to balanced fuzzy F1 and balanced per-zone strict
                recall, with the same realism penalties as f1r. Each painted
                zone has equal weight regardless of area; old objectives stay.
    """
    if mode == "mean":
        return ev["total"]
    vals = ev["f1"] if mode in ("f1", "f1r", "zonefit") else ev["per_class"]
    sc = np.array([v for v in vals.values() if np.isfinite(v)])
    tau = 0.08
    softmin = -tau * np.log(np.mean(np.exp(-sc / tau)))
    fit = 0.5 * sc.mean() + 0.5 * softmin
    if mode == "zonefit":
        rec = np.array([v for v in ev["recall"].values() if np.isfinite(v)])
        if not rec.size:
            raise ValueError("zonefit requires per-zone strict recall")
        rec_softmin = -tau * np.log(np.mean(np.exp(-rec / tau)))
        fit = 0.5 * fit + 0.5 * (0.5 * rec.mean() + 0.5 * rec_softmin)
    r = ev["realism"]
    pen = (np.clip((r["map_median"] - 1300) / 800, 0, 1.5)
           + np.clip((r["map_p95"] - 3500) / 2500, 0, 1.5))
    if mode in ("f1r", "zonefit"):
        pen = pen + np.clip((r.get("wet_summer_hot", 0.0) - 2 * EARTH_WET_SUMMER_HOT) / 0.25, 0, 1.5)
    return float(fit - 0.2 * pen)


def river_check(result, ix):
    """Independent validation (never optimised): is the drawn river network
    densest where the model makes surplus water?

    Rivers integrate water from upstream and the drawing style leaves
    mountain crests bare, so instead of cell-by-cell matching this compares
    ~100 km blocks of lowland: river-line density vs. the model's runoff
    (precipitation minus evaporation, smoothed ~150 km).  Reports the
    Spearman rank correlation (0 = no skill, 1 = perfect ordering).
    """
    from scipy import ndimage as ndi

    g = result.grid
    land = g.inmap & g.land
    T = result.T
    pet_day = np.clip(0.0023 * 17.8 * (T + 17.8) * 1.9, 0.1, None)      # Hargreaves-like
    runoff = (result.P - np.minimum(result.P, 0.75 * pet_day)).sum(0) * \
        result.params.year_days / result.nt
    sig = 75.0 / g.cell_km
    lw = ndi.gaussian_filter(land.astype(float), sig)
    ro = ndi.gaussian_filter(np.where(land, runoff, 0.0), sig) / np.maximum(lw, 1e-6)
    b = max(1, int(round(100.0 / g.cell_km)))
    ny, nx = (g.ny // b) * b, (g.nx // b) * b

    def blk(a):
        return a[:ny, :nx].reshape(ny // b, b, nx // b, b).mean(axis=(1, 3))

    lowland = (g.elev < np.percentile(g.elev[land], 85))
    keep = blk((land & lowland).astype(float)) > 0.7
    dens = blk(np.where(land, g.rivers, 0.0))[keep]
    rr = blk(ro)[keep]
    if dens.size < 10:
        return dict(spearman=np.nan, blocks=int(dens.size))
    ra = np.argsort(np.argsort(dens)).astype(float)
    rb = np.argsort(np.argsort(rr)).astype(float)
    rho = np.corrcoef(ra, rb)[0, 1]
    return dict(spearman=float(rho), blocks=int(dens.size),
                runoff_median=float(np.median(runoff[land])))


def format_report(ev) -> str:
    lines = [f"score {ev['total']:.3f}   hard accuracy {ev['accuracy']:.3f}"]
    for k, v in ev["per_class"].items():
        lines.append(f"  {k:9s} {v:.3f}")
    return "\n".join(lines)


__all__ = ["evaluate", "memberships", "format_report", "RULES", "TARGET_KEYS"]
