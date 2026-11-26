"""Restore public climate benchmark caches without running or changing a model."""
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import urllib.request
import zipfile

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'output/climate_runtime_20261126'


def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def fetch(job):
    path, url, expected = job
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        part = path.with_suffix(path.suffix + '.download')
        try:
            with urllib.request.urlopen(url, timeout=60) as response, part.open('wb') as stream:
                for block in iter(lambda: response.read(1024 * 1024), b''):
                    stream.write(block)
            if expected:
                assert sha(part) == expected, f'Source changed: {path.name}'
            if path.suffix == '.zip':
                with zipfile.ZipFile(part) as archive:
                    assert archive.testzip() is None
            part.replace(path)
        finally:
            part.unlink(missing_ok=True)
    digest = sha(path)
    if expected:
        assert digest == expected, f'Source changed: {path.name}'
    print('Verified', path.name, path.stat().st_size, flush=True)
    return dict(path=str(path.relative_to(ROOT)), url=url, sha256=digest, bytes=path.stat().st_size)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    spec = json.loads((ROOT / 'data/earth_harvest_public_sources_20261113.json').read_text())
    jobs = [(ROOT / r['path'], r['url'], r['sha256']) for r in spec['sources']
            if r['path'].endswith(('5m_tavg.zip', '5m_prec.zip', '5m_elev.zip'))]
    jobs.append((ROOT / 'data/cache/worldclim/wc2.1_5m_vapr.zip',
                 'https://geodata.ucdavis.edu/climate/worldclim/2_1/base/wc2.1_5m_vapr.zip',
                 '3e9c1a369057bcebb9b015e7411e0ba1205db15650adc932096de3c3facef5d8'))
    jobs.append((ROOT / 'data/cache/earth/ncep/pr_wtr.mon.ltm.nc',
                 'https://downloads.psl.noaa.gov/Datasets/ncep.reanalysis.derived/surface/pr_wtr.mon.ltm.nc', None))
    with ThreadPoolExecutor(max_workers=4) as pool:
        sources = list(pool.map(fetch, jobs))
    commands = [
        ['scripts/build_ncep_pw.py'],
        ['scripts/prepare_woa18.py', '--download', '--report', str(OUT / 'woa_receipt.json')],
        ['scripts/make_frozen_sea.py', 'data/cache/earth/woa18_sst_1deg.npz'],
    ]
    for args in commands:
        subprocess.run([sys.executable, '-I', *args], cwd=ROOT, check=True)
    from rotclimate import earth
    earth.west_fetch(1700.); earth.west_fetch(5100.); earth.pole_fetch(); earth.pole_fetch(frozen=True)
    earth.sea_reach(); earth.land_cloud(); earth.monsoon_descent(); earth.sea_depth()
    assert earth.sea_depth() is not None
    caches = {str(p.relative_to(ROOT)): sha(p) for p in sorted(earth.CACHE.glob('*.npz'))}
    receipt = dict(status='restored_public_climate_inputs_no_new_model_result', sources=sources,
                   producer_sha256=sha(Path(__file__)), cache_sha256=caches,
                   woa_receipt_sha256=sha(OUT / 'woa_receipt.json'),
                   atlas_rebuilt=False, climate_parameters_changed=False)
    (OUT / 'restoration.json').write_text(json.dumps(receipt, indent=2) + '\n')
    print('All shared caches ready before any regional run.', flush=True)


if __name__ == '__main__':
    sys.path.insert(0, str(ROOT))
    main()
