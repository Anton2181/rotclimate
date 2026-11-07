"""Figure for reports/SETTLEMENT_MODEL_EARTH_20261107.md: the blind Sui AD 610 test of the unmarked-town model
(calibration/settlement_model_20261107/plan.json, already evaluated once; this only redraws it).

    .venv/bin/python -I scripts/plot_settlement_model.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "scripts")]


def main():
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import polity_earth_check as P
    import earth_control_blind2 as B2
    import settlement_model_earth as S
    g = P.load_window("han"); land = g["land"].astype(bool); H, W = land.shape
    pts = B2.seats(610); r, c, ok = P.snap(g, pts[:, 0], pts[:, 1])
    inside, _ = B2.target(g, 610, ("Sui Dynasty",))
    x = S.inputs(g, np.zeros(land.shape, bool), inside)
    real = np.unique((r * W + c)[ok]); x["real"] = real; real = real[x["allowed"].ravel()[real]]
    towns = S.place(x, S.CURRENT); placed = np.array([y * W + q for y, q in towns])
    km = float(g["cell_km"])
    fig, axes = plt.subplots(1, 2, figsize=(12, 5.6), constrained_layout=True)
    base = np.where(land, np.where(x["allowed"], 0.80, 0.92), 1.0)
    dens = np.log1p(x["density"]) * x["allowed"]
    for ax, title in zip(axes, ("Real county seats, AD 610 (CHGIS V6)", "Model towns (unmarked-town rule, no seats given)")):
        ax.imshow(np.dstack([base * 0.95, base * 0.94, base * 0.90]), origin="upper", extent=(0, W * km, H * km, 0))
        ax.imshow(np.ma.masked_where(dens <= 0, dens), cmap="Greens", alpha=0.35, origin="upper", extent=(0, W * km, H * km, 0))
        ax.set_title(title, fontsize=11); ax.set_xticks([]); ax.set_yticks([])
    for ax, cells, col in ((axes[0], real, "#7a3b2e"), (axes[1], placed, "#1f5f8b")):
        ax.scatter((cells % W + 0.5) * km, (cells // W + 0.5) * km, s=4, c=col, lw=0)
    m = S.metrics(x, towns)
    fig.suptitle(f"Blind test: {len(real):,} seats inside Sui vs {len(placed):,} model towns ({len(placed) / len(real) - 1:+.0%}), "
                 f"F1 {m['F1']:.2f} within 25 km, block rank correlation {m['M1']:.2f}", fontsize=11)
    out = ROOT / "reports/figures/settlement_model_sui610.png"; out.parent.mkdir(exist_ok=True, parents=True)
    fig.savefig(out, dpi=110); print(out)


if __name__ == "__main__":
    main()
