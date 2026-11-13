"""Independent review of the release-2 fantasy settlement build."""
import gzip, hashlib, json, sys
from pathlib import Path
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'output/settlement_release2_20261113'; DATA = ROOT / 'atlases/earth_fit/data'
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
R = json.loads((OUT / 'fantasy.json').read_text()); E = json.loads((OUT / 'results.json').read_text())
problems = []; checked = {}
coef = E['sizes']['primary']['models']['M1']['full_coefficients']; sigma = E['sizes']['primary']['models']['M1']['heldout_sigma']
lo, hi = E['sizes']['primary']['area_range_ha']
for mode in ('raw', 'corrected'):
    folder = DATA / ('corrected' if mode == 'corrected' else '')
    sites = json.loads(gzip.decompress((folder / 'settled_reach.json.gz').read_bytes()))['sites']
    f = np.load(OUT / f'fantasy_{mode}_fields.npz'); t = pd.read_csv(OUT / f'fantasy_{mode}_towns.csv', keep_default_na=False)
    g = np.load(folder / 'administration_grid.npz'); land = g['land']; cell = float(f['cell_km'])
    people = np.where(land, g['density'], 0.) * cell ** 2
    cr = np.array([s['row'] for s in sites]); cc = np.array([s['column'] for s in sites]); n = len(sites)
    lr, lc = np.nonzero(land); H = np.zeros(n)
    for i0 in range(0, len(lr), 3000):
        r_, c_ = lr[i0:i0 + 3000], lc[i0:i0 + 3000]
        d2 = (r_[:, None] - cr[None]) ** 2 + (c_[:, None] - cc[None]) ** 2
        best = d2.min(1); tie = (d2 == best[:, None]) & (best[:, None] * cell ** 2 <= 3600.)
        H += ((tie / np.maximum(tie.sum(1, keepdims=True), 1)) * people[r_, c_][:, None]).sum(0)
    if not np.allclose(H, f['hinterland_people'], rtol=1e-9): problems.append(mode + ' hinterlands')
    draws = np.clip(np.random.default_rng(1).standard_normal(n), -2.5, 2.5); e = f['residual']
    if not np.array_equal(np.sort(draws), np.sort(e)): problems.append(mode + ' residual set')
    area = np.clip(np.exp(coef[0] + coef[1] * np.log(H) + sigma * e), lo, hi)
    if not np.allclose(area, f['area_ha'], rtol=1e-9): problems.append(mode + ' areas')
    sym = t['campaign_symbol'].to_numpy(); rank = {'imperial capital': 0, 'major imperial city': 1, 'fortified city': 2, 'fortified town': 3}
    cls = np.array([rank.get(s, 9) for s in sym])
    for a in range(4):       # every higher class holds residuals no smaller than any lower class
        if (cls == a).any() and (cls > a).any() and e[cls == a].min() < e[cls > a].max(): problems.append(f'{mode} lore order {a}')
    if int((cls < 9).sum()) != R['climates'][mode]['lore_ordering']['marked_reassigned']: problems.append(mode + ' ranked count')
    t_ = np.clip((np.log(area) - np.log(50)) / (np.log(400) - np.log(50)), 0, 1); wanted = area * (100 + 400 * t_)
    res = f['residents_central']
    if not np.allclose(res, wanted, rtol=1e-9): problems.append(mode + ' residents differ from calibrated target (shortfall?)')
    if not np.allclose(f['from_own_hinterland'], np.minimum(wanted, .5 * H), rtol=1e-9): problems.append(mode + ' own draw')
    if not np.allclose(f['residents_low'], np.minimum(area * 100, res), rtol=1e-9): problems.append(mode + ' low scenario')
    rural = f['rural']; moved = f['moved']
    if rural.min() < -1e-6 or not np.allclose(rural + moved, people, rtol=1e-12, atol=1e-6): problems.append(mode + ' cell ledger')
    if abs(moved.sum() - res.sum()) > 1e-6 * res.sum() or moved[~land].any(): problems.append(mode + ' people conservation')
    x = np.load(ROOT / f'output/settlement_feedback_20261112/{mode}_inputs.npz'); loc = x['local_index']
    surplus = np.clip(x['potential_kcal'][loc] - rural.ravel()[loc] * 912500., 0, None)
    col = pd.Series(surplus).groupby(x['owner']).sum().reindex(range(n), fill_value=0.).to_numpy() * .095
    share = col / (res * 912500.)
    if not np.allclose(share, f['local_support_share'], rtol=1e-9): problems.append(mode + ' cereal support')
    c = R['climates'][mode]
    for got, want, what in ((t['residents_central'].sum(), c['residents']['central']['total'], 'csv total'),
            (int((share >= 1).sum()), c['local_cereal']['fully_supported_sites'], 'supported count'),
            (res.sum() / people.sum(), c['residents']['central']['share_of_world_people'], 'urban share')):
        if not np.isclose(got, want, rtol=1e-6): problems.append(f'{mode} {what}')
    if list(t['id']) != [s['id'] for s in sites] or not np.allclose(t['calibrated_area_ha'], area, atol=.006): problems.append(mode + ' csv rows')
    for name, digest in c['outputs'].items():
        if sha(OUT / name) != digest: problems.append(mode + ' stale ' + name)
    checked[mode] = dict(sites=n, land_cells=int(land.sum()), capital_rank_by_residents=int((res > res[cls == 0][0]).sum()) + 1)
out = dict(status='passed' if not problems else 'failed', problems=problems, checked=checked,
           fantasy_sha256=sha(OUT / 'fantasy.json'), reviewer_sha256=sha(__file__))
(OUT / 'fantasy_review.json').write_text(json.dumps(out, indent=1) + '\n'); print(out); sys.exit(bool(problems))
