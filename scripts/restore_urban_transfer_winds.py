"""Recover only the three previously exposed annual-control wind inputs."""
import concurrent.futures
import hashlib
import json
from pathlib import Path
import subprocess
import urllib.request
import urllib.parse

import numpy as np
from prepare_ncep_reference import BASE, parse

ROOT = Path(__file__).resolve().parents[1]
PLAN = ROOT / 'calibration/urban_diagnosis_20261116/seasonal_transfer_wind_restoration.json'
CACHE = ROOT / 'data/cache/ncep_ltm'
OUT = ROOT / 'output/urban_seasonal_transfer_20261116'


def sha(p):
    with p.open('rb') as f:
        return hashlib.file_digest(f, 'sha256').hexdigest()


def recover(var):
    url = f'{BASE}{var}.sig995.mon.ltm.nc.ascii?{var}[0:1:11][0:1:72][0:1:143]'
    path = CACHE / f'{var}.sig995.ascii'
    if not path.exists():
        request = urllib.request.Request(urllib.parse.quote(url, safe=':/?='), headers={'User-Agent': 'rotclimate-reference/1.0'})
        with urllib.request.urlopen(request, timeout=45) as response:
            content = response.read()
        # Validate before writing any cache file.
        parse(content.decode(), var)
        path.write_bytes(content)
    array = parse(path.read_text(), var)
    return var, array, dict(path=str(path.relative_to(ROOT)), url=url, sha256=sha(path),
                           dtype=str(array.dtype), shape=list(array.shape))


def main():
    assert subprocess.check_output(['git', 'show', 'HEAD:'+str(PLAN.relative_to(ROOT))], cwd=ROOT) == PLAN.read_bytes()
    CACHE.mkdir(parents=True, exist_ok=True); OUT.mkdir(parents=True, exist_ok=True)
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
        rows = list(pool.map(recover, ['uwnd', 'vwnd', 'wspd']))
    arrays = {var: a for var, a, _ in rows}
    fallback = CACHE / 'ncep_surface_ltm.npz'
    if not fallback.exists():
        np.savez_compressed(fallback, u=arrays['uwnd'], v=arrays['vwnd'],
                            lat=90 - 2.5*np.arange(73), lon=2.5*np.arange(144))
    with np.load(fallback) as z:
        np.testing.assert_array_equal(z['u'], arrays['uwnd'])
        np.testing.assert_array_equal(z['v'], arrays['vwnd'])
    receipt = dict(status='recovered_public_winds_annual_identity_not_yet_qualified',
                   plan_sha256=sha(PLAN), producer_sha256=sha(Path(__file__)),
                   parser_sha256=sha(ROOT/'scripts/prepare_ncep_reference.py'),
                   sources=[r for _, _, r in rows], fallback_sha256=sha(fallback),
                   original_ignored_wind_hashes_available=False,
                   metadata_note='Existing reader docstring says 1981–2010; fallback preparation docstring says 1991–2020. URLs are unversioned. No historical period identity inferred from either label.',
                   annual_replay_required=True, new_fit=False, adopt=False)
    (OUT/'wind_restoration.json').write_text(json.dumps(receipt, indent=2)+'\n')
    print(receipt['status'], flush=True)


if __name__ == '__main__':
    main()
