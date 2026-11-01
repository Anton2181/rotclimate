"""Probe (not a frozen test): FORGE lifeways vs Binford's dominant food and culture areas (reports/FORAGING_EARTH_20261031.md).

    python -I scripts/forager_lifeway_probe.py
"""
import sys, json
sys.path.insert(0, 'scripts'); sys.path.insert(0, '.')
import numpy as np
from scipy.stats import spearmanr
from sklearn.metrics import adjusted_rand_score, cohen_kappa_score
from sklearn.cluster import KMeans
from forager_earth_test import binford, site_climate, worldclim_months
from forager_salmon import run_D
from foraging.forcing import miami_npp, specification
df = binford(); df = df[(df['subpop'] == 'n') & (df['density'].astype(float) > 0)].copy()
tavg, prec = worldclim_months()
rows, T, P = [], [], []
for _, r in df.iterrows():
    c = site_climate(tavg, prec, float(r['latitude']), float(r['longitude']))
    if c is None: continue
    rows.append(dict(name=str(r['name']), area=str(r['wc.area']), lat=float(r['latitude']), lon=float(r['longitude']),
                     density=float(r['density'])/100, h=float(r['hunting']), g=float(r['gatherin']), f=float(r['fishing'])))
    T.append(c[0]); P.append(c[1])
s = {k: np.array([x[k] for x in rows]) for k in rows[0]}
s['T'] = np.array(T).T; s['P'] = np.array(P).T; s['npp'] = miami_npp(s['T'], s['P'])
inputs = {(x['name'], round(x['lat'], 4), round(x['lon'], 4)): x for x in json.load(open('output/forager_binford_20261031/aquatic_inputs.json'))['sites']}
for key in ('d_coast_km', 'sst_annual_c', 'w_fresh'):
    s[key] = np.array([float(inputs[(x['name'], round(x['lat'], 4), round(x['lon'], 4))][key]) for x in rows])
s['s_salmon'] = np.zeros(len(rows))
res = run_D(s, specification(), 0)
fish = res['mean_fish_share']; meat = res['mean_meat_fraction']
pred = np.stack([(1-fish)*meat, (1-fish)*(1-meat), fish], 1)          # hunting, gathering, fishing shares
obs = np.stack([s['h'], s['g'], s['f']], 1) / 100.0
names = np.array(['hunting', 'gathering', 'fishing'])
for i, n in enumerate(names):
    print(f"{n:10s} share Spearman {spearmanr(pred[:, i], obs[:, i])[0]:+.2f}  pred median {np.median(pred[:, i]):.2f} obs median {np.median(obs[:, i]):.2f}")
pc, oc = pred.argmax(1), obs.argmax(1)
print('dominant food: accuracy %.2f kappa %.2f' % ((pc == oc).mean(), cohen_kappa_score(oc, pc)))
for i, n in enumerate(names):
    m = oc == i; print(f"   observed {n:9s} n={m.sum():3d}: predicted as", {names[j]: int(((pc == j) & m).sum()) for j in range(3)})
# culture areas: cluster sites on lifeway + location, compare with Binford's culture areas (ARI); baselines
area = s['area']; keep = np.isin(area, [a for a in set(area) if (area == a).sum() >= 7])
xyz = np.stack([np.cos(np.radians(s['lat']))*np.cos(np.radians(s['lon'])), np.cos(np.radians(s['lat']))*np.sin(np.radians(s['lon'])), np.sin(np.radians(s['lat']))], 1)
life = np.column_stack([np.log10(np.maximum(res['density_people_km2'], 1e-4)), pred, res['mean_scarcity_days_year']/365.0])
clim = np.column_stack([s['T'].mean(0)/10, s['T'].max(0)/10 - s['T'].min(0)/10, np.log10(s['P'].sum(0))])
z = lambda a: (a - a.mean(0)) / (a.std(0) + 1e-9)
k = len(set(area[keep]))
for label, X in (('location only', z(xyz)), ('location + climate', np.column_stack([z(xyz), z(clim)])),
                 ('location + FORGE lifeway', np.column_stack([z(xyz), z(life)])), ('FORGE lifeway only', z(life))):
    lab = KMeans(k, n_init=20, random_state=0).fit_predict(X[keep])
    print(f"{label:26s} adjusted Rand vs Binford culture areas: {adjusted_rand_score(area[keep], lab):.3f}  (k={k})")
# within North America only (where areas are adjacent and lifeways differ)
na = np.isin(area, ['ARC', 'NNA', 'WNA', 'BC NWC', 'SW'])
for label, X in (('NA location only', z(xyz[na])), ('NA location + FORGE lifeway', np.column_stack([z(xyz[na]), z(life[na])])),
                 ('NA location + climate', np.column_stack([z(xyz[na]), z(clim[na])]))):
    lab = KMeans(5, n_init=20, random_state=0).fit_predict(X)
    print(f"{label:28s} adjusted Rand: {adjusted_rand_score(area[na], lab):.3f}")
# leave-one-area-out: multinomial logistic map from FORGE outputs to the observed dominant food
from sklearn.linear_model import LogisticRegression
X = np.column_stack([np.log10(np.maximum(res['density_people_km2'], 1e-4)), pred, res['mean_scarcity_days_year']/365.0, np.log10(s['npp'])])
held = np.zeros(len(oc), int) - 1
for a in sorted(set(area)):
    m = area == a
    if len(set(oc[~m])) < 3: continue
    clf = LogisticRegression(max_iter=2000, C=1.0, class_weight='balanced').fit(z(X)[~m], oc[~m])
    held[m] = clf.predict(z(X)[m])
ok = held >= 0
print('leave-one-area-out dominant food: accuracy %.2f, kappa %.2f, n %d' % ((held[ok] == oc[ok]).mean(), cohen_kappa_score(oc[ok], held[ok]), ok.sum()))
for i, n in enumerate(names):
    m = (oc == i) & ok; print(f"   observed {n:9s} n={m.sum():3d}: predicted as", {names[j]: int(((held == j) & m).sum()) for j in range(3)})
print('majority-class baseline accuracy %.2f' % (np.bincount(oc).max() / len(oc)))
