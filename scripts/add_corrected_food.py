"""Farming, population and foraging on the Earth-corrected climate, as a switchable variant.

    python -I scripts/add_corrected_food.py atlases/earth_fit --checkpoint output/r40_world/candidate_001.pkl \
        --corrections calibration/earth_correction_r40_20261031

The atlas's farming (harvest), population and FORGE foraging exporters read
only the climate packet's monthly sea-level temperature and rain (T12, P12,
twelve bins from the winter solstice on the model grid) and its Whittaker
biome array. This script builds a copy of that packet with the Earth-trained
corrections applied (scripts/add_corrected_layers.py computes them on the
model grid by calendar month; they are moved to the solstice bins by
periodic interpolation and onto the packet's cells through the same coastal
fill the packet uses), reruns the three unchanged exporters on it in a
staging folder, and attaches their packets, images and layers under
data/corrected/. The page switches to them with #climate=corrected (or the
"Climate for food and people" control); every other topic, the station
card's climate and political reach keep the simulated climate. The
corrections are valid only for the physics they were trained on; any other
physics is refused.
"""
from __future__ import annotations

import argparse
import json
import pickle
import shutil
import sys
from dataclasses import asdict
from math import ceil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / 'scripts'))
import numpy as np  # noqa: E402

from add_corrected_layers import corrected_fields  # noqa: E402
from earth_benchmark import load_params  # noqa: E402
from local_benchmark_protocol import file_hash, write_json  # noqa: E402
from harvest.export import climate_arrays  # noqa: E402
from rotclimate import biomes  # noqa: E402
from rotclimate.analogs import model_bins  # noqa: E402
from rotclimate.atlas import HiRes  # noqa: E402

PARTS = ('harvest', 'population', 'foraging')
PREFIXES = ('land_', 'pop_', 'forage_')


def to_solstice_bins(monthly, year_days, winter_solstice_day):
    """Calendar months (equal months from day 0) -> the packet's bins from the winter solstice."""
    monthly = np.asarray(monthly, float)
    centres = (np.arange(12) + 0.5) * year_days / 12
    targets = (winter_solstice_day + (np.arange(12) + 0.5) * year_days / 12) % year_days
    x = np.concatenate([centres - year_days, centres, centres + year_days])
    y = np.concatenate([monthly, monthly, monthly])
    out = np.empty_like(monthly)
    for i, t in enumerate(targets):
        j = int(np.searchsorted(x, t))
        w = (t - x[j - 1]) / (x[j] - x[j - 1])
        out[i] = (1 - w) * y[j - 1] + w * y[j]
    return out


def corrected_packet(atlas, result, corrections, out_bin):
    data = atlas / 'data'
    meta = json.loads((data / 'atlas.json').read_text())
    arrays = climate_arrays(data, meta)
    p, g = result.params, result.grid
    dT, ratio, fit, change, models = corrected_fields(result, corrections)
    fr = HiRes(result, 2)
    fill_iy, fill_ix = fr._fill
    # the packet is cut on the source map's grid (rotclimate.atlas.build with FullRes), half the 2x image
    ny_m, nx_m = int(ceil(fr.H / 2 / g.f)), int(ceil(fr.W / 2 / g.f))
    sl = (slice(None), slice(g.pad, g.pad + ny_m), slice(g.pad, g.pad + nx_m))
    onto_packet = lambda field: np.asarray(field)[:, fill_iy, fill_ix][sl]
    # the packet's own construction, as a check that these cells are its cells
    T12_raw, P12_raw = model_bins(result.Tsl[:, fill_iy, fill_ix], result.P[:, fill_iy, fill_ix],
                                  result.days, p.winter_solstice_day, p.year_days)
    T12_raw, P12_raw = T12_raw[sl], P12_raw[sl]
    if T12_raw.shape != arrays['T12'].shape:
        raise ValueError(f'Packet grid {arrays["T12"].shape} is not the model map grid {T12_raw.shape} (thinned packet?)')
    if np.abs(np.round(T12_raw * 10) - arrays['T12']).max() > 1 or np.abs(np.round(np.clip(P12_raw, 0, 65000)) - arrays['P12']).max() > 1:
        raise ValueError('The checkpoint does not reproduce this atlas packet')
    dT12 = onto_packet(to_solstice_bins(dT, p.year_days, p.winter_solstice_day))
    ratio12 = onto_packet(to_solstice_bins(ratio, p.year_days, p.winter_solstice_day))
    T12 = np.round(arrays['T12'] + 10 * dT12).astype(np.int16)
    P12 = np.round(np.clip(arrays['P12'] * np.maximum(ratio12, 0.0), 0, 65000)).astype(np.uint16)
    # the packet's biome comes from rotclimate.render.FullRes (source resolution), so correct that view
    from rotclimate.render import FullRes
    fc = FullRes(result)
    plain_monthly = fc.monthly

    def monthly():
        Tm, Pm, summer = plain_monthly()
        Tc = Tm + np.stack([fc.up(d) for d in dT]).astype(np.float32)
        Pc = Pm * np.stack([np.maximum(fc.up(r), 0.0) for r in ratio]).astype(np.float32)
        return Tc, Pc, summer
    fc.monthly = monthly
    fc.koppen()
    biome = biomes.classify(fc._ix['MAT'], fc._ix['MAP'], fc.land)[::2, ::2].astype(np.uint8)
    if biome.shape != arrays['biome'].shape:
        raise ValueError('Corrected biome grid differs from the packet')
    blob = bytearray((data / 'atlas.bin').read_bytes())
    for name, value in (('T12', T12), ('P12', P12), ('biome', biome)):
        spec = meta['arrays'][name]
        raw = np.ascontiguousarray(value, dtype=np.dtype(spec['dtype'])).tobytes()
        if len(raw) != int(np.prod(spec['shape'])) * np.dtype(spec['dtype']).itemsize:
            raise ValueError('Packet array size changed: ' + name)
        blob[spec['offset']:spec['offset'] + len(raw)] = raw
    out_bin.write_bytes(bytes(blob))
    land = arrays['cls'] != 255
    corrected_cells = np.abs(dT12).sum(0) > 0          # land cells and the coastal cells that carry land values
    changes = dict(
        biome_cells_changed=float((biome[land] != arrays['biome'][land]).mean()),
        mean_temperature_change_c=float((T12.astype(float) - arrays['T12'])[:, corrected_cells].mean() / 10),
        rain_total_change=float(P12.astype(float)[:, corrected_cells].sum()
                                / max(float(arrays['P12'].astype(float)[:, corrected_cells].sum()), 1.0) - 1.0))
    return dict(fit=fit, change=change, models=models, packet_change=changes)


def relocate(layer):
    """The same layer, its files under data/corrected/."""
    L = json.loads(json.dumps(layer))
    pre = lambda f: 'corrected/' + f
    L['file'] = pre(L['file'])
    if 'scenario_files' in L:
        L['scenario_files'] = {k: pre(v) for k, v in L['scenario_files'].items()}
    if isinstance(L.get('tiers'), dict):
        if 'file' in L['tiers']:
            L['tiers']['file'] = pre(L['tiers']['file'])
        if 'scenario_files' in L['tiers']:
            L['tiers']['scenario_files'] = {k: pre(v) for k, v in L['tiers']['scenario_files'].items()}
    if isinstance(L.get('variants'), dict):
        for option in L['variants'].get('options', []):
            if 'file' in option:
                option['file'] = pre(option['file'])
    return L


def add(atlas, checkpoint, corrections, staging):
    from harvest.export import export as harvest_export
    from population.export import export as population_export
    from foraging.export import export as foraging_export
    atlas = Path(atlas).resolve(); data = atlas / 'data'
    with Path(checkpoint).open('rb') as stream:
        result = pickle.load(stream)['result']
    if not result.numerics.get('all_checks_passed'):
        raise ValueError('Unverified climate checkpoint')
    plain = lambda q: json.loads(json.dumps(asdict(q)))
    if plain(result.params) != plain(load_params(atlas / 'params.json')):
        raise ValueError('The checkpoint is not the climate this atlas was built from')
    staging = Path(staging)
    if staging.exists():
        shutil.rmtree(staging)
    (staging / 'data').mkdir(parents=True)
    shutil.copyfile(data / 'atlas.json', staging / 'data' / 'atlas.json')
    record = corrected_packet(atlas, result, Path(corrections), staging / 'data' / 'atlas.bin')
    harvest_export(staging)
    population_export(staging)
    foraging_export(staging)
    smeta = json.loads((staging / 'data' / 'atlas.json').read_text())
    target = data / 'corrected'
    if target.exists():
        shutil.rmtree(target)
    target.mkdir()
    skip = {'atlas.json', 'atlas.bin'}
    for path in (staging / 'data').iterdir():
        if path.is_file() and path.name not in skip:
            shutil.copyfile(path, target / path.name)
    layers = [relocate(L) for L in smeta['layers'] if L['id'].startswith(PREFIXES)]
    meta = json.loads((data / 'atlas.json').read_text())
    live_ids = {L['id'] for L in meta['layers'] if L['id'].startswith(PREFIXES)}
    if {L['id'] for L in layers} != live_ids:
        raise ValueError('Corrected exports do not cover the same food and people layers')
    for name in [L['file'] for L in layers]:
        if not (data / name).is_file():
            raise ValueError('Missing corrected layer image: ' + name)
    summaries = {}
    for part in PARTS:
        info = json.loads((target / smeta[part]['metadata']).read_text())
        summaries[part] = info.get('summary')
    meta['corrected_food'] = dict(
        label='Earth-corrected climate',
        note=('Farming, population and foraging recomputed on the climate after the Earth-trained corrections '
              '(temperature, local rain pattern). Political reach, trade and every climate topic keep the simulated climate.'),
        packet_sha256=file_hash(staging / 'data' / 'atlas.bin'),
        **{part: dict(smeta[part], metadata='corrected/' + smeta[part]['metadata'],
                      binary='corrected/' + smeta[part]['binary']) for part in PARTS},
        layers=layers)
    (data / 'atlas.json').write_text(json.dumps(meta, ensure_ascii=False), encoding='utf-8')
    raw = {part: json.loads((data / meta[part]['metadata']).read_text()).get('summary') for part in PARTS}
    out = dict(status='passed', atlas=str(atlas.relative_to(ROOT)), checkpoint=str(checkpoint),
               checkpoint_sha256=file_hash(Path(checkpoint)), corrections=str(corrections), layers=len(layers),
               packet=record['packet_change'], zone_fit=record['fit'], raw=raw, corrected=summaries,
               exporter_sha256=file_hash(Path(__file__)))
    write_json(target / 'corrected_food.json', out)
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('atlas', type=Path); ap.add_argument('--checkpoint', type=Path, required=True)
    ap.add_argument('--corrections', type=Path, required=True)
    ap.add_argument('--staging', type=Path, default=ROOT / 'output/corrected_food/staging')
    a = ap.parse_args()
    out = add(a.atlas, a.checkpoint, a.corrections, a.staging / a.atlas.resolve().name)
    print(json.dumps({k: v for k, v in out.items() if k not in ('raw', 'corrected')}, indent=1, default=str))


if __name__ == '__main__':
    main()
