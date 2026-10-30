"""Figures for reports/PHYSICS_GAPS_20261030.md.

    python -I scripts/physics_gap_figures.py attribution output/physics_gaps_20261030/attribution_r39.json
    python -I scripts/physics_gap_figures.py sst          # model SST minus WOA18 by latitude (31 regions)
    python -I scripts/physics_gap_figures.py circulation north_india 1,5,7
    python -I scripts/physics_gap_figures.py dryheat RUN_DIR [RUN_DIR ...]   # benchmark_local runs with dry_heating
    python -I scripts/physics_gap_figures.py monsoon ATTRIBUTION_JSON RUN_DIR [RUN_DIR ...]   # runs with monsoon_westerly
    python -I scripts/physics_gap_figures.py refit SEARCH_DIR KNOB VALIDATION_DIR NAME   # gate_calibrate search + validation

Output goes to output/physics_gaps_20261030/.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

os.environ.setdefault("OMP_NUM_THREADS", "1")
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))
import matplotlib  # noqa: E402
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

OUT = ROOT / "output/physics_gaps_20261030"
R39 = ROOT / "calibration/local_accuracy_20261023/r39_params.json"


def attribution(path):
    d = json.loads(Path(path).read_text())
    res = d["regions"]
    regs = sorted(res["model"], key=lambda r: -res["model"][r]["rain"]["loss"])
    styles = dict(model=("r39 model", "#c0392b", "o"), observed_wind=("observed winds", "#2471a3", "s"),
                  observed_sst=("observed SST", "#d68910", "^"), observed_both=("both observed", "#229954", "D"))
    fig, axes = plt.subplots(1, 2, figsize=(15, 10), sharey=True)
    y = np.arange(len(regs))
    for name, (label, colour, marker) in styles.items():
        ratio = [np.log2(res[name][r]["rain"]["sim_mean_annual_mm"] / res[name][r]["rain"]["obs_mean_annual_mm"]) for r in regs]
        tm = [res[name][r]["temperature"]["monthly_mae_C"] for r in regs]
        axes[0].scatter(ratio, y, color=colour, marker=marker, label=label, s=36, zorder=3)
        axes[1].scatter(tm, y, color=colour, marker=marker, label=label, s=36, zorder=3)
    axes[0].axvline(0, color="k", lw=1)
    axes[0].set_xlabel("annual rain, log2(model / observed)")
    axes[1].set_xlabel("monthly temperature MAE (°C)")
    axes[0].set_yticks(y)
    axes[0].set_yticklabels(regs, fontsize=8)
    axes[0].invert_yaxis()
    for ax in axes:
        ax.grid(alpha=.3)
    axes[1].legend(fontsize=8, loc="lower right")
    s = d["summary"]
    fig.suptitle("What the circulation and the sea cause: r39 rerun with observed surface winds (NCEP) and/or SST (WOA18)\n"
                 + "  ".join(f"{styles[k][0]}: T {v['all']['T_monthly_mae']:.2f} °C, rain loss {v['all']['P_loss']:.3f}" for k, v in s.items()),
                 fontsize=10)
    plt.tight_layout()
    plt.savefig(OUT / "attribution.png", dpi=85)
    plt.close(fig)


def sst():
    from earth_benchmark import load_params
    from benchmark_local import DEV12_SPECS, DEV31
    from rotclimate import earth
    from rotclimate.model import ClimateModel

    earth.REGIONS.update(json.loads(DEV12_SPECS.read_text()))
    base = load_params(R39)
    days = (np.arange(12) + 0.5) * 365 / 12
    lat_all, bias, amp_m, amp_o = [], [], [], []
    for r in DEV31:
        case = earth.region_case(r, 56.0)
        g, p = case.grid, earth.earth_params(base, case)
        m = ClimateModel(p, g)
        s = np.array([m.sst(d, m.z.ocean(m.lat, d) + p.sst_offset, m.z.land(m.lat, d) + p.land_offset) for d in days])
        oc = ~g.land
        lat_all.append(g.lat[oc]); bias.append((s - g.obs_sst)[:, oc].mean(0))
        amp_m.append(np.ptp(s[:, oc], 0)); amp_o.append(np.ptp(g.obs_sst[:, oc], 0))
    lat_all, bias, amp_m, amp_o = map(np.concatenate, (lat_all, bias, amp_m, amp_o))
    edges = np.arange(10, 66, 5)
    rows = []
    for lo, hi in zip(edges[:-1], edges[1:]):
        k = (lat_all >= lo) & (lat_all < hi)
        if k.sum() >= 50:
            rows.append(dict(band=f"{lo}-{hi}", cells=int(k.sum()), bias=float(bias[k].mean()),
                             amplitude_model=float(amp_m[k].mean()), amplitude_obs=float(amp_o[k].mean())))
    (OUT / "sst_latitude.json").write_text(json.dumps(rows, indent=1))
    fig, axes = plt.subplots(1, 2, figsize=(12, 4.2))
    mid = [int(r["band"].split("-")[0]) + 2.5 for r in rows]
    axes[0].bar(mid, [r["bias"] for r in rows], width=4, color="#2471a3")
    axes[0].axhline(0, color="k", lw=1)
    axes[0].set_xlabel("latitude (°, mirrored southern regions included)"); axes[0].set_ylabel("annual mean SST bias (°C)")
    axes[0].set_title("Model SST minus WOA18, ocean cells of the 31 regions")
    axes[1].plot(mid, [r["amplitude_model"] for r in rows], "-o", color="#c0392b", label="model")
    axes[1].plot(mid, [r["amplitude_obs"] for r in rows], "-o", color="k", label="WOA18")
    axes[1].set_xlabel("latitude (°)"); axes[1].set_ylabel("seasonal range (°C)"); axes[1].legend()
    axes[1].set_title("Seasonal SST range")
    for ax in axes:
        ax.grid(alpha=.3)
    plt.tight_layout()
    plt.savefig(OUT / "sst_latitude.png", dpi=85)
    plt.close(fig)


def circulation(region, months):
    from earth_benchmark import load_params
    from attribute_observed_forcing import ncep_at
    from benchmark_local import DEV12_SPECS
    from rotclimate import earth
    from rotclimate.koppen import monthly_weights
    from rotclimate.model import ClimateModel

    earth.REGIONS.update(json.loads(DEV12_SPECS.read_text()))
    case = earth.region_case(region, 56.0)
    g, p = case.grid, earth.earth_params(load_params(R39), case)
    res = ClimateModel(p, g).run(steps=p.steps_per_year)
    W = monthly_weights(res.days, p.year_days)
    mon = lambda a: (W @ a.reshape(len(res.days), -1)).reshape((12,) + a.shape[1:])
    mu, mv, mw = mon(res.u), mon(res.v), mon(res.W)
    nc = ncep_at(case)
    ny, nx = g.land.shape
    st = 3
    Y, X = np.mgrid[0:ny:st, 0:nx:st]
    fig, axes = plt.subplots(len(months), 3, figsize=(16, 4.6 * len(months)))
    names = "JFMAMJJASOND"
    for row, m in enumerate(months):
        k = m - 1
        for col, (title, u, v) in enumerate((("model surface wind", mu[k], mv[k]), ("NCEP sig995 wind", nc["u"][k], nc["v"][k]))):
            ax = axes[row, col]
            ax.contourf(np.where(g.land, g.elev, np.nan), levels=[0, 300, 1000, 2000, 3000, 4000, 6000], cmap="Greys", alpha=.6)
            ax.contour(g.land.astype(float), [0.5], colors="k", linewidths=.6)
            ax.contour(g.inmap.astype(float), [0.5], colors="tab:red", linewidths=.8, linestyles="--")
            ax.quiver(X, Y, u[::st, ::st], -v[::st, ::st], scale=60, width=.003)
            ax.set_ylim(ny, 0); ax.set_xticks([]); ax.set_yticks([])
            ax.set_title(f"{names[k]}: {title}")
        ax = axes[row, 2]
        im = ax.imshow(mw[k] - nc["pw"][k], cmap="BrBG", vmin=-25, vmax=25)
        ax.contour(g.land.astype(float), [0.5], colors="k", linewidths=.6)
        ax.contour(g.inmap.astype(float), [0.5], colors="tab:red", linewidths=.8, linestyles="--")
        ax.set_xticks([]); ax.set_yticks([])
        ax.set_title(f"{names[k]}: column water model − NCEP (mm)")
        fig.colorbar(im, ax=ax, fraction=.035)
    fig.suptitle(f"{region.replace('_', ' ')}: r39 circulation vs NCEP reanalysis 1991–2020 (grey: terrain; red dashes: scored region)", fontsize=12)
    plt.tight_layout()
    plt.savefig(OUT / f"{region}_circulation.png", dpi=80)
    plt.close(fig)


def dryheat(runs):
    base = json.loads((ROOT / "output/earth_correction_20261030/r39_dev31/summary.json").read_text())["regions"]
    regs = sorted(base, key=lambda r: base[r]["temperature"]["monthly_mae_C"])
    fig, axes = plt.subplots(1, 2, figsize=(14, 9), sharey=True)
    y = np.arange(len(regs))
    colours = ["#2471a3", "#229954", "#d68910", "#7d3c98"]
    for run, colour in zip(runs, colours):
        s = json.loads((Path(run) / "summary.json").read_text())
        ov = s["overrides"]
        label = ", ".join(f"{k} {v}" for k, v in ov.items())
        axes[0].scatter([s["regions"][r]["temperature"]["monthly_mae_C"] - base[r]["temperature"]["monthly_mae_C"] for r in regs], y,
                        color=colour, label=label, s=30)
        axes[1].scatter([s["regions"][r]["rain"]["loss"] - base[r]["rain"]["loss"] for r in regs], y, color=colour, label=label, s=30)
    for ax, xl in zip(axes, ("monthly T MAE change (°C)", "rain loss change")):
        ax.axvline(0, color="k", lw=1); ax.grid(alpha=.3); ax.set_xlabel(xl)
    axes[0].set_yticks(y); axes[0].set_yticklabels(regs, fontsize=8)
    axes[1].legend(fontsize=8)
    fig.suptitle("Dry-ground heating (e54), change against r39 by region (negative = better)", fontsize=11)
    plt.tight_layout()
    plt.savefig(OUT / "dry_heating.png", dpi=85)
    plt.close(fig)


def monsoon(attribution_path, runs):
    from earth_benchmark import load_params
    from benchmark_local import DEV12_SPECS
    from rotclimate import earth
    from rotclimate.koppen import monthly_stats
    from rotclimate.model import ClimateModel

    earth.REGIONS.update(json.loads(DEV12_SPECS.read_text()))
    att = json.loads(Path(attribution_path).read_text())["regions"]
    case = earth.region_case("north_india", 56.0)
    g = case.grid
    m = g.inmap & g.land & np.isfinite(case.obs_P).all(0)
    fig, axes = plt.subplots(1, 2, figsize=(15, 6), gridspec_kw=dict(width_ratios=[1, 1.3]))
    ax = axes[0]
    ax.plot(range(12), att["model"]["north_india"]["monthly_rain_obs"], "k-o", ms=3, label="observed (WorldClim)")
    ax.plot(range(12), att["model"]["north_india"]["monthly_rain_sim"], "-o", color="#c0392b", ms=3, label="r39")
    colours = ["#7fb3d5", "#2471a3", "#1b4f72", "#7d3c98"]
    base = json.loads((ROOT / "output/earth_correction_20261030/r39_dev31/summary.json").read_text())["regions"]
    regs = sorted(base, key=lambda r: base[r]["rain"]["loss"])
    for run, colour in zip(runs, colours):
        s = json.loads((Path(run) / "summary.json").read_text())
        ov = s["overrides"]
        p = earth.earth_params(load_params(R39), case).replace(**ov)
        res = ClimateModel(p, g).run(steps=p.steps_per_year)
        st = monthly_stats(res.T, res.P, res.days, p.year_days, summer_solstice=p.winter_solstice_day + p.year_days / 2)
        label = ", ".join(f"{k} {v}" for k, v in ov.items())
        ax.plot(range(12), st["Pm"][:, m].mean(1), "-o", color=colour, ms=3, label=label)
        axes[1].scatter([s["regions"][r]["rain"]["loss"] - base[r]["rain"]["loss"] for r in regs], range(len(regs)),
                        color=colour, s=30, label=label)
    ax.plot(range(12), att["observed_wind"]["north_india"]["monthly_rain_sim"], "--", color="#229954", label="r39 with observed winds")
    ax.set_xticks(range(12)); ax.set_xticklabels(list("JFMAMJJASOND")); ax.set_ylabel("mm per month"); ax.grid(alpha=.3)
    ax.legend(fontsize=8); ax.set_title("North India rain (scored land)")
    axes[1].axvline(0, color="k", lw=1); axes[1].grid(alpha=.3)
    axes[1].set_yticks(range(len(regs))); axes[1].set_yticklabels(regs, fontsize=8)
    axes[1].set_xlabel("rain loss change against r39 (negative = better)")
    fig.suptitle("Monsoon westerlies (e55): cross-equatorial trades turned westerly toward the ITCZ", fontsize=11)
    plt.tight_layout()
    plt.savefig(OUT / "monsoon_westerly.png", dpi=85)
    plt.close(fig)


def refit(search, knob, validation, name):
    """Search candidates (S against the worst region group, coloured by one knob)
    and the winter-rain regions that bind the trade-off, from the validation runs."""
    rows = [json.loads(line) for line in (Path(search) / "evals.jsonl").read_text().splitlines()]
    best = min(rows, key=lambda r: r["cost"])
    fig, axes = plt.subplots(1, 2, figsize=(15, 6), gridspec_kw=dict(width_ratios=[1, 1.15]))
    ax = axes[0]
    ax.add_patch(plt.Rectangle((0.98, 0.99), 0.015, 0.01, color="#2ecc71", alpha=.15, label="gate passes here"))
    sc = ax.scatter([r["S"] for r in rows], [max(r["groups"].values()) for r in rows], c=[r["knobs"][knob] for r in rows],
                    cmap="viridis", s=40, zorder=3)
    ax.scatter(rows[0]["S"], max(rows[0]["groups"].values()), s=150, facecolor="none", edgecolor="r", marker="s",
               zorder=4, label="start")
    ax.scatter(best["S"], max(best["groups"].values()), s=300, color="r", marker="*", zorder=5, label="lowest cost")
    ax.axhline(1.0, color="k", ls="--", lw=1); ax.axvline(0.995, color="k", ls="--", lw=1)
    ax.set_xlim(0.98, 1.01); ax.set_ylim(0.99, 1.03); ax.grid(alpha=.3); ax.legend(fontsize=8)
    ax.set_xlabel("31-region S (lower is better)"); ax.set_ylabel("worst region-group score")
    plt.colorbar(sc, ax=ax, label=knob)
    ax.set_title(f"{len(rows)} candidates; none clears every group", fontsize=10)
    ax = axes[1]
    regions = ["california", "iberia", "cape", "morocco", "great_basin"]
    colours = ["#c0392b", "#2471a3", "#229954", "#7d3c98", "#d68910"]
    for r, colour in zip(regions, colours):
        a = np.load(Path(validation) / "r39_dev31/cells" / f"{r}.npz")
        b = np.load(Path(validation) / "candidate_dev31/cells" / f"{r}.npz")
        ax.plot(range(12), a["Po"].mean(1), "-", color=colour, lw=2.5, alpha=.45)
        ax.plot(range(12), a["Ps"].mean(1), "--", color=colour, lw=1.2)
        ax.plot(range(12), b["Ps"].mean(1), "-o", color=colour, ms=3, lw=1.2, label=r.replace("_", " "))
    ax.plot([], [], "-", color="grey", lw=2.5, alpha=.45, label="observed (WorldClim)")
    ax.plot([], [], "--", color="grey", lw=1.2, label="r39")
    ax.plot([], [], "-o", color="grey", ms=3, lw=1.2, label="refit winner")
    ax.set_xticks(range(12)); ax.set_xticklabels(list("JFMAMJJASOND")); ax.set_ylabel("mm per month (scored land, model's season frame)")
    ax.grid(alpha=.3); ax.legend(fontsize=8, ncol=2)
    ax.set_title("Winter-rain coasts: r39 already 40-90 % too wet in winter; the refit adds ~5 %", fontsize=10)
    fig.suptitle(name, fontsize=11)
    plt.tight_layout()
    plt.savefig(OUT / f"{Path(search).parent.name.split('_2026')[0]}.png", dpi=85)
    plt.close(fig)


if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    what = sys.argv[1]
    if what == "attribution":
        attribution(sys.argv[2])
    elif what == "sst":
        sst()
    elif what == "circulation":
        circulation(sys.argv[2], [int(x) for x in sys.argv[3].split(",")])
    elif what == "dryheat":
        dryheat(sys.argv[2:])
    elif what == "monsoon":
        monsoon(sys.argv[2], sys.argv[3:])
    elif what == "refit":
        refit(sys.argv[2], sys.argv[3], sys.argv[4], sys.argv[5])
    else:
        sys.exit(__doc__)
