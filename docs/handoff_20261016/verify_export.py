"""Verify retained export files only; no climate code or network calls."""
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
    raise SystemExit('Export verification failed:\n'+'\n'.join(failures))
print(f"Verified {len(manifest['files'])} retained files. This is a partial archive; omitted files are listed in EXPORT_MANIFEST.json.")
