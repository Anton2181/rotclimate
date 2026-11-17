"""Independent sampling, partition, scalar resource/OLS and direct-pair CRPS checks."""
import argparse
import csv
from pathlib import Path
import sys

import numpy as np

ROOT = Path(__file__).resolve().parents[1]; sys.path[:0] = [str(ROOT), str(ROOT / 'scripts')]
from cereal_activity_packet import read, write, sha
from conditional_grain_extent import OUT, GRID, WINDOW, ROMAN, MODELS, KCAL, verify_inputs
from polity.urban_predictive_pilot import nested_fit
from harvest.models import settlement_fields
from rotclimate import biomes


def close(a, b):
    np.testing.assert_allclose(a, b, rtol=2e-12, atol=2e-9)


def scalar_fit(x, y, use):
    yy = y[use]; mu = yy.mean()
    if x is None: return np.array([mu])
    xx = x[use]; mx = xx.mean()
    slope = np.sum((xx-mx)*(yy-mu)) / np.sum((xx-mx)**2)
    return np.array([mu - slope*mx, slope])


def review(out):
    assert not (out / 'review.json').exists(), 'Keep completed review'
    verify_inputs(); r = read(out / 'results.json')
    for n, h in r['sources_sha256'].items(): assert sha(ROOT / n) == h, n
    for n, h in r['files_sha256'].items(): assert sha(out / n) == h, n
    with np.load(out / 'features.npz') as z: f = dict(z)
    with np.load(out / 'ensembles.npz') as z: e = dict(z)
    with np.load(GRID) as z: g = dict(z)
    with np.load(WINDOW) as z: w = dict(z)
    with np.load(ROMAN / 'design.npz') as z: d = dict(z)
    with np.load(ROMAN / 'ensemble.npz') as z: old = dict(z)
    step = g['lat'][0] - g['lat'][1]
    rr = (g['lat'][0] - w['lat']) / step
    cc = (w['lon'] - g['lon'][0]) / step
    inside = (rr >= -.5) & (rr <= len(g['lat'])-.5) & (cc >= -.5) & (cc <= len(g['lon'])-.5)
    row = np.floor(np.clip(rr, 0, len(g['lat'])-1)+.5).astype(int)
    col = np.floor(np.clip(cc, 0, len(g['lon'])-1)+.5).astype(int)
    land = w['land']; covered = land & inside
    sample = lambda a: np.where(covered, np.nan_to_num(a)[row, col], 0.)
    np.testing.assert_array_equal(inside, f['inside'])
    for i, crop in enumerate(['wheat', 'barley']): np.testing.assert_array_equal(sample(g['kcal_'+crop]), f['energy'][i])
    np.testing.assert_array_equal(sample(g['arable']), f['arable'])
    biome = biomes.classify(np.nan_to_num(g['T_ann']), np.nan_to_num(g['P_ann']), g['land'])
    water = np.minimum(-6*np.log(np.maximum(np.nan_to_num(g['irr_distance']), 1e-12)), 300)
    sf = settlement_fields(*[np.nan_to_num(g[k]) for k in ['capacity', 'npp']], biome,
                           np.nan_to_num(g['arable']), water, np.nan_to_num(g['malaria']))
    people = sample(np.nan_to_num(sf['settlement_base']) * .3245772699601042) * float(w['cell_km'])**2
    np.testing.assert_array_equal(people, f['people'])
    wheat, barley = f['energy']; wh = np.divide(336, wheat, out=np.full_like(wheat, np.inf), where=wheat>0)
    bh = np.divide(208, barley, out=np.full_like(barley, np.inf), where=barley>0)
    crop = np.where(np.isfinite(np.minimum(wh, bh)), np.where(wh<=bh, 1, 2), 0)
    np.testing.assert_array_equal(crop, f['crop'])
    yield_ = np.where(crop==1, wheat, np.where(crop==2, barley, 0))
    hours = np.where(crop==1, 336., 208.); reap = np.where(crop==1, 48., 32.)
    ha = float(w['cell_km'])**2 * 100 * f['arable'] * .36 * land
    close(ha, f['hectares']); close(ha*yield_, f['potential'])
    gross = {'G_potential':ha*yield_}
    for label, annual in [('G_h600',600.), ('G_h300',300.)]:
        # Independent direct cropped-area cap, rather than per-million-kcal ratios.
        completed_ha = np.minimum(ha, np.minimum(people*.4*annual/hours, people*.4*min(annual,240)/reap))
        gross[label] = completed_ha * yield_
        close(gross[label], f['potential'] * f[label+'__retained'])
    # Independently enumerate each centre's <=60km disk and all integer-distance ties.
    centres = np.column_stack(np.unravel_index(w['real'], land.shape))
    minimum = np.full(land.shape, np.inf); count = np.zeros(land.shape, int)
    disks = []
    for cr, cc in centres:
        rr, co = np.meshgrid(np.arange(max(0,cr-6), min(land.shape[0],cr+7)),
                             np.arange(max(0,cc-6), min(land.shape[1],cc+7)), indexing='ij')
        dist = (rr-cr)**2 + (co-cc)**2
        valid = land[rr,co] & (dist*float(w['cell_km'])**2<=60**2)
        rr,co,dist = rr[valid],co[valid],dist[valid]; disks.append((rr,co,dist))
        better = dist < minimum[rr,co]; equal = dist == minimum[rr,co]
        count[rr[better],co[better]] = 1; minimum[rr[better],co[better]] = dist[better]
        count[rr[equal],co[equal]] += 1
    fields = {'H':people, **gross}; totals = {key:[] for key in fields}
    for rr,co,dist in disks:
        use = dist == minimum[rr,co]; rr,co = rr[use],co[use]
        for key, v in fields.items(): totals[key].append(np.sum(v[rr,co] / count[rr,co]))
    for key, v in totals.items():
        total = np.array(v); scale = 1 if key=='H' else KCAL
        close(total/scale, f['centre_H' if key=='H' else key+'__centre_rations'])
        close(total.sum(), fields[key][count>0].sum())
    observed_weight = np.bincount(f['origin'], weights=f['weight'], minlength=land.size).reshape(land.shape)
    np.testing.assert_array_equal(observed_weight>0, count>0)
    close(observed_weight[count>0], 1.)
    fold = d['fold']; y = np.log(d['area']); n = len(y); means = {}; fit_count = 0
    for model in MODELS:
        x = None if model=='M0' else f['x__'+model]
        X = np.ones((n,1)) if x is None else np.column_stack([np.ones(n),x])
        mean = np.zeros(n)
        for outer in range(4):
            test = fold==outer; training = ~test; beta = scalar_fit(x,y,training)
            receipt = next(v for v in r['fits'] if v['model']==model and v['outer']==outer)
            close(beta, receipt['coefficients']); residuals = []
            for held in range(4):
                if held==outer: continue
                tr = training & (fold!=held); te = training & (fold==held)
                inner = scalar_fit(x,y,tr); residuals.extend(y[te]-X[te]@inner)
                old_inner = next(v for v in receipt['inner'] if v['heldout']==held)
                close(inner, old_inner['coefficients'])
            sigma = np.sqrt(np.mean(np.square(residuals))); close(sigma, receipt['sigma'])
            perturbed = y.copy(); perturbed[test] += 1000
            bb, ss, _ = nested_fit(X, perturbed, fold, np.ones(n,bool), outer)
            close(bb, beta); close(ss, sigma)
            mean[test] = X[test]@beta
            for j, seed in enumerate(e['seeds']):
                normal = np.clip(np.random.default_rng(int(seed)).standard_normal(n), -2.5, 2.5)
                area = np.clip(np.exp(X@beta + sigma*normal), *r['bounds_ha'])
                close(area[test], e[model][j,test])
            fit_count += 1
        close(mean, e['mean__'+model]); means[model]=mean
    np.testing.assert_array_equal(e['M0'], old['baseline'])
    np.testing.assert_array_equal(e['hierarchy_reference'], old['hierarchy'])
    sets = {'all664':np.ones(n,bool), 'AD200_compatible':d['year200'],
            'AD200_strict':d['year200']&d['strict'], 'AD200_known_end':d['year200']&d['end_known']}
    names = read(ROMAN/'preparation.json')['province_names']; scored=0
    for model in MODELS+['hierarchy_reference']:
        z = np.log(e[model]); median = np.median(z,axis=0); error=median-y
        direct = np.empty(n)
        for start in range(0,n,8):
            part=z[:,start:start+8]
            direct[start:start+8]=np.abs(part-y[start:start+8]).mean(0)-.5*np.abs(part[:,None,:]-part[None,:,:]).mean((0,1))
        for filename in ['scores.csv','folds.csv','provinces.csv']:
            for record in csv.DictReader((out/filename).open()):
                if record['model']!=model: continue
                mask=sets[record['cohort']].copy()
                if filename=='folds.csv': mask &= fold==int(record['outer'])
                if filename=='provinces.csv': mask &= d['province']==names.index(record['province'])
                assert mask.sum()==int(record['n'])
                if not mask.any():
                    assert record['log_area_crps']==''; continue
                expected = dict(log_area_crps=direct[mask].mean(), median_log_area_mae=np.abs(error[mask]).mean(),
                    median_log_area_rmse=np.sqrt(np.square(error[mask]).mean()), median_log_bias=error[mask].mean(),
                    mean_generated_total_area_ratio=e[model][:,mask].sum(1).mean()/d['area'][mask].sum())
                for k,v in expected.items(): close(v,float(record[k])); scored+=1
    # Rebuild the identifiability measures separately from the production polyfit.
    a,b=f['x__G_h600'],f['x__G_h300']; slope=np.cov(a,b,ddof=0)[0,1]/np.var(a)
    intercept=b.mean()-slope*a.mean(); resid=b-intercept-slope*a; identification=r['identifiability']
    close(slope,identification['affine_h300_on_h600_slope']); close(intercept,identification['affine_intercept'])
    close(np.sqrt(np.mean(resid**2)),identification['affine_residual_rms'])
    close(np.sqrt(np.mean((means['G_h300']-means['G_h600'])**2)),identification['out_of_fold_mean_log_prediction_difference_rms'])
    write(out/'review.json', dict(status='passed_independent_grain_features_fits_and_scores',
        results_sha256=sha(out/'results.json'), reviewer_sha256=sha(Path(__file__)),
        scalar_cell_capacity_scenarios=3, independently_enumerated_centre_disks=len(disks),
        independent_outer_fits=fit_count, heldout_outcome_perturbation_checks=fit_count,
        direct_pair_CRPS_models=6, independently_checked_score_cells=scored,
        baseline_archive_exact=True, H_archive_exact=True, gross_grain_not_surplus=True,
        hours_identified=False, historical_capacity_calibrated=False, adopt=False))
    print(f'Independent sampling/resource/partition/fit checks pass; {scored} score cells; no hours inferred.')


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--out',type=Path,default=OUT)
    review(p.parse_args().out)
