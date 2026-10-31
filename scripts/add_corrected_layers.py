"""Add the Earth-trained corrections to an atlas as a "Corrected" map topic.

    python -I scripts/add_corrected_layers.py atlases/earth_fit --checkpoint output/r40_world/candidate_001.pkl \
        --corrections calibration/earth_correction_r40_20261031

The temperature and rain-pattern corrections (reports/EARTH_CORRECTION_20261030.md)
were learned from the 31 Earth regions with whole clusters held out. Here they
are applied to the atlas's own verified climate (the checkpoint it was built
from, mean of its surroundings layouts) on the model grid, then carried into
the full-resolution fields the climate layers are drawn from. Eight layers
are added: Köppen, Whittaker biomes, simulated zones, mean temperature and
precipitation under the corrected climate, and the changes themselves (year-mean
temperature, seasonal swing, rain). Every other topic, the station card and the farming,
population, foraging and political layers keep the raw simulation. The
corrections are valid only for the physics they were trained on; any other
physics is refused.
"""
from __future__ import annotations

import argparse
import json
import pickle
import shutil
import sys
import tempfile
from dataclasses import asdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / 'scripts'))
import matplotlib.colors as mc  # noqa: E402
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

from earth_benchmark import load_params  # noqa: E402
from local_benchmark_protocol import file_hash, write_json  # noqa: E402
from preview_map_correction import zone_fit  # noqa: E402
from rotclimate import biomes  # noqa: E402
from rotclimate.atlas import HiRes, _cmap_img, _overlay_rivers, _save_webp, zones_layer  # noqa: E402
from rotclimate.config import Params  # noqa: E402
from rotclimate.correction import RainPatternCorrection, TemperatureCorrection  # noqa: E402
from rotclimate.joint import SHARED_FIELDS  # noqa: E402
from rotclimate.koppen import CODES, COLORS, DESCRIPTIONS, monthly_stats, monthly_weights, rgb_image  # noqa: E402
from rotclimate.numerics import matrix_product  # noqa: E402
from rotclimate.render import shaded_rgb  # noqa: E402

RAIN_EPS_MM = 1.0        # mm per month added to both sides of the rain ratio (dry months)


def stops(cmap, n=9):
    cm = plt.get_cmap(cmap)
    return [mc.to_hex(cm(i / (n - 1))) for i in range(n)]


def corrected_fields(result, corrections):
    p, g = result.params, result.grid
    temperature = TemperatureCorrection.load(corrections / 'temperature' / 'correction.npz')
    rain = RainPatternCorrection.load(corrections / 'rain_pattern' / 'correction.npz')
    for model in (temperature, rain):
        physics = Params.from_json(ROOT / model.meta['physics_params'])
        differ = sorted(k for k in SHARED_FIELDS if getattr(p, k) != getattr(physics, k))
        if differ:
            raise SystemExit(f'The corrections were trained on other physics; shared fields differ: {differ}')
    st = monthly_stats(result.T, result.P, result.days, p.year_days, summer_solstice=p.winter_solstice_day + p.year_days / 2)
    mask = g.land & g.inmap
    Tc = temperature.apply(st['Tm'], st['Pm'], g, p.year_days, p.winter_solstice_day, mask=mask)
    Pm = np.maximum(st['Pm'], 0.0)
    Wm = monthly_weights(result.days, p.year_days)
    um, vm = (matrix_product(Wm, a.reshape(len(result.days), -1)).reshape((12,) + a.shape[1:]) for a in (result.u, result.v))
    Pc = rain.apply(st['Tm'], Pm, um, vm, g, p.year_days, p.winter_solstice_day, mask=mask)
    dT = np.where(mask, Tc - st['Tm'], 0.0)
    ratio = np.where(mask, (Pc + RAIN_EPS_MM) / (Pm + RAIN_EPS_MM), 1.0)
    fit = dict(raw=zone_fit(st['Tm'], Pm, st['summer'], g), corrected=zone_fit(Tc, Pc, st['summer'], g))
    change = dict(mean_temperature_c=float(dT[:, mask].mean()), mean_abs_temperature_c=float(np.abs(dT[:, mask]).mean()),
                  rain_total=float(Pc[:, mask].sum() / Pm[:, mask].sum() - 1.0))
    models = dict(temperature=temperature.meta, rain_pattern=rain.meta)
    return dT, ratio, fit, change, models


def corrected_view(result, dT, ratio, scale):
    """HiRes fields whose monthly climate carries the corrections."""
    fr = HiRes(result, scale)
    raw = fr.monthly

    def monthly():
        Tm, Pm, summer = raw()
        Tc = Tm + np.stack([fr.up(d) for d in dT]).astype(np.float32)
        Pc = Pm * np.stack([np.maximum(fr.up(r), 0.0) for r in ratio]).astype(np.float32)
        return Tc, Pc, summer
    fr.monthly = monthly
    return fr


def add(atlas, checkpoint, corrections, scale=2):
    atlas = Path(atlas).resolve(); data = atlas / 'data'
    with Path(checkpoint).open('rb') as stream:
        cached = pickle.load(stream)
    result = cached['result']
    if not result.numerics.get('all_checks_passed'):
        raise ValueError('Unverified climate checkpoint')
    plain = lambda q: json.loads(json.dumps(asdict(q)))       # tuples and lists compare equal
    if plain(result.params) != plain(load_params(atlas / 'params.json')):
        raise ValueError('The checkpoint is not the climate this atlas was built from')
    dT, ratio, fit, change, models = corrected_fields(result, Path(corrections))
    raw, fc = HiRes(result, scale), corrected_view(result, dT, ratio, scale)
    k = fc.koppen(); ix = fc._ix; k0 = raw.koppen(); ix0 = raw._ix
    _save_webp(_overlay_rivers(shaded_rgb(rgb_image(k).astype(float) / 255.0, fc, 0.42), fc), data / 'koppen_corrected.webp')
    biome = biomes.classify(ix['MAT'], ix['MAP'], fc.land)
    _save_webp(_overlay_rivers(shaded_rgb(biomes.rgb_image(biome), fc, 0.25), fc), data / 'whittaker_corrected.webp')
    _save_webp(_cmap_img(ix['MAT'], 'turbo', -10, 30, fc, 20), data / 't_annual_corrected.webp')
    _save_webp(_cmap_img(np.log10(np.maximum(ix['MAP'], 50)), 'YlGnBu', np.log10(100), np.log10(3000), fc, 14),
               data / 'precip_corrected.webp')
    # the correction mostly moves the seasons (on Earth: maritime coasts a month late
    # and too continental), so the year mean barely changes; show the swing too
    _save_webp(_cmap_img(ix['MAT'] - ix0['MAT'], 'RdBu_r', -1, 1, fc, 10), data / 'correction_temperature.webp')
    swing = (fc._Tm.max(0) - fc._Tm.min(0)) - (raw._Tm.max(0) - raw._Tm.min(0))
    _save_webp(_cmap_img(swing, 'PuOr_r', -4, 4, fc, 16), data / 'correction_swing.webp')
    rain_change = 100 * ((ix['MAP'] + 12 * RAIN_EPS_MM) / (ix0['MAP'] + 12 * RAIN_EPS_MM) - 1)
    _save_webp(_cmap_img(rain_change, 'BrBG', -20, 20, fc, 8), data / 'correction_rain.webp')
    with tempfile.TemporaryDirectory() as tmp:
        zones_layer(fc, Path(tmp))
        shutil.move(str(Path(tmp) / 'zones.webp'), data / 'zones_corrected.webp')
    land = fc.land
    shares = {c: float((k[land] == i).mean()) for i, c in enumerate(CODES)}
    present = [c for c in CODES if shares[c] >= 0.005]
    note = ('Earth-trained corrections (temperature, local rain pattern) applied to this climate; learned from 31 Earth '
            'regions and scored with whole clusters held out (temperature error −14 %, rain loss −3 %). The station card '
            'and every other topic show the raw simulation.')
    layers = [
        dict(id='koppen_corrected', file='koppen_corrected.webp', label='Köppen, corrected', kind='categories', group='Corrected',
             items=[dict(color=mc.to_hex(np.array(COLORS[c]) / 255), label=f'{c} {DESCRIPTIONS.get(c, "")} · {100 * shares[c]:.0f}%'.strip())
                    for c in present], note=note),
        # the page's 'biomes' legend carries the raw shares, so list the corrected ones
        dict(id='whittaker_corrected', file='whittaker_corrected.webp', label='Whittaker biomes, corrected', kind='categories',
             group='Corrected', items=[dict(color=b['color'], label=f"{b['label']} · {100 * b['share']:.1f}%")
                                       for b in biomes.legend(biome, fc.land) if b['share'] > 0], note=note),
        dict(id='zones_corrected', file='zones_corrected.webp', label='Simulated zones, corrected', kind='zones', group='Corrected'),
        dict(id='t_annual_corrected', file='t_annual_corrected.webp', label='Mean temperature, corrected', kind='ramp',
             group='Corrected', unit='°C, year mean', vmin=-10, vmax=30, stops=stops('turbo'), note=note),
        dict(id='precip_corrected', file='precip_corrected.webp', label='Precipitation, corrected', kind='ramp',
             group='Corrected', unit='mm per year', vmin=100, vmax=3000, log=True, stops=stops('YlGnBu'), note=note),
        dict(id='correction_temperature', file='correction_temperature.webp', label='Temperature correction', kind='ramp',
             group='Corrected', unit='°C, corrected minus raw year mean', vmin=-1, vmax=1, stops=stops('RdBu_r'), note=note),
        dict(id='correction_swing', file='correction_swing.webp', label='Seasonal swing correction', kind='ramp',
             group='Corrected', unit='°C, change in warmest minus coldest month (purple: milder seasons)', vmin=-4, vmax=4,
             stops=stops('PuOr_r'), note=note),
        dict(id='correction_rain', file='correction_rain.webp', label='Rain correction', kind='ramp', group='Corrected',
             unit='% change in yearly rain', vmin=-20, vmax=20, stops=stops('BrBG'), note=note)]
    meta = json.loads((data / 'atlas.json').read_text())
    ids = {L['id'] for L in layers}
    meta['layers'] = [L for L in meta['layers'] if L['id'] not in ids] + layers
    meta['earth_correction'] = dict(
        note=note, physics=models['temperature'].get('physics_params'), zone_fit=fit, change=change,
        heldout=dict(temperature_c=[1.807, 1.548], temperature_14km_c=[1.913, 1.283], rain_loss=[0.4329, 0.4201]),
        models={k: dict(physics_sha256=v.get('physics_params_sha256'), trained_on=v.get('trained_on')) for k, v in models.items()})
    (data / 'atlas.json').write_text(json.dumps(meta, ensure_ascii=False), encoding='utf-8')
    record = dict(status='passed', atlas=str(atlas.relative_to(ROOT)), checkpoint=str(Path(checkpoint)),
                  checkpoint_sha256=file_hash(Path(checkpoint)), corrections=str(corrections),
                  correction_sha256={n: file_hash(Path(corrections) / n / 'correction.npz') for n in ('temperature', 'rain_pattern')},
                  layers=sorted(ids), zone_fit=fit, change=change, raw_koppen_share_changed=float((k[land] != k0[land]).mean()),
                  exporter_sha256=file_hash(Path(__file__)))
    write_json(data / 'earth_correction.json', record)
    return record


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('atlas', type=Path); ap.add_argument('--checkpoint', type=Path, required=True)
    ap.add_argument('--corrections', type=Path, required=True); ap.add_argument('--scale', type=int, default=2)
    a = ap.parse_args()
    print(json.dumps(add(a.atlas, a.checkpoint, a.corrections, a.scale), indent=1, default=str))


if __name__ == '__main__':
    main()
