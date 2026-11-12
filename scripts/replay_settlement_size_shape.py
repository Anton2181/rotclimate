"""Fresh producer run of the size-shape comparison; require identical bytes."""
from pathlib import Path
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
from settlement_locations_earth import sha,write


def main():
    out=ROOT/'output/settlement_size_shape_20261112';fresh=out/'fresh';fresh.mkdir(exist_ok=True)
    subprocess.run([sys.executable,'-I',str(ROOT/'scripts/compare_settlement_size_shape.py'),'--out',str(fresh)],
                   cwd=ROOT,check=True,stdout=subprocess.DEVNULL)
    if (fresh/'results.json').read_bytes()!=(out/'results.json').read_bytes():raise ValueError('Fresh comparison differs from the reviewed result')
    write(out/'replay.json',dict(status='passed',results_sha256=sha(out/'results.json'),fresh_byte_exact=True))
    print('Fresh comparison byte exact.')


if __name__=='__main__':main()
