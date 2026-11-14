"""Post-hoc exploratory diagnostic (not declared): where eastern cities stay short in the Frier-level supply run
(scripts/supply_people_level.py, floodplain production) at 270 km and the west's 95% share."""
import json, sys
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parents[1]; sys.path[:0] = [str(ROOT), str(ROOT / 'scripts')]
import supply_people_level as PL
from settlement_locations_earth import write

FS, SH, ES, S = PL.FS, PL.SH, PL.ES, PL.S
BOXES = {'Egypt': (29, 32.6, 22, 32), 'Levant': (32.6, 37.5, 29, 37), 'Syria-Mesopotamia': (37.5, 50, 30, 38), 'Asia Minor': (26, 45, 36, 42.5),
         'Greece and Aegean': (19, 26, 34.5, 42.5), 'Balkans and Danube': (15, 30, 42.5, 48.5), 'Cyrenaica': (19, 29, 29, 34)}


def main():
    ES.memoise(); S.HARVEST = FS.GRID; fields = S.earth_fields
    def with_basin(lat, lon):
        wheat, barley, arable, inside = fields(lat, lon); sb, W = FS.basin_on_pool(lat, lon); boost = W * FS.F_B / (S.FARMED * S.SOWN)
        return (1 - sb) * wheat + sb * boost, (1 - sb) * barley + sb * boost, arable, inside
    S.earth_fields = with_basin
    x = dict(np.load(S.PILOT.POOL)); land = x['land']; cell = float(x['cell_km']) ** 2
    p2 = np.where(land, SH.capacity(x['lat'], x['lon']) * x['history'], 0.0); allowed = land & x['allowed']
    x['density'] = p2 * PL.FRIER / float((p2[allowed] * cell).sum())
    a, meta = S.prepare(x); res = a['residents']; west = a['lon'] <= np.median(a['lon']); width = land.shape[1]
    r = json.loads((ROOT / 'output/supply_people_level_20261114/results.json').read_text())['variants']['frier']['surface']['270']
    e = r['west']['e95']; fed = S.fed_surface(a, [e], [270])[0, 0]
    rr, cc = np.divmod(a['nodes'], width); lat, lon = x['lat'][rr, cc], x['lon'][rr, cc]
    out = dict(status='post_hoc_exploratory_diagnostic', share=e, haul_km=270, east_fed=float(fed[~west].sum() / res[~west].sum()), west_fed=float(fed[west].sum() / res[west].sum()),
               east_west_boundary_lon=float(np.median(a['lon'])), regions={})
    for name, (lo0, lo1, la0, la1) in BOXES.items():
        m = (~west) & (lon >= lo0) & (lon < lo1) & (lat >= la0) & (lat < la1)
        if m.any(): out['regions'][name] = dict(cities=int(m.sum()), residents=float(res[m].sum()), fed_share=float(fed[m].sum() / res[m].sum()), shortfall=float((res - fed)[m].sum()))
    short = np.argsort(-(res - fed) * (~west))[:12]
    out['largest_eastern_shortfalls'] = [dict(lat=float(lat[i]), lon=float(lon[i]), residents=float(res[i]), fed_share=float(fed[i] / res[i])) for i in short]
    write(ROOT / 'output/supply_people_level_20261114/east_gap_diagnostic.json', out)
    print(json.dumps({k: v for k, v in out.items() if k != 'largest_eastern_shortfalls'}, indent=1))
    for c in out['largest_eastern_shortfalls']: print(c)


if __name__ == '__main__':
    main()
