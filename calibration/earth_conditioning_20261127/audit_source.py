"""Record Earth conditioning from existing source; no imports or integrations."""
import ast
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
SOURCES = [
    'rotclimate/config.py', 'rotclimate/model.py', 'rotclimate/earth.py',
    'rotclimate/geography.py', 'rotclimate/temperature.py',
    'rotclimate/ebm.py', 'rotclimate/solver.py',
    'calibration/local_accuracy_20261023/r58_params.json',
    'calibration/local_accuracy_20261023/r58_adoption.json',
    'calibration/map_world_r51/params.json',
]
KEYS = ['edge_obs_pw', 'land_edge_rh', 'sst_source', 'cloud_reference',
        'monsoon_descent', 'convective_descent']
defaults = {}
for node in ast.walk(ast.parse((ROOT / SOURCES[0]).read_text())):
    if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
        if node.target.id in KEYS:
            defaults[node.target.id] = ast.literal_eval(node.value)
profiles = {}
for name in [SOURCES[7], SOURCES[9]]:
    saved = json.loads((ROOT / name).read_text())
    profiles[name] = {k: dict(value=saved.get(k, defaults[k]),
                             explicit=k in saved) for k in KEYS}
assert profiles[SOURCES[7]]['edge_obs_pw']['value'] > 0
assert profiles[SOURCES[9]]['edge_obs_pw']['value'] == 0
for profile in profiles.values():
    assert profile['sst_source']['value'] == 'model'
    assert profile['cloud_reference']['value'] == 'domain'
target_reads = []
target_scanned = [name for name in SOURCES[:7] if name != 'rotclimate/earth.py']
for name in target_scanned:
    tree = ast.parse((ROOT / name).read_text())
    for node in ast.walk(tree):
        if (isinstance(node, ast.Attribute) and node.attr == 'target'
                and isinstance(node.value, ast.Name) and node.value.id in ('g', 'grid')):
            target_reads.append(dict(source=name, line=node.lineno,
                statement=(ROOT / name).read_text().splitlines()[node.lineno - 1].strip()))
assert len(target_reads) == 1
assert target_reads[0]['source'] == 'rotclimate/model.py'
assert '.shape' in target_reads[0]['statement']
adoption = json.loads((ROOT / SOURCES[8]).read_text())
receipt = dict(status='static_source_scope_audit_not_transfer_validation',
    files_sha256={n: hashlib.sha256((ROOT / n).read_bytes()).hexdigest() for n in SOURCES},
    producer_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
    profiles=profiles, target_scanned_files=target_scanned,
    target_attribute_occurrences_in_scanned_files=target_reads,
    existing_adoption_atlas_note=adoption['atlas_note'], integrations=0,
    scope='Selected source files only; not a complete dynamic dependency or target-leak proof.',
    climate_adopted=False, atlas_changed=False)
destination = HERE / 'source_audit.json'
rendered = json.dumps(receipt, indent=2) + '\n'
if destination.exists():
    assert destination.read_text() == rendered, 'Preserve source epoch receipt'
else:
    destination.write_text(rendered)
print('Source scope checks passed; no integrations or source changes.')
