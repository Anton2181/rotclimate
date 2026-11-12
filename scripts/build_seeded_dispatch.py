"""Versioned threshold-seeded cases using the unchanged field/food writer.

The effective model factory is scoped to one worker call and explicitly hashed
along with this adapter. Old model/writer source and all old artifacts stay intact.
"""
import argparse
from concurrent.futures import ProcessPoolExecutor
import itertools
import json
from pathlib import Path
import subprocess
import sys

import numpy as np

ROOT = Path(__file__).resolve().parents[1]; sys.path[:0] = [str(ROOT), str(ROOT / 'scripts')]
import build_settlement_dispatch as BASE
from polity.settlement_seeded_dispatch import ThresholdSeededDispatchFeedback
from settlement_locations_earth import sha, write

OUT = ROOT / 'output/settlement_dispatch_seeded_20261112'
PLAN = ROOT / 'calibration/settlement_dispatch_seeded_20261112/plan.json'


def run(mode, hours, load, profile, out=OUT):
    if subprocess.check_output(['git', 'show', 'HEAD:' + str(PLAN.relative_to(ROOT))], cwd=ROOT) != PLAN.read_bytes():
        raise ValueError('Commit threshold-seeded declaration first')
    produced = []
    def factory(*args, **kwargs):
        model = ThresholdSeededDispatchFeedback(*args, **kwargs); produced.append(model); return model
    previous = BASE.DispatchFeedback
    try:
        BASE.DispatchFeedback = factory
        result = BASE.run(mode, hours, load, profile, out)
    finally:
        BASE.DispatchFeedback = previous
    assert len(produced) == 1
    model = produced[0]; folder = out / result['key']; fields = dict(np.load(folder / 'fields.npz'))
    fields.update(threshold_seeded=model.threshold_seeded, threshold_feasible=model.threshold_feasible,
        preseed_total=model.preseed_total, preseed_active=model.preseed_active)
    np.savez_compressed(folder / 'fields.npz', **fields)
    result.update(status='threshold_seeded_joint_dispatch_resident_scenario', parent_plan_sha256=result['plan_sha256'],
        plan_sha256=sha(PLAN), effective_model='ThresholdSeededDispatchFeedback',
        fields_sha256=sha(folder / 'fields.npz'), seeded_sites=int(model.threshold_seeded.sum()),
        preseed_town_people=float(model.preseed_total.sum()), preseed_active_sources=int(model.preseed_active.sum()),
        search='64intervals plus known staffactivation seed and24bracket refinements;not globaloptimality',
        source_factory_scope='one worker call;original factory restored before serialization')
    result['sources'][str(PLAN.relative_to(ROOT))] = sha(PLAN)
    for path in (Path(__file__), ROOT / 'polity/settlement_seeded_dispatch.py'):
        result['producers'][str(path.relative_to(ROOT))] = sha(path)
    write(folder / 'results.json', result)
    print(result['key'], 'threshold-seeded:', round(result['town_people']), 'people;', result['active_sources'],
        'sources;', result['seeded_sites'], 'explicit threshold additions', flush=True)
    return result


def task(args): return run(*args)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__); parser.add_argument('--jobs', type=int, default=4)
    parser.add_argument('--out', type=Path, default=OUT); a = parser.parse_args()
    jobs = [(*case, a.out) for case in itertools.product(('raw', 'corrected'), (600, 300), (60000, 120000), ('all_open', 'bins6_7_8_closed'))]
    with ProcessPoolExecutor(max_workers=a.jobs) as workers: list(workers.map(task, jobs))
