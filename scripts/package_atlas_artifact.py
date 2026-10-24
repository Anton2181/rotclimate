"""Copy an atlas into a folder ready to publish as a claude.ai artifact.

    python3 -I scripts/package_atlas_artifact.py --atlas atlases/earth_fit \
        --out output/artifact_pack/earth_fit

The host takes at most 15 MB per binary file and 64 MB per publish and does
not serve .bin files, so the arrays go out gzip-compressed as .wasm (the page
inflates them; raw files still load). Each atlas is its own artifact, so the links between the fits and to
the hub point at the artifact URLs in atlases/artifact_links.json; a fit
without a URL yet loses its link.
"""
from __future__ import annotations

import argparse
import gzip
import json
import re
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LINKS = ROOT / "atlases" / "artifact_links.json"
NAV_TARGETS = {"../": "hub", "../free_fit/": "free_fit", "../earth_fit/": "earth_fit",
               "../whittaker_fit/": "whittaker_fit"}


def rewrite_nav(html: str, links: dict) -> str:
    nav = re.search(r'(<nav class="atlas-nav"[^>]*>)(.*?)</nav>', html, re.S)
    if not nav:
        return html
    kept = []
    for href, attrs, label in re.findall(r'<a href="([^"]*)"([^>]*)>(.*?)</a>', nav.group(2)):
        key = NAV_TARGETS.get(href)
        if key is None:
            kept.append(f'<a href="{href}"{attrs}>{label}</a>')
        elif key in links:
            kept.append(f'<a href="{links[key]}"{attrs}>{label}</a>')
    return html.replace(nav.group(0), nav.group(1) + " ".join(kept) + "</nav>", 1)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--atlas", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args()
    links = json.loads(LINKS.read_text()) if LINKS.exists() else {}
    if a.out.exists():
        shutil.rmtree(a.out)
    shutil.copytree(a.atlas, a.out)
    for path in a.out.rglob("*.bin"):          # .bin is not a served type; .wasm is
        path.with_suffix(".wasm").write_bytes(gzip.compress(path.read_bytes(), 9, mtime=0))
        path.unlink()
    meta_path = a.out / "data" / "atlas.json"
    meta = json.loads(meta_path.read_text())
    for part in ("harvest", "population"):
        if meta.get(part, {}).get("binary", "").endswith(".bin"):
            meta[part]["binary"] = meta[part]["binary"][:-4] + ".wasm"
    meta_path.write_text(json.dumps(meta, ensure_ascii=False, separators=(",", ":")))
    page = a.out / "index.html"
    page.write_text(rewrite_nav(page.read_text(), links))
    files = sorted(p for p in a.out.rglob("*") if p.is_file())
    big = [(p.relative_to(a.out), p.stat().st_size) for p in files if p.stat().st_size > 15e6]
    total = sum(p.stat().st_size for p in files)
    print(f"{a.out}: {len(files)} files, {total / 1e6:.1f} MB" + (f"; over 15 MB: {big}" if big else ""))


if __name__ == "__main__":
    main()
