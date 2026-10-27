"""Build separate adapted FORGE products from completed atlas climate packets."""
import argparse
import fcntl
import json
from pathlib import Path
import shutil
import sys
import time
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from foraging.export import export
from foraging.validation import verify


def save(path,value):
    temporary=path.with_suffix('.tmp');temporary.write_text(json.dumps(value,indent=2,allow_nan=False)+'\n');temporary.replace(path)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('atlases',nargs='+')
    parser.add_argument('--coarsen',type=int,default=4)
    parser.add_argument('--chunk-cells',type=int,default=512)
    parser.add_argument('--years',type=int)
    parser.add_argument('--force',action='store_true')
    parser.add_argument('--staging',action='store_true',help='write isolated packets; do not alter live atlas files')
    parser.add_argument('--out',type=Path,default=ROOT/'output/foraging_20261027')
    args=parser.parse_args();args.out.mkdir(parents=True,exist_ok=True)
    status=dict(status='running',staging=args.staging,atlases={},coarsen=args.coarsen,chunk_cells=args.chunk_cells)
    status_path=args.out/'export_status.json';save(status_path,status);started=time.monotonic()
    try:
        with (ROOT/'atlases/.build.lock').open('a') as lock:
            fcntl.flock(lock,fcntl.LOCK_EX)
            for name in args.atlases:
                atlas=Path(name);atlas=atlas if atlas.is_absolute() else ROOT/atlas
                destination=atlas
                if args.staging:
                    destination=args.out/'staging'/atlas.name;(destination/'data').mkdir(parents=True,exist_ok=True)
                    for file in ['atlas.json','atlas.bin','harvest.json','harvest.bin']:
                        shutil.copyfile(atlas/'data'/file,destination/'data'/file)
                status['atlases'][atlas.name]=dict(status='running',destination=str(destination));save(status_path,status)
                info=export(destination,coarsen=args.coarsen,chunk_cells=args.chunk_cells,years=args.years,force=args.force)
                status['atlases'][atlas.name]=dict(status='passed',destination=str(destination),fingerprint=info['fingerprint'],
                    verification=verify(destination/'data'),summary=info['summary'],seconds=info['seconds'])
                status['elapsed_seconds']=time.monotonic()-started;save(status_path,status)
        status['status']='passed';status['elapsed_seconds']=time.monotonic()-started;save(status_path,status)
    except Exception as error:
        status['status']='failed';status['error']=repr(error);status['elapsed_seconds']=time.monotonic()-started;save(status_path,status)
        raise
