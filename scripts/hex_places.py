"""Place the full name list (hex-names.csv) on the map.

The names come on a pointy-top hex grid: 90 hexes per row, numbered from 1,
odd rows shifted half a hex right. The grid's origin and spacing are fitted
(robust least squares) to the towns that also appear in data/places.csv
(label positions read off the labels layer), then every hex gets a pixel
position in map coordinates (2000 x 926).
"""
import csv
import json
import sys
import unicodedata
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
NCOL = 90


def norm(s):
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode().casefold()
    return "".join(ch for ch in s if ch.isalnum()).replace("l", "i")


def rowcol(h):
    return (h - 1) // NCOL, (h - 1) % NCOL


rows = [r for r in csv.reader(open(ROOT / "data" / "hex-names.csv", encoding="utf-8"))][1:]
names = [(int(r[0]), r[1].strip()) for r in rows if r and r[0].strip().isdigit()]
old = {norm(r["name"]): (float(r["x"]), float(r["y"]))
       for r in csv.DictReader(open(ROOT / "data" / "places.csv", encoding="utf-8"))}

pairs = [(h, old[norm(n)]) for h, n in names if norm(n) in old]
keep = np.ones(len(pairs), bool)
for it in range(4):
    H = np.array([p[0] for p in pairs])
    rr, cc = rowcol(H)
    X = np.array([p[1][0] for p in pairs]); Y = np.array([p[1][1] for p in pairs])
    ax = np.stack([np.ones_like(cc, dtype=float), cc + 0.5 * (rr % 2)], 1)
    ay = np.stack([np.ones_like(rr, dtype=float), rr.astype(float)], 1)
    px, *_ = np.linalg.lstsq(ax[keep], X[keep], rcond=None)
    py, *_ = np.linalg.lstsq(ay[keep], Y[keep], rcond=None)
    res = np.hypot(ax @ px - X, ay @ py - Y)
    keep = res < max(3 * np.median(res[keep]), 12)
print(f"matched {len(pairs)} towns, used {keep.sum()}; x0={px[0]:.2f} dx={px[1]:.3f} "
      f"y0={py[0]:.2f} dy={py[1]:.3f} (dy/dx={py[1]/px[1]:.3f}, hex ideal 0.866); "
      f"median residual {np.median(res[keep]):.1f}px, 90th pct {np.percentile(res[keep], 90):.1f}px")

# positions for every name; same name in adjacent hexes -> merged; two names
# in one hex -> nudged apart vertically
pos = {}
for h, n in names:
    r, c = rowcol(h)
    x, y = px[0] + px[1] * (c + 0.5 * (r % 2)), py[0] + py[1] * r
    pos.setdefault(n, []).append((h, x, y))
out = []
for n, lst in pos.items():
    groups = []
    for h, x, y in lst:
        for g in groups:
            if np.hypot(g[-1][1] - x, g[-1][2] - y) < 1.6 * px[1]:
                g.append((h, x, y)); break
        else:
            groups.append([(h, x, y)])
    for g in groups:
        out.append(dict(name=n, hex=g[0][0], x=float(np.mean([q[1] for q in g])),
                        y=float(np.mean([q[2] for q in g]))))
by_hex = {}
for o in out:
    by_hex.setdefault(o["hex"], []).append(o)
for lst in by_hex.values():
    if len(lst) > 1:
        for i, o in enumerate(lst):
            o["y"] += (i - (len(lst) - 1) / 2) * 0.45 * py[1]
for o in out:
    o["kind"] = "temple" if "temple" in o["name"].casefold() else "town"
with open(ROOT / "data" / "places.csv", "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f)
    w.writerow(["name", "x", "y", "kind", "hex"])
    for o in sorted(out, key=lambda o: o["hex"]):
        w.writerow([o["name"], round(o["x"], 1), round(o["y"], 1), o["kind"], o["hex"]])
(ROOT / "data" / "hexgrid.json").write_text(json.dumps(dict(ncol=NCOL, x0=px[0], dx=px[1], y0=py[0], dy=py[1])))
# update the atlas in place
mp = ROOT / "atlas" / "data" / "atlas.json"
meta = json.loads(mp.read_text())
meta["places"] = [dict(name=o["name"], x=round(o["x"], 1), y=round(o["y"], 1), kind=o["kind"]) for o in out]
mp.write_text(json.dumps(meta, ensure_ascii=False))
print(f"wrote {len(out)} places")
