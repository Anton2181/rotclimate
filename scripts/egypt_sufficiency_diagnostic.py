"""Post-hoc diagnostic (exploratory, not declared): where Egyptian grain fails to reach Egyptian cities in the
Egypt-sufficiency variant YP_2.16 at 270 km and marketed share 0.5. Per-city residents, own-hinterland delivery,
shipments received, and the cheapest network cost from the city to Egyptian surplus land."""
import json, sys
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parents[1]; sys.path[:0] = [str(ROOT), str(ROOT / 'scripts')]
import egypt_sufficiency as ES
S = ES.S; W = S.W
from settlement_locations_earth import write


def main():
    ES.memoise(); fields = S.earth_fields
    def scaled(lat, lon):
        a, b, c, d = fields(lat, lon); f = np.where(ES.egypt(lat, lon), 2.16, 1.0); return a * f, b * f, c, d
    S.earth_fields = scaled
    x = dict(np.load(S.PILOT.POOL)); eg = ES.egypt(x['lat'], x['lon']); x['density'] = np.where(eg, x['density'] * 2.16, x['density'])
    a, meta = S.prepare(x); res = a['residents']; L = 270.0; e = 0.5; width = x['land'].shape[1]
    share = np.where(a['owner'] >= 0, W.delivered_share(a['dist'].astype(float), L), 0.0)
    between = W.delivered_share(a['between'].astype(float), L).mean(0); np.fill_diagonal(between, 0.0)
    delivered, _ = W.hinterland_delivery(a['owner'], share, a['surplus'] * e, len(res))
    sent, received = W.ship(np.maximum(delivered - res, 0), np.maximum(res - delivered, 0), between)
    egc = eg.ravel()[a['nodes']]; idx = np.where(egc)[0]
    flows = dict(egypt_to_egypt=0.0, egypt_to_abroad=0.0, abroad_to_egypt=0.0)
    for (i, j), move in sent.items():
        if egc[i] and egc[j]: flows['egypt_to_egypt'] += move
        elif egc[i]: flows['egypt_to_abroad'] += move
        elif egc[j]: flows['abroad_to_egypt'] += move
    excess_eg = float(np.maximum(delivered - res, 0)[egc].sum()); deficit_eg = float(np.maximum(res - delivered, 0)[egc].sum())
    unshipped_eg = excess_eg - flows['egypt_to_egypt'] - flows['egypt_to_abroad']
    zero_share_eg = int(((between[np.ix_(idx, idx)] == 0).sum() - len(idx)))
    surplus_cells = eg.ravel() & (a['surplus'] > 0)
    # where Egyptian surplus goes: owner city of each surplus cell, by month-average reach
    own = a['owner'][0]; reach = (own >= 0) & surplus_cells
    to_egypt = float((a['surplus'] * e)[reach & egc[np.maximum(own, 0)]].sum()); lost_no_owner = float((a['surplus'] * e)[surplus_cells & (own < 0)].sum())
    mean_share = float(np.average(share.mean(0)[surplus_cells], weights=a['surplus'][surplus_cells]))
    cities = []
    for i in idx[np.argsort(-res[idx])][:12]:
        r_, c_ = divmod(int(a['nodes'][i]), width)
        cities.append(dict(lat=float(x['lat'][r_, c_]), lon=float(x['lon'][r_, c_]), residents=float(res[i]), own_hinterland=float(min(delivered[i], res[i])), received=float(received[i]),
                           fed_share=float((min(delivered[i], res[i]) + received[i]) / res[i]), egyptian_cities_reachable=int((between[idx, i] > 0).sum()), mean_cost_to_nearest_egypt_city=float(np.sort(a['between'][:, i, idx].mean(0))[1])))
    out = dict(status='post_hoc_exploratory_diagnostic', variant='YP_2.16', haul_limit=L, marketed_share=e,
        egypt_marketed_surplus=float((a['surplus'] * e)[surplus_cells].sum()), egypt_marketed_surplus_owned_by_egyptian_cities=to_egypt, egypt_marketed_surplus_with_no_city_within_limit=lost_no_owner,
        surplus_weighted_delivered_share=mean_share, egypt_residents=float(res[egc].sum()), flows_sent=flows, egypt_city_excess_after_hinterland=excess_eg, egypt_city_deficit_after_hinterland=deficit_eg, egypt_excess_unshipped=unshipped_eg, egypt_city_pairs_beyond_haul_limit=zero_share_eg, egypt_city_pairs=len(idx) * (len(idx) - 1), egypt_fed=float((np.minimum(delivered, res) + received)[egc].sum()), largest_egyptian_cities=cities)
    write(ES.OUT / 'diagnostic.json', out); print(json.dumps({k: v for k, v in out.items() if k != 'largest_egyptian_cities'}, indent=1))
    for c in cities: print({k: round(v, 3) if abs(v) < 100 else round(v) for k, v in c.items()})


if __name__ == '__main__':
    main()
