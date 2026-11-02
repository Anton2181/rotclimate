"""Content-keyed, atomic checkpoints for expensive deterministic trade exports."""
from pathlib import Path
import hashlib
import json
import os
import tempfile
import zipfile

import numpy as np
import scipy


def slot(directory, operation, nets, arrays, parameters):
    if directory is None:
        return None
    digest = hashlib.sha256()
    digest.update(json.dumps(dict(operation=operation, parameters=parameters,
        numpy=np.__version__, scipy=scipy.__version__), sort_keys=True, allow_nan=False).encode())
    # Graph inputs cover geography, population-dependent tracks and weather;
    # source hashes also invalidate checkpoints after algorithm changes.
    for source in sorted(Path(__file__).parent.glob('*.py')):
        digest.update(source.name.encode()); digest.update(source.read_bytes())
    def add(value):
        value = np.ascontiguousarray(value)
        digest.update(json.dumps([value.shape, value.dtype.str]).encode()); digest.update(value.tobytes())
    for net in nets:
        digest.update(json.dumps([net.base.shape, net.n_cells]).encode())
        for value in (net.base.data, net.base.indices, net.base.indptr,
                      getattr(net, 'river_cells', np.zeros(0, dtype=np.int64))):
            add(value)
    for value in arrays:
        add(value)
    identity = digest.hexdigest()
    path = Path(directory) / operation / (identity + '.npz')
    path.parent.mkdir(parents=True, exist_ok=True)
    return path, identity


def read(checkpoint):
    if checkpoint is None or not checkpoint[0].exists():
        return None
    path, identity = checkpoint
    try:
        with np.load(path, allow_pickle=False) as z:
            if str(z['identity']) != identity:
                return None
            return {key: z[key].copy() for key in z.files if key != 'identity'}
    except (OSError, ValueError, KeyError, EOFError, zipfile.BadZipFile):
        # A cache is optional. An interrupted/corrupt file never becomes data.
        return None


def write(checkpoint, **arrays):
    if checkpoint is None:
        return
    path, identity = checkpoint
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(dir=path.parent, suffix='.tmp', delete=False) as stream:
            temporary = Path(stream.name)
            np.savez(stream, identity=np.array(identity), **arrays)
        os.replace(temporary, path)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
