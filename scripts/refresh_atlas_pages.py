"""Re-copy the atlas page template (atlas/index.html) into the separate atlases
in atlases/, keeping each one's heading. No simulation is re-run.

    python -I scripts/refresh_atlas_pages.py
"""
import argparse
import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parent))
from build_atlas_variant import page  # noqa: E402

PAGES = json.loads((ROOT / "atlases" / "pages.json").read_text())


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--staging',action='store_true',help='refresh completed _next directories instead')
    args=parser.parse_args()
    src = (ROOT / "atlas" / "index.html").read_text()
    for name, h in PAGES.items():
        out = ROOT / "atlases" / (name+'_next' if args.staging else name)
        if not out.exists():
            continue
        text=page(src, h["title"], h["eyebrow"], h["lede"], h["note"])
        if (out/'data/farm_work.json').exists():
            text=text.replace('<script src="farm-work.js"></script>','<script src="farm-work.js" data-farm-work-enabled></script>')
        if (out/'data/administrative_access.json').exists():
            text=text.replace('<script src="administration.js"></script>','<script src="administration.js" data-administration-enabled></script>')
        if (out/'data/administrative_hierarchy.json').exists():
            text=text.replace('<script src="administrative-hierarchy.js"></script>','<script src="administrative-hierarchy.js" data-hierarchy-enabled></script>')
        if (out/'data/pasture.json').exists():
            text=text.replace('<script src="pasture.js"></script>','<script src="pasture.js" data-pasture-enabled></script>')
        if (out/'data/coverage.json').exists():
            text=text.replace('<script src="coverage.js"></script>','<script src="coverage.js" data-coverage-enabled></script>')
        if (out/'data/presence_mobility.json').exists():
            text=text.replace('<script src="presence-mobility.js"></script>','<script src="presence-mobility.js" data-presence-mobility-enabled></script>')
        if (out/'data/settled_reach.json').exists():
            text=text.replace('<script src="settled-reach.js"></script>','<script src="settled-reach.js" data-settled-reach-enabled></script>')
        (out / "index.html").write_text(text)
        shutil.copy(ROOT / "atlas" / "climate-comparison.js", out / "climate-comparison.js")
        shutil.copy(ROOT / "atlas" / "harvest.js", out / "harvest.js")
        shutil.copy(ROOT / "atlas" / "farm-work.js", out / "farm-work.js")
        shutil.copy(ROOT / "atlas" / "administration.js", out / "administration.js")
        shutil.copy(ROOT / "atlas" / "administrative-hierarchy.js", out / "administrative-hierarchy.js")
        shutil.copy(ROOT / "atlas" / "pasture.js", out / "pasture.js")
        shutil.copy(ROOT / "atlas" / "coverage.js", out / "coverage.js")
        shutil.copy(ROOT / "atlas" / "presence-mobility.js", out / "presence-mobility.js")
        shutil.copy(ROOT / "atlas" / "settled-reach.js", out / "settled-reach.js")
        if (ROOT / "atlas" / "population.js").exists():
            shutil.copy(ROOT / "atlas" / "population.js", out / "population.js")
        if (ROOT / "atlas" / "foraging.js").exists():
            shutil.copy(ROOT / "atlas" / "foraging.js", out / "foraging.js")
        print("refreshed", out / "index.html")


if __name__ == "__main__":
    main()
