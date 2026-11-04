"""Match the owner's commanderies and icon key against actual map inputs."""
from pathlib import Path
import json
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'scripts')]


def main():
    import numpy as np
    from PIL import Image
    from scipy import ndimage as ndi
    from collections import Counter
    from polity.administration import named_markers,match_commanderies,legion_markers,name_key
    from local_benchmark_protocol import file_hash,write_json
    sources=['data/imperial_administration.json','data/imperial_datasheet_evidence.json','data/source/ravages_v8/settlements.png',
        'data/source/ravages_v8/legions.png','ravages/data.json','atlases/earth_fit/data/atlas.json',
        'polity/administration.py','scripts/audit_administrative_inventory.py']
    authority=json.loads((ROOT/'data/imperial_administration.json').read_text())
    evidence=json.loads((ROOT/'data/imperial_datasheet_evidence.json').read_text())
    meta=json.loads((ROOT/'atlases/earth_fit/data/atlas.json').read_text())
    sheet=json.loads((ROOT/'ravages/data.json').read_text())
    pixels=np.asarray(Image.open(ROOT/'data/source/ravages_v8/settlements.png').convert('RGBA'))
    markers=named_markers(pixels,meta['places'],meta['width'],meta['height'])
    for marker in markers:
        marker['datasheet_records']=[t for t in evidence['towns'] if name_key(t['name'])==name_key(marker['name'])]
        rows=[t for t in sheet['towns'] if name_key(t[1])==name_key(marker['name'])]
        if not marker['symbol_verified'] and len(rows)==1 and rows[0][2]=='Elder Village':
            marker.update(kind='unmarked village',source_hex=int(rows[0][0]),
                coordinate_basis='existing name-list position; no matching stronghold symbol')
    commanderies=match_commanderies(authority['commanderies'],markers,sheet,evidence)
    legions=legion_markers(np.asarray(Image.open(ROOT/'data/source/ravages_v8/legions.png').convert('RGBA')),meta['width'],meta['height'])
    labels,components=ndi.label(pixels[...,3]>0);overlap={}
    for m in markers:
        x=int(m['x']/meta['width']*pixels.shape[1]);y=int(m['y']/meta['height']*pixels.shape[0])
        label=int(labels[y,x]);overlap.setdefault(label,[]).append(m['id'])
    out=ROOT/'output/administrative_inventory_20261104';out.mkdir(exist_ok=True)
    record=dict(status='audited_inventory',commandery_authority='owner list and key, with ID-linked workbook seat evidence',
        datasheet_sources=evidence['sources'],
        width=meta['width'],height=meta['height'],markers=markers,commanderies=commanderies,legions=legions,
        named_marker_count=len(markers),alpha_component_count=components,
        touching_named_marker_groups=[v for k,v in overlap.items() if k and len(v)>1],
        roles=dict(Counter(m['kind'] for m in markers)),
        matched_commanderies=sum(c['status']=='matched' for c in commanderies),
        unresolved_commanderies=[c['name'] for c in commanderies if c['status']!='matched'],
        sources_sha256={p:file_hash(ROOT/p) for p in sources},
        scope='Administrative identity is supplied lore; markers are typed from local source evidence. No assumed manpower, political allegiance from proximity, or fabricated locations for unresolved centres. No change to legacy control exports.')
    write_json(out/'review.json',record)
    print(json.dumps({k:record[k] for k in ['named_marker_count','alpha_component_count','touching_named_marker_groups','roles','matched_commanderies','unresolved_commanderies']},ensure_ascii=False,indent=2))


if __name__=='__main__':main()
