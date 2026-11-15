"""Reba/Modelski large-city blind test (calibration/reba_cities_blind_20261115/plan.json)."""
import argparse, csv, json, subprocess, sys
from pathlib import Path
import numpy as np
from scipy import ndimage as ndi
from scipy.stats import spearmanr

ROOT = Path(__file__).resolve().parents[1]; sys.path[:0] = [str(ROOT), str(ROOT / 'scripts')]
from polity import earth as E
from polity.settlement_locations import site_fields
from polity.survey_transfer import relative_ranks, sphere_distance
from rotclimate.earth import forward
from settlement_locations_earth import sha, write
import polity_earth_check as P

PLAN = ROOT / 'calibration/reba_cities_blind_20261115/plan.json'; OUT = ROOT / 'output/reba_cities_blind_20261115'; CACHE = ROOT / 'data/cache/reba_2016'
CELL, SIDE = 9.0, 600.0


def table(name, column):
    rows = []
    with open(CACHE / name, encoding='utf-8', errors='replace') as h:
        for r in csv.DictReader(h):
            try: pop = float(r[column]); lat = float(r['Latitude']); lon = float(r['Longitude'])
            except (ValueError, TypeError, KeyError): continue
            if pop > 0: rows.append(dict(city=r['City'], country=r['Country'], certainty=r.get('Certainty'), lat=lat, lon=lon, pop=pop))
    return rows


def main(out):
    if subprocess.check_output(['git', 'show', 'HEAD:' + str(PLAN.relative_to(ROOT))], cwd=ROOT) != PLAN.read_bytes():
        raise ValueError('Commit the exact declaration first')
    out.mkdir(parents=True, exist_ok=True)
    from rotclimate.earth import _wc
    from population_cores import travel_distance, CORE_SETS
    from settlement_model_earth import sample_earth
    with np.load(ROOT / 'output/land_people/earth/earth.npz') as a: gf = dict(a)
    distance = travel_distance(gf, CORE_SETS['cradles + Rome'], forest_cost=2., sea_cost=1., relief_cost=1.); elevation = _wc('elev')
    finite = np.isfinite(elevation); filled = np.nan_to_num(elevation)
    rome = E.cliopatria('Roman Empire', 150); hw = P.WINDOWS['han']
    def excluded(lat, lon):
        if not (0 <= lat <= 56 and -12 <= lon <= 125): return 'outside_window'
        if E.inside_polygons(dict(lat=np.array([[lat]]), lon=np.array([[lon]])), rome)[0, 0]: return 'roman_empire_150'
        x, y = forward(np.array([lat]), np.array([lon]), hw['lat0'], hw['lon0'])
        if abs(x[0]) <= hw['width_km'] / 2 and abs(y[0]) <= hw['height_km'] / 2: return 'han_window'
        return None
    primary = table('modelskiAncientV2.csv', 'AD_200'); secondary = table('chandlerV2.csv', 'AD_100')
    secondary = [s for s in secondary if not any(sphere_distance(s['lat'], s['lon'], p['lat'], p['lon']) <= 25 for p in primary)]
    cohorts = {}
    for label, rows in (('modelski_ad200', primary), ('chandler_ad100_extra', secondary)):
        kept, dropped = [], {}
        for r in rows:
            why = excluded(r['lat'], r['lon'])
            if why: dropped[why] = dropped.get(why, 0) + 1; continue
            g = E.grid(r['lat'], r['lon'], SIDE, SIDE, CELL); lat, lon = g['lat'], g['lon']
            land = E.sample_global(finite.astype(np.uint8), lat, lon).astype(bool); elev = E.sample_global(filled, lat, lon, order=1)
            density, herders, covered = E.earth_people(lat, lon); river = E.rivers(g) & land; water = ndi.distance_transform_edt(~river) * CELL
            aridity = sample_earth(gf['aridity'], lat, lon); d = sample_earth(distance, lat, lon)
            args = dict(density=density * land, land=land, water_km=water, road=np.zeros(land.shape, bool), elev=np.where(land, elev, 0.),
                        aridity=aridity, allowed=land.copy(), cell_km=CELL)
            score, eligible = site_fields(**args); hist = np.exp(-d / 800.)
            fields = {'environment': np.where(eligible, score, 0.), 'release3': np.where(eligible, score * hist, 0.)}
            cy, cx = land.shape[0] // 2, land.shape[1] // 2
            if not land[cy, cx]:
                dist, (iy, ix) = ndi.distance_transform_edt(~land, return_indices=True)
                if dist[cy, cx] * CELL > 9.0: dropped['no_land_within_9km'] = dropped.get('no_land_within_9km', 0) + 1; continue
                cy, cx = iy[cy, cx], ix[cy, cx]
            yy, xx = np.mgrid[:land.shape[0], :land.shape[1]]; near = land & (np.hypot(yy - cy, xx - cx) * CELL <= 50)
            kept.append(dict(city=r['city'], country=r['country'], certainty=r['certainty'], lat=r['lat'], lon=r['lon'], pop=r['pop'],
                             percentile={k: float(relative_ranks([f[cy, cx]], f[land])[0]) for k, f in fields.items()},
                             people_within_50km=float((density * land * CELL ** 2)[near].sum())))
        pr = [k['percentile']['release3'] for k in kept]; pe = [k['percentile']['environment'] for k in kept]
        rho = spearmanr([k['pop'] for k in kept], [k['people_within_50km'] for k in kept]).statistic if len(kept) >= 3 else None
        cohorts[label] = dict(cities=len(kept), dropped=dropped, mean_percentile_release3=float(np.mean(pr)) if pr else None,
                              mean_percentile_environment=float(np.mean(pe)) if pe else None, share_above_half_release3=float(np.mean(np.array(pr) > .5)) if pr else None,
                              spearman_pop_vs_people_50km=None if rho is None else float(rho), rows=kept)
        print(label, {k: v for k, v in cohorts[label].items() if k != 'rows'}, flush=True)
    m = cohorts['modelski_ad200']; scored = m['cities'] >= 10
    write(out / 'results.json', dict(status='reba_cities_blind_test', plan_sha256=sha(PLAN), producer_sha256=sha(Path(__file__)),
        sources={n: sha(CACHE / n) for n in ('modelskiAncientV2.csv', 'chandlerV2.csv')}, cliopatria_subset_sha256=sha(ROOT / 'data/cache/cliopatria/geo/subset_ad2_117_150.json'),
        scored=scored, test_P_pass=bool(scored and m['mean_percentile_release3'] >= 0.70), cohorts=cohorts))


if __name__ == '__main__':
    ap = argparse.ArgumentParser(); ap.add_argument('--out', type=Path, default=OUT); main(ap.parse_args().out)
