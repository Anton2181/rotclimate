"""Independent stock traces, fixed-reference capacities and monthly freight ledgers."""
from pathlib import Path
import argparse
import sys

import numpy as np

ROOT = Path(__file__).resolve().parents[1]; sys.path[:0] = [str(ROOT), str(ROOT/'scripts')]
from urban_storage_loss import OUT, BASE, ANNUAL, INPUTS, COMBOS, SHARES
from urban_earth_monthly import read, write, sha, total, KCAL
from review_urban_earth_monthly import inventory as five_percent_inventory, close


def zero_inventory(c, prefix, harvest, need, capacity):
    """Compose clipped stock maps independently, then trace every recorded bin.

    Map composition uses net-energy clipping, while the production ledger pays
    immediate meals before clipping. Their rounding differences are compared
    at the unchanged inventory tolerance, never propagated into flow decisions.
    """
    shape = harvest.shape[1:]; cap = np.broadcast_to(capacity, shape)
    tolerance = 1e-10*np.maximum(1, np.maximum(harvest.sum(0), need.sum(0)))
    allowance = tolerance + 100*np.finfo(float).eps*np.maximum(1, np.maximum(harvest.sum(0), need.sum(0)))

    def annual(start):
        stock = np.array(start, float, copy=True)
        for month in range(12): stock = np.clip(stock+harvest[month]-need[month], 0, cap)
        return stock

    lower = annual(np.zeros(shape)); upper = annual(cap)
    lower = np.where(lower <= tolerance, 0., lower)
    repeats_lower = abs(annual(lower)-lower) <= tolerance
    expected = np.where(repeats_lower, lower, upper)
    maximum = 0.

    def check(field, value):
        nonlocal maximum
        error = abs(c[prefix+'__'+field]-value)
        assert np.all(error <= allowance), (prefix, field, float((error/allowance).max()))
        maximum = max(maximum, float((error/allowance).max()))

    check('initial_stock', expected)
    stock = c[prefix+'__initial_stock'].copy(); initial = stock.copy(); peak = stock.copy()
    consumed = np.zeros(shape); missing = consumed.copy(); overflow = consumed.copy(); shortdays = consumed.copy()
    paths = [stock.copy()]; deficits = []
    for month in range(12):
        available = stock+harvest[month]; eaten = np.minimum(available, need[month]); unmet = need[month]-eaten
        excess = np.maximum(available-need[month], 0)
        overflow += np.maximum(excess-cap, 0); stock = np.minimum(excess, cap)
        consumed += eaten; missing += unmet; shortdays += np.where(unmet>tolerance, 365/12, 0)
        peak = np.maximum(peak, stock); paths.append(stock.copy()); deficits.append(unmet)
    expected_fields = dict(final_stock=stock, peak_stock=peak, harvested=harvest.sum(0), needed=need.sum(0),
        consumed=consumed, unmet=missing, spoiled=np.zeros(shape), overflow=overflow,
        shortfall_days=shortdays, stock_path=np.stack(paths), unmet_path=np.stack(deficits),
        ledger_residual=initial+harvest.sum(0)-consumed-overflow-stock,
        periodic_residual=abs(stock-initial))
    for field, value in expected_fields.items(): check(field, value)
    assert np.all(abs(stock-initial) <= allowance)
    assert c[prefix+'__periodic_converged'].all()
    assert (c[prefix+'__spoiled'] == 0).all()
    return maximum


def main(reading, label):
    folder = OUT/'cases'/f'{reading}_{label}'; r = read(folder/'results.json')
    assert not (folder/'review.json').exists(), 'Preserve completed review'
    for name, digest in {**r['sources_sha256'], **r['protected_sha256']}.items(): assert sha(ROOT/name) == digest, name
    assert sha(folder/'fields.npz') == r['fields_sha256']
    c = dict(np.load(folder/'fields.npz')); baseline = dict(np.load(BASE/'cases'/reading/'fields.npz'))
    a = dict(np.load(ANNUAL/f'low_{reading}.npz'))
    for key in INPUTS: np.testing.assert_array_equal(c[key], baseline[key], err_msg=key)
    assert r['marketed_share'] == SHARES[reading]
    _, loss, days = next(combo for combo in COMBOS if combo[0] == label)
    assert r['loss_fraction_year'] == loss and r['commercial_days'] == days
    reference = baseline['marketed'].sum(0)
    np.testing.assert_array_equal(c['reference_market'], reference)
    capacity = reference if days == 365 else reference*90/365
    np.testing.assert_array_equal(c['commercial_capacity'], capacity)
    assert np.all(capacity[reference == 0] == 0)
    ratios = []

    def inventory(prefix, harvest, need, cap):
        if loss == .05:
            _, ratio = five_percent_inventory(c, prefix, harvest, need, cap)
        else:
            ratio = zero_inventory(c, prefix, harvest, need, cap)
        ratios.append(ratio)

    harvest = np.zeros_like(c['harvest'])
    for cell in range(len(c['rural'])):
        for component in range(len(c['produced_components'])):
            grain = c['produced_components'][component, cell]
            if grain > 0: harvest[c['boundary'][component, cell], cell] += grain
    np.testing.assert_array_equal(c['harvest'], harvest)
    need = np.broadcast_to(c['rural']*KCAL/12, harvest.shape)
    inventory('rural_food', harvest, need, c['rural']*KCAL)
    protected = c['rural_food__unmet'] <= 1e-8*np.maximum(1, c['rural_food__needed'])
    protected_cap = c['rural_food__needed']*365/365
    marketed = np.maximum(c['rural_food__stock_path'][:-1]+harvest-need-protected_cap, 0)*protected*SHARES[reading]
    np.testing.assert_array_equal(c['marketed'], marketed)
    dispatch = np.broadcast_to(marketed.sum(0)/12, marketed.shape).copy()
    owner = c['owner']; fraction = c['retention']
    for month in range(12): dispatch[month] *= (owner[month//3]>=0)&(fraction[month//3]>0)
    np.testing.assert_array_equal(c['dispatch'], dispatch)
    inventory('export_food', marketed, dispatch, capacity)
    np.testing.assert_array_equal(c['departures'], dispatch-c['export_food__unmet_path'])
    assert not (c['departures'][:, ~protected]>1e-6).any()
    direct = np.zeros_like(c['direct'])
    for month in range(12):
        q = month//3; valid = (owner[q]>=0)&(fraction[q]>0)
        np.add.at(direct[(month+1)%12], owner[q, valid], c['departures'][month, valid]*fraction[q, valid])
    close(direct, c['direct'])
    town_need = np.broadcast_to(c['request']*KCAL/12, direct.shape); town_capacity = c['request']*2500*90
    inventory('direct_food', c['direct'], town_need, town_capacity)
    eligible = (c['request']>0)&(c['direct_food__unmet']<=1e-8*np.maximum(1, c['direct_food__needed']))
    np.testing.assert_array_equal(eligible, c['protected_exporters'])
    overflow = np.maximum(c['direct_food__stock_path'][:-1]+c['direct']-town_need-town_capacity, 0)*eligible
    between = np.maximum(1-a['between'].astype(float)/270, 0)
    for quarter in range(4): np.fill_diagonal(between[quarter], 0)
    received = np.zeros_like(direct); exported = np.zeros_like(direct); moves = []
    for month in range(12):
        matrix = between[month//3]; excess = overflow[month].copy(); deficit = c['direct_food__unmet_path'][(month+1)%12].copy()
        sender, receiver = np.nonzero((matrix>0)&(excess[:, None]>0)&(deficit[None, :]>0))
        links = sorted(zip(sender.tolist(), receiver.tolist()), key=lambda pair: (-matrix[pair], pair[0], pair[1]))
        for i, j in links:
            if excess[i]<=0 or deficit[j]<=0: continue
            sent = min(excess[i], deficit[j]/matrix[i, j]); arrival = sent*matrix[i, j]
            excess[i] -= sent; deficit[j] -= arrival
            if deficit[j]<1e-9*max(1, sent): deficit[j] = 0
            exported[month, i] += sent; received[(month+1)%12, j] += arrival
            moves.append([month, i, j, sent, arrival])
    close(c['shipments'], np.array(moves).reshape(-1, 5)); close(c['inter_received'], received); close(c['inter_exported'], exported)
    assert np.all(exported<=overflow+.01)
    assert not ((exported.sum(0)>0)&(received.sum(0)>0)).any()
    close(c['arrivals'], c['direct']+received)
    inventory('town_food', c['arrivals'], town_need, town_capacity)
    ledger = dict(produced_kcal=total(harvest), rural_meals_kcal=total(c['rural_food__consumed']),
        rural_spoiled_kcal=total(c['rural_food__spoiled']), export_spoiled_kcal=total(c['export_food__spoiled']),
        town_spoiled_kcal=total(c['town_food__spoiled']), source_unused_kcal=total(c['rural_food__overflow'])-total(marketed)+total(c['export_food__overflow']),
        town_unused_kcal=total(c['town_food__overflow'])-total(exported), source_freight_loss_kcal=total(c['departures'])-total(c['direct']),
        intertown_freight_loss_kcal=total(exported)-total(received), town_meals_kcal=total(c['town_food__consumed']),
        stock_change_kcal=sum(total(c[p+'__final_stock']-c[p+'__initial_stock']) for p in ('rural_food', 'export_food', 'town_food')))
    for key, value in ledger.items(): close(r['audit']['ledger'][key], value, atol=.1)
    residual = ledger['produced_kcal']-sum(value for key, value in ledger.items() if key!='produced_kcal')
    assert abs(residual)<1e-9*ledger['produced_kcal']
    old_protected = baseline['rural_food__unmet']<=1e-8*np.maximum(1, baseline['rural_food__needed'])
    newly_zero = ~old_protected & protected & (reference==0)
    assert r['newly_protected_zero_capacity_origins'] == int(newly_zero.sum())
    close(r['newly_protected_zero_capacity_departures_person_years'], total(c['departures'][:, newly_zero])/KCAL, atol=1e-7)
    # Zero reference capacity permits immediate meals/dispatch but cannot carry stock.
    assert np.all(c['export_food__stock_path'][:, reference==0] == 0)
    receipt = dict(status='passed_fixed_reference_storage_loss_stock_routes_and_ledger', reading=reading, label=label,
        reviewer_sha256=sha(Path(__file__)), reviewer_dependency_sha256=sha(ROOT/'scripts/review_urban_earth_monthly.py'),
        results_sha256=sha(folder/'results.json'), fields_sha256=sha(folder/'fields.npz'),
        physical_sources=len(reference), inventory_groups=4, independent_shipments=len(moves),
        maximum_fraction_of_original_inventory_tolerance=max(ratios), grain_residual_person_years=residual/KCAL,
        original_inputs_exact=True, fixed_commercial_reference_exact=True, loss_fraction_year=loss,
        smallest_zero_loss_endpoint_reviewed=loss==0, five_percent_canonical_bisection_reviewed=loss==.05,
        demographic_iteration=False, actual_population_changed=False, new_fit=False, new_validation_claim=False, adopt=False)
    write(folder/'review.json', receipt)
    print(reading, label, 'PASS', 'inventory ratio', max(ratios), 'ledger PY', residual/KCAL, flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(); parser.add_argument('reading', choices=['central', 'low'])
    parser.add_argument('label', choices=[item[0] for item in COMBOS]); args = parser.parse_args()
    main(args.reading, args.label)
