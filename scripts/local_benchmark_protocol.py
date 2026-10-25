"""Input identity and atomic records for per-location Earth experiments."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np


def file_hash(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda:stream.read(1024*1024), b''):
            digest.update(block)
    return digest.hexdigest()


def identity(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, allow_nan=False).encode()).hexdigest()


def write_json(path, value):
    path = Path(path)
    temporary = path.with_suffix('.tmp')
    temporary.write_text(json.dumps(value, indent=2, allow_nan=False)+'\n')
    temporary.replace(path)


def freeze(path, value):
    """Never reinterpret a folder's previous results under different inputs."""
    path = Path(path)
    value = json.loads(json.dumps(value, allow_nan=False))
    if path.exists() and json.loads(path.read_text()) != value:
        raise ValueError('Frozen benchmark inputs changed; choose a new output directory')
    if not path.exists() and ((path.parent/'summary.json').exists() or
                              any((path.parent/'cells').glob('*.npz'))):
        raise ValueError('Existing benchmark has no manifest; preserve it and choose a new output directory')
    write_json(path, value)
    return identity(value)


def case_hash(case, *, observed_sea=False):
    """Hash actual model inputs, independent of NPZ compression and timestamps."""
    g = case.grid
    arrays = {k:getattr(g,k) for k in ['land', 'land_frac', 'elev', 'elev_max', 'lat', 'inmap',
                                      'target', 'chi_far', 'chi_far_long']}
    # Later physics uses polar fetch, ocean connections, cloud references,
    # remote monsoon forcing and shelf depths. Their actual derived fields
    # matter even if the raw observational archives have not changed.
    arrays.update({k:getattr(g,k,None) for k in ['chi_pole', 'sea_reach', 'cloud_ref', 'descent', 'sea_depth']})
    arrays.update(obs_T=case.obs_T, obs_P=case.obs_P, lon=case.lon, coast_km=case.coast_km)
    if observed_sea: arrays['obs_sst'] = g.obs_sst
    digest = hashlib.sha256()
    digest.update(json.dumps(dict(cell_km=g.cell_km, pad=g.pad), sort_keys=True).encode())
    for name, array in sorted(arrays.items()):
        if array is None:
            digest.update((name+':null').encode()); continue
        array = np.ascontiguousarray(array)
        digest.update(json.dumps([name, array.shape, array.dtype.str]).encode())
        digest.update(array.tobytes())
    return digest.hexdigest()


def reusable(path, run_identity, grid_identity, cells):
    if not path.exists() or not cells.exists(): return None
    row = json.loads(path.read_text())
    if row.get('identity') != run_identity or row.get('case_identity') != grid_identity:
        raise ValueError('Saved regional inputs differ: '+str(path))
    if (row.get('status') == 'passed' and row.get('numerics', {}).get('all_checks_passed') is True
            and row.get('cells_sha256') == file_hash(cells)):
        return row
    return None
