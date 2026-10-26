"""Advance only predeclared shear qualifiers through full Earth gates."""
from pathlib import Path
from dataclasses import asdict
import argparse
import json
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT/'scripts'))
from benchmark_local import DEV31
from check_constrained_blend import benchmark, paired_score
from gate_local import evaluate
from local_benchmark_protocol import file_hash, freeze, write_json
from earth_benchmark import load_params
from rotclimate import joint


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--screen', type=Path, default=ROOT/'output/column_shear_20261026')
    args = parser.parse_args()
    screen = args.screen.resolve()
    review = json.loads((screen/'review.json').read_text())
    protocol = json.loads((screen/'protocol.json').read_text())
    plan = protocol['plan']
    if not review['complete']:
        raise ValueError('Incomplete screening')
    for name, expected in protocol['sources'].items():
        if file_hash(ROOT/name) != expected:
            raise ValueError('Screen sources changed: '+name)
    # Bind selection to the actual records, not an editable shortlist.
    from check_column_shear import screening
    rows = []
    for name in ['reference', *plan['candidates']]:
        for region in plan['regions']:
            path = screen/name/f'{region}.json'
            row = json.loads(path.read_text())
            if row['identity'] != review['identity']:
                raise ValueError('Run identity changed')
            if row['status'] == 'passed' and file_hash(path.with_suffix('.npz')) != row['arrays_sha256']:
                raise ValueError('Screen arrays changed')
            rows.append(row)
    computed = screening(rows, plan)
    if computed != review['screen']:
        raise ValueError('Screen review differs from actual records')
    finalists = sorted((n for n in computed if computed[n]['qualifies']), key=lambda n: computed[n]['S'])
    finalists = finalists[:plan['screen']['maximum_development_finalists']]
    if finalists != review['development_finalists']:
        raise ValueError('Shortlist changed')
    out = screen/'advance'
    out.mkdir(exist_ok=True)
    sources = list((ROOT/'rotclimate').glob('*.py'))+[Path(__file__), screen/'review.json', screen/'protocol.json',
        ROOT/'scripts/check_constrained_blend.py', ROOT/'scripts/benchmark_local.py', ROOT/'scripts/gate_local.py',
        ROOT/'calibration/local_accuracy_20261023/policy_v2.json',
        ROOT/'calibration/local_accuracy_20261023/regions_sealed6.json']
    freeze(out/'protocol.json', dict(plan=plan, finalists=finalists,
        sources={str(p.relative_to(ROOT)): file_hash(p) for p in sources}))
    if not finalists:
        write_json(out/'review.json', dict(complete=True, eligible_for_earth_adoption=False,
            reason='No screening qualifier; no full development, finer-grid or established-six run.',
            atlas_climate_adoption=False))
        print('No candidate advances; retained r39', flush=True)
        return
    params = out/'params'
    params.mkdir(exist_ok=True)
    base = load_params(ROOT/plan['physics'])
    reference_params = params/'reference.json'
    joint.earth_profile(base).to_json(reference_params)
    reference = benchmark(reference_params, out/'reference', ['dev31'], 56.0)
    if reference is None:
        raise ValueError('Fresh full reference failed')
    archive = ROOT/plan['archive']
    for name in DEV31:
        previous = json.loads((archive/'cases'/f'{name}.json').read_text())
        current = reference['regions'][name]
        if (current['case_identity'] != previous['case_identity'] or
                abs(current['rain']['loss']-previous['rain']['loss']) > 1e-10 or
                abs(current['temperature']['monthly_mae_C']-previous['temperature']['monthly_mae_C']) > 1e-10):
            raise ValueError('Full exact r39 error control changed: '+name)
    policy = json.loads((ROOT/'calibration/local_accuracy_20261023/policy_v2.json').read_text())
    rp = json.loads((out/'reference/protocol.json').read_text())
    development, qualified = {}, []
    for name in finalists:
        path = params/f'{name}.json'
        joint.earth_profile(base.replace(moisture_pressure_drag_ratio=plan['candidates'][name])).to_json(path)
        candidate = benchmark(path, out/'development'/name, ['dev31'], 56.0)
        if candidate is None:
            development[name] = dict(passes_development_gate=False, failures=['Numerical failure'])
        else:
            cp = json.loads((out/'development'/name/'protocol.json').read_text())
            development[name] = evaluate(reference, candidate, rp, cp, policy)
            if development[name]['passes_development_gate']:
                qualified.append(name)
    qualified.sort(key=lambda n: development[n]['score'])
    write_json(out/'progress.json', dict(complete=False, development=development))
    fine, selected = {}, None
    names = ['california', 'western_europe', 'japan', 'new_zealand']
    if qualified:
        if benchmark(reference_params, out/'fine_reference', names+['north_india'], 28.0) is None:
            raise ValueError('Fine reference failed')
        for name in qualified:
            folder = out/'fine'/name
            candidate = benchmark(params/f'{name}.json', folder, names+['north_india'], 28.0)
            if candidate is None:
                fine[name] = dict(passed=False, reason='Numerical failure')
            else:
                s = paired_score(out/'fine_reference', folder, names)
                baseline = json.loads((out/'fine_reference/summary.json').read_text())
                ratio = candidate['regions']['north_india']['rain']['loss']/baseline['regions']['north_india']['rain']['loss']
                fine[name] = dict(S=s, north_india_rain_loss_ratio=ratio, passed=s <= 1.01 and ratio <= .98)
            if fine[name]['passed']:
                selected = name
                break
    established = None
    if selected:
        specs = ROOT/'calibration/local_accuracy_20261023/regions_sealed6.json'
        names = list(json.loads(specs.read_text()))
        a = benchmark(reference_params, out/'established_reference', names, 56.0, specs)
        b = benchmark(params/f'{selected}.json', out/'established_candidate', names, 56.0, specs)
        s = paired_score(out/'established_reference', out/'established_candidate', names) if a and b else None
        established = dict(S=s, passed=s is not None and s <= 1.01,
                           note='Reused established regions, not an independent holdout')
    adopted = bool(selected and established and established['passed'])
    profile = None
    if adopted:
        profile = ROOT/'calibration/local_accuracy_20261023/r40_params.json'
        values = asdict(base.replace(moisture_pressure_drag_ratio=plan['candidates'][selected]))
        if profile.exists() and json.loads(profile.read_text()) != json.loads(json.dumps(values)):
            raise ValueError('Existing r40 adoption must be preserved')
        write_json(profile, values)
    final = dict(complete=True, development=development, fine=fine, selected=selected, established=established,
                 eligible_for_earth_adoption=adopted, profile=str(profile.relative_to(ROOT)) if profile else None,
                 atlas_climate_adoption=False, note='A separate matched-world refit is required before atlas promotion')
    write_json(out/'review.json', final)
    write_json(out/'progress.json', final)
    print(json.dumps(final, indent=2), flush=True)


if __name__ == '__main__':
    main()
