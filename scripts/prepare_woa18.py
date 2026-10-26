"""Check or prepare the complete monthly WOA18 ocean-temperature reference.

Default is read-only. --download retrieves missing public NOAA files and builds
a missing cache. --rebuild explicitly replaces a stale derived cache. The
normal atlas launcher does not need this tool or its scientific dependencies.
"""
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import argparse
import gzip
import hashlib
import json
import subprocess
import sys
import urllib.request

import numpy as np

ROOT=Path(__file__).resolve().parents[1]
BASE='https://www.ncei.noaa.gov/data/oceans/woa/WOA18/DATA/temperature/csv/decav/1.00/'
NAMES=[f'woa18_decav_t{month:02d}an01.csv.gz' for month in range(1,13)]


def sha(path):
    digest=hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda:stream.read(1024*1024),b''):
            digest.update(block)
    return digest.hexdigest()


def raw_sources(folder):
    missing=[name for name in NAMES if not (folder/name).is_file()]
    if missing:
        raise ValueError('Incomplete monthly WOA18 sources: '+', '.join(missing))
    return {name:sha(folder/name) for name in NAMES}


def check(cache,sources):
    with np.load(cache,allow_pickle=False) as arrays:
        required={'sst','lat','lon','sources'}
        if not required<=set(arrays.files):
            raise ValueError('WOA18 cache lacks fields or source provenance')
        sst=arrays['sst']
        if sst.shape!=(12,180,360) or np.isinf(sst).any():
            raise ValueError('Invalid monthly WOA18 grid')
        finite=np.isfinite(sst)
        if (finite.sum((1,2))<10000).any() or (sst[finite]<=-3).any() or (sst[finite]>=40).any():
            raise ValueError('Incomplete or out-of-range WOA18 temperatures')
        if not np.array_equal(arrays['lat'],np.arange(180)-89.5) or not np.array_equal(arrays['lon'],np.arange(360)-179.5):
            raise ValueError('Unexpected WOA18 coordinate grid')
        stored=arrays['sources']
        if stored.shape!=(12,2) or len(set(stored[:,0]))!=12 or dict(stored.tolist())!=sources:
            raise ValueError('WOA18 cache and raw monthly source checksums differ')
    return dict(status='passed',monthly_ocean_cells=finite.sum((1,2)).tolist(),
                cache_sha256=sha(cache),source_sha256=sources,
                source_url=BASE,reference='WOA18 objectively analyzed temperature, all decades, 1 degree, surface level')


def fetch_missing(folder,name):
    path=folder/name
    if path.exists():
        return
    temporary=path.with_suffix('.download')
    try:
        with urllib.request.urlopen(BASE+name,timeout=45) as response, temporary.open('wb') as stream:
            count=0
            for block in iter(lambda:response.read(1024*1024),b''):
                count+=len(block)
                if count>32*1024*1024:
                    raise ValueError('Unexpectedly large WOA18 download')
                stream.write(block)
        # Validate the full gzip stream and CRC before publishing a raw file.
        with gzip.open(temporary,'rb') as stream:
            for _ in iter(lambda:stream.read(1024*1024),b''):
                pass
        temporary.replace(path)
    except Exception:
        temporary.unlink(missing_ok=True)
        raise


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source',type=Path,default=ROOT/'data/cache/woa18')
    parser.add_argument('--cache',type=Path,default=ROOT/'data/cache/earth/woa18_sst_1deg.npz')
    parser.add_argument('--download',action='store_true',help='download missing NOAA sources and build a missing cache')
    parser.add_argument('--rebuild',action='store_true',help='explicitly rebuild the derived cache after a source revision')
    parser.add_argument('--report',type=Path)
    args=parser.parse_args()
    if args.download:
        args.source.mkdir(parents=True,exist_ok=True)
        with ThreadPoolExecutor(max_workers=3) as pool:
            list(pool.map(lambda name:fetch_missing(args.source,name),NAMES))
    try:
        sources=raw_sources(args.source)
        if args.rebuild or (args.download and not args.cache.exists()):
            args.cache.parent.mkdir(parents=True,exist_ok=True)
            temporary=args.cache.with_name(args.cache.stem+'.building.npz')
            try:
                subprocess.run([sys.executable,'-I',str(ROOT/'scripts/build_woa_sst.py'),
                                str(args.source),str(temporary)],check=True)
                check(temporary,sources)
                temporary.replace(args.cache)
            finally:
                temporary.unlink(missing_ok=True)
        if not args.cache.exists():
            parser.error('Monthly sources exist but SST cache is missing; use --download to build it')
        result=check(args.cache,sources)
    except ValueError as error:
        parser.error(str(error)+'; use --download for missing sources, or --rebuild after a deliberate data revision')
    if args.report:
        args.report.parent.mkdir(parents=True,exist_ok=True)
        args.report.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))


if __name__=='__main__':main()
