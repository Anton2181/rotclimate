"""Outside-reference circulation diagnostics; no production forcing or tuning.

Reuse the constrained, provenance-checked NCEP ASCII reader from the V10 lab.
All new geometry/aggregation is for the production model's projected grids.
"""
from pathlib import Path
import json
import ssl
import urllib.request

import numpy as np
from experiments import v10_forcing_audit as old
from rotclimate import earth
from scripts.local_benchmark_protocol import file_hash, write_json

VARIABLES = ('uwnd', 'vwnd', 'shum', 'hgt')


def acquire_mexico(root, plan, *, fetch=False):
    """Read verified old subsets and atomically acquire only new regional boxes."""
    root = Path(root)
    original = root/'data/v10_atmosphere'
    cache = root/'data/cache/transport_diagnosis_20261028'
    saved_path = cache/'downloads.json'
    original_records = json.loads((original/'downloads.json').read_text())
    saved = json.loads(saved_path.read_text()) if saved_path.exists() else {}
    texts, sources = {}, {}
    boxes = {**{n: old.BOXES[n] for n in plan['regions'] if n in old.BOXES},
             **plan['new_reference_boxes']}
    for var in VARIABLES:
        entries = [(f'{var}.das', old.BASE+f'{var}.mon.1981-2010.ltm.nc.das', None)]
        for region in plan['regions']:
            for index, box in enumerate(boxes[region]):
                y0, y1, x0, x1 = box
                query = f'{var}[0:1:11][0:1:{old.VARIABLES[var]-1}][{y0}:1:{y1}][{x0}:1:{x1}]'
                entries.append((f'{var}_{region}_{index}.ascii',
                    old.BASE+f'{var}.mon.1981-2010.ltm.nc.ascii?'+query, box))
        for name, url, box in entries:
            legacy = name in original_records
            path = (original if legacy else cache)/name
            records = original_records if legacy else saved
            if path.exists():
                if name not in records or records[name]['url'] != url or records[name]['sha256'] != file_hash(path):
                    raise ValueError('Reference provenance changed: '+str(path))
                payload = path.read_text()
            else:
                if not fetch or legacy:
                    raise ValueError('Reference missing; explicitly acquire with --fetch: '+str(path))
                print('Fetching NOAA regional reference: '+name, flush=True)
                request = urllib.request.Request(url, headers={'User-Agent': 'rotclimate-circulation-audit/1.0'})
                with urllib.request.urlopen(request, timeout=45, context=ssl.create_default_context()) as response:
                    binary = response.read(4*1024*1024+1)
                if len(binary) > 4*1024*1024:
                    raise ValueError('Oversized reference response')
                payload = binary.decode('utf-8')
                if box is None:
                    old.metadata(payload, var)
                else:
                    old.validate_subset(old.parse_ascii(payload, var), box, old.VARIABLES[var])
                cache.mkdir(parents=True, exist_ok=True)
                temporary = path.with_suffix('.tmp')
                temporary.write_text(payload); temporary.replace(path)
                saved[name] = dict(url=url, sha256=file_hash(path), bytes=path.stat().st_size)
                write_json(saved_path, saved)
            texts[name] = payload
            sources[str(path.relative_to(root))] = records.get(name, saved.get(name))
    fields = {}
    for var in VARIABLES:
        units = old.metadata(texts[f'{var}.das'], var)
        for region in plan['regions']:
            pieces = []
            for index, box in enumerate(boxes[region]):
                field = old.parse_ascii(texts[f'{var}_{region}_{index}.ascii'], var)
                old.validate_subset(field, box, old.VARIABLES[var])
                pieces.append(old.normalize(field, var, units))
            first = pieces[0]
            for other in pieces[1:]:
                for axis in ('pressure_hpa', 'latitude', 'time'):
                    if not np.array_equal(getattr(first, axis), getattr(other, axis)):
                        raise ValueError('Inconsistent split-grid axes')
            longitude = np.concatenate([f.longitude for f in pieces])
            order = np.argsort(longitude)
            fields[region, var] = old.Field(np.concatenate([f.values for f in pieces], axis=-1)[..., order],
                first.pressure_hpa, first.latitude, longitude[order], first.time)
    return fields, sources



def acquire(root,plan,*,fetch=False):
    from scripts.circulation_reference import acquire as existing
    regions=[r for r in plan["regions"] if r!="mexico"]
    fields,sources=existing(root,dict(regions=regions,new_reference_boxes={k:v for k,v in plan["new_reference_boxes"].items() if k in regions}),fetch=False)
    if "mexico" in plan["regions"]:
        more,refs=acquire_mexico(root,dict(regions=["mexico"],new_reference_boxes={"mexico":plan["new_reference_boxes"]["mexico"]}),fetch=fetch)
        fields.update(more);sources.update(refs)
    return fields,sources
