"""Rebuild the Earth atlas's two Fit-check diagnostics for its current physics.

    python -I scripts/add_r40_atlas_diagnostics.py atlases/earth_fit_r40_stage --out output/atlas_r40/diagnostics

The r38 atlas carried a surroundings-sensitivity pair (rain and temperature
spread over nine generated surroundings layouts at ds16, from the r39 audit's
r38 members) and an initialization check (three extra spin-up years at ds16,
layout 1, from the seasonal-cycle pilot). Both were measured for r38's
climate, so they are rerun here for the atlas's own parameters: the same nine
layouts (diagnostic only; they gate nothing) through the existing member runner
and exporter, and a matched pair with and without three extra years. No
climate, food, population or political layer changes.
"""
from __future__ import annotations

import argparse
import json
import pickle
import sys
from dataclasses import asdict
from multiprocessing import Pool
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / 'scripts'))
import matplotlib  # noqa: E402
matplotlib.use('Agg')
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
from matplotlib.colors import TwoSlopeNorm  # noqa: E402

from earth_benchmark import load_params  # noqa: E402
from local_benchmark_protocol import file_hash, write_json  # noqa: E402
from check_r39_world_transfer import member  # noqa: E402
import add_surroundings_sensitivity as sensitivity  # noqa: E402
from rotclimate.koppen import monthly_stats  # noqa: E402
from rotclimate.model import ClimateModel  # noqa: E402

LAYOUTS = json.loads((ROOT / 'calibration/map_world_r39_audit/plan.json').read_text())['layouts']
FIELDS = ['temperature', 'rain', 'water', 'soil_water', 'recycled_rain', 'snow_water']


def sources():
    paths = list((ROOT / 'rotclimate').glob('*.py')) + [p for p in (ROOT / 'data/source').iterdir() if p.is_file()]
    return {str(p.relative_to(ROOT)): file_hash(p) for p in paths}


def surroundings(atlas, out):
    p = load_params(atlas / 'params.json').replace(downsample=16)
    folder = out / 'sensitivity'; (folder / 'members').mkdir(parents=True, exist_ok=True)
    run = 'r40-atlas-surroundings-sensitivity'
    jobs = [(asdict(p), int(s), str(folder / 'members' / f'audit_reference_seed{s}.pkl'), run) for s in LAYOUTS]
    with Pool(2) as pool:
        pool.map(member, jobs)
    write_json(folder / 'protocol.json', dict(plan=dict(layouts=LAYOUTS, purpose='diagnostic spread only; gates nothing'),
                                              source_hashes=sources(), atlas_params_sha256=file_hash(atlas / 'params.json')))
    write_json(folder / 'review.json', dict(complete=True, members=len(LAYOUTS), run=run))
    return sensitivity.add(atlas, folder)


def monthly_rain(result):
    st = monthly_stats(result.T, result.P, result.days, result.params.year_days,
                       summer_solstice=result.params.winter_solstice_day + result.params.year_days / 2)
    return st['Pm'], st['Tm']


def initialization(atlas, out):
    p = load_params(atlas / 'params.json').replace(downsample=16, beyond_seed=1, seasonal_spinup_years=0,
                                                   seasonal_require_convergence=False)
    folder = out / 'initialization'; folder.mkdir(parents=True, exist_ok=True)
    results = {}
    for years in (0, 3):
        path = folder / f'years_{years}.pkl'
        q = p.replace(seasonal_spinup_years=years)
        if path.exists():
            with path.open('rb') as stream:
                saved = pickle.load(stream)
            if asdict(saved['result'].params) != asdict(q):
                raise ValueError('Changed initialization checkpoint')
            results[years] = saved['result']
        else:
            results[years] = ClimateModel(q).run()
            with path.open('wb') as stream:
                pickle.dump(dict(result=results[years]), stream)
        if not results[years].numerics.get('all_checks_passed'):
            raise ValueError('Unverified initialization run')
    base, warm = results[0], results[3]
    g = base.grid
    if not np.array_equal(base.days, warm.days) or not np.array_equal(g.land, warm.grid.land):
        raise ValueError('Initialization pair differs in calendar or geography')
    mask = g.inmap & g.land
    (P0, T0), (P3, T3) = monthly_rain(base), monthly_rain(warm)
    def change(a, b):
        d = (b - a)[:, mask]
        return dict(mean_absolute=float(np.abs(d).mean()), maximum_absolute=float(np.abs(d).max()),
                    mean_signed=float(d.mean()), monthly_signed=d.mean(1).tolist())
    changes = dict(temperature_c=change(T0, T3), rain_mm_month=change(P0, P3))
    cycle = warm.numerics['annual_cycle']
    last = cycle['comparisons'][-1]
    ratio = [last['fields'][k]['domain_max_abs'] / cycle['limits'][k] for k in FIELDS]
    fig, ax = plt.subplots(figsize=(9, 2.6), constrained_layout=True)
    im = ax.imshow(np.minimum([ratio], 2), norm=TwoSlopeNorm(vmin=0, vcenter=1, vmax=2), cmap='RdYlGn_r', aspect='auto')
    for j, v in enumerate(ratio):
        ax.text(j, 0, f'{v:.2g}', ha='center', va='center', fontsize=10, color='#222222',
                bbox=dict(facecolor='white', alpha=.65, edgecolor='none', pad=1))
    ax.set(xticks=np.arange(len(FIELDS)), xticklabels=['T', 'Rain', 'Vapor', 'Soil', 'Rain memory', 'Snow'], yticks=[0],
           yticklabels=['Earth atlas, r40' + (' · land passes' if last.get('map_land_repeats') else '')],
           title='Do the annual cycles repeat? 3 extra years · final two complete cycles')
    fig.colorbar(im, ax=ax, shrink=.9, label='Maximum / limit (>1 fails)')
    image = folder / 'annual_repeatability.png'
    fig.savefig(image, dpi=150); plt.close(fig)
    data = atlas / 'data'
    message = ('Initialization check (layout 1, screening grid): three extra years changed monthly rain by '
               f'at most {np.ceil(changes["rain_mm_month"]["maximum_absolute"] * 100) / 100:.2f} mm on mapped model-grid land. '
               'This is a settling check, not measured climate accuracy.')
    (data / 'initialization_check.png').write_bytes(image.read_bytes())
    write_json(data / 'initialization_check.json', dict(
        scope='One fixed surroundings layout at ds16; main atlas remains layouts1–3 at ds8.', additional_years=3,
        changes=changes, annual_cycle=cycle, message=message, scientific_sources=sources(),
        exporter_sha256=file_hash(Path(__file__)), image_sha256=file_hash(image)))
    meta = json.loads((data / 'atlas.json').read_text())
    meta['initialization_check'] = dict(metadata='initialization_check.json', image='initialization_check.png', message=message,
                                        scope='One fixed surroundings layout at ds16; main atlas remains layouts1–3 at ds8.',
                                        additional_years=3, domain_repeats=cycle['domain_repeats'])
    (data / 'atlas.json').write_text(json.dumps(meta, ensure_ascii=False), encoding='utf-8')
    return dict(status='passed', message=message, domain_repeats=cycle['domain_repeats'],
                land_repeats=last.get('map_land_repeats'))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('atlas', type=Path); ap.add_argument('--out', type=Path, required=True)
    a = ap.parse_args()
    atlas = a.atlas.resolve(); a.out.mkdir(parents=True, exist_ok=True)
    result = dict(surroundings=surroundings(atlas, a.out), initialization=initialization(atlas, a.out))
    write_json(a.out / 'diagnostics.json', result)
    print(json.dumps(result, indent=1, default=str))


if __name__ == '__main__':
    main()
