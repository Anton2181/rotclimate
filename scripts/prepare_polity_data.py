"""Rebuild the Earth inputs of the political-reach checks in data/cache (not committed).

    python -I scripts/prepare_polity_data.py --cliopatria /home/user/seshat-global-history-databank/cliopatria

Downloads (each into its own folder; sources and hashes in data/cache/polity_sources.json):
  itinere/itinere_roads.gpkg   Itiner-e static 2024 (de Soto et al. 2025, Zenodo 10.5281/zenodo.17122148)
  hanson2016/cities.xlsx        Hanson (2016) OxREP cities database
  han_ad2/                      Zheng & Wu (2026) county-level population of ancient China (figshare 10.6084/m9.figshare.30518417)
Derived here:
  cliopatria/geo/subset_ad2_117_150.json, subset_742_1102_1820.json   from Cliopatria v0.2.1 (Seshat, CC BY 4.0)
  naturalearth_dl/ne_10m_rivers_lake_centerlines.geojson               from the Natural Earth 1:10m shapefile
The NCEP winds are read from data/cache/ncep_ltm (polity.earth._ncep falls back on them).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CACHE = ROOT / "data/cache"


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def cliopatria_subsets(repo):
    z = zipfile.ZipFile(Path(repo) / "cliopatria.geojson.zip")
    name = [n for n in z.namelist() if n.endswith(".geojson")][0]
    d = json.loads(z.read(name))
    out = CACHE / "cliopatria/geo"; out.mkdir(parents=True, exist_ok=True)
    for file, years in (("subset_ad2_117_150.json", (2, 117, 150)), ("subset_742_1102_1820.json", (742, 1102, 1820))):
        polities = []
        for f in d["features"]:
            p = f["properties"]
            present = [y for y in years if p["FromYear"] <= y <= p["ToYear"]]
            if present and f["geometry"]:
                polities.append(dict(name=p["Name"], years=present, from_year=p["FromYear"], to_year=p["ToYear"],
                                     type=p.get("Type"), geometry=f["geometry"]))
        (out / file).write_text(json.dumps(dict(source=f"Cliopatria {name} (Seshat Global History Databank, CC BY 4.0)",
                                                years=list(years), polities=polities)))
        print(file, len(polities), "polity shapes")
    return dict(file=name, zip_sha256=sha(Path(repo) / "cliopatria.geojson.zip"))


def natural_earth_rivers():
    import shapefile
    src = CACHE / "naturalearth/x/ne_10m_rivers_lake_centerlines.shp"
    r = shapefile.Reader(str(src))
    fields = [f[0] for f in r.fields[1:]]
    feats = []
    for shp, rec in zip(r.iterShapes(), r.iterRecords()):
        props = {k.lower(): v for k, v in zip(fields, rec)}
        pts = shp.points; parts = list(shp.parts) + [len(pts)]
        lines = [[list(p) for p in pts[a:b]] for a, b in zip(parts[:-1], parts[1:])]
        feats.append(dict(type="Feature", properties=props,
                          geometry=dict(type="MultiLineString", coordinates=lines) if lines else None))
    out = CACHE / "naturalearth_dl"; out.mkdir(parents=True, exist_ok=True)
    (out / "ne_10m_rivers_lake_centerlines.geojson").write_text(json.dumps(dict(type="FeatureCollection", features=feats)))
    print("Natural Earth rivers", len(feats))
    return dict(shp_sha256=sha(src))


def han_shapefiles():
    archive = CACHE / "han_ad2/han_shapefiles.zip"
    z = zipfile.ZipFile(archive)
    out = CACHE / "han_ad2/shp"; out.mkdir(parents=True, exist_ok=True)
    wanted = ("CountyPointsWithPopulation", "ResearchArea")
    got = []
    for n in z.namelist():
        base = Path(n).name
        if any(base.startswith(w + ".") for w in wanted) and "AD" not in Path(n).parent.name.upper()[:0]:
            (out / base).write_bytes(z.read(n)); got.append(n)
    print("Han shapefile members", got[:12])
    return dict(zip_sha256=sha(archive), members=got)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--cliopatria", type=Path, required=True)
    a = ap.parse_args()
    sources = dict(
        itinere=dict(url="https://zenodo.org/records/17122148", sha256=sha(CACHE / "itinere/itinere_roads.gpkg")),
        hanson2016=dict(url="https://oxrep.web.ox.ac.uk/cities-database", sha256=sha(CACHE / "hanson2016/cities.xlsx")),
        cliopatria=dict(url="https://github.com/Seshat-Global-History-Databank/cliopatria", **cliopatria_subsets(a.cliopatria)),
        naturalearth=dict(url="https://www.naturalearthdata.com/", **natural_earth_rivers()))
    if (CACHE / "han_ad2/han_shapefiles.zip").exists():
        sources["han_ad2"] = dict(url="https://doi.org/10.6084/m9.figshare.30518417", **han_shapefiles())
    (CACHE / "polity_sources.json").write_text(json.dumps(sources, indent=1))


if __name__ == "__main__":
    main()
