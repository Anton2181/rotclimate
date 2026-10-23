"""Build population-budget and market-access layers without rerunning climate."""
import argparse
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from population.export import export
if __name__=='__main__':
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('atlases',nargs='+');a=ap.parse_args()
    for atlas in a.atlases:export(ROOT/atlas)
