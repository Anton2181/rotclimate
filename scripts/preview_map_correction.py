"""Preview what the Earth corrections change on the invented map.

    python -I scripts/preview_map_correction.py --params calibration/map_world_r39/world/best_params.json \
        --correction calibration/earth_correction_20261030 --rain calibration/earth_rain_pattern_20261030 \
        --downsample 16 --out output/earth_correction_20261030/map_preview

Runs the map once with the given parameters (one surroundings layout), then
applies the temperature correction (and, with --rain, the rain pattern, from
the run's own monthly winds, centred over the drawn land) with the world's own
calendar. Refuses parameters whose shared physics differ from those the
corrections were trained on. This previews an unadopted world candidate, not
an atlas: the painted-zone fit is reported for information and nothing
published changes.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

os.environ.setdefault("OMP_NUM_THREADS", "1")
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import numpy as np  # noqa: E402

from rotclimate.config import Params  # noqa: E402
from rotclimate.correction import RainPatternCorrection, TemperatureCorrection  # noqa: E402
from rotclimate.joint import SHARED_FIELDS  # noqa: E402
from rotclimate.koppen import monthly_stats, monthly_weights  # noqa: E402
from rotclimate.numerics import matrix_product  # noqa: E402
from rotclimate.model import ClimateModel  # noqa: E402


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--params", required=True)
    ap.add_argument("--correction", required=True)
    ap.add_argument("--rain", help="rain-pattern training folder")
    ap.add_argument("--downsample", type=int, default=16)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    corr = TemperatureCorrection.load(Path(args.correction) / "correction.npz")
    rain = RainPatternCorrection.load(Path(args.rain) / "correction.npz") if args.rain else None
    p = Params.from_json(args.params).replace(downsample=args.downsample)
    for model in (corr, rain):
        if model is None:
            continue
        physics = Params.from_json(ROOT / model.meta["physics_params"])
        differ = sorted(k for k in SHARED_FIELDS if getattr(p, k) != getattr(physics, k))
        if differ:
            raise SystemExit(f"Correction was trained on other physics; shared fields differ: {differ}")
    started = time.monotonic()
    res = ClimateModel(p).run()
    if not res.numerics.get("all_checks_passed"):
        raise SystemExit("Map run failed its numerical checks")
    st = monthly_stats(res.T, res.P, res.days, p.year_days, summer_solstice=p.winter_solstice_day + p.year_days / 2)
    g = res.grid
    mask = g.land & g.inmap
    Tc = corr.apply(st["Tm"], st["Pm"], g, p.year_days, p.winter_solstice_day, mask=mask)
    Pm = np.maximum(st["Pm"], 0.0)
    Pc = Pm
    if rain is not None:
        Wm = monthly_weights(res.days, p.year_days)
        um, vm = (matrix_product(Wm, a.reshape(len(res.days), -1)).reshape((12,) + a.shape[1:]) for a in (res.u, res.v))
        Pc = rain.apply(st["Tm"], Pm, um, vm, g, p.year_days, p.winter_solstice_day, mask=mask)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(out / "monthly.npz", Tm=st["Tm"].astype(np.float32), Tc=Tc.astype(np.float32),
                        Pm=Pm.astype(np.float32), Pc=Pc.astype(np.float32), mask=mask, summer=st["summer"])
    d = (Tc - st["Tm"])[:, mask]
    summary = dict(params=args.params, downsample=args.downsample, cells=int(mask.sum()), seconds=time.monotonic() - started,
                   numerics_passed=True, mean_change_C=float(d.mean()), mean_abs_change_C=float(np.abs(d).mean()),
                   monthly_mean_change_C=d.mean(1).tolist(), p95_abs_change_C=float(np.percentile(np.abs(d), 95)),
                   annual_range_change_C=float(((Tc.max(0) - Tc.min(0)) - (st["Tm"].max(0) - st["Tm"].min(0)))[mask].mean()),
                   calendar=dict(year_days=p.year_days, winter_solstice_day=p.winter_solstice_day),
                   painted_zones=dict(note="fit to the drawn target, not an accuracy measure",
                                      raw=zone_fit(st["Tm"], Pm, st["summer"], g),
                                      temperature=zone_fit(Tc, Pm, st["summer"], g)))
    if rain is not None:
        ratio = np.log2((Pc.sum(0) + 50.0) / (Pm.sum(0) + 50.0))[mask]
        summary.update(rain_mean_abs_log2_change=float(np.abs(ratio).mean()),
                       rain_share_changed_25pct=float((np.abs(ratio) > np.log2(1.25)).mean()),
                       rain_total_change=float(Pc[:, mask].sum() / Pm[:, mask].sum() - 1.0))
        summary["painted_zones"]["both"] = zone_fit(Tc, Pc, st["summer"], g)
    (out / "summary.json").write_text(json.dumps(summary, indent=1))
    plot(out, st["Tm"], Tc, mask, p)
    if rain is not None:
        plot_rain(out, Pm, Pc, mask)
    print(json.dumps({k: v for k, v in summary.items() if k != "monthly_mean_change_C"}, indent=1))


def zone_fit(Tm, Pm, summer, g):
    """Painted-zone agreement under the calibration's rules (score.evaluate):
    mean membership per zone, strict best-zone accuracy and recall."""
    from rotclimate.koppen import classify, climate_indices
    from rotclimate.score import TARGET_CLASSES, best_zone, memberships, terrain_slope

    ix = climate_indices(Tm, Pm, summer)
    mem = memberships(ix, slope=terrain_slope(g))
    pred = best_zone(mem, koppen=classify(Tm, Pm, summer))
    valid = g.inmap & g.land
    painted = valid & (g.target > 0)
    per = {key: float(mem[key][valid & (g.target == cid)].mean()) for cid, key, _, _ in TARGET_CLASSES
           if (valid & (g.target == cid)).any()}
    recall = {key: float((pred[valid & (g.target == cid)] == cid).mean()) for cid, key, _, _ in TARGET_CLASSES
              if (valid & (g.target == cid)).any()}
    return dict(mean_membership=float(np.mean(list(per.values()))), strict_accuracy=float((pred[painted] == g.target[painted]).mean()),
                membership=per, recall=recall)


def plot_rain(out, Pm, Pc, mask):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    rows, cols = np.nonzero(mask)
    sl = (slice(rows.min(), rows.max() + 1), slice(cols.min(), cols.max() + 1))
    fig, axes = plt.subplots(1, 2, figsize=(15, 4.6))
    im0 = axes[0].imshow(np.where(mask, Pm.sum(0), np.nan)[sl], cmap="YlGnBu", interpolation="nearest")
    axes[0].set_title("r39 raw annual rain (mm)", fontsize=10)
    ratio = np.log2((Pc.sum(0) + 50.0) / (Pm.sum(0) + 50.0))
    im1 = axes[1].imshow(np.where(mask, ratio, np.nan)[sl], cmap="BrBG", vmin=-1, vmax=1, interpolation="nearest")
    axes[1].set_title("rain-pattern correction: log2(corrected / raw) annual rain", fontsize=10)
    for ax, im in zip(axes, (im0, im1)):
        ax.set_xticks([]); ax.set_yticks([])
        fig.colorbar(im, ax=ax, fraction=.03)
    fig.suptitle("Rain redistributed by the wind-over-terrain pattern (its 300 km local mean removed each month)", fontsize=11)
    plt.savefig(out / "map_rain_pattern.png", dpi=85, bbox_inches="tight")
    plt.close(fig)


def plot(out, Tm, Tc, mask, p):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    rows, cols = np.nonzero(mask)
    sl = (slice(rows.min(), rows.max() + 1), slice(cols.min(), cols.max() + 1))
    # months after the winter solstice: ~1, 4, 7 and 10 months into the year
    after = ((np.arange(12) + 0.5) * p.year_days / 12 - p.winter_solstice_day) % p.year_days
    picks = [int(np.argmin(np.abs(after - t))) for t in (p.year_days * k / 12 for k in (1, 4, 7, 10))]
    names = ["midwinter", "spring", "midsummer", "autumn"]
    fig, axes = plt.subplots(2, 3, figsize=(16, 7.5))
    panels = [("annual mean", (Tc - Tm).mean(0))] + [(f"{n} (month {m + 1})", Tc[m] - Tm[m]) for n, m in zip(names, picks)]
    for ax, (title, field) in zip(axes.flat, panels):
        im = ax.imshow(np.where(mask, field, np.nan)[sl], cmap="RdBu_r", vmin=-3, vmax=3, interpolation="nearest")
        ax.set_title(f"correction: {title}", fontsize=10); ax.set_xticks([]); ax.set_yticks([])
    ax = axes.flat[5]
    ax.plot(Tm[:, mask].mean(1), "-o", color="#c0392b", ms=3, label="r39 raw (map mean)")
    ax.plot(Tc[:, mask].mean(1), "-o", color="#2471a3", ms=3, label="corrected")
    ax.set_xticks(range(12)); ax.set_xlabel("equal month of the local year"); ax.set_ylabel("°C"); ax.grid(alpha=.3); ax.legend(fontsize=8)
    fig.colorbar(im, ax=axes.flat[:5], orientation="horizontal", fraction=.04, pad=.04, label="corrected minus raw temperature (°C)")
    fig.suptitle("What the Earth-trained temperature correction changes on the map (unadopted r39 world candidate, one layout)", fontsize=11)
    plt.savefig(out / "map_correction.png", dpi=85, bbox_inches="tight")
    plt.close(fig)


if __name__ == "__main__":
    main()
