"""Staging copies of the Earth-fit atlas for downstream rebuilds (release 4).

    stage_atlas.py <out_dir> raw|corrected
raw: a copy of atlases/earth_fit. corrected: the same with data/corrected/* overlaid on data/ and atlas.json's climate keys
replaced by atlas.json["corrected_climate"]'s (as the release-3 downstream report describes); a --legacy exporter run on it
must reproduce the published corrected layers.
"""
import json, shutil, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]; SRC = ROOT / 'atlases/earth_fit'
KEYS = ('accuracy', 'arrays', 'binary', 'biomes', 'cell_px', 'foraging', 'gifs', 'harvest', 'koppen', 'lapse12', 'lapse_local', 'layers',
        'population', 'present', 'reach', 'score', 'zones')

if __name__ == '__main__':
    out, mode = Path(sys.argv[1]), sys.argv[2]
    if out.exists(): shutil.rmtree(out)
    shutil.copytree(SRC, out, symlinks=True)
    if mode == 'corrected':
        data = out / 'data'
        for f in (data / 'corrected').iterdir():
            if f.is_dir():
                shutil.rmtree(data / f.name, ignore_errors=True); shutil.copytree(f, data / f.name)
            else:
                shutil.copyfile(f, data / f.name)
        meta = json.loads((data / 'atlas.json').read_text()); c = meta['corrected_climate']
        for k in KEYS:
            if k in c: meta[k] = c[k]
        (data / 'atlas.json').write_text(json.dumps(meta))
    print('staged', out, mode)
