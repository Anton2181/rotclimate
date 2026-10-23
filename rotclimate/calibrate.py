"""Calibrate the unknowns of the world against the painted target zones.

Unknown "world" facts (what the map does not tell us) and uncertain physics
constants are searched together with CMA-ES.  Categorical choices (spin
direction, what lies beyond each edge) are encoded as continuous genes and
thresholded, which CMA-ES copes with fine at this population size.

    python -m rotclimate.calibrate --out calibration/run1 --evals 600
"""
from __future__ import annotations

import os

for _v in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ.setdefault(_v, "1")          # one BLAS thread per worker process

import argparse
import json
import multiprocessing as mp
import time
from dataclasses import asdict
from pathlib import Path

import numpy as np

from .config import Params, apply_numerics

BEYOND_MODES = ["ocean", "land", "extend"]

# name, low, high  (genes are mapped linearly from [0, 1] to [low, high])
SPACE = [
    ("lat_center", 26.0, 48.0),
    ("tilt", 8.0, 45.0),
    ("retrograde", 0.0, 1.0),
    ("beyond_north", 0.0, 2.999),
    ("beyond_south", 0.0, 2.999),
    ("beyond_west", 0.0, 2.999),
    ("beyond_east", 0.0, 2.999),
    ("beyond_north_gap_km", 0.0, 1000.0),
    ("beyond_south_gap_km", 0.0, 1000.0),
    ("beyond_west_gap_km", 0.0, 1000.0),
    ("beyond_east_gap_km", 0.0, 1000.0),
    ("tier1", 100.0, 900.0),
    ("tier2_add", 200.0, 1200.0),
    ("tier3_add", 300.0, 1800.0),
    ("tier4_add", 500.0, 3000.0),
    ("land_tau_days", 0.6, 5.0),
    ("ocean_tau_days", 0.5, 3.0),
    ("current_strength", 0.0, 8.0),
    ("sst_offset", -4.0, 4.0),
    ("land_offset", -5.0, 5.0),
    ("inland_sea_warming", 0.0, 8.0),
    ("hadley_edge", 22.0, 40.0),
    ("hadley_shift", 0.0, 10.0),
    ("itcz_mean", 0.0, 10.0),
    ("itcz_shift", 2.0, 16.0),
    ("trade_speed", 2.0, 10.0),
    ("westerly_speed", 2.0, 12.0),
    ("monsoon_strength", 0.0, 3.0),
    ("monsoon_scale_km", 250.0, 900.0),
    ("cross_isobar_deg", 10.0, 60.0),
    ("terrain_drag", 0.0, 2.0),
    ("ocean_rh", 0.65, 0.9),
    ("evap_tau_days", 0.5, 5.0),
    ("land_recycling", 0.0, 0.8),
    ("precip_tau_days", 2.0, 15.0),
    ("rh_threshold", 0.2, 0.7),
    ("storm_track", 0.0, 5.0),
    ("storm_width", 4.0, 15.0),
    ("convective", 0.0, 6.0),
    ("orographic", 0.0, 6.0),
    ("subsidence", 0.0, 0.95),
    ("subsidence_asym", 0.0, 1.0),
]
# physics v3: storm-eddy mixing + procedural surroundings (land fraction per
# side instead of ocean/land/extend blocks); enabled with --physics v3
_BLOCK_GENES = {"beyond_north", "beyond_south", "beyond_west", "beyond_east",
                "beyond_north_gap_km", "beyond_south_gap_km", "beyond_west_gap_km",
                "beyond_east_gap_km"}
SPACE_V3 = [g for g in SPACE if g[0] not in _BLOCK_GENES] + [
    ("beyond_north_land", 0.0, 1.0),
    ("beyond_south_land", 0.0, 1.0),
    ("beyond_west_land", 0.0, 1.0),
    ("beyond_east_land", 0.0, 1.0),
    ("beyond_continuity_km", 100.0, 700.0),
    ("beyond_relief_m", 0.0, 1500.0),
    ("eddy_rate", 0.0, 2.0),
    ("eddy_scale_km", 200.0, 900.0),
]
# physics v4: lakes and small seas follow the land temperature
SPACE_V4 = SPACE_V3 + [("lake_coupling", 0.0, 0.95), ("land_amplitude", 0.7, 1.7)]
# physics v5: east-west asymmetric storm track
SPACE_V5 = SPACE_V4 + [("storm_asym", 0.0, 1.0), ("storm_reach", 0.0, 10.0)]
# physics v6: convective instability of hot moist air
SPACE_V6 = SPACE_V5 + [("instability", 0.0, 3.0), ("beyond_southeast_land", 0.0, 1.0),
                       ("beyond_northeast_land", 0.0, 1.0)]
# physics v7: summer-strengthened subtropical highs, and the search box set
# on physical grounds, the same for both spins. Modelling choices that either
# spin's best fit had pinned (round 14 / 15p) are widened; true limits
# (land fraction, current strength >= 0, sea-air humidity <= 0.9, surface
# westerlies >= 2 m/s) stay.
_V7_BOUNDS = {
    "tier1": (50.0, 900.0),              # lowland top: coastal plains can be lower
    "tier3_add": (300.0, 2500.0),
    "land_tau_days": (0.3, 5.0),
    "evap_tau_days": (0.3, 5.0),
    "monsoon_strength": (0.0, 5.0),      # round 15p's 2.95 gives land winds <= 7.5 m/s
    "monsoon_scale_km": (250.0, 1500.0),  # thermal lows are continent-sized
    "storm_track": (0.0, 8.0),
    "beyond_continuity_km": (100.0, 1200.0),
    "land_amplitude": (0.7, 2.0),
}
SPACE_V7 = [(n, *_V7_BOUNDS.get(n, (lo, hi))) for n, lo, hi in SPACE_V6] + [("subsidence_summer", 0.0, 1.0)]
# physics v8: wet ground evaporates away part of the summer warmth
SPACE_V8 = SPACE_V7 + [("wet_cooling", 0.0, 0.8)]
# v9: the map's orientation is unknown too - true north may point anywhere
# (with the spin, this also covers mirror images and the southern hemisphere)
SPACE_V9 = SPACE_V8 + [("north_bearing", -180.0, 180.0)]
# physics e1, fitted on real regions (rotclimate/earth.py, scripts/earth_calibrate.py):
# Sverdrup sinking under equatorward flow, the width of the highs' sinking and
# the summer weakening of the storm track become free
SPACE_E1 = SPACE_V9 + [("sverdrup", 0.0, 2.0), ("subsidence_width", 4.0, 14.0), ("storm_seasonality", 0.0, 0.9),
                       ("circulation_lag_days", 10.0, 75.0), ("subsidence_drying", 0.0, 0.5),
                       ("land_heat_capacity", 0.7, 4.0), ("continentality", 0.0, 3.0),
                       ("upwelling", 0.0, 8.0)]
# the world's unknowns only (where, how tilted, which way it spins, which way is
# north, how high the terrain tiers are, what lies beyond the map): physics
# held at an Earth-calibrated fit
WORLD_GENES = ("lat_center", "tilt", "retrograde", "north_bearing", "tier1", "tier2_add", "tier3_add", "tier4_add",
               "beyond_north_land", "beyond_south_land", "beyond_west_land", "beyond_east_land",
               "beyond_southeast_land", "beyond_northeast_land", "beyond_continuity_km", "beyond_relief_m")
SPACE_WORLD = [g for g in SPACE_V9 if g[0] in WORLD_GENES]
# only the e1 additions, around an existing fit (everything else held at the start)
SPACE_E1_NEW = [g for g in SPACE_E1 if g[0] not in {n for n, *_ in SPACE_V9}]
# physics e2: the rain closure and seasonal land coupling from the literature
# review (reports/research_remaining_failures_20261016.md)
SPACE_E2 = SPACE_E1 + [("background_ascent", 0.0, 1.0), ("convective_rain", 0.0, 3.0), ("convective_rh", 0.4, 0.95),
                       ("subcloud_evaporation", 0.0, 2.0), ("land_coupling_insolation", 0.0, 2.5)]
SPACE_E2_NEW = [g for g in SPACE_E2 if g[0] not in {n for n, *_ in SPACE_E1}]
SPACE_NEW = SPACE_E1_NEW + SPACE_E2_NEW          # every addition since v9, around an existing fit
# physics e3: oceanic subtropical highs, stable marine surface air, heat vs
# moisture eddy exchange (string options ebm_land / sea_enclosure via --set)
SPACE_E3 = SPACE_E2 + [("ocean_tau_stable", 0.05, 3.0), ("eddy_heat", 0.0, 1.5), ("subtropical_high", 0.0, 10.0),
                       ("subtropical_high_scale_km", 400.0, 2000.0), ("subtropical_high_width", 5.0, 15.0),
                       ("subtropical_high_seasonality", 0.0, 1.0)]
# e3b: terrain-limited eddy moisture transport
SPACE_E3B = SPACE_E3 + [("eddy_rainout", 0.0, 2.0)]
SPACE_E3B_NEW = [g for g in SPACE_E3B if g[0] not in {n for n, *_ in SPACE_E2}]
# physics e4 (research round 2): terrain-aware eddy moisture, cloud and
# clear-sky radiation on land, sub-grid marine air on coasts
SPACE_E4 = SPACE_E3B + [("eddy_moisture_height_km", 1.5, 8.0), ("cloud_radiation", 0.0, 15.0),
                        ("cloud_longwave", 0.0, 2.0), ("marine_layer", 0.0, 1.0), ("marine_reach_km", 10.0, 80.0),
                        ("marine_inversion_m", 200.0, 1500.0), ("marine_contrast", 1.0, 10.0),
                        ("monsoon_heating", 0.0, 1.5), ("monsoon_rain0", 0.0, 3.0), ("trade_land", 0.0, 1.0)]
SPACE_E4_NEW = [g for g in SPACE_E4 if g[0] not in {n for n, *_ in SPACE_E3B}]
# physics e5: pressure-driven boundary-layer winds (replace the thermal wind)
SPACE_E5 = SPACE_E4 + [("slp_large", 0.0, 4.0), ("slp_local", 0.0, 2.0), ("slp_scale_km", 800.0, 3000.0),
                       ("slp_local_km", 60.0, 400.0), ("bl_drag_ocean", 1.0e-5, 1.0e-4),
                       ("bl_drag_land", 3.0e-5, 4.0e-4), ("divergence_drying", 0.0, 2.0)]
SPACE_E5_NEW = [g for g in SPACE_E5 if g[0] not in {n for n, *_ in SPACE_E4}]
# the map fit's own settings plus the pressure winds (without the e4 extras)
SPACE_E3B5 = SPACE_E3B + SPACE_E5_NEW
SPACE_E3_NEW = [g for g in SPACE_E3 if g[0] not in {n for n, *_ in SPACE_E2}]
# the rain genes alone, around a map fit (the painted swamp and hot desert
# need the winter storm rains and summer drought to stop further north)
_RAIN = ("ocean_rh", "land_recycling", "precip_tau_days", "rh_threshold", "storm_track", "storm_width", "convective",
         "subsidence", "subsidence_asym", "instability", "subsidence_summer", "sverdrup", "subsidence_width",
         "storm_seasonality", "circulation_lag_days", "subsidence_drying", "background_ascent", "convective_rain",
         "convective_rh", "subcloud_evaporation")
# e8: the soil bucket's size and the evaporation factor it scales (bounded
# above 0.8 here: with the bucket, 1 is Priestley-Taylor's own rate)
SPACE_E8_NEW = [("soil_bucket_mm", 20.0, 400.0), ("land_recycling", 0.05, 1.2)]
SPACE_RAIN_MAP = [g for g in SPACE_E3B5 if g[0] in _RAIN] + [("eddy_seasonality", 0.0, 0.9)]
SPACE_STORM_WATER = [("eddy_rate", .05, 3.), ("eddy_scale_km", 100., 1200.),
                    ("eddy_seasonality", 0., .9), ("ocean_rh", .55, .95),
                    ("rh_threshold", .2, .6), ("land_recycling", .05, .8),
                    ("precip_tau_days", 2., 15.), ("orographic", 0., 8.)]
# e6 on the map: the pressure winds, the surroundings beyond the map and the
# weight of their land share at the grid's edge, with the base temperatures
# they trade against (fitted on several random layouts of the surroundings)
SPACE_E6_MAP = (SPACE_E5_NEW + [g for g in SPACE_WORLD if g[0].startswith("beyond_")] + [("far_fetch", 0.0, 1.0)]
                + [g for g in SPACE_E2 if g[0] in ("land_offset", "sst_offset", "land_amplitude", "continentality",
                                                    "eddy_rate")])


def _set_space(space):
    global SPACE, NAMES, LO, HI
    SPACE = space
    NAMES = [s[0] for s in SPACE]
    LO = np.array([s[1] for s in SPACE])
    HI = np.array([s[2] for s in SPACE])


_set_space(SPACE)


def decode(x: np.ndarray, base: Params) -> Params:
    x = np.clip(x, 0.0, 1.0)
    v = dict(zip(NAMES, LO + x * (HI - LO)))
    kw = {}
    for k, val in v.items():
        if k == "retrograde":
            kw[k] = bool(val > 0.5)
        elif k in ("beyond_north", "beyond_south", "beyond_west", "beyond_east"):
            kw[k] = BEYOND_MODES[int(val)]
        elif k.startswith("tier"):
            continue
        else:
            kw[k] = float(val)
    if "tier1" in v:                 # spaces without the terrain tiers keep the base's
        t1 = v["tier1"]
        t2 = t1 + v["tier2_add"]
        t3 = t2 + v["tier3_add"]
        t4 = t3 + v["tier4_add"]
        kw["tier_tops"] = (round(t1), round(t2), round(t3), round(t4))
    return base.replace(**kw)


def encode(p: Params) -> np.ndarray:
    v = {k: getattr(p, k) for k in NAMES if hasattr(p, k)}
    if "north_bearing" in v:
        # Screened bearings use 0..360; v9 searches -180..180. Wrap before
        # clipping so e.g. 330 degrees starts at -30, not at 180.
        v["north_bearing"] = (v["north_bearing"] + 180.0) % 360.0 - 180.0
    v["retrograde"] = 0.75 if p.retrograde else 0.25
    for side in ("north", "south", "west", "east"):
        if f"beyond_{side}" in NAMES:
            v[f"beyond_{side}"] = BEYOND_MODES.index(getattr(p, f"beyond_{side}")) + 0.5
    t = p.tier_tops
    v["tier1"], v["tier2_add"], v["tier3_add"], v["tier4_add"] = t[0], t[1] - t[0], t[2] - t[1], t[3] - t[2]
    v = {k: x for k, x in v.items() if k in NAMES}
    x = (np.array([v[k] for k in NAMES], float) - LO) / (HI - LO)
    return np.clip(x, 0.0, 1.0)


def evaluate_params(p: Params, mode="mean", seeds=None, cutoff=None, ensemble_objective="scores") -> dict:
    """Score a parameter set; with several seeds the unknown surroundings are
    re-generated for each and the zone scores averaged (ensemble).

    Racing: with a `cutoff`, a candidate whose first world scores below it
    skips the remaining worlds. This is a speed heuristic, not an upper
    bound: a candidate could recover on other worlds. Winners must always
    be fully scored; use race=0 for an exhaustive ensemble comparison."""
    if ensemble_objective not in ('scores', 'climate'):
        raise ValueError('Unknown ensemble objective')
    if ensemble_objective == 'climate':
        if cutoff is not None:
            raise ValueError('Mean-climate objectives require every layout; disable racing')
        return evaluate_mean_climate(p, mode, seeds)
    from .model import ClimateModel
    from .score import evaluate, objective

    guarded = mode == "guarded"
    if guarded:
        mode = "zonefit"
    biome_profile = {'whittaker': 'strict', 'whittaker-broad': 'broad', 'whittaker-covered':'strict'}.get(mode)
    evs, meds, biome_rows, coverage_rows, covered_scores = [], [], [], [], []
    seeds = seeds or [None]
    for i, sd in enumerate(seeds):
        q = p if sd is None else p.replace(beyond_seed=int(sd))
        result = ClimateModel(q).run()
        evs.append(evaluate(result))
        meds.append(mediterranean_shares(result, evs[-1]))
        if biome_profile:
            from . import biome_targets
            biome_rows.append(biome_targets.evaluate(evs[-1]['indices'], result.grid.target,
                              result.grid.inmap & result.grid.land, biome_profile))
        first_score = biome_rows[-1]['score'] if biome_profile else objective(evs[-1], mode)
        if mode == 'whittaker-covered':
            coverage_rows.append(biome_targets.rendered_coverage(result))
            first_score = biome_targets.covered_score(first_score,coverage_rows[-1])
            covered_scores.append(first_score)
        if cutoff is not None and i == 0 and len(seeds) > 1 and first_score < cutoff:
            break
    ev = dict(evs[0])
    ev["per_class"] = {k: float(np.mean([e["per_class"][k] for e in evs])) for k in ev["per_class"]}
    ev["total"] = float(np.nanmean(list(ev["per_class"].values())))
    for key in ("precision", "f1", "recall"):
        ev[key] = {k: float(np.mean([e[key][k] for e in evs])) for k in ev[key]}
    ev["accuracy"] = float(np.mean([e["accuracy"] for e in evs]))
    display_accuracy = float(np.mean([e["label_policy_audit"]["display_accuracy"] for e in evs]))
    ev["realism"] = {k: float(np.mean([e["realism"][k] for e in evs])) for k in ev["realism"]}
    med = {k: float(np.mean([m[k] for m in meds])) for k in meds[0]}
    biome_result = biome_targets.average(biome_rows) if biome_profile else None
    score = biome_result['score'] if biome_profile else objective(ev, mode)
    if covered_scores:
        score = float(np.mean(covered_scores))
    penalty = guard_penalty(ev, med) if guarded else 0.0
    return dict(score=score - penalty, guard_penalty=penalty, mediterranean=med,
                mean=ev["total"], accuracy=ev["accuracy"], raced=len(evs) < len(seeds),
                per_class=ev["per_class"], f1=ev["f1"], recall=ev["recall"],
                display_accuracy=display_accuracy, precision=ev["precision"], realism=ev["realism"],
                spread=float(np.std([e["total"] for e in evs])),
                **(dict(whittaker=biome_result, zonefit_score=objective(ev, 'zonefit')) if biome_profile else {}),
                **(dict(whittaker_coverage=dict(scope='source_land_pixels',layouts=len(coverage_rows),
                    **{k:float(np.mean([r[k] for r in coverage_rows])) for k in ['outside_share','distance_debt']}))
                   if coverage_rows else {}))


def evaluate_mean_climate(p, mode, seeds):
    """Score precisely the ensemble climate that an atlas would publish."""
    from .model import ClimateModel, ensemble_mean
    from .score import evaluate, objective
    from . import biome_targets
    runs = [ClimateModel(p if seed is None else p.replace(beyond_seed=int(seed))).run()
            for seed in (seeds or [None])]
    result = ensemble_mean(runs)
    ev = evaluate(result)
    med = mediterranean_shares(result, ev)
    guarded = mode == 'guarded'
    if guarded: mode = 'zonefit'
    profile = {'whittaker':'strict', 'whittaker-broad':'broad', 'whittaker-covered':'strict'}.get(mode)
    biome = (biome_targets.evaluate(ev['indices'], result.grid.target,
             result.grid.inmap & result.grid.land, profile) if profile else None)
    coverage = biome_targets.rendered_coverage(result) if mode == 'whittaker-covered' else None
    score = biome['score'] if biome else objective(ev, mode)
    if coverage is not None: score = biome_targets.covered_score(score, coverage)
    penalty = guard_penalty(ev, med) if guarded else 0.
    member_totals = [evaluate(run)['total'] for run in runs]
    return dict(score=score-penalty, guard_penalty=penalty, mediterranean=med,
        mean=ev['total'], accuracy=ev['accuracy'], raced=False, per_class=ev['per_class'],
        f1=ev['f1'], recall=ev['recall'], display_accuracy=ev['label_policy_audit']['display_accuracy'],
        precision=ev['precision'], realism=ev['realism'], spread=float(np.std(member_totals)),
        ensemble_objective='climate', layouts=len(runs), observed_numerics=result.numerics,
        **(dict(whittaker=biome, zonefit_score=objective(ev, 'zonefit')) if biome else {}),
        **(dict(whittaker_coverage=dict(scope='source_land_pixels', layouts=len(runs),
             outside_share=coverage['outside_share'], distance_debt=coverage['distance_debt'])) if coverage is not None else {}))


def mediterranean_shares(result, ev) -> dict:
    """Share of the painted Mediterranean classed dry (Koppen B) and Cs."""
    from .koppen import CODES, classify

    g = result.grid
    st = ev["monthly"]
    codes = np.array(CODES)[classify(st["Tm"], st["Pm"], st["summer"])]
    med = g.inmap & g.land & (g.target == 4)
    return dict(dry_share=float(np.char.startswith(codes[med], "B").mean()),
                cs_share=float(np.char.startswith(codes[med], "Cs").mean()))


# The handoff's promotion guards, as a penalty against a reference fit (the
# live atlas scored at the same resolution; file named by ROTCLIMATE_GUARDS):
# overall strict agreement may fall 1 point, cold-dry recall 2, hot-dry 3 and
# the painted Mediterranean's Cs share 2; its dry share may not exceed
# max(reference, 5 %). Each point beyond a limit costs GUARD_WEIGHT / 100.
GUARD_WEIGHT = 2.0


def guard_penalty(ev, med) -> float:
    import os

    ref = json.loads(Path(os.environ["ROTCLIMATE_GUARDS"]).read_text())
    over = (max(0.0, ref["strict"] - ev["accuracy"] - 0.01)
            + max(0.0, ref["cold_dry"] - ev["recall"]["cold_dry"] - 0.02)
            + max(0.0, ref["hot_dry"] - ev["recall"]["hot_dry"] - 0.03)
            + max(0.0, med["dry_share"] - max(ref["med_dry"], 0.05))
            + max(0.0, ref["med_cs"] - med["cs_share"] - 0.02))
    return GUARD_WEIGHT * over


def _worker(args):
    x, base_dict, mode, space, seeds, cutoff, *options = args
    _set_space(space)
    p = decode(np.asarray(x), Params(**base_dict))
    try:
        out = evaluate_params(p, mode, seeds, cutoff, ensemble_objective=options[0] if options else 'scores')
    except Exception as e:  # keep the search alive on numerical failures
        out = dict(score=-1.0, mean=0.0, accuracy=0.0, per_class={}, error=repr(e))
    out["params"] = asdict(p)
    return out


def _indexed_worker(job):
    index, args = job
    started = time.monotonic()
    result = _worker(args)
    result["seconds"] = time.monotonic() - started
    return index, result


def calibrate(out_dir: Path, evals: int, base: Params, x0=None, sigma0=0.25,
              popsize=16, workers=4, seed=1, fixed=None, mode="mean", seeds=None, race=0.06, stds=None,
              resume=False, ensemble_objective="scores"):
    import pickle

    import cma

    if evals < 1:
        raise ValueError("evals must include at least the starting candidate")
    if ensemble_objective not in ('scores', 'climate'):
        raise ValueError('Unknown ensemble objective')
    if ensemble_objective == 'climate' and race:
        raise ValueError('Mean-climate calibration requires race=0')
    out_dir.mkdir(parents=True, exist_ok=True)
    # Never resume a score-average search as a different mathematical objective.
    config = dict(mode=mode, ensemble_objective=ensemble_objective, seeds=seeds,
                  space=SPACE, base=asdict(base), fixed=fixed or {}, sigma=sigma0,
                  popsize=popsize, seed=seed, stds=stds, race=race)
    import hashlib
    from .config import REPO
    sources = list((REPO/'rotclimate').glob('*.py')) + list((REPO/'data/source').iterdir())
    sources += [REPO/'data'/name for name in ('biome_target_crosswalk.json', 'whittaker_coverage.json', 'whittaker_biomes.csv')]
    config['sources'] = {str(path.relative_to(REPO)):hashlib.sha256(path.read_bytes()).hexdigest()
                         for path in sources if path.is_file()}
    config = json.loads(json.dumps(config))
    config_path = out_dir/'calibration_config.json'
    if config_path.exists():
        if json.loads(config_path.read_text()) != config:
            raise ValueError('Calibration configuration changed; use a new output directory')
    elif resume and (out_dir/'state.pkl').exists() and ensemble_objective != 'scores':
        raise ValueError('Old checkpoints have no mean-climate objective certificate; use a new output directory')
    if not resume and (out_dir/'evals.jsonl').exists() and (out_dir/'evals.jsonl').stat().st_size:
        raise ValueError('Calibration already has results; use --resume or a new output directory')
    config_path.write_text(json.dumps(config, indent=2)+'\n')
    def job_args(x, cutoff):
        job = (x, asdict(base), mode, SPACE, seeds, cutoff)
        return job if ensemble_objective == 'scores' else (*job, ensemble_objective)
    log = open(out_dir / "evals.jsonl", "a")
    x0 = encode(base) if x0 is None else np.asarray(x0)
    fixed = fixed or {}
    fixed_idx = {NAMES.index(k): v for k, v in fixed.items()}
    for i, v in fixed_idx.items():
        x0[i] = v
    free = [i for i in range(len(NAMES)) if i not in fixed_idx]
    opts = {"bounds": [0, 1], "popsize": popsize, "seed": seed, "verbose": -9}
    if stds:                     # per-gene step sizes, as multiples of sigma0
        opts["CMA_stds"] = np.array([stds.get(NAMES[i], 1.0) for i in free])
    es = cma.CMAEvolutionStrategy(x0[free], sigma0, opts)
    state = out_dir / "state.pkl"
    if resume and state.exists():
        with state.open("rb") as f:          # our own checkpoint, written each generation below
            es, best, n, n_raced = pickle.load(f)
        print(f"Resumed at {n} evaluations, best {best[0]:.3f}", flush=True)
    else:
        # The supplied fit is a candidate too. Previously only random offspring
        # were saved, so a short restart could silently replace it with a worse fit.
        print(f"Scoring starting candidate on {len(seeds or [None])} world(s)...", flush=True)
        initial = _worker(job_args(x0, None))
        if "error" in initial or not np.isfinite(initial["score"]):
            log.close()
            raise RuntimeError(f"Starting candidate failed: {initial.get('error', initial['score'])}")
        initial.update(eval=1, x=list(map(float, x0)), stage="initial")
        log.write(json.dumps(initial) + "\n")
        log.flush()
        Params(**initial["params"]).to_json(out_dir / "best_params.json")
        best = (initial["score"], initial)
        n, n_raced = 1, 0
    t0 = time.time()
    # The initial evaluation has already initialized NumPy/Numba runtimes.
    # Fresh processes avoid inheriting their native locks (notably on macOS).
    with mp.get_context("spawn").Pool(workers) as pool:
        # CMA-ES needs complete populations. Never exceed the requested budget.
        while n + popsize <= evals and not es.stop():
            sols = es.ask()
            full = []
            for s in sols:
                x = x0.copy()
                x[free] = s
                for i, v in fixed_idx.items():
                    x[i] = v
                full.append(x)
            cutoff = best[0] - race if (race and best[1] is not None) else None
            # Persist each finished candidate instead of going silent until
            # the slowest candidate in the population finishes. CMA-ES still
            # receives results in ask() order once the population is complete.
            res = [None] * len(full)
            jobs = [(i, job_args(x, cutoff)) for i, x in enumerate(full)]
            for index, r in pool.imap_unordered(_indexed_worker, jobs, chunksize=1):
                x = full[index]
                res[index] = r
                n += 1
                r["eval"] = n
                r["x"] = list(map(float, x))
                log.write(json.dumps(r) + "\n")
                log.flush()
                if not r.get("error") and not r.get("raced") and r["score"] > best[0]:
                    best = (r["score"], r)
                    Params(**r["params"]).to_json(out_dir / "best_params.json")
                print(f"  [{n}/{evals} candidates, {time.time() - t0:.0f}s] "
                      f"finished in {r['seconds']:.0f}s; score {r['score']:.3f}; best {best[0]:.3f}"
                      + (f"; error: {r['error']}" if r.get("error") else ""), flush=True)
            n_raced += sum(bool(r.get("raced")) for r in res)
            es.tell(sols, [-r["score"] for r in res])
            with (out_dir / "state.tmp").open("wb") as f:
                pickle.dump((es, best, n, n_raced), f)
            (out_dir / "state.tmp").replace(state)
            pc = best[1]["per_class"]
            f1 = best[1].get("f1", {}) if mode in ("f1", "f1r", "zonefit", "guarded") else {}
            print(f"[{n:5d} evals, {n_raced} raced, {time.time() - t0:6.0f}s] best {best[0]:.3f} "
                  f"(mean {best[1].get('mean', best[0]):.3f})  gen-mean "
                  f"{np.mean([r['score'] for r in res]):.3f}  "
                  + " ".join(f"{k}={v:.2f}" + (f"/F{f1[k]:.2f}" if k in f1 else "") for k, v in pc.items()),
                  flush=True)
    log.close()
    return best[1]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="calibration/run")
    ap.add_argument("--evals", type=int, default=600)
    ap.add_argument("--start", default=None, help="params json to start from")
    ap.add_argument("--downsample", type=int)
    ap.add_argument("--steps", type=int)
    ap.add_argument("--picard", type=int)
    ap.add_argument("--saved-numerics", action="store_true", help="preserve the starting numerical configuration")
    ap.add_argument("--plan", action="store_true", help="show starting configuration without running a calibration")
    ap.add_argument("--sigma", type=float, default=0.25)
    ap.add_argument("--popsize", type=int, default=16)
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--fix", default="{}", help='json of genes to hold fixed, e.g. {"retrograde":0.75}')
    ap.add_argument("--objective", default="mean", choices=["mean", "balanced", "f1", "f1r", "zonefit", "guarded",
                                                           "whittaker", "whittaker-broad", "whittaker-covered"])
    ap.add_argument("--guards", default=None, help="json of reference guard measures (for --objective guarded)")
    ap.add_argument("--physics", default="v2", choices=["v2", "v3", "v4", "v5", "v6", "v7", "v8", "v9", "e1", "e1new", "e2", "e2new", "e3", "e3new",
                                                    "e3b", "e3bnew", "e4", "e4new", "e5", "e5new", "e3b5", "e6map", "rain", "storm-water", "new", "world"])
    ap.add_argument("--seeds", default="", help="comma list of surroundings seeds (ensemble)")
    ap.add_argument('--ensemble-objective', choices=['climate', 'scores'], default='climate',
                    help='climate scores the field average published by the atlas; scores reproduces legacy layout-score averaging')
    ap.add_argument("--race", type=float,
                    help="skip the other worlds for candidates whose first world scores this far below the best (0 = off)")
    ap.add_argument("--set", default="{}", help="json of parameter overrides for the start point")
    ap.add_argument("--bounds", default="{}", help='json of search bounds to override, e.g. {"sst_offset": [-2, 2]}')
    ap.add_argument("--stds", default="{}", help='json of per-gene step sizes as multiples of --sigma, e.g. {"north_bearing": 0.1}')
    ap.add_argument("--resume", action="store_true", help="continue from --out/state.pkl (saved every generation)")
    a = ap.parse_args()
    if a.physics == "v3":
        _set_space(SPACE_V3)
    elif a.physics == "v4":
        _set_space(SPACE_V4)
    elif a.physics == "v5":
        _set_space(SPACE_V5)
    elif a.physics == "v6":
        _set_space(SPACE_V6)
    elif a.physics == "v7":
        _set_space(SPACE_V7)
    elif a.physics == "v8":
        _set_space(SPACE_V8)
    elif a.physics == "v9":
        _set_space(SPACE_V9)
    elif a.physics == "e1":
        _set_space(SPACE_E1)
    elif a.physics == "world":
        _set_space(SPACE_WORLD)
    elif a.physics == "e1new":
        _set_space(SPACE_E1_NEW)
    elif a.physics == "e2":
        _set_space(SPACE_E2)
    elif a.physics == "e2new":
        _set_space(SPACE_E2_NEW)
    elif a.physics == "e3":
        _set_space(SPACE_E3)
    elif a.physics == "e3new":
        _set_space(SPACE_E3_NEW)
    elif a.physics == "e3b":
        _set_space(SPACE_E3B)
    elif a.physics == "e3bnew":
        _set_space(SPACE_E3B_NEW)
    elif a.physics == "e4":
        _set_space(SPACE_E4)
    elif a.physics == "e4new":
        _set_space(SPACE_E4_NEW)
    elif a.physics == "e5":
        _set_space(SPACE_E5)
    elif a.physics == "e5new":
        _set_space(SPACE_E5_NEW)
    elif a.physics == "e3b5":
        _set_space(SPACE_E3B5)
    elif a.physics == "e6map":
        _set_space(SPACE_E6_MAP)
    elif a.physics == "rain":
        _set_space(SPACE_RAIN_MAP)
    elif a.physics == "storm-water":
        _set_space(SPACE_STORM_WATER)
    elif a.physics == "new":
        _set_space(SPACE_NEW)
    bounds = json.loads(a.bounds)
    if bounds:
        _set_space([(n, *bounds.get(n, (lo, hi))) for n, lo, hi in SPACE])
    base = Params.from_json(a.start) if a.start else Params()
    base = apply_numerics(base, saved=a.saved_numerics,
                          defaults=dict(downsample=16, steps_per_year=25, picard_iters=2),
                          downsample=a.downsample, steps=a.steps, picard=a.picard)
    if a.physics in ("v3", "v4", "v5", "v6", "v7", "v8", "v9", "e1", "e1new", "e2", "e2new", "e3", "e3new", "e3b",
                     "e3bnew", "e4", "e4new", "e5", "e5new", "e3b5", "e6map", "rain", "new", "world"):
        base = base.replace(beyond_style="procedural")
    base = base.replace(**{k: (tuple(v) if isinstance(v, list) else v)
                           for k, v in json.loads(a.set).items()})
    seeds = [int(x) for x in a.seeds.split(",") if x.strip()] or None
    race = a.race if a.race is not None else (0. if a.ensemble_objective == 'climate' else .06)
    if a.ensemble_objective == 'climate' and race:
        ap.error('--ensemble-objective climate requires --race 0')
    if a.objective == "guarded":
        import os
        if not a.guards:
            raise SystemExit("--objective guarded needs --guards")
        os.environ["ROTCLIMATE_GUARDS"] = str(Path(a.guards).resolve())     # inherited by the workers
    fixed = json.loads(a.fix)
    if a.plan:
        print(json.dumps(dict(params=asdict(base), objective=a.objective, seeds=seeds,
                              evals=a.evals, fixed=fixed, ensemble_objective=a.ensemble_objective, race=race), indent=2))
        return
    best = calibrate(Path(a.out), a.evals, base, sigma0=a.sigma, popsize=a.popsize,
                     workers=a.workers, seed=a.seed, fixed=fixed, mode=a.objective, seeds=seeds, race=race,
                     stds=json.loads(a.stds), resume=a.resume, ensemble_objective=a.ensemble_objective)
    print(json.dumps(best["per_class"], indent=1), best["score"])


if __name__ == "__main__":
    main()
