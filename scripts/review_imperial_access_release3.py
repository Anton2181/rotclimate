"""Rerun the imperial access audit on release-3 towns without touching the original audit.

Executes scripts/review_imperial_access.py unchanged except for its output
folder, after routing town placement to the reviewed release-3 positions.
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]; sys.path[:0] = [str(ROOT), str(ROOT / 'scripts')]
from polity.release3_placement import install

OLD = "out=ROOT/'output/imperial_access_20261104'"
NEW = "out=ROOT/'output/imperial_access_release3_20261113'"

if __name__ == '__main__':
    source = (ROOT / 'scripts/review_imperial_access.py').read_text()
    if source.count(OLD) != 1:
        raise ValueError('Original audit layout changed')
    used = install()
    exec(compile(source.replace(OLD, NEW), str(ROOT / 'scripts/review_imperial_access.py'), 'exec'),
         {'__name__': '__main__', '__file__': str(ROOT / 'scripts/review_imperial_access.py')})
    print('release-3 placements used:', used)
