"""Wider grain supply for the release-3 towns (declared scenario).

calibration/settlement_wide_supply_20261113/plan.json. Uses the atlas freight
network on release-3 towns and tracks; nothing is fitted.
"""
import argparse, csv, json, sys
from pathlib import Path
import numpy as np
from scipy.sparse.csgraph import dijkstra

ROOT = Path(__file__).resolve().parents[1]; sys.path[:0] = [str(ROOT), str(ROOT / 'scripts')]
from polity import trade as T, wide_supply as W
from harvest.field_support import field_support
from settlement_locations_earth import sha, write

PLAN = ROOT / 'calibration/settlement_wide_supply_20261113/plan.json'
R3 = ROOT / 'output/settlement_release3_20261113'; OUT = ROOT / 'output/settlement_wide_supply_20261113'
KCAL = 2500.0 * 365.0; EXTRACTION = (1.0 / 3.0, 0.10); DENSITY = ('central', 'low'); HOURS = (600.0, 300.0)
HEADLINE = 'central_x33'


def network(mode):
    from polity.administrative_world import audit_world
    r, _ = audit_world(ROOT / 'atlases/earth_fit', mode)
    sites = json.loads((R3 / f'placed_{mode}_sites.json').read_text())['sites']
    width = r['land'].shape[1]; nodes = np.array([s['node'] for s in sites])
    if {t['row'] * width + t['col'] for t in r['towns']} != set(nodes.tolist()):
        raise ValueError('Freight world is not built on the release-3 towns')
    n = r['land'].size; owner = []; share = []; between = np.zeros((len(nodes), len(nodes)))
    lookup = np.full(n, -1, int); lookup[nodes] = np.arange(len(nodes))
    for month in T.TRADE_MONTHS:
        net = T.cost_network(r['world'], r['statics'], r['climate'], month, r['ports'], r['river_places'])
        d, _, src = dijkstra(net.base.T.tocsr(), directed=True, indices=nodes, min_only=True, return_predecessors=True,
                             limit=W.VALUE_LIMIT_ROAD_KM)
        d, src = d[:n], src[:n]; ok = np.isfinite(d) & (src >= 0)
        o = np.full(n, -1, int); o[ok] = lookup[src[ok]]
        owner.append(o); share.append(np.where(o >= 0, W.delivered_share(d), 0.0))
        for s, c in T.costs_from(net, nodes, limit=W.VALUE_LIMIT_ROAD_KM, batch=48):
            between[lookup[s]] += W.delivered_share(c[:, nodes])
    between /= len(T.TRADE_MONTHS); np.fill_diagonal(between, 0.0)
    return r, sites, nodes, np.array(owner), np.array(share), between


def plan_for(grain, need, owner, share, between):
    towns = len(need); delivered, sent = W.hinterland_delivery(owner, share, grain, towns)
    excess = np.maximum(delivered - need, 0.0); deficit = np.maximum(need - delivered, 0.0)
    shipments, received = W.ship(excess, deficit, between)
    exported = np.zeros(towns)
    for (i, _), v in shipments.items():
        exported[i] += v
    fed = np.minimum(delivered, need) + received
    return dict(delivered=delivered, sent=sent, excess=excess, deficit=deficit, exported=exported, received=received,
                fed=fed, shipments=shipments)


def build(mode, out):
    r, sites, nodes, owner, share, between = network(mode)
    f = np.load(R3 / f'placed_{mode}_fields.npz'); x = np.load(ROOT / f'output/settlement_feedback_20261112/{mode}_inputs.npz')
    land = f['land'].ravel(); potential = np.where(land, x['potential_kcal'], 0.0)
    if not np.array_equal(f['land'], r['land']):
        raise ValueError('Land grids differ')
    summary = {}; arrays = dict(owner=owner.astype(np.int32), share=share.astype(np.float32), between=between, nodes=nodes); rows = None
    for density in DENSITY:
        res = f['residents_' + density]; need = res * KCAL; rural = f['rural_' + density].ravel()
        for hours, fraction in [(HOURS[0], e) for e in EXTRACTION] + [(HOURS[1], EXTRACTION[0])]:
            work = field_support(potential, x['listed_hours'], x['reaping_hours'], rural_need_kcal=rural * KCAL, hours_worker_year=hours)
            surplus = np.where(land, np.maximum(work.produced_kcal - rural * KCAL, 0.0), 0.0)
            key = f'{density}_x{int(round(fraction * 100)):02d}' + ('' if hours == HOURS[0] else f'_h{int(hours)}'); grain = surplus * fraction
            p = plan_for(grain, need, owner, share, between); fedshare = np.divide(p['fed'], need, out=np.ones_like(need), where=need > 0)
            self_fed = p['delivered'] >= need * (1 - 1e-9); full = fedshare >= 1 - 1e-6
            ship_sent = float(sum(p['shipments'].values())); ship_got = float(p['received'].sum())
            ledger = dict(available=float(grain.sum()), sent_to_towns=float(p['sent'].sum()), left_in_cells=float(grain.sum() - p['sent'].sum()),
                delivered_to_towns=float(p['delivered'].sum()), hinterland_transport=float(p['sent'].sum() - p['delivered'].sum()),
                eaten_from_hinterland=float(np.minimum(p['delivered'], need).sum()), shipped_between_towns=ship_sent,
                received_between_towns=ship_got, between_town_transport=ship_sent - ship_got,
                unused_excess=float(p['excess'].sum() - ship_sent))
            ledger['residual'] = ledger['available'] - ledger['left_in_cells'] - ledger['hinterland_transport'] - ledger['eaten_from_hinterland'] \
                - ledger['between_town_transport'] - ledger['received_between_towns'] - ledger['unused_excess']
            if abs(ledger['residual']) > 1e-6 * ledger['available']:
                raise ValueError('Grain ledger does not close')
            summary[key] = dict(density=density, extraction=fraction, hours_worker_year=hours, towns=len(need), residents=float(res.sum()),
                produced_person_years=float(work.produced_kcal[land].sum() / KCAL), rural_people=float(rural.sum()),
                marketed_per_rural_person=float(grain.sum() / KCAL / rural.sum()),
                residents_fed=float(p['fed'].sum() / KCAL), fed_share_of_residents=float(p['fed'].sum() / need.sum()),
                self_sufficient_towns=int(self_fed.sum()), fed_with_imports_towns=int((full & ~self_fed).sum()), short_towns=int((~full).sum()),
                residents_in_short_towns=float(res[~full].sum()), shipments=len(p['shipments']),
                exporters=int((p['exported'] > 0).sum()), importers=int((p['received'] > 0).sum()),
                ledger_person_years={k: v / KCAL for k, v in ledger.items()})
            arrays.update({f'{key}_delivered': p['delivered'], f'{key}_received': p['received'], f'{key}_exported': p['exported'],
                f'{key}_fed_share': fedshare,
                f'{key}_shipments': np.array([[i, j, v, v * between[i, j]] for (i, j), v in sorted(p['shipments'].items())]).reshape(-1, 4)})
            if key == HEADLINE:
                rows = []
                for i, s in enumerate(sites):
                    partners = [(j, v) for (a, j), v in p['shipments'].items() if a == i] if p['exported'][i] > 0 else \
                               [(a, v * between[a, i]) for (a, j), v in p['shipments'].items() if j == i]
                    top = max(partners, key=lambda t: t[1])[0] if partners else None
                    rows.append(dict(id=s['id'], name=s['name'], row=s['row'], column=s['column'], marked=bool(s['marked']), actor=s['actor'] or '',
                        residents=round(float(res[i]), 1), hinterland_grain_people=round(float(p['delivered'][i] / KCAL), 1),
                        exported_people=round(float(p['exported'][i] / KCAL), 1), imported_people=round(float(p['received'][i] / KCAL), 1),
                        fed_share=round(float(fedshare[i]), 4),
                        status='self-sufficient' if self_fed[i] else ('fed with imports' if full[i] else 'short'),
                        main_partner=sites[top]['name'] if top is not None else ''))
    target = out / f'supply_{mode}_towns.csv'
    with target.open('w', newline='', encoding='utf-8') as h:
        wr = csv.DictWriter(h, fieldnames=list(rows[0]), lineterminator='\r\n'); wr.writeheader(); wr.writerows(rows)
    np.savez_compressed(out / f'supply_{mode}.npz', **arrays)
    reach = share.max(0) > 0
    return dict(climate=mode, scenarios=summary, land_cells_within_grain_reach=float((reach & land).sum() / land.sum()),
        mean_trading_partners=float((between > 0).sum(1).mean()),
        outputs={p.name: sha(p) for p in (target, out / f'supply_{mode}.npz')})


def run(out):
    import subprocess
    if subprocess.check_output(['git', 'show', 'HEAD:' + str(PLAN.relative_to(ROOT))], cwd=ROOT) != PLAN.read_bytes():
        raise ValueError('Commit the exact declaration first')
    from polity.release3_placement import install
    install(); out.mkdir(parents=True, exist_ok=True)
    result = dict(status='wide_grain_supply_scenario_release3_towns_not_fitted', plan_sha256=sha(PLAN), producer_sha256=sha(__file__),
        model_sha256=sha(ROOT / 'polity/wide_supply.py'), value_limit_road_km=W.VALUE_LIMIT_ROAD_KM, headline=HEADLINE,
        fantasy_sha256=sha(R3 / 'fantasy.json'), climates={m: build(m, out) for m in ('raw', 'corrected')})
    write(out / 'results.json', result); return result


if __name__ == '__main__':
    a = argparse.ArgumentParser(); a.add_argument('--out', type=Path, default=OUT); r = run(a.parse_args().out)
    for m, c in r['climates'].items():
        print(m, round(c['land_cells_within_grain_reach'], 3), round(c['mean_trading_partners'], 1))
        for k, s in c['scenarios'].items():
            L = s['ledger_person_years']
            print(' ', k, 'fed', round(s['fed_share_of_residents'], 3), 'self', s['self_sufficient_towns'], 'imports', s['fed_with_imports_towns'], 'short', s['short_towns'],
                  'avail M', round(L['available'] / 1e6, 2), 'transport M', round((L['hinterland_transport'] + L['between_town_transport']) / 1e6, 2), 'unused M', round(L['unused_excess'] / 1e6, 2), 'left M', round(L['left_in_cells'] / 1e6, 2))
