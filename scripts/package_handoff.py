"""Create a portable analysis/development handoff without the historical archive."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import zipfile

ROOT = Path(__file__).resolve().parents[1]
SKIP = {'.DS_Store', '__pycache__', '.pytest_cache'}
TEXT_OUTPUT = {'.json', '.jsonl', '.md', '.log', '.csv', '.png', '.svg', '.py'}


def digest(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024*1024), b''):
            h.update(chunk)
    return h.hexdigest()


def select_files():
    chosen = {}
    for name in ('rotclimate', 'rotclimate_v10', 'experiments', 'scripts', 'tests',
                 'docs', 'reports', 'research_notes', 'calibration', 'atlas', 'data'):
        for path in (ROOT/name).rglob('*'):
            rel = path.relative_to(ROOT)
            if not path.is_file() or any(part in SKIP for part in rel.parts) or path.suffix == '.pyc':
                continue
            if name == 'data' and any(part in ('raw', 'cache', 'wmo_cache') for part in rel.parts):
                continue
            chosen[rel] = 'Source, documentation, atlas, settings or prepared input'
    for name in ('README.md', 'requirements.txt', '.gitignore'):
        chosen[Path(name)] = 'Project entry file'
    for path in (ROOT/'output').rglob('*'):
        rel = path.relative_to(ROOT)
        if not path.is_file() or path.suffix not in TEXT_OUTPUT:
            continue
        if any(part in SKIP or part.startswith('atlas_previous_') for part in rel.parts):
            continue
        # Completed annual evidence is retained where selected below. Obsolete
        # monthly-resume metadata is not useful in this partial archive.
        if path.name.endswith('_partial.json'):
            continue
        chosen[rel] = 'Historical summary, provenance, log or figure'
    latest = ROOT/'output/v10_regional_transport'
    state = json.loads((latest/'state.json').read_text())
    for key, row in state['cases'].items():
        for name in row['evidence_sha256']:
            chosen[(latest/'cases'/key/name).relative_to(ROOT)] = 'Latest completed annual evidence'
    parent = ROOT/'output/v10_spatial_humidity'
    state = json.loads((parent/'state.json').read_text())
    for key, row in state['cases'].items():
        if key.startswith('test_') and key.endswith('_local_matched'):
            for year in (row['years']-1, row['years']):
                chosen[(parent/'cases'/key/f'year{year}.npz').relative_to(ROOT)] = 'Paired source start/final anchor'
    for pattern in ('output/v10_*review*/*.npz', 'output/v10_cloud_lab/*.npz',
                    'output/v10_flux_transport_lab/*.npz', 'output/v10_regional_transport_preflight/*.npz'):
        for path in ROOT.glob(pattern):
            chosen[path.relative_to(ROOT)] = 'Saved diagnostic fields or manufactured evidence'
    chosen[Path('output/overnight_mediterranean/cases/anchor_warm2_fields.npz')] = 'Published V9 atlas anchor fields'
    return chosen


def portable_markdown(text, rel):
    prefix = str(ROOT)
    pattern = re.compile(r'\]\(<?('+re.escape(prefix)+r'/[^)\n]+?)>?\)')
    def link(match):
        target = match.group(1).rstrip('>')
        suffix = ''
        position = re.search(r':\d+$', target)
        if position:
            suffix = position.group(); target = target[:position.start()]
        target = os.path.relpath(target, ROOT/rel.parent)+suffix
        return ']('+('<'+target+'>' if ' ' in target else target)+')'
    return pattern.sub(link, text).replace(prefix, '<PROJECT_ROOT>')


START = """# Start here — lightweight climate project handoff

Read [the current handoff](reports/HANDOFF_20261016.md), then the
[verified latest analysis](output/v10_regional_transport_review/review.md).
The latest experiment stopped at **6/8 cases**; the production atlas is unchanged.

This is an analysis/development export, **not the full experiment archive**.
It includes:

- Source code, tests, requirements, research reports and calibration settings.
- The complete current atlas, source map layers and prepared Earth/monthly atmospheric inputs.
- Historical JSON summaries/manifests, logs and static figures.
- All 16 completed annual records from the latest transport attempt, eight paired
  source anchor checkpoints, diagnostic arrays, small numerical laboratories
  and the published V9 anchor's climate fields.

It omits the local Python environment, bytecode/test caches, raw downloaded
WorldClim/OISST archives, old atlas backups, animations, most historical binary
checkpoints and large generated weather-forcing tables. Nothing was removed
from the original project. EXPORT_MANIFEST.json lists retained hashes and
omitted file paths/sizes, so missing evidence can be located in the full copy.

## What can be done from this copy

Read reports and saved data, inspect/change code in a new branch/module, run
manufactured tests after installing dependencies, and view the existing atlas.
The saved annual arrays can be inspected directly with NumPy. Markdown links
have been made relative; original code, JSON provenance and atlas files retain
their exact bytes. Absolute paths inside original JSON are historical provenance.

The original strict annual reviewers and resume runners depend recursively on
omitted historical checkpoints/forcing. **They cannot fully verify or resume
from this lightweight copy.** This is expected missing evidence, not evidence
of corrupt physics or permission to relax an integrity check. In particular,
do not run scripts/review_v10_regional_transport.py here expecting its full
parent-chain verification to succeed. Read its already verified output instead.
Request specific omitted files from the full project if they become necessary.

The handoff's original safe-review command refers to the full workspace.
For this export, verify package contents without any climate simulation:

```sh
python3 verify_export.py
```

After installing Python dependencies, the existing atlas can be served with:

```sh
python3 -m http.server -d atlas
```

Open http://localhost:8000. Do not regenerate the atlas just to view it.
All real climate simulations/calibrations remain user-run. NOAA six-hourly
downloads remain paused. Preserve frozen evidence and use a new module/output
folder for changed physics. No new long run is recommended at this handoff.
"""

VERIFY = '''"""Verify retained export files only; no climate code or network calls."""
import hashlib
import json
from pathlib import Path
root = Path(__file__).resolve().parent
manifest = json.loads((root/'EXPORT_MANIFEST.json').read_text())
failures = []
for item in manifest['files']:
    path = root/item['path']
    if not path.is_file():
        failures.append(item['path']+': missing')
    elif hashlib.sha256(path.read_bytes()).hexdigest() != item['export_sha256']:
        failures.append(item['path']+': changed')
if failures:
    raise SystemExit('Export verification failed:\\n'+'\\n'.join(failures))
print(f"Verified {len(manifest['files'])} retained files. This is a partial archive; omitted files are listed in EXPORT_MANIFEST.json.")
'''


def build(destination):
    if destination.exists() or destination.with_suffix('.zip').exists():
        raise ValueError('Choose a new export name; existing exports are never overwritten.')
    chosen = select_files(); inventory = []
    for name in ('rotclimate', 'rotclimate_v10', 'experiments', 'scripts', 'tests',
                 'docs', 'reports', 'research_notes', 'calibration', 'atlas', 'data', 'output', '.venv', '.pytest_cache'):
        inventory.extend(p for p in (ROOT/name).rglob('*') if p.is_file())
    omitted = [{'path': str(p.relative_to(ROOT)), 'bytes': p.stat().st_size}
               for p in sorted(inventory) if p.relative_to(ROOT) not in chosen]
    destination.mkdir(parents=True)
    entries = []
    for rel, reason in sorted(chosen.items()):
        source = ROOT/rel; target = destination/rel
        target.parent.mkdir(parents=True, exist_ok=True)
        original = digest(source)
        shutil.copy2(source, target)
        if digest(target) != original:
            raise ValueError('Copy verification failed: '+str(rel))
        if source.suffix.lower() == '.md':
            text = portable_markdown(target.read_text(), rel)
            if rel == Path('reports/HANDOFF_20261016.md'):
                text = ('> Lightweight export: first read [START_HERE.md](../START_HERE.md). '
                        'Some historical binary evidence is intentionally omitted; full-chain '
                        'review/resume commands require the original workspace.\n\n')+text
            target.write_text(text)
        entries.append({'path': str(rel), 'bytes': target.stat().st_size, 'source_sha256': original,
                        'export_sha256': digest(target), 'reason': reason})
    for name, content in (('START_HERE.md', START), ('verify_export.py', VERIFY)):
        path = destination/name; path.write_text(content)
        entries.append({'path': name, 'bytes': path.stat().st_size, 'export_sha256': digest(path),
                        'reason': 'Export-specific entry/verification file'})
    manifest = {'schema': 1, 'kind': 'partial_analysis_development_handoff',
                'source_project': str(ROOT), 'date': '2026-10-16',
                'files': entries, 'omitted': omitted,
                'retained_bytes_without_manifest': sum(e['bytes'] for e in entries),
                'omitted_bytes': sum(e['bytes'] for e in omitted),
                'note': 'Code/JSON/atlas remain exact; Markdown links/paths were made portable. The full historical evidence chain is not included.'}
    (destination/'EXPORT_MANIFEST.json').write_text(json.dumps(manifest, indent=2)+'\n')
    # Confirm source files did not change during copying. This never mutates them.
    for entry in entries:
        if 'source_sha256' in entry and digest(ROOT/entry['path']) != entry['source_sha256']:
            raise ValueError('Source changed during export: '+entry['path'])
    archive = destination.with_suffix('.zip')
    with zipfile.ZipFile(archive, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=6) as z:
        for path in sorted(destination.rglob('*')):
            if path.is_file():
                z.write(path, str(Path(destination.name)/path.relative_to(destination)))
    with zipfile.ZipFile(archive) as z:
        if z.testzip() is not None:
            raise ValueError('Export ZIP integrity check failed.')
    print(json.dumps({'folder': str(destination), 'zip': str(archive), 'files': len(entries)+1,
                      'folder_mib': sum(p.stat().st_size for p in destination.rglob('*') if p.is_file())/1024**2,
                      'zip_mib': archive.stat().st_size/1024**2,
                      'omitted_mib': manifest['omitted_bytes']/1024**2}, indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, default=ROOT/'exports/rotclimate-handoff-20261016')
    args = parser.parse_args()
    destination = args.out.resolve()
    if destination == ROOT or destination in ROOT.parents:
        raise ValueError('Export must be separate from the original project.')
    build(destination)
