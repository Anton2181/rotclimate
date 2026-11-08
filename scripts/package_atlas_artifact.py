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


TIER_PART_BYTES = 8_000_000


def bundle_tiers(out: Path) -> dict | None:
    """The host caps the files per artifact (511), so the tier twins (*_tiers.webp, one per ramp image) go out
    concatenated in a few data/tiers_bundle_<k>.wasm parts; the page cuts each image out by offset
    (atlas/index.html tierImage). Returns the index {parts: [...], files: {"data/...": [part, offset, length]}}."""
    files = sorted(p for p in (out / "data").rglob("*_tiers.webp") if p.is_file())
    if not files:
        return None
    parts, index, chunks, size = [], {}, [], 0

    def flush():
        nonlocal chunks, size
        if chunks:
            name = f"tiers_bundle_{len(parts)}.wasm"
            (out / "data" / name).write_bytes(b"".join(chunks))
            parts.append(name)
            chunks, size = [], 0
    for path in files:
        raw = path.read_bytes()
        if size and size + len(raw) > TIER_PART_BYTES:
            flush()
        index[path.relative_to(out).as_posix()] = [len(parts), size, len(raw)]
        chunks.append(raw); size += len(raw)
        path.unlink()
    flush()
    return dict(parts=parts, files=index)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--atlas", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args()
    links = json.loads(LINKS.read_text()) if LINKS.exists() else {}
    if a.out.exists():
        shutil.rmtree(a.out)
    shutil.copytree(a.atlas, a.out)
    # .bin is not a served type; .wasm is. Packets named in atlas.json ("binary") go out
    # gzip-compressed (the page inflates them). Feature packets named in other manifests
    # (farm work, administration, pasture, ...) are hashed as fetched, so they keep raw bytes.
    page_packets = set()

    def collect(node, base):
        if isinstance(node, dict):
            b = str(node.get("binary", ""))
            if b.endswith(".bin"):
                page_packets.add((a.out / "data" / b).resolve())
            for value in node.values():
                collect(value, base)
        elif isinstance(node, list):
            for value in node:
                collect(value, base)
    collect(json.loads((a.out / "data" / "atlas.json").read_text()), None)
    page_packets.add((a.out / "data" / "atlas.bin").resolve())      # the page's own climate packet
    for path in a.out.rglob("*.bin"):
        raw = path.read_bytes()
        path.with_suffix(".wasm").write_bytes(gzip.compress(raw, 9, mtime=0) if path.resolve() in page_packets else raw)
        path.unlink()
    for path in a.out.rglob("*.npz"):          # model inputs for later exports (winds); no page reads them
        path.unlink()
    meta_path = a.out / "data" / "atlas.json"
    meta = json.loads(meta_path.read_text())
    # every packet the page fetches by its "binary" entry (harvest, population,
    # FORGE foraging, the Earth-corrected copies under corrected_food and any
    # later one) must follow its renamed file
    renamed, specs = [], {}

    def walk(node, path):
        if isinstance(node, dict):
            if str(node.get("binary", "")).endswith(".bin"):
                node["binary"] = node["binary"][:-4] + ".wasm"
                renamed.append(path); specs[path] = node
            for key, value in node.items():
                walk(value, f"{path}.{key}" if path else key)
    walk(meta, "")
    missing = [part for part in renamed if not (a.out / "data" / specs[part]["binary"]).is_file()]
    if missing:
        raise SystemExit(f"Renamed packet binaries are missing: {missing}")
    bundle = bundle_tiers(a.out)
    if bundle:
        meta["tiers_bundle"] = bundle
    meta_path.write_text(json.dumps(meta, ensure_ascii=False, separators=(",", ":")))
    # other packet manifests (farm work, administration, pasture, ...) name their binaries
    # relative to data/; follow the rename wherever the .wasm exists (source paths untouched)
    data_dir = a.out / "data"
    for manifest in data_dir.rglob("*.json"):
        if manifest == meta_path:
            continue
        text = manifest.read_text()
        fixed = re.sub(r'"([^"\s]+)\.bin"', lambda m: f'"{m.group(1)}.wasm"' if (data_dir / (m.group(1) + ".wasm")).is_file() else m.group(0), text)
        if fixed != text:
            manifest.write_text(fixed)
            renamed.append(str(manifest.relative_to(a.out)))
    page = a.out / "index.html"
    page.write_text(rewrite_nav(page.read_text(), links))
    files = sorted(p for p in a.out.rglob("*") if p.is_file())
    big = [(p.relative_to(a.out), p.stat().st_size) for p in files if p.stat().st_size > 15e6]
    total = sum(p.stat().st_size for p in files)
    print(f"{a.out}: {len(files)} files, {total / 1e6:.1f} MB; packets {renamed}" + (f"; over 15 MB: {big}" if big else ""))


if __name__ == "__main__":
    main()
