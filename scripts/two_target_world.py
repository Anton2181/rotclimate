"""Side project: world refit with two targets only (calibration/two_target_20261121/plan.json).

    .venv/bin/python -I scripts/two_target_world.py search [--resume]
    .venv/bin/python -I scripts/two_target_world.py check     # ds8 layouts 1-3: start vs best
    .venv/bin/python -I scripts/two_target_world.py maps      # Koppen + nomad chance, start vs best (ds8)
"""
import json, sys
from dataclasses import asdict
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / 'scripts'))
import numpy as np
from earth_benchmark import load_params
from world_campaign_r50 import SPACE, FIXED, assert_world_only
from local_benchmark_protocol import write_json
from rotclimate import calibrate as C

FOLDER = ROOT / 'calibration/two_target_20261121'


def search(plan, resume):
    base = load_params(ROOT / plan['start']).replace(downsample=plan['downsample'])
    C._set_space(SPACE); enc = C.encode(base)
    fixed = {n: float(enc[C.NAMES.index(n)]) for n in FIXED}
    ctrl = FOLDER / 'start_score.json'
    if not ctrl.exists():
        r = C.evaluate_params(base, 'twotarget', seeds=plan['layouts'], ensemble_objective='climate')
        write_json(ctrl, r); print('start', r['two_target'], flush=True)
    best = C.calibrate(FOLDER / 'world', plan['evaluations'], base, sigma0=plan['sigma'], popsize=plan['popsize'],
                       workers=plan['workers'], seed=plan['seed'], fixed=fixed, mode='twotarget', seeds=plan['layouts'],
                       race=0., stds={'north_bearing': 0.05}, resume=resume, ensemble_objective='climate')
    assert_world_only(load_params(FOLDER / 'world/best_params.json'), base)
    write_json(FOLDER / 'best_result.json', best); print('done', best.get('two_target'), flush=True)


def check(plan):
    out = {}
    for tag, path in [('start', ROOT / plan['start']), ('best', FOLDER / 'world/best_params.json')]:
        p = load_params(path).replace(downsample=8)
        r = C.evaluate_params(p, 'twotarget', seeds=[1, 2, 3], ensemble_objective='climate')
        out[tag] = dict(two_target=r['two_target'], accuracy=r['accuracy'], recall=r['recall'],
                        zonefit=r['zonefit_score'], mediterranean=r['mediterranean'])
        print(tag, json.dumps(out[tag]['two_target']), flush=True)
    write_json(FOLDER / 'ds8_check.json', out)


def maps(plan):
    import matplotlib; matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from rotclimate.model import ClimateModel, ensemble_mean
    from rotclimate.score import evaluate
    from rotclimate.koppen import CODES, classify, rgb_image
    rule = json.loads((FOLDER / 'nomad_rule.json').read_text())
    out = ROOT / 'output/two_target'; out.mkdir(parents=True, exist_ok=True)
    rows = {}
    for tag, path in [('start', ROOT / plan['start']), ('best', FOLDER / 'world/best_params.json')]:
        p = load_params(path).replace(downsample=8)
        res = ensemble_mean([ClimateModel(p.replace(beyond_seed=s)).run() for s in (1, 2, 3)])
        ev = evaluate(res); st = ev['monthly']; g = res.grid
        k = classify(st['Tm'], st['Pm'], st['summer'])
        ratio = np.maximum(np.asarray(ev['indices']['aridity'], float), 0.01)
        nom = 1 / (1 + np.exp(-(rule['a'] + rule['b'] * np.log(ratio))))
        land = g.inmap & g.land
        rows[tag] = dict(k=np.where(land, k, -1), nom=np.where(land, nom, np.nan), target=g.target, land=land,
                         ratio=ratio)
        np.savez_compressed(out / f'fields_{tag}.npz', koppen=rows[tag]['k'], nomads=rows[tag]['nom'],
                            aridity=ratio, target=g.target, land=land)
    fig, ax = plt.subplots(2, 2, figsize=(16, 8.4), constrained_layout=True)
    for j, tag in enumerate(['start', 'best']):
        r = rows[tag]
        ax[0, j].imshow(rgb_image(r['k'], r['land'], (214, 227, 240)), interpolation='nearest')
        ax[1, j].set_facecolor('#d6e3f0')
        im = ax[1, j].imshow(r['nom'] * 100, cmap='YlOrBr', vmin=0, vmax=30, interpolation='nearest')
        for a in ax[:, j]:
            a.contour(r['target'] == 4, [0.5], colors='#1f5fbf', linewidths=1.2)
            a.contour(r['target'] == 2, [0.5], colors='#b00020', linewidths=1.2)
            a.set_xticks([]); a.set_yticks([])
        name = 'Today\'s world' if tag == 'start' else 'Two-target world'
        ax[0, j].set_title(f'{name}: Koppen (blue = painted Mediterranean, red = painted cold dry)')
        ax[1, j].set_title(f'{name}: chance of pastoral nomads, %')
    fig.colorbar(im, ax=ax[1, :], shrink=0.8, label='% chance of pastoral nomads (aridity rule)')
    fig.savefig(out / 'two_target_maps.png', dpi=90)
    summ = {t: dict(cold_dry_ratio_median=float(np.median(rows[t]['ratio'][rows[t]['land'] & (rows[t]['target'] == 2)])),
                    cold_dry_codes={c: float(np.mean(np.array(CODES)[rows[t]['k'][rows[t]['land'] & (rows[t]['target'] == 2)]] == c))
                                    for c in set(np.array(CODES)[rows[t]['k'][rows[t]['land'] & (rows[t]['target'] == 2)]])})
            for t in rows}
    write_json(FOLDER / 'maps_summary.json', summ); print(json.dumps(summ, indent=1))


if __name__ == '__main__':
    plan = json.loads((FOLDER / 'plan.json').read_text())
    dict(search=lambda: search(plan, '--resume' in sys.argv), check=lambda: check(plan), maps=lambda: maps(plan))[sys.argv[1]]()
