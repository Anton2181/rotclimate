"""Assemble the land-and-people viewer's files.

Each layer of output/land_people/land_people.npz is written as an 8-bit grey
image (0 = sea, 1-255 the value on the layer's scale) that the page colours;
the base is the summer orbital view, greyed, to give the layers relief; the
rivers are drawn on top in their two classes. Per hex: the layer means, the
land area and the people it could feed, with the campaign sheet's own
commandery, province, settlement level and wealth base; per province the
totals. The Earth check (output/land_people/earth/regions.json) and the
sheet check (sheet_check.json) ride along for the notes.

    python -I scripts/build_land_page.py output/land_people land
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from land_people_hexes import hex_index  # noqa: E402

MAP_KM = 3680.0
# key, title, unit, scale (log / lin / cat), lo, hi, ramp, note
LAYERS = [
    ("capacity", "People the land could feed", "per km²", "log", 1.0, 1000.0, "people",
     "Calories per hectare × arable share × 60 % of it in fields × the share sown in a year "
     "(68 %, fitted to the Han census; all of it where a second crop fits) ÷ 1.1 million kcal a "
     "person needs a year. A ceiling, not a census."),
    ("main_crop", "Staple crop", "", "cat", 0, 0, "crops",
     "The crop (or crop pair) that gives the most calories after seed; hatched where a second crop "
     "fits in the months the first leaves free. Where both grow, barley and millet feed about as "
     "many (millet is within 5 % on over a quarter of the land); a hex's card lists every crop."),
    ("kcal_ha", "Food per hectare", "million kcal/ha/yr", "lin", 0.0, 8.0, "food",
     "Low-input yields of the period (grain ~1 t/ha, paddy ~1.8 t/ha, dates 3 t/ha), scaled by "
     "the season's water balance (FAO-33), net of seed."),
    ("lgp_days", "Growing season", "days", "lin", 0.0, 365.0, "season",
     "FAO length of growing period: months at or above 5 °C with rain plus soil water at least half "
     "the potential evaporation (Thornthwaite, 100 mm soil)."),
    ("npp", "Wild productivity", "g dry matter/m²/yr", "lin", 0.0, 3000.0, "npp",
     "Net primary productivity, Miami model (Lieth 1975): the lesser of the temperature and rain limits."),
    ("aridity", "Rain against evaporation", "P / PET", "lin", 0.0, 3.0, "water",
     "Annual rain over Thornthwaite potential evaporation: under 0.2 desert, 0.2-0.5 steppe, "
     "0.5-1 dry farming, over 1 humid."),
    ("irr", "Irrigation reach", "share of land", "lin", 0.0, 1.0, "irr",
     "Land watered from the rivers: exp(-d/6 km) from the navigable rivers, 0.6 exp(-d/2.5 km) "
     "from streams."),
    ("malaria", "Malaria climate", "0-1", "lin", 0.0, 1.0, "malaria",
     "MARA climatic suitability (Craig et al. 1999): five months running at 22-32 °C with 80 mm "
     "of rain or more (fuzzy edges)."),
]
PEOPLE_RAMP = ["#f4ecc4", "#e8c46a", "#d38a3a", "#ad4a2f", "#6e2238", "#2f1638"]      # as the page's
CROP_CLASSES = ["Wheat & barley", "Foxtail millet", "Paddy rice", "Date palm", "Nothing grows"]


def quantise(v, kind, lo, hi):
    v = np.asarray(v, float)
    if kind == "log":
        t = (np.log10(np.clip(v, lo, hi)) - np.log10(lo)) / (np.log10(hi) - np.log10(lo))
    else:
        t = (np.clip(v, lo, hi) - lo) / (hi - lo)
    q = 1 + np.round(np.nan_to_num(t) * 254)
    return np.where(np.isfinite(v), q, 0).astype(np.uint8)


def crop_codes(z, names):
    mc = z["main_crop"].astype(int)
    cls = {"wheat": 1, "barley": 1, "millet": 2, "rice": 3, "dates": 4}
    code = np.zeros(mc.shape, np.uint8)
    for i, n in enumerate(names):
        code[mc == i] = cls[n]
    code[(mc == -1)] = 5
    code[z["double_crop"] & (code > 0) & (code < 5)] += 8
    code[~z["land"]] = 0
    return code


def main(src, dst):
    src, dst = Path(src), Path(dst)
    (dst / "layers").mkdir(parents=True, exist_ok=True)
    z = dict(np.load(src / "land_people.npz"))
    summ = json.loads((src / "summary.json").read_text())
    names = summ["crops"]
    land = z["land"]
    h, w = land.shape
    div = int(z["div"])
    for key, title, unit, kind, lo, hi, ramp, note in LAYERS:
        v = z[key] / 1e6 if key == "kcal_ha" else z[key]               # shown in million kcal
        q = crop_codes(z, names) if kind == "cat" else quantise(np.where(land, v, np.nan), kind, lo, hi)
        Image.fromarray(q).save(dst / "layers" / f"{key}.png", optimize=True)
    # base: the summer orbital view, greyed and lifted so colours read over it
    sat = Image.open(ROOT / "satellite" / "summer.webp").convert("L")
    W2, H2 = w * 2, h * 2
    sat = np.asarray(sat.crop((0, 0, w * div, h * div)).resize((W2, H2), Image.LANCZOS), np.float32) / 255.0
    land2 = np.asarray(Image.fromarray(land.astype(np.uint8) * 255).resize((W2, H2), Image.BILINEAR)) > 127
    lum = np.clip(sat / np.percentile(sat[land2], 97), 0, 1)
    grey = 0.6 + 0.4 * lum ** 0.8
    sea = np.array([22, 34, 46]) / 255.0 + 0.25 * lum[..., None]
    base = np.where(land2[..., None], grey[..., None], sea)
    Image.fromarray((np.clip(base, 0, 1) * 255).astype(np.uint8)).save(dst / "base.webp", quality=84, method=4)
    # rivers in their two classes (drawing resolution, then halved)
    from render_satellite import original_terrain
    from vector_rivers import river_alpha
    rivers = original_terrain()[3]
    a, _ = river_alpha(rivers, 1)
    a = np.asarray(Image.fromarray((a * 255).astype(np.uint8)).crop((0, 0, w * div, h * div))
                   .resize((W2, H2), Image.LANCZOS))
    rgba = np.zeros((H2, W2, 4), np.uint8)
    rgba[..., :3] = (38, 92, 150)
    rgba[..., 3] = np.clip(a.astype(float) * 1.6, 0, 255).astype(np.uint8)
    Image.fromarray(rgba, "RGBA").save(dst / "rivers.webp", quality=90, lossless=False, method=4)
    # per hex
    grid = json.loads((ROOT / "data" / "hexgrid.json").read_text())
    idx = hex_index(land.shape, div, grid)
    cell_km2 = (MAP_KM / 4401 * div) ** 2
    data = json.loads((ROOT / "ravages" / "data.json").read_text())
    emax = data["economy"]["max"]
    codes = crop_codes(z, names) % 8
    vals = ["capacity", "kcal_ha", "lgp_days", "npp", "irr", "malaria", "aridity"]
    hexes, prov = {}, {}
    lh = idx[land]
    n = np.bincount(lh, minlength=idx.max() + 1)
    sums = {k: np.bincount(lh, np.nan_to_num(z[k][land].astype(float)), minlength=n.size) for k in vals}
    grains = {"wb": np.maximum(z["kcal_wheat"], z["kcal_barley"]), "millet": z["kcal_millet"],
              "rice": z["kcal_rice"], "dates": z["kcal_dates"]}
    gsum = {k: np.bincount(lh, np.nan_to_num(v[land].astype(float)), minlength=n.size) for k, v in grains.items()}
    crop_n = np.array([np.bincount(lh, codes[land] == c, minlength=n.size) for c in range(1, 6)])
    for hx in np.nonzero(n)[0]:
        rec = data["hexes"].get(str(hx), ["", "", "", "", 0])
        area = n[hx] * cell_km2
        mean = {k: sums[k][hx] / n[hx] for k in vals}
        people = mean["capacity"] * area
        lvl, base_w = emax.get(str(hx), [0, 0])
        hexes[int(hx)] = [round(mean["capacity"], 1), round(mean["kcal_ha"] / 1e6, 2), round(mean["lgp_days"]),
                          round(mean["npp"]), round(mean["irr"], 3), round(mean["malaria"], 2), round(mean["aridity"], 2),
                          round(area), round(people), int(np.argmax(crop_n[:, hx])),
                          rec[0], rec[1], rec[2], rec[3], lvl, base_w,
                          [round(gsum[k][hx] / n[hx] / 1e6, 2) for k in grains]]
        name = rec[1] or ""
        if name:
            p = prov.setdefault(name, dict(name=name, hexes=[], area=0.0, people=0.0, crops=np.zeros(5),
                                           lvl=[], wealth=[]))
            p["hexes"].append(int(hx))
            p["area"] += area
            p["people"] += people
            p["crops"] += crop_n[:, hx]
            if lvl:
                p["lvl"].append(lvl)
                p["wealth"].append(base_w)
    provinces = sorted(({"name": p["name"], "hexes": p["hexes"], "area": round(p["area"]), "people": round(p["people"]),
                         "density": round(p["people"] / max(p["area"], 1), 1),
                         "crops": [round(float(c), 3) for c in p["crops"] / max(p["crops"].sum(), 1)],
                         "settlement": round(float(np.mean(p["lvl"])), 1) if p["lvl"] else None,
                         "wealth": round(float(np.mean(p["wealth"])), 1) if p["wealth"] else None}
                        for p in prov.values()), key=lambda r: -r["people"])
    # the same rules on Earth, in the people ramp of the page
    ez = src / "earth" / "earth.npz"
    if ez.exists():
        e = np.load(ez)
        q = quantise(np.where(e["land"], e["capacity"], np.nan), "log", 1.0, 1000.0).astype(int)
        stops = np.array([[int(c[i:i + 2], 16) for i in (1, 3, 5)] for c in PEOPLE_RAMP], float)
        t = np.clip((q - 1) / 254.0, 0, 1) * (len(stops) - 1)
        i0 = np.minimum(t.astype(int), len(stops) - 2)
        rgb = stops[i0] + (stops[i0 + 1] - stops[i0]) * (t - i0)[..., None]
        rgb[q == 0] = (26, 37, 48)
        im = Image.fromarray(rgb.astype(np.uint8))
        im.resize((im.width * 2 // 3, im.height * 2 // 3), Image.LANCZOS).save(dst / "earth.webp", quality=86, method=4)
    sat_meta = json.loads((ROOT / "satellite" / "meta.json").read_text())
    places = [dict(p, x=round(p["x"] / 2, 1), y=round(p["y"] / 2, 1)) for p in sat_meta["places"]]
    s = W2 / 2000.0 * (4401 / (w * div))
    earth = src / "earth" / "regions.json"
    check = src / "sheet_check.json"
    meta = dict(width=W2, height=H2, grid=dict(w=w, h=h, cell_km2=round(cell_km2, 3)),
                hexgrid=dict(ncol=grid["ncol"], x0=grid["x0"] * s, dx=grid["dx"] * s, y0=grid["y0"] * s, dy=grid["dy"] * s),
                layers=[dict(key=k, title=t, unit=u, kind=kd, lo=lo, hi=hi, ramp=r, note=nt)
                        for k, t, u, kd, lo, hi, r, nt in LAYERS],
                crop_classes=CROP_CLASSES,
                hex_fields=["capacity", "kcal_ha", "lgp_days", "npp", "irr", "malaria", "aridity", "area", "people",
                            "crop", "commandery", "province", "region", "terrain", "settlement", "wealth", "crop_kcal"],
                hexes=hexes, provinces=provinces, places=places,
                summary=dict(people=summ["capacity_people"], land_km2=summ["land_km2"],
                             density=summ["mean_capacity_per_km2"], double=summ["double_crop_share"],
                             crops={c: round(float(np.mean(codes[land] == i + 1)), 3) for i, c in enumerate(CROP_CLASSES)}),
                world=sat_meta.get("world"),
                earth=json.loads(earth.read_text()) if earth.exists() else None,
                check=json.loads(check.read_text()) if check.exists() else None)
    (dst / "meta.json").write_text(json.dumps(meta, ensure_ascii=False, separators=(",", ":")))
    print(f"{dst}: {len(hexes)} hexes, {len(provinces)} provinces, {meta['summary']['people'] / 1e6:.0f} M people")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
