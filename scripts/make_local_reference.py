"""Build paired reference runs for screen_v6 in THIS container (same caches as the candidates), named NAME_<part>.

    .venv/bin/python -I scripts/make_local_reference.py PARAMS OUT_DIR NAME
Parts: dev31, retired_a/b/c, tropical_t, sealed_r, sealed_S18, sealed_U18 (the 97-region v6 pool).
Needed when the stored reference was made in another container whose derived caches differ (case_identity)."""
import json, subprocess, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
PY = str(ROOT / '.venv/bin/python')
PARTS = {'dev31': None, 'retired_a': 'calibration/sealed_20261031/regions.json', 'retired_b': 'calibration/sealed_20261031b/regions.json',
         'retired_c': 'calibration/sealed_20261101c/regions.json', 'tropical_t': 'calibration/tropical_check_20261122t/regions.json',
         'sealed_r': 'calibration/sealed_20261122r/regions.json', 'sealed_S18': 'calibration/sealed_20261123S18/regions.json',
         'sealed_U18': 'calibration/sealed_20261124U18/regions.json'}
params, out, name = Path(sys.argv[1]), Path(sys.argv[2]), sys.argv[3]
out.mkdir(parents=True, exist_ok=True)
(out / f'{name}_params.json').write_text(params.read_text())
for part, spec in PARTS.items():
    o = out / f'{name}_{part}'
    if (o / 'summary.json').is_file():
        continue
    regs = ['dev31'] if spec is None else list(json.loads((ROOT / spec).read_text()))
    cmd = [PY, '-I', str(ROOT / 'scripts/benchmark_local.py'), '--fit', str(ROOT / params), '--regions', *regs, '--workers', '4', '--out', str(o)]
    if spec:
        cmd += ['--region-specs', str(ROOT / spec)]
    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    print(part, 'done', flush=True)
