"""Install a corrected staging atlas's reach export into a raw staging atlas's data/corrected (release-4 chain on r49).

    install_corrected_reach.py <raw staging> <corrected staging>

After export_reach_release3.py on both staging copies (scripts/stage_atlas.py raw|corrected), every file of the corrected
staging's data/ that the published atlas keeps under data/corrected/ and that the export changed is copied into
<raw staging>/data/corrected/, and atlas.json's corrected_climate.reach takes the corrected export's reach metadata — the layout
add_corrected_climate.py gives the published atlas.
"""
import hashlib, json, shutil, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]; LIVE = ROOT / 'atlases/earth_fit/data/corrected'
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()

if __name__ == '__main__':
    raw, cor = Path(sys.argv[1]) / 'data', Path(sys.argv[2]) / 'data'; copied = []
    for live in sorted(LIVE.rglob('*')):
        if not live.is_file(): continue
        rel = live.relative_to(LIVE); src = cor / rel
        if src.is_file() and sha(src) != sha(live):
            dst = raw / 'corrected' / rel; dst.parent.mkdir(parents=True, exist_ok=True); shutil.copyfile(src, dst); copied.append(str(rel))
    meta = json.loads((raw / 'atlas.json').read_text()); cmeta = json.loads((cor / 'atlas.json').read_text())
    meta['corrected_climate']['reach'] = cmeta.get('reach')
    (raw / 'atlas.json').write_text(json.dumps(meta, ensure_ascii=False))
    print('installed', len(copied), 'corrected files:', ', '.join(copied))
