"""The Earth-corrected climate as an atlas's default climate, every topic included.

    python -I scripts/add_corrected_climate.py atlases/earth_fit --checkpoint output/r40_world/candidate_001.pkl \
        --corrections calibration/earth_correction_r40_20261031

The two Earth-trained correction stages (temperature; local rain pattern;
reports/EARTH_CORRECTION_20261030.md) run on the atlas's own verified climate
on the model grid by calendar month (scripts/add_corrected_layers.py,
corrected_fields). Here they are carried into every model step (periodic
linear interpolation between the month centres: temperature and sea-level
temperature shifted, rain scaled; the snowpack rerun from the corrected
temperature and rain), and the corrected climate goes through the same
exporters as the simulated one in a staging folder: the climate layers and
the station-card packet (rotclimate.atlas.build), the year animations of
temperature and rain, farming, population, foraging and political reach.

Every climate-dependent layer, the packet, the legends and the food,
people and political packets are attached under data/corrected/ and listed
in atlas.json["corrected_climate"]. The page opens on the corrected climate
and keeps the raw simulation one switch away (#climate=raw): the raw output
stays alongside, as the project's rules require. Winds and the sea surface are
not corrected and stay as simulated. The separate Corrected topic
(add_corrected_layers.py) and the food-only variant (add_corrected_food.py)
are removed; the three correction-change maps move to Fit checks. The
corrections are valid only for the physics they were trained on; any other
physics is refused.
"""
from __future__ import annotations

import argparse
import dataclasses
import json
import pickle
import shutil
import sys
import time
from dataclasses import asdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / 'scripts'))
import numpy as np  # noqa: E402

from add_corrected_layers import corrected_fields  # noqa: E402
from earth_benchmark import load_params  # noqa: E402
from local_benchmark_protocol import file_hash, write_json  # noqa: E402

# layer groups drawn from the climate; "Air and sea" (winds, sea surface) is not corrected
CLIMATE_GROUPS = ('Climate', 'Temperature', 'Water', 'Month by month', 'Harvest', 'Population', 'Political reach',
                  'Foraging')
KEEP_RAW = {'target'}                         # the drawn target zones, not a climate field
OLD_TOPIC = {'koppen_corrected', 'whittaker_corrected', 'zones_corrected', 't_annual_corrected', 'precip_corrected'}
CHANGE_MAPS = ('correction_temperature', 'correction_swing', 'correction_rain')
META_FIELDS = ('koppen', 'present', 'biomes', 'zones', 'score', 'accuracy', 'lapse_local', 'lapse12', 'cell_px')
PARTS = ('harvest', 'population', 'foraging')


def month_weights(days, year_days):
    """Per step: the two calendar months around it and the weight of the second."""
    centres = (np.arange(12) + 0.5) * year_days / 12
    d = np.asarray(days, float) % year_days
    j = np.searchsorted(centres, d)                       # 0..12
    lo, hi = (j - 1) % 12, j % 12
    c_lo = np.where(j == 0, centres[11] - year_days, centres[lo])
    c_hi = np.where(j == 12, centres[0] + year_days, centres[hi])
    return lo, hi, (d - c_lo) / (c_hi - c_lo)


def corrected_result(result, dT, ratio):
    """The simulation with the monthly corrections carried into every step."""
    from rotclimate.model import snowpack
    p = result.params
    lo, hi, w = month_weights(result.days, p.year_days)
    w = w[:, None, None]
    dTk = (1.0 - w) * dT[lo] + w * dT[hi]
    rk = np.maximum((1.0 - w) * ratio[lo] + w * ratio[hi], 0.0)
    T = (result.T + dTk).astype(result.T.dtype)
    Tsl = (result.Tsl + dTk).astype(result.Tsl.dtype)
    P = (result.P * rk).astype(result.P.dtype)
    snow = snowpack(T, P, p.year_days / len(result.days)).astype(result.snow.dtype)
    numerics = dict(result.numerics or {})
    numerics['earth_corrected'] = True
    return dataclasses.replace(result, T=T, Tsl=Tsl, P=P, snow=snow, numerics=numerics)


def relocate(layer):
    """The same layer, its files under data/corrected/."""
    L = json.loads(json.dumps(layer))
    pre = lambda f: 'corrected/' + f
    L['file'] = pre(L['file'])
    if L.get('frames'):
        L['frames'] = [pre(f) for f in L['frames']]
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


def layer_files(layer):
    """Every file a layer's images use (frames, tiers, scenarios, variants)."""
    files = [layer['file']]
    files += list(layer.get('frames') or [])
    files += list(layer.get('scenario_files', {}).values())
    tiers = layer.get('tiers')
    if isinstance(tiers, dict):
        files += [tiers['file']] if 'file' in tiers else []
        files += list(tiers.get('scenario_files', {}).values())
    variants = layer.get('variants')
    if isinstance(variants, dict):
        files += [o['file'] for o in variants.get('options', []) if 'file' in o]
    return sorted(set(files))


def stage(atlas, result, staging, image_scale, gifs=False):
    """Run the atlas's own exporters on the corrected climate in a staging atlas."""
    from rotclimate import render as R
    from rotclimate.atlas import build
    from rotclimate.score import evaluate
    from harvest.export import export as harvest_export
    from population.export import export as population_export
    from foraging.export import export as foraging_export
    from polity.export import export as reach_export
    from add_market_views import render_views
    if staging.exists():
        shutil.rmtree(staging)
    (staging / 'data').mkdir(parents=True)
    shutil.copyfile(atlas / 'params.json', staging / 'params.json')
    t = time.time()
    ev = evaluate(result)
    fr = R.FullRes(result)
    build(result, fr, ev, outdir=staging / 'data', image_scale=image_scale)
    print(f'climate layers and packet {time.time() - t:.0f} s', flush=True)
    if gifs:
        R.season_gif(fr, staging / 'data' / 'year_temperature.gif', 'T')
        R.season_gif(fr, staging / 'data' / 'year_precipitation.gif', 'P')
        R.season_gif(fr, staging / 'data' / 'year_growing.gif', 'G')
    del fr
    # winds are not corrected: political reach reads the atlas's own monthly winds
    shutil.copyfile(atlas / 'data' / 'winds12.npz', staging / 'data' / 'winds12.npz')
    for name, fn in (('harvest', harvest_export), ('population', population_export), ('foraging', foraging_export),
                     ('reach', reach_export)):
        t = time.time()
        fn(staging)
        print(f'{name} {time.time() - t:.0f} s', flush=True)
    render_views(staging, ROOT / 'output/polity_map' / f'{staging.name}.npz')
    return ev


def add(atlas, checkpoint, corrections, staging, image_scale=2, gifs=False):
    atlas = Path(atlas).resolve(); data = atlas / 'data'
    with Path(checkpoint).open('rb') as stream:
        result = pickle.load(stream)['result']
    if not result.numerics.get('all_checks_passed'):
        raise ValueError('Unverified climate checkpoint')
    plain = lambda q: json.loads(json.dumps(asdict(q)))
    if plain(result.params) != plain(load_params(atlas / 'params.json')):
        raise ValueError('The checkpoint is not the climate this atlas was built from')
    dT, ratio, fit, change, models = corrected_fields(result, Path(corrections))
    corrected = corrected_result(result, dT, ratio)
    del result
    staging = Path(staging)
    ev = stage(atlas, corrected, staging, image_scale, gifs)
    smeta = json.loads((staging / 'data' / 'atlas.json').read_text())
    meta = json.loads((data / 'atlas.json').read_text())
    live = {L['id']: L for L in meta['layers']}
    swap = [L for L in smeta['layers'] if L.get('group') in CLIMATE_GROUPS and L['id'] not in KEEP_RAW]
    missing = sorted(L['id'] for L in swap if L['id'] not in live)
    absent = sorted(i for i, L in live.items() if L.get('group') in CLIMATE_GROUPS and i not in KEEP_RAW
                    and i not in {S['id'] for S in swap} and i not in OLD_TOPIC)
    if missing or absent:
        raise ValueError(f'Corrected layers do not match the atlas: new {missing}, not recomputed {absent}')
    target = data / 'corrected'
    if target.exists():
        shutil.rmtree(target)
    target.mkdir()
    sdata = staging / 'data'
    copied = set()
    for L in swap:
        for f in layer_files(L):
            src = sdata / f
            if not src.is_file():
                raise ValueError('Missing corrected image: ' + f)
            (target / f).parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(src, target / f); copied.add(f)
    extras = ['atlas.bin', 'year_temperature.gif', 'year_precipitation.gif', 'year_growing.gif']
    extras += [path.name for path in sdata.glob('*.csv')]          # the download tables (places, provinces, polities)
    for part in PARTS:
        extras += [smeta[part]['metadata'], smeta[part]['binary']]
    for f in extras:
        if (sdata / f).is_file():
            shutil.copyfile(sdata / f, target / f); copied.add(f)
    if (sdata / 'vectors').is_dir():                               # political reach as GIS layers
        shutil.copytree(sdata / 'vectors', target / 'vectors')
    gif_files = {f: 'corrected/' + f for f in ('year_temperature.gif', 'year_precipitation.gif', 'year_growing.gif')
                 if f in copied}
    # the held-out scores of the corrections in use (add_corrected_layers.py records them; r40's otherwise)
    held = meta.get('earth_correction', {}).get('heldout', dict(temperature_c=[1.807, 1.548], rain_loss=[0.4329, 0.4201]))
    pct = lambda v: f'{100 * (v[1] / v[0] - 1):+.0f} %'.replace('-', '−')
    cc = dict(
        label='Earth-corrected climate',
        note=('Every climate-drawn map, the station card, farming, population, foraging and political reach use the '
              'simulated climate after the Earth-trained corrections (temperature and local rain pattern; learned from '
              f'31 Earth regions, scored with whole clusters held out: temperature error {pct(held["temperature_c"])}, '
              f'rain loss {pct(held["rain_loss"])}). Winds '
              'and the sea surface are as simulated. Switch to the raw simulation to see the model alone.'),
        binary='corrected/atlas.bin', arrays=smeta['arrays'],
        packet_sha256=file_hash(target / 'atlas.bin'),
        layers=[relocate(L) for L in swap], gifs=gif_files,
        downloads={f: 'corrected/' + f for f in sorted(copied) if f.endswith('.csv')},
        **{k: smeta[k] for k in META_FIELDS if k in smeta},
        **{part: dict(smeta[part], metadata='corrected/' + smeta[part]['metadata'],
                      binary='corrected/' + smeta[part]['binary']) for part in PARTS},
        reach=smeta.get('reach'))
    meta['corrected_climate'] = cc
    meta.pop('corrected_food', None)
    shutil.rmtree(data / 'corrected_food', ignore_errors=True)
    meta['layers'] = [L for L in meta['layers'] if L['id'] not in OLD_TOPIC]
    for L in meta['layers']:
        if L['id'] in CHANGE_MAPS:
            L['group'] = 'Fit checks'
    for f in OLD_TOPIC:
        (data / f'{f}.webp').unlink(missing_ok=True)
    if 'earth_correction' in meta:
        meta['earth_correction']['note'] = cc['note']
    (data / 'atlas.json').write_text(json.dumps(meta, ensure_ascii=False), encoding='utf-8')
    raw = {part: json.loads((data / meta[part]['metadata']).read_text()).get('summary') for part in PARTS}
    summaries = {part: json.loads((target / smeta[part]['metadata']).read_text()).get('summary') for part in PARTS}
    out = dict(status='passed', atlas=str(atlas.relative_to(ROOT)), checkpoint=str(checkpoint),
               checkpoint_sha256=file_hash(Path(checkpoint)), corrections=str(corrections),
               layers=len(swap), files=len(copied), zone_fit=fit, change=change,
               score=dict(raw=meta.get('score'), corrected=smeta.get('score')),
               accuracy=dict(raw=meta.get('accuracy'), corrected=smeta.get('accuracy')),
               raw=raw, corrected=summaries, exporter_sha256=file_hash(Path(__file__)))
    write_json(target / 'corrected_climate.json', out)
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('atlas', type=Path); ap.add_argument('--checkpoint', type=Path, required=True)
    ap.add_argument('--corrections', type=Path, required=True)
    ap.add_argument('--image-scale', type=int, default=2)
    ap.add_argument('--gif', action='store_true', help='also the year animations (only if the atlas has them)')
    ap.add_argument('--staging', type=Path, default=ROOT / 'output/corrected_climate/staging')
    a = ap.parse_args()
    out = add(a.atlas, a.checkpoint, a.corrections, a.staging / (a.atlas.resolve().name + '_corrected'),
              a.image_scale, a.gif)
    print(json.dumps({k: v for k, v in out.items() if k not in ('raw', 'corrected', 'zone_fit')}, indent=1, default=str))


if __name__ == '__main__':
    main()
