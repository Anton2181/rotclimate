"""Regenerate the r42 development comparison from its archived paired runs."""
import json
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
ROOT = Path(__file__).resolve().parents[2]
out = Path(__file__).resolve().parent
summary = json.loads((out / "accuracy.json").read_text())
tr = summary["temperature_monthly_mae_c"]["r41"]
pr = summary["rain_loss"]["r41"]
changes = {n: .5 * (r["temperature_mae_c"][1] - r["temperature_mae_c"][0]) / tr
               + .5 * (r["rain_loss"][1] - r["rain_loss"][0]) / pr for n, r in summary["regions"].items()}
names = sorted(changes, key=changes.get)
show = names[:7] + names[-7:]
fig, (ax, ay) = plt.subplots(1, 2, figsize=(12, 6), gridspec_kw={"width_ratios": [1, 1.6]}, layout="constrained")
ax.bar([0, 1], [1, summary["combined_score"]], color=["#81919d", "#287e79"], width=.6)
ax.set(xticks=[0, 1], xticklabels=["r41", "r42"], ylim=(0, 1.12), ylabel="Combined error relative to r41", title="Overall development error: −3.7%")
ax.text(.5, .55, "49 development regions\nT MAE: 1.98 → 1.88 °C\nRain loss: 0.515 → 0.501\n\nUnseen set d combined error: −5.9%", ha="center", va="center", fontsize=11, bbox=dict(facecolor="white", alpha=.88, edgecolor="none"))
v = np.array([changes[n] * 100 for n in show])
ay.barh(np.arange(len(show)), v, color=np.where(v < 0, "#287e79", "#bd673b"))
ay.set(yticks=np.arange(len(show)), yticklabels=[n.replace("_", " ").title() for n in show], xlabel="Regional error change (normalised by r41 overall means, ×100)", title="Largest regional gains and regressions")
ay.axvline(0, color="#333", lw=.8)
ay.invert_yaxis()
fig.suptitle("Adopted Earth model: r42 vs r41 · raw physics", fontsize=16)
fig.savefig(out / "r42_accuracy.png", dpi=150)
