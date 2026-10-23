"""Add farming, health and c.200 AD settlement products to completed atlas data."""
import argparse
import fcntl
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from harvest.export import export
from population.export import export as export_population


if __name__=='__main__':
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('atlases',nargs='+')
    args=ap.parse_args()
    with (ROOT/'atlases/.build.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX)
        for atlas in args.atlases:
            export(atlas)
            export_population(atlas)
