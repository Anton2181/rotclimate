"""Build a reviewable patch and isolated copies; never edit active physics."""
import difflib
import json
from pathlib import Path
import shutil
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from local_benchmark_protocol import file_hash, freeze

PLAN = ROOT / 'calibration/marine_budget_export_patch_20261126/plan.json'
OUT = ROOT / 'output/marine_budget_export_patch_20261126'


def replace_once(text, old, new):
    assert text.count(old) == 1, old
    return text.replace(old, new, 1)


def main():
    plan = json.loads(PLAN.read_text())
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / '.gitignore').write_text('baseline/\npatched/\n!**/fields.npz\n')
    sources = {**plan['base_model_sources_sha256'], **plan['regression_sources_sha256']}
    sources['scripts/local_benchmark_protocol.py'] = file_hash(ROOT / 'scripts/local_benchmark_protocol.py')
    for name, digest in sources.items():
        assert file_hash(ROOT / name) == digest, name
        for label in ['baseline', 'patched']:
            path = OUT / label / name
            path.parent.mkdir(parents=True, exist_ok=True)
            if path.exists():
                # Do not overwrite an already validated/modified private tree.
                continue
            shutil.copyfile(ROOT / name, path)
    changes = {}
    name = 'rotclimate/model.py'
    text = (ROOT / name).read_text()
    text = replace_once(text, "'evaporation', 'column_drying', 'monsoon_drying', 'convergence_import')}",
        "'evaporation', 'marine_exchange', 'column_drying', 'monsoon_drying', 'convergence_import')}")
    marker = "            if p.moisture_transport_form == 'flux':\n                from .transport import flux_budget"
    text = replace_once(text, marker,
        "            if budget is not None or p.moisture_transport_form == 'flux':\n"
        "                # Surface E omits single-column land humidity relaxation.\n"
        "                # Independent reservoirs already include it in their E.\n"
        "                marine_exchange = (np.zeros_like(W) if p.moisture_reservoirs else\n"
        "                    np.where(land, ocean_rate(p, lamE, W, W_ocean) * (W_ocean - W) * DAY, 0.0))\n" + marker)
    text = replace_once(text, '                net=E if sink is None else E-sink*W*DAY',
        '                net=E+marine_exchange\n                if sink is not None:net=net-sink*W*DAY')
    text = replace_once(text,
        '                    E_net = E if sink is None else E - sink * W * DAY      # subsidence drying as negative evaporation',
        '                    E_net = E + marine_exchange\n'
        '                    if sink is not None:E_net = E_net - sink * W * DAY  # subsidence drying as negative evaporation')
    text = replace_once(text, "                    terms['evaporation'] = E\n",
        "                    terms['evaporation'] = E\n                    terms['marine_exchange'] = marine_exchange\n")
    changes[name] = text
    name = 'rotclimate/transport.py'
    text = (ROOT / name).read_text()
    text = replace_once(text, "('column_drying', 'convergence_import')", "('marine_exchange', 'column_drying', 'convergence_import')")
    text = replace_once(text, 'residual = evaporation + column_drying + convergence_import + transport sources - rain.',
        'residual = evaporation + marine_exchange + column_drying + convergence_import + transport sources - rain.')
    text = replace_once(text, 'Older archives without these two components cannot reconstruct active drying/import.',
        'Older archives may omit source components and cannot be assumed to reconstruct the full active equation.')
    text = replace_once(text, '    return dict(note=note,zones=zones)',
        "    note+=' The optional marine_exchange component is signed single-column land humidity relaxation beyond surface E; independent reservoirs already include it in evaporation, so their additional component is zero.'\n"
        '    return dict(note=note,zones=zones)')
    changes[name] = text
    patch = ''
    for name, text in changes.items():
        patch += ''.join(difflib.unified_diff((ROOT / name).read_text().splitlines(keepends=True), text.splitlines(keepends=True),
                                             fromfile='a/' + name, tofile='b/' + name))
        path = OUT / 'patched' / name
        if path.read_text() != (ROOT / name).read_text():
            assert path.read_text() == text, 'Private patch changed: ' + name
        else:
            path.write_text(text)
    patch_path = PLAN.parent / 'marine_budget.patch'
    if patch_path.exists():
        assert patch_path.read_text() == patch
    else:
        patch_path.write_text(patch)
    for label in ['baseline', 'patched']:
        (OUT / label / 'pytest.ini').write_text('[pytest]\npythonpath = . tests\n')
    freeze(OUT / 'preparation.json', dict(plan_sha256=file_hash(PLAN), preparer_sha256=file_hash(Path(__file__)),
        sources_sha256=sources, patch_sha256=file_hash(patch_path),
        patched_sources_sha256={name:file_hash(OUT / 'patched' / name) for name in plan['base_model_sources_sha256']},
        main_physical_source_unchanged=True, padding_snapshot_unchanged=True))
    print('Prepared private baseline/patch; main source unchanged.')


if __name__ == '__main__':
    main()
