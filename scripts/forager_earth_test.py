"""The adapted FORGE foraging scenario against Binford's (2001) hunter-gatherers.

    python -I scripts/forager_earth_test.py --out output/forager_binford_20261031

Implements calibration/forager_binford_20261031/plan.json (frozen before any
run): every normal-case group in Binford's table, observed WorldClim 2.1
monthly climate within 25 km of it (months from the local winter solstice),
the atlas's resource adapter and kernel, and the configurations A (current
atlas summary), B (long-window median) and C (B plus food storage, its
capacity fitted on the North American fit set only). Metrics on the fit and
test sets; the plan's decision rule is applied and recorded.
"""
from __future__ import annotations

import argparse
import json
import math
import sys
import tarfile
import warnings
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import numpy as np  # noqa: E402

from foraging.forcing import daily_resources, miami_npp, specification  # noqa: E402
from foraging.models import ForagingParams, simulate_foraging  # noqa: E402

PLAN = ROOT / 'calibration/forager_binford_20261031/plan.json'
ARCHIVE = ROOT / 'data/cache/binford_dl/binford_0.1.0.tar.gz'
FIT_AREAS = {'SW', 'BC NWC', 'NNA', 'ARC', 'WNA', 'ENA'}
CAPACITIES = [0.0, 250.0, 500.0, 1000.0, 2000.0, 4000.0]
STORAGE_DECAY = 0.003


def binford():
    """Binford's LRB table from the CRAN package (extracted into its own cache folder)."""
    folder = ARCHIVE.parent / 'x'
    member = folder / 'binford/data/LRB.rdata'
    if not member.exists():
        with tarfile.open(ARCHIVE) as tar:
            tar.extractall(folder, filter='data')
    import rdata
    with warnings.catch_warnings():
        warnings.simplefilter('ignore')
        return rdata.read_rda(member)['LRB']


def worldclim_months():
    from rotclimate.earth import _wc
    return (np.stack([_wc('tavg', m) for m in range(1, 13)]), np.stack([_wc('prec', m) for m in range(1, 13)]))


def site_climate(tavg, prec, lat, lon, radius_km=25.0):
    """Mean monthly climate over WorldClim land cells within radius_km; None if there are none."""
    ny, nx = tavg.shape[1:]
    res = 180.0 / ny
    i0 = int((90.0 - lat) / res); j0 = int((lon + 180.0) / res)
    di = int(math.ceil(radius_km / 111.2 / res)) + 1
    dj = int(math.ceil(radius_km / (111.2 * max(math.cos(math.radians(lat)), 0.05)) / res)) + 1
    rows = np.arange(i0 - di, i0 + di + 1); cols = np.arange(j0 - dj, j0 + dj + 1)
    rows = rows[(rows >= 0) & (rows < ny)]; cols = cols % nx
    rr, cc = np.meshgrid(rows, cols, indexing='ij')
    clat = 90.0 - (rr + 0.5) * res; clon = -180.0 + (cc + 0.5) * res
    dlon = (clon - lon + 180.0) % 360.0 - 180.0
    dist = 111.2 * np.hypot(clat - lat, dlon * np.cos(np.radians(lat)))
    t = tavg[:, rr, cc]; p = prec[:, rr, cc]
    ok = (dist <= radius_km) & np.isfinite(t).all(0) & np.isfinite(p).all(0)
    if not ok.any():
        return None
    T = t[:, ok].mean(1); P = p[:, ok].mean(1)
    if lat < 0:                       # the year starts after the local winter solstice
        T, P = np.roll(T, -6), np.roll(P, -6)
    return T, P


def spearman(a, b):
    a, b = np.asarray(a, float), np.asarray(b, float)
    ok = np.isfinite(a) & np.isfinite(b)
    if ok.sum() < 5:
        return float('nan')
    from scipy.stats import rankdata          # tied ranks averaged
    ra, rb = rankdata(a[ok]), rankdata(b[ok])
    return float(np.corrcoef(ra, rb)[0, 1])


def metrics(model_density, sites, mask, result=None):
    obs = sites['density_km2'][mask]; mod = np.maximum(model_density[mask], 1e-4)
    err = np.log10(mod / obs)
    out = dict(n=int(mask.sum()), density_spearman=spearman(np.log10(mod), np.log10(obs)),
               median_abs_log10_error=float(np.median(np.abs(err))), median_log10_bias=float(np.median(err)))
    if result is not None:
        animal = np.asarray(result['meat_fraction'])[mask]
        out['animal_share_spearman'] = spearman(animal, (sites['hunting'][mask] + sites['fishing'][mask]) / 100)
        dry = sites['fishing'][mask] < 20
        terr = sites['hunting'][mask] / np.maximum(sites['hunting'][mask] + sites['gathering'][mask], 1e-9)
        out['terrestrial_animal_share_spearman'] = spearman(animal[dry], terr[dry])
        out['n_low_fishing'] = int(dry.sum())
        if 'mean_stored_share' in result:
            out['stored_share_vs_storage_spearman'] = spearman(np.asarray(result['mean_stored_share'])[mask], sites['store'][mask])
    return out


def run(sites, config, spec, capacity=0.0):
    run = dict(spec['run'])
    display = 'mean'
    if config in ('B', 'C'):
        run.update(years=600, averaging_years=300); display = 'median'
    kernel = dict(spec['kernel_parameters'])
    if config == 'C':
        kernel.update(storage_capacity_mj=float(capacity), storage_decay_day=STORAGE_DECAY)
    forcing = daily_resources(sites['T'], sites['P'], sites['npp'], spec['adapter'])
    return simulate_foraging(forcing['plant_supply'], forcing['meat_supply'], params=ForagingParams(**kernel),
                             display=display, **run)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--out', type=Path, default=ROOT / 'output/forager_binford_20261031')
    a = ap.parse_args(); a.out.mkdir(parents=True, exist_ok=True)
    plan = json.loads(PLAN.read_text())
    df = binford()
    df = df[(df['subpop'] == 'n') & (df['density'].astype(float) > 0)].copy()
    tavg, prec = worldclim_months()
    rows, T, P = [], [], []
    for _, r in df.iterrows():
        lat, lon = float(r['latitude']), float(r['longitude'])
        c = site_climate(tavg, prec, lat, lon)
        if c is None:
            continue
        rows.append(dict(name=str(r['name']), area=str(r['wc.area']), lat=lat, lon=lon,
                         density_km2=float(r['density']) / 100.0, gathering=float(r['gatherin']),
                         hunting=float(r['hunting']), fishing=float(r['fishing']),
                         store=float('nan') if r['store'] is None or str(r['store']) == '<NA>' else float(r['store'])))
        T.append(c[0]); P.append(c[1])
    sites = {k: np.array([row[k] for row in rows]) for k in rows[0]}
    sites['T'] = np.array(T).T; sites['P'] = np.array(P).T
    sites['npp'] = miami_npp(sites['T'], sites['P'])
    fit = np.isin(sites['area'], list(FIT_AREAS)); test = ~fit
    spec = specification()
    report = dict(plan=str(PLAN.relative_to(ROOT)), sites=len(rows), fit_sites=int(fit.sum()), test_sites=int(test.sum()),
                  excluded_no_climate=int(len(df) - len(rows)), configurations={})
    results = {}
    for config in ('A', 'B'):
        res = run(sites, config, spec); results[config] = res
        report['configurations'][config] = dict(fit=metrics(res['density_people_km2'], sites, fit, res),
                                                test=metrics(res['density_people_km2'], sites, test, res))
    scan = []
    for capacity in CAPACITIES:
        res = run(sites, 'C', spec, capacity)
        scan.append(dict(capacity_mj=capacity, fit=metrics(res['density_people_km2'], sites, fit, res)))
        results[('C', capacity)] = res
    best = min(scan, key=lambda s: s['fit']['median_abs_log10_error'])['capacity_mj']
    res = results[('C', best)]
    report['configurations']['C'] = dict(storage_capacity_mj=best, storage_decay_day=STORAGE_DECAY, scan_on_fit_set=scan,
                                         fit=metrics(res['density_people_km2'], sites, fit, res),
                                         test=metrics(res['density_people_km2'], sites, test, res))
    A, B, C = (report['configurations'][k]['test'] for k in 'ABC')
    b_ok = (B['median_abs_log10_error'] <= A['median_abs_log10_error'] + 0.02 and B['density_spearman'] >= A['density_spearman'] - 0.02)
    c_ok = (C['median_abs_log10_error'] < B['median_abs_log10_error'] and C['density_spearman'] >= B['density_spearman'] - 0.02)
    report['decision'] = dict(B_replaces_A=bool(b_ok), C_replaces_B=bool(c_ok and b_ok), rule=plan['decision'])
    # per culture area
    areas = {}
    for area in sorted(set(sites['area'])):
        m = sites['area'] == area
        areas[area] = {k: metrics(results[k]['density_people_km2'], sites, m) for k in ('A', 'B')}
        areas[area]['C'] = metrics(res['density_people_km2'], sites, m)
        areas[area]['observed_median_density_km2'] = float(np.median(sites['density_km2'][m]))
    report['by_culture_area'] = areas
    (a.out / 'binford_test.json').write_text(json.dumps(report, indent=1, default=float))
    np.savez(a.out / 'binford_sites.npz', **{k: v for k, v in sites.items()},
             density_A=results['A']['density_people_km2'], density_B=results['B']['density_people_km2'],
             density_C=res['density_people_km2'], meat_A=results['A']['meat_fraction'], meat_C=res['meat_fraction'])
    plot(sites, results['A']['density_people_km2'], res['density_people_km2'], fit, best, a.out / 'binford_density.png')
    print(json.dumps({k: v for k, v in report.items() if k != 'by_culture_area'}, indent=1, default=float))


def plot(sites, dA, dC, fit, capacity, path):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig, axes = plt.subplots(1, 2, figsize=(12, 5.4), sharex=True, sharey=True)
    obs = sites['density_km2']
    for ax, d, title in [(axes[0], dA, 'Current atlas FORGE (A)'), (axes[1], dC, f'Long-window median + storage {capacity:.0f} MJ (C)')]:
        for m, c, lab in [(fit, '#9aa3ad', 'North America (fit set)'), (~fit, '#2a78d6', 'rest of world (test set)')]:
            ax.scatter(obs[m], np.maximum(d[m], 1e-4), s=16, color=c, alpha=.8, label=lab, edgecolors='none')
        ax.plot([1e-3, 10], [1e-3, 10], color='#444', lw=1); ax.set_xscale('log'); ax.set_yscale('log')
        ax.set_xlim(1e-3, 5); ax.set_ylim(1e-4, 5); ax.set_title(title, loc='left', fontsize=11)
        ax.set_xlabel('Binford (2001) density, people/km²'); ax.grid(color='#e4e3de', lw=.6)
    axes[0].set_ylabel('model density, people/km²'); axes[0].legend(frameon=False, fontsize=9, loc='upper left')
    fig.tight_layout(); fig.savefig(path, dpi=130, facecolor='white')


if __name__ == '__main__':
    main()
