"""Check staged atlas assets in a fresh checkout with Windows-style line endings."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import tempfile

ROOT=Path(__file__).resolve().parents[1]


def check(snapshot,*,retained):
    # Only the independently served site and launcher are needed. Copying every
    # tracked experiment/plot unnecessarily exhausted the small /tmp filesystem.
    paths=subprocess.run(['git','ls-files','-z','--','atlases','reports','docs','scripts/serve_atlases.py',
        'start_atlases.bat','start_atlases.command','.gitattributes'],cwd=ROOT,
        capture_output=True,check=True).stdout
    subprocess.run(['git','-c','core.autocrlf=true','checkout-index','-z','--stdin',
        '--prefix='+str(snapshot)+'/'],input=paths,cwd=ROOT,capture_output=True,check=True)
    assets=[]
    for name in ['free_fit','earth_fit','whittaker_fit','climate_accuracy']:
        for path in sorted((ROOT/'atlases'/name/'data').rglob('*')):
            if not path.is_file() or path.suffix not in {'.bin','.json','.webp','.png','.gif','.csv','.npz'}:continue
            relative=path.relative_to(ROOT);actual=hashlib.sha256(path.read_bytes()).hexdigest()
            assert hashlib.sha256((snapshot/relative).read_bytes()).hexdigest()==actual,str(relative)
            assets.append(dict(file=str(relative),sha256=actual))
    return dict(status='passed',snapshot=str(snapshot),snapshot_retained=retained,
        scope='tracked atlas site, documentation and standard-library launcher; no calibration outputs',
        git_autocrlf=True,byte_exact_assets=len(assets),assets=assets)


def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--out',required=True,type=Path)
    ap.add_argument('--destination',type=Path,help='new persistent snapshot folder (must not exist)');a=ap.parse_args()
    if a.destination:
        snapshot=a.destination.resolve();snapshot.mkdir(parents=True,exist_ok=False)
        result=check(snapshot,retained=True)
    else:
        # The default is a verification scratch copy, automatically removed on
        # success AND failure. Explicit --destination still supports browsers.
        with tempfile.TemporaryDirectory(prefix='atlas-check-',dir=ROOT/'output') as directory:
            result=check(Path(directory),retained=False)
    a.out.parent.mkdir(parents=True,exist_ok=True);a.out.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({key:value for key,value in result.items() if key!='assets'},indent=2))


if __name__=='__main__':main()
