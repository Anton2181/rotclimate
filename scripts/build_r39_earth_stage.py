"""Build a qualified r39 world into staging and verify its complete atlas packet."""
from pathlib import Path
import json
import subprocess
import sys
import argparse

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT));sys.path.insert(0,str(ROOT/'scripts'))
import numpy as np
from PIL import Image
from harvest.validation import verify as verify_food
from population.validation import verify as verify_population
from local_benchmark_protocol import file_hash,write_json


def layer_files(node,asset=False):
    if isinstance(node,dict):
        for key,value in node.items():yield from layer_files(value,asset or key in {'file','files','scenario_files','binary','download'})
    elif isinstance(node,list):
        for value in node:yield from layer_files(value,asset)
    elif asset and isinstance(node,str) and node and '://' not in node:
        yield node


def verify_packet(data,meta):
    data=Path(data);blob=(data/'atlas.bin').read_bytes();end=0
    for name,spec in sorted(meta['arrays'].items(),key=lambda item:item[1]['offset']):
        size=int(np.prod(spec['shape']))*np.dtype(spec['dtype']).itemsize;offset=spec['offset']
        if offset!=end or offset+size>len(blob):raise ValueError('Truncated or inconsistent climate binary: '+name)
        end=offset+size
    if end!=len(blob):raise ValueError('Unexpected bytes after climate arrays')
    assets=set(layer_files(meta['layers']))
    mapped_assets=assets.copy()
    for key in ['surroundings_sensitivity','initialization_check']:
        diagnostic=meta.get(key,{})
        assets.update(diagnostic[name] for name in ['metadata','download','image'] if diagnostic.get(name))
    for name in assets:
        path=data/name
        if not path.resolve().is_relative_to(data.resolve()) or not path.is_file() or not path.stat().st_size:
            raise ValueError('Missing or invalid layer asset: '+name)
        if path.suffix.lower() in {'.webp','.png','.gif','.jpg'}:
            with Image.open(path) as image:
                # Climate maps may be rendered at 2x the coordinate grid;
                # economic maps use its native size. Preserve the aspect,
                # allowing half a row for integer resampling.
                width,height=image.size
                if width<1 or height<1 or (name in mapped_assets and abs(height-width*meta['height']/meta['width'])>.51):
                    raise ValueError('Wrong map dimensions: '+name)
                image.verify()
    return dict(status='passed',climate_bytes=len(blob),layer_assets=len(assets),climate_sha256=file_hash(data/'atlas.bin'))


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--review',type=Path,default=ROOT/'output/r39_world_publication/review.json')
    args=ap.parse_args();root=args.review.resolve().parent;review=json.loads(args.review.read_text())
    if not review.get('eligible_for_publication'):
        print('No qualified world; canonical atlas remains unchanged.',flush=True);return
    name='earth_fit_r39_next';stage=ROOT/'atlases'/name
    command=[sys.executable,'-u','-I',str(ROOT/'scripts/build_atlas_variant.py'),
        '--params',review['params'],'--name',name,'--title','Rotclimate Earth-Fit Atlas',
        '--eyebrow','Climate, farming and settlement · three layouts · c.200 AD',
        '--note','Only world properties fitted; Earth r39 physics held fixed. Planetary size, spin, tilt, orbit and stellar input remain those of the preceding atlas. Climate averages surroundings layouts 1–3, with verified numerical checks and additional-layout transfer checks. Farming and population use low-input c.200 AD settlement scenarios.',
        '--downsample','8','--image-scale','2','--seeds','1,2,3','--workers','2',
        '--fit-objective','zonefit','--require-verified','--checkpoint',review['checkpoint']]
    print('Building staging Earth atlas from the verified native checkpoint',flush=True)
    subprocess.run(command,cwd=ROOT,check=True)
    meta=json.loads((stage/'data/atlas.json').read_text());summary=json.loads((stage/'summary.json').read_text())
    checkpoint_name=Path(review['checkpoint']).stem
    expected=next(row['metrics'] for row in review['native'] if row['name']==checkpoint_name)
    if abs(summary['zonefit']-expected['zonefit'])>1e-12 or abs(summary['strict_accuracy']-expected['accuracy'])>1e-12:
        raise ValueError('Staged climate does not reproduce qualified native scores')
    if not summary['observed_numerics']['all_checks_passed']:raise ValueError('Unverified staging climate')
    packet=verify_packet(stage/'data',meta)
    food=verify_food(stage/'data',meta);population=verify_population(stage/'data',meta)
    trade=next(layer for layer in meta['layers'] if layer['id']=='reach_trade')
    if meta['reach']['trade']['model']!='inbound-directed' or len(trade['variants']['options'])!=3:
        raise ValueError('Current directed-market views are missing')
    write_json(root/'staging_verification.json',dict(status='passed',stage=str(stage.relative_to(ROOT)),
        packet=packet,food=food,population=population,metadata_sha256=file_hash(stage/'data/atlas.json'),
        params_sha256=file_hash(stage/'params.json'),note='Staging only; browser verification and canonical promotion remain.'))
    print('Staging packet, food budget and population checks passed.',flush=True)


if __name__=='__main__':main()
