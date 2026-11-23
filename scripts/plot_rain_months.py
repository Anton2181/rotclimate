"""Monthly rain, observed vs two model versions, from rainprobe text outputs (rows 'P mm/mo' and 'obs').

    python3 -I scripts/plot_rain_months.py OUT.png TITLE  LABEL_A LABEL_B  NAME:FILE_A:FILE_B [...]
Southern regions are mirrored into the northern hemisphere with months rolled by six; they are rolled back here.
"""
import re, sys
import numpy as np
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
C1, C2, INK, INK2, GRID, BG = "#2a78d6", "#eb6834", "#0b0b0b", "#52514e", "#e4e3df", "#fcfcfb"
plt.rcParams.update({"font.size": 9, "axes.edgecolor": INK2, "axes.labelcolor": INK2, "xtick.color": INK2,
                     "ytick.color": INK2, "axes.spines.top": False, "axes.spines.right": False,
                     "figure.facecolor": BG, "axes.facecolor": BG})


def row(txt, key):
    m = re.search(re.escape(key) + r"\s*\[([^\]]*)\]", txt)
    return np.array([float(v) for v in m.group(1).split()])


out, title, la, lb = sys.argv[1:5]
specs = [s.split(":") for s in sys.argv[5:]]
fig, axs = plt.subplots(1, len(specs), figsize=(3.6 * len(specs), 3.4), sharey=False)
mon = np.arange(12); names = list("JFMAMJJASOND")
for ax, (name, fa, fb) in zip(np.atleast_1d(axs), specs):
    ta, tb = open(fa).read(), open(fb).read()
    south = name.endswith("(S)")
    roll = (lambda a: np.roll(a, 6)) if south else (lambda a: a)
    obs, a, b = roll(row(ta, "obs")), roll(row(ta, "P mm/mo")), roll(row(tb, "P mm/mo"))
    ax.bar(mon, obs, color=GRID, width=0.8, label="observed")
    ax.plot(mon, a, color=C1, lw=2, marker="o", ms=4, label=la)
    ax.plot(mon, b, color=C2, lw=2, marker="o", ms=4, label=lb)
    ax.set_xticks(mon, names); ax.set_title(name, loc="left", fontsize=9.5, color=INK)
    ax.grid(axis="y", color=GRID, lw=0.6); ax.set_axisbelow(True)
np.atleast_1d(axs)[0].set_ylabel("rain (mm per month)")
np.atleast_1d(axs)[0].legend(frameon=False, fontsize=8, loc="upper center")
fig.suptitle(title, x=0.01, ha="left", fontsize=10, color=INK)
fig.tight_layout(); fig.savefig(out, dpi=160)
