"""Integrate the qualified soil-fertility state into the shared grain -> residents -> reach chain.

Declared integration (reports/FERTILITY_INTEGRATION_20261106.md):
  * AD 200 non-fertilizer N input 27.5 kg N/ha/yr in model units: the middle of the
    20-35 band (the fitted 52.4 scaled by the literature pre-industrial/1850-1925 ratio
    0.4-0.65), chosen by the user.
  * The existing chain's grain = A0 x arable x 0.6 fields x 0.68 sown share (0.68 = the
    three-field rotation, 2 crops in 3 years). Per cell, the fertility factor
        F = Y_land(regime, I = 27.5) / (0.68 x A0)
    multiplies that grain: the regime's absolute equilibrium grain per field hectare
    (min(kappa x A0, N-limited), as validated) against the previous chain's.
  * Regimes on the three-field rotation: 'bare' (fallow third, no transfer), 'legume'
    (clover third), and 'transfer' (bare third + m t FYM-equivalent/ha before each crop:
    the nutrients carried from pasture, stalls and households). m is calibrated so the
    Han North China Plain keeps its AD 2 census fit, replacing the old 0.68 fit like for like;
    the other census regions are then compared (development, already seen in A2).
  * Residues scale with the stand below 0.5 t grain (harvest/soil_fertility.STAND_T; rechecked on
    spent data with the frozen round-2 parameters: scripts/recheck_stand_residues.py).
  * Paddy rice and date palms keep F = 1 (paddy N supply is not this model). Climate:
    Hargreaves PET x 0.625 (Rothamsted's open-pan ratio, amendment_evaporation.json);
    Rothamsted soil everywhere (no soil map).

    python -I scripts/fertility_integration.py earth
    python -I scripts/fertility_integration.py maps
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "scripts")]
from atlas_set import active  # noqa: E402  (free and Whittaker fits retired, 8 Nov 2026)
import numpy as np  # noqa: E402

from harvest.fertility_regimes import SPRING_CURVE, WHEAT_CURVE, equilibrium_yield  # noqa: E402

OUT = ROOT / "output/fertility_integration_20261106"
SEL = ROOT / "output/soil_fertility_round2_20261106/selection.json"
I_AD200, I_REF, SOWN = 27.5, None, 0.68
PET_FACTOR = 448.0 / 717.0
SEASON = dict(wheat=(9, WHEAT_CURVE), barley=(5, SPRING_CURVE), millet=(4, SPRING_CURVE))
REGIMES = dict(bare=["crop", "crop", "fallow"], legume=["crop", "crop", "clover"], transfer=["crop", "crop", "fallow"])
START = dict(dpm=0.1, rpm=4.4, bio=0.55, hum=21.4, dpm_n=2.5, rpm_n=110.0)


def lowest_bit(bits):
    """First (lowest) tied harvest boundary of a 12-bin mask; 0 where none."""
    bits = np.asarray(bits).astype(np.int64)
    out = np.zeros(bits.shape, int)
    found = np.zeros(bits.shape, bool)
    for i in range(12):
        hit = ((bits >> i) & 1).astype(bool) & ~found
        out[hit] = i; found |= hit
    return out


def params():
    sel = json.loads(SEL.read_text())
    p = sel["parameters"]
    from harvest.soil_fertility import wet_deposition
    return dict(uptake_rate=p["uptake_rate"], kappa=p["kappa"]), p["input_n"] + wet_deposition(1900)


def yields(T, P, PET, hb, A0, crop, regime, manure=0.0, input_n=I_AD200, years=300):
    kw, _ = params()
    out_c = np.zeros(T.shape[1]); out_l = np.zeros(T.shape[1])
    for name, (L, curve) in SEASON.items():
        sel = crop == name
        if not sel.any():
            continue
        r = equilibrium_yield(T[:, sel], P[:, sel], PET[:, sel] * PET_FACTOR, hb[sel], A0[sel], regime=regime, manure_t=manure,
                              input_n=input_n, season_bins=L, curve=curve, years=years, report_years=30, start=START,
                              stand_residues=True, **kw)
        out_c[sel] = r["per_cropped_ha"]; out_l[sel] = r["per_rotation_ha"]
    return out_c, out_l


def factor(T, P, PET, hb, A0, crop, regime_name, manure=0.0, ref=None):
    """F = Y_land(regime, I = 27.5) / (0.68 x A0): the regime's absolute equilibrium grain per
    field hectare against the previous chain's A0 x sown share. (A first pass divided by the
    model's own continuous-unmanured reference instead; that ratio explodes where the
    N-limited reference approaches zero, so it was replaced before publication.) The
    reference is still computed and stored as a diagnostic."""
    _, i_ref = params()
    if ref is None:
        ref, _ = yields(T, P, PET, hb, A0, crop, ["crop"], 0.0, i_ref)
    _, land = yields(T, P, PET, hb, A0, crop, REGIMES[regime_name], manure, I_AD200)
    F = np.divide(land, SOWN * A0, out=np.ones_like(land), where=A0 > 1e-6)
    return F, ref


# --- Earth census anchor -----------------------------------------------------------------------

def earth():
    from matplotlib.path import Path as Poly
    import land_people_earth as E
    from harvest.crop_sequences import crop_windows
    from harvest.work_maps import tied_harvest_boundaries
    from land_people import CROPS, bucket, hargreaves, sunlight_top
    OUT.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    full = dict(np.load(ROOT / "output/land_people/earth/earth.npz"))
    land, lat, lon = full["land"], full["lat"], full["lon"]
    names = [str(x) for x in full["crops"]]
    shape = land.shape
    LAT = np.broadcast_to(lat[:, None], shape); LON = np.broadcast_to(lon[None, :], shape)
    pts = np.stack([LON.ravel(), LAT.ravel()], 1)
    region_of = np.full(shape, -1, int)
    regions = list(E.REGIONS)
    for i, name in enumerate(regions):
        inside = Poly(E.REGIONS[name]["poly"]).contains_points(pts).reshape(shape) & land
        region_of[inside & (region_of < 0)] = i
    cells = np.flatnonzero((region_of.ravel() >= 0) & (np.nan_to_num(full["capacity"]).ravel() > 0))
    rs, cs = E.window_slices()
    print("cells", len(cells), flush=True)

    def monthly(var):
        return np.stack([E.wc(var, m)[rs, cs].ravel()[cells] for m in range(1, 13)])
    T = monthly("tavg"); P = monthly("prec"); D = monthly("tmax") - monthly("tmin")
    print(f"climate read {time.time() - t0:.0f}s", flush=True)
    latc = LAT.ravel()[cells]
    PET = hargreaves(T, D, sunlight_top(latc, E.TILT, E.WS_DAY))
    soil = bucket(P, PET)
    irr = full["irr"].ravel()[cells]
    main = np.nan_to_num(full["main_crop"].ravel()[cells], nan=-1).astype(int)
    crop = np.array([names[m] if m >= 0 else "none" for m in main])
    hb = np.zeros(len(cells), int); A0 = np.zeros(len(cells))
    for name in ("wheat", "barley", "millet"):
        sel = crop == name
        if not sel.any():
            continue
        cat = crop_windows(T[:, sel], P[:, sel], PET[:, sel], soil[:, sel], irr[sel], crops={name: CROPS[name]})
        best, bits = tied_harvest_boundaries(cat)
        low = lowest_bit(bits)
        hb[sel] = low
        c = CROPS[name]
        A0[sel] = np.nan_to_num(full["kcal_" + name].ravel()[cells][sel]) / (1000 * c["edible"] * c["kcal"] * (1 - c["seed"]))
    model = np.isin(crop, list(SEASON)) & (A0 > 0)
    print(f"windows {time.time() - t0:.0f}s; modelled cells {model.sum()} of {len(cells)} (rice/dates/none keep F=1)", flush=True)
    cap = np.nan_to_num(full["capacity"]).ravel()[cells] * (E.KM_DEG / E.RES) ** 2 * np.cos(np.radians(latc))
    km2 = (E.KM_DEG / E.RES) ** 2 * np.cos(np.radians(latc))
    reg = region_of.ravel()[cells]
    Tm, Pm, Em, hbm, A0m, cm = T[:, model], P[:, model], PET[:, model], hb[model], A0[model], crop[model]
    F_bare, ref = factor(Tm, Pm, Em, hbm, A0m, cm, "bare")
    F_leg, _ = factor(Tm, Pm, Em, hbm, A0m, cm, "legume", ref=ref)
    print(f"bare/legume factors {time.time() - t0:.0f}s", flush=True)
    ncp = regions.index("North China Plain (Han Yan, Yu, Ji, Qing, Xu)")

    def full_F(Fm):
        F = np.ones(len(cells)); F[model] = Fm
        return F

    def region_caps(Fm):
        F = full_F(Fm)
        return np.array([float((cap * F)[reg == i].sum()) for i in range(len(regions))])
    base_caps = region_caps(np.ones(model.sum()))

    def ncp_ratio(m):
        Fm, _ = factor(Tm, Pm, Em, hbm, A0m, cm, "transfer", m, ref=ref)
        return region_caps(Fm)[ncp] / base_caps[ncp], Fm
    lo, hi = 0.0, 30.0
    for _ in range(18):
        mid = 0.5 * (lo + hi)
        r, _ = ncp_ratio(mid)
        lo, hi = (mid, hi) if r < 1.0 else (lo, mid)
    m_star = 0.5 * (lo + hi)
    r_star, F_tr = ncp_ratio(m_star)
    print(f"calibrated transfer m* = {m_star:.2f} t/ha (NCP capacity ratio {r_star:.4f}) {time.time() - t0:.0f}s", flush=True)
    rows = {}
    caps = {k: region_caps(v) for k, v in (("bare", F_bare), ("legume", F_leg), ("transfer", F_tr))}
    for i, name in enumerate(regions):
        r = E.REGIONS[name]
        area = float(km2[reg == i].sum())
        lo_h, hi_h = r["people"] if "people" in r else (d * area / 1e6 for d in r["density"])
        rows[name] = dict(area_km2=round(area), fitted=bool(r.get("fitted", False)), historical_m=[lo_h, hi_h],
                          capacity_m={"existing": base_caps[i] / 1e6, **{k: v[i] / 1e6 for k, v in caps.items()}},
                          ratio={"existing": [lo_h * 1e6 / base_caps[i], hi_h * 1e6 / base_caps[i]],
                                 **{k: [lo_h * 1e6 / v[i], hi_h * 1e6 / v[i]] for k, v in caps.items()}},
                          mean_F={k: float(np.average(full_F(f)[reg == i], weights=cap[reg == i] + 1e-12))
                                  for k, f in (("bare", F_bare), ("legume", F_leg), ("transfer", F_tr))})
    res = dict(I_ad200=I_AD200, I_reference=params()[1], sown_share=SOWN, pet_factor=PET_FACTOR, transfer_t_ha=m_star,
               modelled_cells=int(model.sum()), cells=len(cells), regions=rows)
    (OUT / "earth_census.json").write_text(json.dumps(res, indent=1, ensure_ascii=False))
    np.savez_compressed(OUT / "earth_factors.npz", cells=cells, shape=np.array(shape), model=model, F_bare=F_bare, F_legume=F_leg,
                        F_transfer=F_tr, ref=ref, crop=crop, region=reg)
    for name, v in rows.items():
        print(f"{name[:40]:40s} " + "  ".join(f"{k} {v['ratio'][k][0]:.2f}-{v['ratio'][k][1]:.2f}" for k in v["ratio"]) +
              "   F " + " ".join(f"{k} {f:.2f}" for k, f in v["mean_F"].items()))
    return res


# --- map atlases ----------------------------------------------------------------------------------

def atlas_modes():
    for name in active(("free_fit", "earth_fit", "whittaker_fit")):
        data = ROOT / "atlases" / name / "data"
        meta = json.loads((data / "atlas.json").read_text())
        yield name, "raw", data, data, meta
        if meta.get("corrected_climate"):
            import copy
            m = copy.deepcopy(meta)
            for k in ("arrays", "lapse12", "cell_px", "harvest"):
                m[k] = meta["corrected_climate"][k]
            yield name, "corrected", data, data / "corrected", m


def map_factors(name, mode, data, folder, meta, m_star):
    from harvest.export import climate_arrays, surface_months
    from population.export import decode_harvest
    from land_people import CROPS, hargreaves, sunlight_top
    t0 = time.time()
    hm, hf = decode_harvest(folder)
    with np.load(folder / "farm_work_grid.npz") as g:
        cereal = g["cereal"]; bits = g["harvest_boundaries"]
    arrays = climate_arrays(folder, meta)
    t, p, dtr, latitude = surface_months(meta, arrays)
    cells = np.flatnonzero(cereal.ravel() > 0)
    T, P, D = (a.reshape(12, -1)[:, cells] for a in (t, p, dtr))
    PET = hargreaves(T, D, sunlight_top(latitude.ravel()[cells], meta["world"]["tilt"], 0))
    code = cereal.ravel()[cells]
    crop = np.where(code == 1, "wheat", "barley")
    A0 = np.zeros(len(cells))
    for cname, cc in (("wheat", 1), ("barley", 2)):
        c = CROPS[cname]; sel = code == cc
        A0[sel] = np.nan_to_num(hf["kcal_" + cname].ravel()[cells][sel]) / (1000 * c["edible"] * c["kcal"] * (1 - c["seed"]))
    hb = lowest_bit(bits.ravel()[cells])
    out = {}
    ref = np.full(len(cells), np.nan)
    runs = [("bare", ("bare", 0.0)), ("legume", ("legume", 0.0))]
    if m_star >= 0.05:                     # a transfer case only when the census anchor needs one
        runs.insert(0, ("transfer", ("transfer", m_star)))
    for k, (regime, man) in runs:
        Fk = np.ones(len(cells))
        for s0 in range(0, len(cells), 40000):
            sl = slice(s0, min(s0 + 40000, len(cells)))
            r_ref = None if np.isnan(ref[sl]).any() else ref[sl]
            f_, rr = factor(T[:, sl], P[:, sl], PET[:, sl], hb[sl], A0[sl], crop[sl], regime, man, ref=r_ref)
            Fk[sl] = f_; ref[sl] = rr
        grid = np.full(cereal.shape, np.nan, np.float32); grid.ravel()[cells] = Fk
        out["F_" + k] = grid
        print(f"{name} {mode} {k}: cells {len(cells)} median F {np.median(Fk):.3f} p10 {np.percentile(Fk, 10):.3f} p90 {np.percentile(Fk, 90):.3f} ({time.time() - t0:.0f}s)", flush=True)
    refgrid = np.full(cereal.shape, np.nan, np.float32); refgrid.ravel()[cells] = ref
    np.savez_compressed(OUT / f"{name}_{mode}_factors.npz", **out, reference_t_ha=refgrid, cereal=cereal, transfer_t_ha=m_star)
    return out, cereal


def maps():
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.colors import BoundaryNorm, ListedColormap
    m_star = json.loads((OUT / "earth_census.json").read_text())["transfer_t_ha"]
    summary = {}
    for name, mode, data, folder, meta in atlas_modes():
        out, cereal = map_factors(name, mode, data, folder, meta, m_star)
        summary[f"{name}_{mode}"] = {k: dict(median=float(np.nanmedian(v)), p10=float(np.nanpercentile(v, 10)), p90=float(np.nanpercentile(v, 90)))
                                     for k, v in out.items()}
        bounds = [0, 0.25, 0.4, 0.55, 0.7, 0.85, 0.95, 1.05, 1.2, 1.5, 2.0, 4.0]
        cols = ["#6e2238", "#ad4a2f", "#d38a3a", "#e8c46a", "#f1e3a8", "#f4f0e2", "#e9eedf", "#c3d188", "#78b365", "#348a64", "#155b51"]
        cmap = ListedColormap(cols); cmap.set_bad("#d8d6cf"); norm = BoundaryNorm(bounds, cmap.N)
        panels = [(k, t) for k, t in (("F_transfer", f"three-field + {m_star:.1f} t/ha transfer"),
                                      ("F_bare", "three-field, bare fallow, no transfer (default)"),
                                      ("F_legume", "three-field with a clover third")) if k in out]
        fig, axs = plt.subplots(1, len(panels), figsize=(6 * len(panels), 3.6), constrained_layout=True)
        for ax, (k, title) in zip(axs, panels):
            im = ax.imshow(np.where(cereal > 0, out[k], np.nan), cmap=cmap, norm=norm, interpolation="nearest")
            ax.set_title(title, fontsize=9.5); ax.set_xticks([]); ax.set_yticks([])
        fig.colorbar(im, ax=axs, shrink=0.85, label="grain factor vs previous chain (x)")
        fig.suptitle(f"{name} ({mode} climate): soil-fertility factor on wheat/barley grain, AD 200 N input 27.5 (grey: no wheat/barley)", fontsize=11)
        fig.savefig(OUT / f"{name}_{mode}_factors.png", dpi=90)
        plt.close(fig)
    (OUT / "map_factors.json").write_text(json.dumps(summary, indent=1))


if __name__ == "__main__" and sys.argv[1] in ("earth", "maps"):
    {"earth": earth, "maps": maps}[sys.argv[1]]()


def earth_figure():
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    d = json.loads((OUT / "earth_census.json").read_text())
    names = list(d["regions"])
    short = [n.split(" (")[0] for n in names]
    cases = [("existing", "#888888", "previous chain"), ("transfer", "#2f7d32", f"three-field + {d['transfer_t_ha']:.1f} t/ha transfer (anchored on NCP)"),
             ("bare", "#b5651d", "three-field, bare fallow"), ("legume", "#2b5d8a", "three-field, clover third")]
    fig, axs = plt.subplots(1, 2, figsize=(15, 5.6), constrained_layout=True, gridspec_kw=dict(width_ratios=[1.4, 1]))
    ax = axs[0]
    y = np.arange(len(names))
    for j, (k, col, lab) in enumerate(cases):
        lo = [d["regions"][n]["ratio"][k][0] for n in names]; hi = [d["regions"][n]["ratio"][k][1] for n in names]
        yy = y + (j - 1.5) * 0.18
        ax.hlines(yy, lo, hi, color=col, lw=3)
        ax.plot(lo, yy, "|", color=col, ms=8); ax.plot(hi, yy, "|", color=col, ms=8, label=lab)
    ax.axvline(1, color="#444", lw=0.8, ls="--")
    ax.set_xscale("log"); ax.set_yticks(y); ax.set_yticklabels(short, fontsize=9); ax.invert_yaxis()
    ax.set_xlabel("historical population / modelled capacity (1 = capacity met; below 1 = capacity not reached)")
    ax.set_title("Census regions around AD 1-200 (North China Plain is the anchor)", fontsize=10); ax.legend(fontsize=8, loc="upper left")
    ax = axs[1]
    for j, (k, col, lab) in enumerate(cases[1:]):
        f = [d["regions"][n]["mean_F"][k] for n in names]
        ax.barh(y + (j - 1) * 0.27, f, height=0.25, color=col, label=lab)
    ax.axvline(1, color="#444", lw=0.8, ls="--")
    ax.set_yticks(y); ax.set_yticklabels(short, fontsize=9); ax.invert_yaxis(); ax.set_xscale("log")
    ax.set_xlabel("capacity-weighted fertility factor (x previous chain)"); ax.set_title("Grain factor by region and regime", fontsize=10)
    fig.suptitle("Soil-fertility integration on Earth (WorldClim, AD 200 N input 27.5): the transfer level that keeps the Han census fit, and what the regimes do elsewhere", fontsize=11)
    fig.savefig(OUT / "earth_census.png", dpi=95)


if __name__ == "__main__" and sys.argv[1] == "earth_figure":
    earth_figure()
