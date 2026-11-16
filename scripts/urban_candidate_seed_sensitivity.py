"""Declared five paired seeds, fixed released sites and models; no fitting."""
import argparse
import csv
import hashlib
import json
from pathlib import Path
import subprocess
import sys

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / 'scripts')]
from polity import settlement_sizes as Z
import settlement_hierarchy_map as H
from build_urban_hierarchy_candidate import development_builder

BASE = ROOT / 'output/urban_hierarchy_candidate_20261116'
OUT = ROOT / 'output/urban_candidate_seeds_20261116'
PLAN = ROOT / 'calibration/urban_diagnosis_20261116/candidate_supply_robustness.json'
RELEASE = ROOT / 'output/settlement_release4_20261116'
SEEDS = [1, 7, 19, 43, 97]
KEYS = ['area_ha', 'residual', 'residents_central', 'residents_low',
        'from_own_hinterland_central', 'from_own_hinterland_low',
        'from_wider_region_central', 'from_wider_region_low',
        'wider_radius_km_central', 'wider_radius_km_low',
        'local_support_share_central', 'local_support_share_low']


def sha(path):
    with path.open('rb') as f:
        return hashlib.file_digest(f, 'sha256').hexdigest()


def write(path, obj):
    path.write_text(json.dumps(obj, indent=2) + '\n')


def table(path, rows):
    with path.open('w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)


def concentration(values):
    v = np.sort(values)[::-1]; total = float(v.sum()); n = len(v)
    return dict(total=total, largest=float(v[0]), top1_share=float(v[0]/total),
                top10_share=float(v[:10].sum()/total),
                gini=float((2*np.arange(1, n+1)-n-1) @ v[::-1] / (n*total)))


def main(out):
    assert subprocess.check_output(['git', 'show', 'HEAD:'+str(PLAN.relative_to(ROOT))], cwd=ROOT) == PLAN.read_bytes()
    plan = json.loads(PLAN.read_text()); assert plan['paired_seed_comparison']['seeds'] == SEEDS
    receipt = json.loads((BASE/'review.json').read_text())
    assert receipt['status'] == 'passed' and receipt['results_sha256'] == sha(BASE/'results.json')
    previous = json.loads((BASE/'results.json').read_text())
    for name, digest in {**previous['sources_sha256'], **previous['protected_sha256']}.items():
        assert sha(ROOT/name) == digest, name
    sources = {str(p.relative_to(ROOT)): sha(p) for p in [PLAN, Path(__file__),
        ROOT/'scripts/settlement_hierarchy_map.py', ROOT/'scripts/build_settlement_release2.py',
        ROOT/'scripts/build_urban_hierarchy_candidate.py', ROOT/'polity/settlement_sizes.py',
        BASE/'results.json', BASE/'review.json', BASE/'candidate_earth.json', RELEASE/'earth_results.json']}
    out.mkdir(parents=True, exist_ok=True); compact = {}; towns = []; cases = []; intervals = []
    earth = dict(published=json.loads((RELEASE/'earth_results.json').read_text()),
                 candidate=json.loads((BASE/'candidate_earth.json').read_text()))
    assert earth['candidate']['adopt'] is False and earth['candidate']['sizes']['primary']['gate']['passed'] is False
    Z.MODELS['M1C'] = ('lnH', 'capital')
    candidate, adapted, adapter = development_builder()
    (out/'development_adapter_snapshot.txt').write_text(adapted)
    for mode in ['raw', 'corrected']:
        sitespath = BASE/f'control/placed_{mode}_sites.json'
        sources[str(sitespath.relative_to(ROOT))] = sha(sitespath)
        sites = json.loads(sitespath.read_text())['sites']
        with np.load(BASE/f'prepared/{mode}.npz') as z:
            p = {k:z[k] for k in z.files}
        custom = dict(sites=sites, local=p['local'], catchment=p['catchment'], prefix='placed',
                      extra={k:p[k] for k in ['tracks', 'prior', 'claimed', 'density', 'marked_cells']})
        values = {}
        for label in ['published', 'candidate']:
            builder = H.patched_build() if label == 'published' else candidate
            primary = earth[label]['sizes']['primary']; model = primary['models']['M1C']
            builder.HIER_PHI = model['hierarchy_phi']; stacked = {key:[] for key in KEYS}
            for seed in SEEDS:
                builder.SEED = seed
                caseout = out/'cases'/mode/label/str(seed); caseout.mkdir(parents=True, exist_ok=True)
                summary = builder.build(mode, earth[label], caseout, custom=custom)
                fields = caseout/f'placed_{mode}_fields.npz'
                with np.load(fields) as z:
                    f = {k:z[k] for k in z.files}
                exact = None
                if seed == 1:
                    ref = BASE/('control' if label == 'published' else 'candidate')
                    for name in [f'placed_{mode}_fields.npz', f'placed_{mode}_towns.csv']:
                        assert sha(caseout/name) == sha(ref/name), (mode, label, name)
                    exact = True
                for key in KEYS:
                    stacked[key].append(f[key])
                for reading in ['central', 'low']:
                    wanted = Z.residents(f['area_ha'], reading); res = f['residents_'+reading]
                    rural = f['rural_'+reading]; before = f['people']; moved = f['moved_'+reading]
                    residual = float(before.sum()-rural.sum()-res.sum())
                    assert abs(residual) < 1e-6 and rural.min() >= -1e-8
                    assert np.allclose(moved, before-rural, atol=0, rtol=0)
                    unmet = np.maximum(wanted-res, 0)
                    assert np.all(res <= wanted+1e-6)
                    ledger = summary['residents'][reading]
                    case = dict(mode=mode, model=label, seed=seed, reading=reading,
                        sites=len(sites), area_ha=float(f['area_ha'].sum()),
                        requested=float(wanted.sum()), allocated=float(res.sum()),
                        unmet=float(unmet.sum()), rural=float(rural.sum()),
                        world_people=float(before.sum()), population_residual=residual,
                        own=float(f['from_own_hinterland_'+reading].sum()),
                        wide=float(f['from_wider_region_'+reading].sum()),
                        local_supported=ledger['local_cereal']['fully_supported_sites'],
                        local_import_dependent=ledger['local_cereal']['import_dependent_sites'],
                        rural_array_sha256=hashlib.sha256(rural.tobytes()).hexdigest(),
                        seed1_exact=exact, **{'residents_'+k:v for k,v in concentration(res).items()})
                    cases.append(case)
                print(mode, label, seed, 'annual people closed', flush=True)
            values[label] = {key:np.stack(v) for key,v in stacked.items()}
            compact.update({f'{mode}__{label}__{key}':a for key,a in values[label].items()})
            for j, seed in enumerate(SEEDS):
                for i, site in enumerate(sites):
                    towns.append(dict(mode=mode, model=label, seed=seed, id=site['id'], name=site['name'],
                        **{key:float(values[label][key][j,i]) for key in KEYS}))
        ratios = values['candidate']['area_ha']/values['published']['area_ha']
        for i, site in enumerate(sites):
            row = dict(mode=mode, id=site['id'], name=site['name'], marked=site['marked'],
                       ratio_gt2_fraction=float((ratios[:,i]>2).mean()),
                       ratio_lt_half_fraction=float((ratios[:,i]<.5).mean()))
            for key, v in [('paired_area_ratio', ratios), *[(label+'_area_ha', values[label]['area_ha']) for label in values]]:
                for q, suffix in [(.1,'p10'),(.5,'p50'),(.9,'p90')]:
                    row[key+'_'+suffix] = float(np.quantile(v[:,i],q))
            for label in values:
                for reading in ['central','low']:
                    for q, suffix in [(.1,'p10'),(.5,'p50'),(.9,'p90')]:
                        row[f'{label}_residents_{reading}_{suffix}'] = float(np.quantile(values[label]['residents_'+reading][:,i],q))
            intervals.append(row)
    np.savez_compressed(out/'model.npz', **compact)
    table(out/'seed_towns.csv', towns); table(out/'cases.csv', cases); table(out/'town_intervals.csv', intervals)
    summaries = {}
    for mode in ['raw','corrected']:
        rows = [r for r in intervals if r['mode']==mode]
        ratios = compact[f'{mode}__candidate__area_ha']/compact[f'{mode}__published__area_ha']
        summaries[mode] = dict(sites=len(rows),
            seed1_gt2=int((ratios[0]>2).sum()), seed1_lt_half=int((ratios[0]<.5).sum()),
            majority_seeds_gt2=sum(r['ratio_gt2_fraction']>=.6 for r in rows),
            all_seeds_gt2=sum(r['ratio_gt2_fraction']==1 for r in rows),
            majority_seeds_lt_half=sum(r['ratio_lt_half_fraction']>=.6 for r in rows),
            all_seeds_lt_half=sum(r['ratio_lt_half_fraction']==1 for r in rows),
            median_paired_ratio=float(np.median([r['paired_area_ratio_p50'] for r in rows])))
    files = ['model.npz','seed_towns.csv','cases.csv','town_intervals.csv','development_adapter_snapshot.txt']
    write(out/'results.json', dict(status='fixed_site_five_seed_development_sensitivity',
        sources_sha256=sources, protected_sha256=previous['protected_sha256'],
        files_sha256={name:sha(out/name) for name in files}, seeds=SEEDS,
        size_draws=20, annual_population_cases=40, per_site_seed_rows=len(towns),
        summary=summaries, cases=cases, development_adapter=adapter,
        interval_meaning='Five scenario seeds,not calibrated posterior intervals or independent validation.',
        wider_supply_rebuilt=False, seasonal_origin_food_work_validated=False,
        adopt=False, main_atlas_published=False))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(); parser.add_argument('--out', type=Path, default=OUT)
    main(parser.parse_args().out)
