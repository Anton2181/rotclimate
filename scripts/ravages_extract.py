"""Extract the army movements (ComLoc) and what explains them from the Ravages
master sheet into one JSON for the army tracker page.

    python -I scripts/ravages_extract.py <Ravages_Master_sheet.xlsx> ravages/data.json
"""
from __future__ import annotations

import datetime as dt
import itertools
import json
import re
import sys
import unicodedata
from pathlib import Path

import numpy as np
import openpyxl
from PIL import Image
from scipy import ndimage as ndi

ROOT = Path(__file__).resolve().parents[1]
NCOL = 90
NROW = 47
EVENT_KINDS = [  # (kind, pattern) checked in order; anything else is routine and dropped
    ("battle", r"battle|victory|defeat|routed|ambush"),
    ("assault", r"assault|siege|storm|sack"),
    ("operation", r"operation"),
    ("march", r"force[d]? march|rest\b"),
    ("command", r"subcommander|command|joined|merge|split"),
    ("recruit", r"recruit"),
    ("tax", r"taxation|tax collection"),
]


def iso(d):
    return d.date().isoformat() if isinstance(d, dt.datetime) else None


def shift(day, n):
    return (dt.date.fromisoformat(day) + dt.timedelta(days=n)).isoformat()


def main(xlsx, out):
    wb = openpyxl.load_workbook(xlsx, read_only=True, data_only=True)
    loc = list(wb["ComLoc"].iter_rows(values_only=True))
    names = [str(n).strip() for n in loc[0][2:] if n]
    dates, pos = [], {n: [] for n in names}
    for r in loc[1:]:
        if not isinstance(r[0], dt.datetime):
            break
        dates.append(iso(r[0]))
        for n, v in zip(names, r[2:2 + len(names)]):
            pos[n].append(int(v) if isinstance(v, (int, float)) else None)
    # armies moved to ComLocArchive (same rows as ComLoc) when they left play
    archived = set()
    arch = list(wb["ComLocArchive"].iter_rows(values_only=True))
    for j, n in enumerate(arch[0]):
        n = str(n).strip() if n else None
        if not n or n in pos:
            continue
        col = [arch[1 + i][j] if 1 + i < len(arch) and j < len(arch[1 + i]) else None for i in range(len(dates))]
        pos[n] = [int(v) if isinstance(v, (int, float)) else None for v in col]
        names.append(n)
        archived.add(n)
    dtab = {iso(r[0]): (r[1], r[2]) for r in list(wb["DateTable"].iter_rows(values_only=True))[1:] if r and r[0]}
    days = [dict(date=d, ig=(dtab.get(d) or (None,))[0], season=(dtab.get(d) or (None, None))[1]) for d in dates]

    com = list(wb["Commanders"].iter_rows(values_only=True))
    cnames = [str(c).strip() if c else None for c in com[0]]
    label_rows = {str(r[0]).strip(): r for r in com if r and r[0]}
    numbers_at = next(i for i, r in enumerate(com) if r and r[0] == "Numbers")
    units = [str(r[0]).strip() for r in com[numbers_at + 1:numbers_at + 8]]
    info = {}
    for j, n in enumerate(cnames):
        if not n or j == 0:
            continue
        g = lambda lab: (label_rows.get(lab) or [None] * (j + 1))[j]
        troops = {u: round(float(com[numbers_at + 1 + k][j] or 0)) for k, u in enumerate(units)}
        info[n] = dict(traits=[t for t in (g("Trait 1"), g("Trait 2"), g("Trait 3")) if t],
                       tradition=g("Army Tradition"), troops={k: v for k, v in troops.items() if v},
                       morale=g("Current Morale"), speed=g("Speed (Miles/Day)"),
                       supplies=round(float(g("Current Supplies") or 0)), coin=round(float(g("Current Coin") or 0)),
                       wagons=round(float(g("Wagons") or 0)), noncombatants=round(float(g("Noncombatants") or 0)),
                       length=round(float(g("Army Length (Miles)") or 0), 2), upkeep=round(float(g("Daily Supply Consumption") or 0)))

    events = []
    year = int(dates[0][:4])
    first_seen, raised_on, ledger = {}, {}, {}
    # the ledger's money and supplies, summed per commander for the leaderboard
    BOOKS = [("foraged", "supplies", 1, r"forag"), ("taxes", "coin", 1, r"tax"),
             ("loot", "coin", 1, r"loot|sack|pillag|ransom|plunder"), ("loot_supplies", "supplies", 1, r"loot|sack|pillag"),
             ("training", "coin", -1, r"train|recruit"), ("wages", "coin", -1, r"payday|payment|salary|wage|mercenary"),
             ("bought", "supplies", 1, r"purchase|buying"), ("operations", None, 1, r"operation")]
    books = {}
    upkeep_days = {}
    ledger_rows = list(wb["ComEvents"].iter_rows(values_only=True))[1:] + list(wb["ComDaily"].iter_rows(values_only=True))[1:]
    for r in ledger_rows:
        if not r or not r[0] or not isinstance(r[1], dt.datetime) or len(r) < 6:
            continue
        who, note = str(r[0]).strip(), str(r[5] or "").strip()
        sup = r[2] if isinstance(r[2], (int, float)) else 0.0
        coin = r[3] if isinstance(r[3], (int, float)) else 0.0
        b = books.setdefault(who, {k: 0.0 for k, *_ in BOOKS})
        if re.match(r"supply consumption", note, re.I) and sup < 0:
            d = iso(r[1].replace(year=year))
            upkeep_days.setdefault(who, {})[d] = upkeep_days.get(who, {}).get(d, 0.0) - sup
            continue
        for key, what, sign, pat in BOOKS:
            if re.search(pat, note, re.I):
                if what is None:
                    b[key] += 1
                else:
                    v = sup if what == "supplies" else coin
                    if v * sign > 0:
                        b[key] += v * sign
                break
    for r in list(wb["ComEvents"].iter_rows(values_only=True))[1:]:
        if not r or not r[0] or not isinstance(r[1], dt.datetime):
            continue
        who, when = str(r[0]).strip(), r[1]
        if when.year != year:                       # a year typo in the ledger (2206 for 2026)
            when = when.replace(year=year)
        first_seen[who] = min(first_seen.get(who, iso(when)), iso(when))
        ledger.setdefault(who, []).append(iso(when))
        if r[5] and re.search(r"new (sub)?commander|army spawn", str(r[5]), re.I):
            raised_on.setdefault(who, iso(when))
        if not r[5]:
            continue
        note = str(r[5]).strip()
        kind = next((k for k, pat in EVENT_KINDS if re.search(pat, note, re.I)), None)
        if kind is None:
            continue
        events.append(dict(army=str(r[0]).strip(), date=iso(r[1]), kind=kind, note=note,
                           morale=r[4] if isinstance(r[4], (int, float)) else None))

    hexes, hex_region, economy_max, stronghold = {}, {}, {}, set()
    for r in list(wb["Hex"].iter_rows(values_only=True))[2:]:
        if r[0] is None:
            continue
        h = int(r[0])
        row, col = int(r[20]), int(r[21])
        assert h == (row - 1) * NCOL + col, (h, row, col)
        terrain = r[5]
        if r[4]:
            hex_region[h] = str(r[4]).strip()
        if terrain in (None, "N/A", "Ocean", "Sea"):
            continue
        if r[6] == "Yes":
            stronghold.add(h)
        if isinstance(r[11], (int, float)) and isinstance(r[13], (int, float)) and r[11] * r[13] > 0:
            economy_max[h] = [r[11], r[13]]                  # settlement level, wealth base
        hexes[h] = [r[2] if r[2] not in (None, "N/A") else "", r[3] if r[3] not in (None, "N/A") else "",
                    r[4] or "", terrain, r[11] or 0]
    towns = []
    for r in list(wb["TownsCities"].iter_rows(values_only=True))[1:]:
        if r and isinstance(r[0], (int, float)) and r[1]:
            towns.append([int(r[0]), str(r[1]).strip(), r[2] or "", r[6] or ""])
    # Framanders (sub-commanders) ride in their Sakar's ComLoc column until
    # they are raised. An army whose ledger starts after the campaign does is
    # raised on its "New subcommander" ("New commander", "Army spawn") entry,
    # or, when it shadows another army from the first day, on its first
    # ledger entry. Its parent is the army it rode with. Everyone else is
    # there from the start.
    day_of = {d: i for i, d in enumerate(dates)}

    def shared_start(a, b):                         # days two columns agree from the first
        return sum(1 for _ in itertools.takewhile(lambda hh: hh[0] is not None and hh[0] == hh[1], zip(a, b)))

    raised, parent = {}, {}
    for n in names:
        if first_seen.get(n, dates[0]) <= dates[0]:
            continue
        shadow = max(shared_start(pos[n], pos[m]) for m in names if m != n)
        when = raised_on.get(n) or (first_seen[n] if shadow >= 3 else None)
        if when:
            raised[n] = day_of.get(when, len(dates) - 1)
    for n, d in raised.items():
        older = [m for m in names if m != n and raised.get(m, -1) < d]
        k, m = max((shared_start(pos[n], pos[m]), m) for m in older)
        if k >= min(3, d):
            parent[n] = m
    # Commanders keep a daily ledger (supply consumption at the least); when
    # it stops well before the sheet does, the commander has left the
    # campaign (retired, died, disbanded) and their ComLoc column just stands
    # still. "Destroyed" or "Disbanding" entries do not end a commander: they
    # rebuild. A rumour naming them near that day says what happened.
    sheet_end = min(max(max(v) for v in ledger.values()), dates[-1])
    rumours = [(iso(r[1]), str(r[0]).strip()) for r in list(wb["Rumours"].iter_rows(values_only=True))[1:]
               if r and r[0] and isinstance(r[1], dt.datetime)]
    fold = lambda x: unicodedata.normalize("NFKD", x).encode("ascii", "ignore").decode().lower()
    ended, fate = {}, {}
    for n in names:
        days_n = ledger.get(n, [])
        last = max(days_n) if days_n else None
        if len(days_n) < 20 or last > shift(sheet_end, -5):
            continue
        ended[n] = day_of.get(last, len(dates) - 1)
    for n in archived:                                  # archived columns stop being filled
        filled = [i for i, v in enumerate(pos[n]) if v is not None]
        if filled and filled[-1] < len(dates) - 1:
            ended[n] = min(ended.get(n, filled[-1]), filled[-1])
    fate_words = re.compile(r"died|dead|death|killed|slain|execut|disband|retire|fallen ill|fell ill|relieved|"
                            r"captured|lost (his|her|their) life|passed away|assassinat", re.I)
    for n, d in ended.items():
        last, key = dates[d], fold(n)
        for when, text in rumours:                     # news travels: look up to three weeks on
            if not shift(last, -3) <= when <= shift(last, 21):
                continue
            para = next((q.strip("# ").strip() for q in text.split("\n")
                         if key in fold(q) and fate_words.search(q)), None)
            if para:
                fate[n] = dict(date=when, text=para[:900])
                break
    grid = json.loads((ROOT / "data" / "hexgrid.json").read_text())

    # detachments under each commander now (and how many are mercenaries)
    detachments = {}
    for r in list(wb["Detachments"].iter_rows(values_only=True))[1:]:
        if r and r[0] and r[1] and r[2] != "Wagons":
            d = detachments.setdefault(str(r[1]).strip(), [0, 0])
            d[0] += 1
            d[1] += bool(r[4])

    # Weather: one state per region per day
    wl = list(wb["WeatherLog"].iter_rows(values_only=True))
    regions = [str(c).strip() for c in wl[0][2:] if c]
    wdays = {iso(r[0]): r for r in wl[1:] if r and isinstance(r[0], dt.datetime)}
    states = []
    weather = []
    for d in dates:
        r = wdays.get(d)
        row = []
        for k in range(len(regions)):
            v = str(r[2 + k]).strip() if r and 2 + k < len(r) and r[2 + k] else None
            if v and v not in states:
                states.append(v)
            row.append(states.index(v) if v else -1)
        weather.append(row)
    reg_index = {n: i for i, n in enumerate(regions)}
    hexreg = [reg_index.get(hex_region.get(h), -1) for h in range(1, NCOL * NROW + 1)]

    # The hexes' economy: HexArchive (past seasons) and HexEvents (this one)
    # log changes to settlement level, wealth base and wealth surplus (a
    # share of the full surplus, 1000 x settlement x base coin) and how often
    # a hex was recruited, foraged or taxed. A hex's state resets each season.
    econ = []
    for sheet in ("HexArchive", "HexEvents"):
        for r in list(wb[sheet].iter_rows(values_only=True))[1:]:
            if not r or not r[0] or not isinstance(r[1], dt.datetime) or iso(r[1]) not in day_of:
                continue
            v = [float(r[2 + k]) if 2 + k < len(r) and isinstance(r[2 + k], (int, float)) else 0.0 for k in range(6)]
            if any(v):
                econ.append([int(r[0]), day_of[iso(r[1])]] + [round(x, 3) for x in v])
    econ.sort(key=lambda e: e[1])
    season_start = [i for i, d in enumerate(days) if i == 0 or d["season"] != days[i - 1]["season"]]
    # the sheet's own reset: HexEvents holds the current season from its first day
    cur = [day_of[iso(r[1])] for r in list(wb["HexEvents"].iter_rows(values_only=True))[1:]
           if r and r[0] and isinstance(r[1], dt.datetime) and iso(r[1]) in day_of]
    if cur:
        near = min(season_start, key=lambda i: abs(i - min(cur)))
        if abs(near - min(cur)) <= 2:
            season_start[season_start.index(near)] = min(cur)

    # Strongholds: armies stand at the drawn town marker, not the hex centre
    rs = np.array(Image.open(ROOT / "data" / "source" / "original" / "roads_settlements.png").convert("RGBA"))
    road = (rs[..., 0] > 200) & (rs[..., 1] > 80) & (rs[..., 1] < 140) & (rs[..., 2] < 60)
    marks = (rs[..., 3] > 128) & ~road
    lab, n_lab = ndi.label(marks)
    scale = 2000.0 / rs.shape[1]                       # original pixels -> map coordinates
    centres = ndi.center_of_mass(marks, lab, range(1, n_lab + 1))
    sizes = ndi.sum(marks, lab, range(1, n_lab + 1))
    R = grid["dx"] / np.sqrt(3)
    anchors = {}
    for (cy, cx), size in zip(centres, sizes):
        x, y = (cx + 0.5) * scale, (cy + 0.5) * scale
        row = int(round((y - grid["y0"]) / grid["dy"]))
        best = None
        for rr in (row - 1, row, row + 1):
            col = int(round((x - grid["x0"]) / grid["dx"] - 0.5 * (rr % 2)))
            for cc in (col - 1, col, col + 1):
                hx, hy = grid["x0"] + grid["dx"] * (cc + 0.5 * (rr % 2)), grid["y0"] + grid["dy"] * rr
                d = np.hypot(hx - x, hy - y)
                if best is None or d < best[0]:
                    best = (d, rr * NCOL + cc + 1)
        h = best[1]
        if best[0] < R and (h in stronghold or any(t[0] == h for t in towns)):
            if h not in anchors or size > anchors[h][2]:
                anchors[h] = [round(x, 1), round(y, 1), float(size)]
    anchors = {h: v[:2] for h, v in anchors.items()}

    data = dict(days=days, armies=[dict(name=n, hex=pos[n], info=info.get(n), raised=raised.get(n),
                                        parent=parent.get(n), ended=ended.get(n), fate=fate.get(n),
                                        archived=n in archived,
                                        books={k: round(v) for k, v in books.get(n, {}).items()},
                                        upkeep=[round(upkeep_days.get(n, {}).get(d, 0)) or None for d in dates],
                                        detachments=detachments.get(n))
                                   for n in names],
                events=events, hexes=hexes, towns=towns, anchors=anchors,
                weather=dict(regions=regions, states=states, days=weather, hexreg=hexreg),
                economy=dict(max=economy_max, events=econ, season_start=season_start),
                grid=dict(ncol=NCOL, x0=grid["x0"], dx=grid["dx"], y0=grid["y0"], dy=grid["dy"], width=2000, height=926),
                source=Path(xlsx).name)
    Path(out).write_text(json.dumps(data, ensure_ascii=False, separators=(",", ":")))
    kinds = {}
    for e in events:
        kinds[e["kind"]] = kinds.get(e["kind"], 0) + 1
    print(f"{len(names)} armies x {len(dates)} days ({dates[0]} .. {dates[-1]}), {len(events)} events {kinds}, "
          f"{len(hexes)} land hexes, {len(towns)} towns; {Path(out).stat().st_size / 1024:.0f} KB")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
