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
    sym = t['campaign_symbol'].to_numpy(); rank = {'imperial capital': 0, 'major imperial city': 1, 'fortified city': 2, 'fortified town': 3}
    cls = np.array([rank.get(s, 9) for s in sym])
    for a in range(4):       # A2: every higher class holds residuals no smaller than any lower class
        if (cls == a).any() and (cls > a).any() and e[cls == a].min() < e[cls > a].max(): problems.append(f'{mode} lore residual order {a}')
    drawn = np.clip(np.exp(coef[0] + coef[1] * np.log(H) + sigma * e), lo, hi); area = f['area_ha']
    if not np.allclose(area[cls == 9], drawn[cls == 9], rtol=1e-9): problems.append(mode + ' unranked areas')
    if not np.allclose(np.sort(area[cls < 9]), np.sort(drawn[cls < 9]), rtol=1e-9): problems.append(mode + ' ranked area set changed')
    for a in range(3):       # A3: areas strictly follow campaign rank among ranked places
        if area[cls == a].min() < area[(cls > a) & (cls < 9)].max(): problems.append(f'{mode} lore area order {a}')
    if int((cls < 9).sum()) != R['climates'][mode]['lore_ordering']['marked_reassigned']: problems.append(mode + ' ranked count')
    x = np.load(ROOT / f'output/settlement_feedback_20261112/{mode}_inputs.npz'); loc = x['local_index']
    t_ = np.clip((np.log(area) - np.log(50)) / (np.log(400) - np.log(50)), 0, 1)
    for k, wanted in (('central', area * (100 + 400 * t_)), ('low', area * 100.)):
        res = f['residents_' + k]; rural = f['rural_' + k]; moved = f['moved_' + k]; c = R['climates'][mode]['residents'][k]
        if not np.allclose(res, wanted, rtol=1e-9): problems.append(f'{mode} {k} residents differ from calibrated target')
        if not np.allclose(f['from_own_hinterland_' + k], np.minimum(wanted, .5 * H), rtol=1e-9): problems.append(f'{mode} {k} own draw')
        if rural.min() < -1e-6 or not np.allclose(rural + moved, people, rtol=1e-12, atol=1e-6): problems.append(f'{mode} {k} cell ledger')
        if abs(moved.sum() - res.sum()) > 1e-6 * res.sum() or moved[~land].any(): problems.append(f'{mode} {k} people conservation')
        surplus = np.clip(x['potential_kcal'][loc] - rural.ravel()[loc] * 912500., 0, None)
        col = pd.Series(surplus).groupby(x['owner']).sum().reindex(range(n), fill_value=0.).to_numpy() * .095
        share = col / (res * 912500.)
        if not np.allclose(share, f['local_support_share_' + k], rtol=1e-9): problems.append(f'{mode} {k} cereal support')
        for got, want, what in ((t['residents_' + k].sum(), c['total'], 'csv total'),
                (int((share >= 1).sum()), c['local_cereal']['fully_supported_sites'], 'supported count'),
                (res.sum() / people.sum(), c['share_of_world_people'], 'urban share')):
            if not np.isclose(got, want, rtol=1e-6): problems.append(f'{mode} {k} {what}')
    res = f['residents_central']
    c = R['climates'][mode]
    if list(t['id']) != [s['id'] for s in sites] or not np.allclose(t['calibrated_area_ha'], area, atol=.006): problems.append(mode + ' csv rows')
    for name, digest in c['outputs'].items():
        if sha(OUT / name) != digest: problems.append(mode + ' stale ' + name)
    checked[mode] = dict(sites=n, land_cells=int(land.sum()), capital_rank_by_residents=int((res > res[cls == 0][0]).sum()) + 1,
                         headline=R['climates'][mode]['headline_scenario'])
out = dict(status='passed' if not problems else 'failed', problems=problems, checked=checked,
           fantasy_sha256=sha(OUT / 'fantasy.json'), reviewer_sha256=sha(__file__))
(OUT / 'fantasy_review.json').write_text(json.dumps(out, indent=1) + '\n'); print(out); sys.exit(bool(problems))
