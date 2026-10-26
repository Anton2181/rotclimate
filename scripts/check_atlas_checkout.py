"""Check staged atlas assets in a fresh checkout with Windows-style line endings."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import tempfile

ROOT=Path(__file__).resolve().parents[1]
if __name__=='__main__':
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--out',required=True,type=Path)
    ap.add_argument('--destination',type=Path,help='new persistent snapshot folder (must not exist)');a=ap.parse_args()
    if a.destination:
        snapshot=a.destination.resolve();snapshot.mkdir(parents=True,exist_ok=False)
    else:snapshot=Path(tempfile.mkdtemp(prefix='rotclimate-atlases-'))
    subprocess.run(['git','-c','core.autocrlf=true','checkout-index','--all','--prefix='+str(snapshot)+'/'],cwd=ROOT,check=True)
    assets=[]
    for name in ['free_fit','earth_fit','whittaker_fit','climate_accuracy']:
        for path in sorted((ROOT/'atlases'/name/'data').rglob('*')):
            if not path.is_file() or path.suffix not in {'.bin','.json','.webp','.png','.gif','.csv'}:continue
            relative=path.relative_to(ROOT);actual=hashlib.sha256(path.read_bytes()).hexdigest()
            assert hashlib.sha256((snapshot/relative).read_bytes()).hexdigest()==actual,str(relative)
            assets.append(dict(file=str(relative),sha256=actual))
    result=dict(status='passed',snapshot=str(snapshot),git_autocrlf=True,byte_exact_assets=len(assets),assets=assets)
    a.out.parent.mkdir(parents=True,exist_ok=True);a.out.write_text(json.dumps(result,indent=2)+'\n');print(snapshot)
