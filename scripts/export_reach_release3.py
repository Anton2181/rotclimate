"""Run the standard reach and trade exporter on a staging atlas.

    export_reach_release3.py <staging-atlas> [--legacy]

Without --legacy the standard town placement is routed to the reviewed
release-3 positions (polity.release3_placement). With --legacy the unmodified
exporter runs, as a control that must reproduce the published layers.
"""
import sys, time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]; sys.path[:0] = [str(ROOT), str(ROOT / 'scripts')]

if __name__ == '__main__':
    staging = Path(sys.argv[1]); legacy = '--legacy' in sys.argv
    used = None
    if not legacy:
        from polity.release3_placement import install
        used = install()
    from polity.export import export
    from add_market_views import render_views
    t = time.time(); export(staging)
    render_views(staging, ROOT / 'output/polity_map' / f'{staging.name}.npz')
    print('done', staging, 'legacy' if legacy else used, round(time.time() - t), 's', flush=True)
