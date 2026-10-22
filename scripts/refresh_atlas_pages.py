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
        (out / "index.html").write_text(page(src, h["title"], h["eyebrow"], h["lede"], h["note"]))
        shutil.copy(ROOT / "atlas" / "climate-comparison.js", out / "climate-comparison.js")
        shutil.copy(ROOT / "atlas" / "harvest.js", out / "harvest.js")
        print("refreshed", out / "index.html")


if __name__ == "__main__":
    main()
