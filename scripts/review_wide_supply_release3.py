"""Independent review of the wider grain supply plan.

Recomputes available grain, hinterland delivery (pandas group sums) and the
between-town plan with a separately written allocator (sorted link table,
no dictionary state shared with the producer), then checks conservation,
bounds and every per-town result. The freight costs themselves come from the
atlas network and are not re-derived here.
"""
import hashlib, json, sys
from pathlib import Path
import numpy as np, pandas as pd

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'output/settlement_wide_supply_20261113'; R3 = ROOT / 'output/settlement_release3_20261113'
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest(); KCAL = 912500.0
R = json.loads((OUT / 'results.json').read_text()); problems = []; checked = 0
for mode, c in R['climates'].items():
    z = np.load(OUT / f'supply_{mode}.npz'); f = np.load(R3 / f'placed_{mode}_fields.npz')
    x = np.load(ROOT / f'output/settlement_feedback_20261112/{mode}_inputs.npz'); land = f['land'].ravel()
    owner, share, between = z['owner'], z['share'].astype(float), z['between']
    if between.min() < 0 or between.max() > 1 or np.diag(between).any() or share.min() < 0 or share.max() > 1:
        problems.append(mode + ' share bounds')
    for key, s in c['scenarios'].items():
        res = f['residents_' + s['density']]; need = res * KCAL
        grain = np.where(land, np.clip(x['potential_kcal'] - f['rural_' + s['density']].ravel() * KCAL, 0, None), 0.) * s['extraction']
        delivered = np.zeros(len(need))
        for season in range(owner.shape[0]):
            t = pd.DataFrame(dict(o=owner[season], g=grain / owner.shape[0] * share[season]))
            g = t[t.o >= 0].groupby('o').g.sum(); delivered[g.index.to_numpy()] += g.to_numpy()
        if not np.allclose(delivered, z[key + '_delivered'], rtol=1e-6, atol=1.):      # share stored as float32
            problems.append(f'{mode} {key} hinterland delivery')
        delivered = z[key + '_delivered']
        ex = np.clip(delivered - need, 0, None); de = np.clip(need - delivered, 0, None)
        i, j = np.nonzero(between > 0); links = pd.DataFrame(dict(i=i, j=j, s=between[i, j]))
        links = links[(ex[links.i.to_numpy()] > 0) & (de[links.j.to_numpy()] > 0)].sort_values(['s', 'i', 'j'], ascending=[False, True, True])
        left = ex.copy(); want = de.copy(); got = np.zeros(len(need)); out_ = np.zeros(len(need)); n = 0
        for a, b, sh in zip(links.i.to_numpy(), links.j.to_numpy(), links.s.to_numpy()):
            if left[a] <= 0 or want[b] <= 0:
                continue
            move = min(left[a], want[b] / sh); left[a] -= move; want[b] -= move * sh; got[b] += move * sh; out_[a] += move; n += 1
            if want[b] < 1e-9 * max(1., move): want[b] = 0.
        fed = np.minimum(delivered, need) + got; fs = np.divide(fed, need, out=np.ones_like(need), where=need > 0)
        for name, mine, theirs in (('received', got, z[key + '_received']), ('exported', out_, z[key + '_exported']), ('fed share', fs, z[key + '_fed_share'])):
            if not np.allclose(mine, theirs, rtol=1e-9, atol=1e-6 * max(1., np.abs(theirs).max())): problems.append(f'{mode} {key} {name}')
        if n != s['shipments'] or np.any(out_ > ex * (1 + 1e-9) + 1e-6) or np.any(fed > need * (1 + 1e-6)) or np.any((out_ > 0) & (got > 0)):
            problems.append(f'{mode} {key} shipment constraints')
        full = fs >= 1 - 1e-6
        if int((~full).sum()) != s['short_towns'] or not np.isclose(fed.sum() / need.sum(), s['fed_share_of_residents'], rtol=1e-9):
            problems.append(f'{mode} {key} summary')
        L = s['ledger_person_years']
        if abs(L['residual']) > 1e-6 * L['available'] or not np.isclose(L['available'] * KCAL, grain.sum(), rtol=1e-9) or min(v for k, v in L.items() if k != 'residual') < -1e-6:
            problems.append(f'{mode} {key} ledger')
        checked += 1
    t = pd.read_csv(OUT / f'supply_{mode}_towns.csv', keep_default_na=False)
    if not np.allclose(t.fed_share, z['central_x10_fed_share'], atol=6e-5) or (t.status == 'short').sum() != c['scenarios']['central_x10']['short_towns']:
        problems.append(mode + ' csv')
    for name, digest in c['outputs'].items():
        if sha(OUT / name) != digest: problems.append(mode + ' stale ' + name)
out = dict(status='passed' if not problems else 'failed', problems=problems, scenarios_checked=checked,
           results_sha256=sha(OUT / 'results.json'), reviewer_sha256=sha(__file__),
           scope='allocation, ledgers and summaries recomputed; freight costs taken from the atlas network')
(OUT / 'review.json').write_text(json.dumps(out, indent=1) + '\n'); print(out); sys.exit(bool(problems))
