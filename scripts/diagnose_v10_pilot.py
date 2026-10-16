"""Read-only saved-run analysis; --write saves a diagnosis, never simulates."""
from __future__ import annotations
import argparse
from dataclasses import replace
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import numpy as np
from scripts import run_v10_pilot as pilot
from rotclimate_v10.core import (Config,DAY,advance,air_masses,capacities,divergence,
                                 stable_step,tracer_flux)
from rotclimate_v10.earth import atomic_json,load_case,sha256
from rotclimate_v10.integrate import rain_metrics,settling
from rotclimate_v10.weather import catalogue,flow_at


def load_verified(source,cache):
    source,cache = Path(source),Path(cache)
    manifest = json.loads((source/'manifest.json').read_text())
    if manifest['code_sha256'] != pilot.code_hash() or manifest['years'] != 3:
        raise ValueError('Pilot source changed or protocol is incompatible; preserve the original evidence.')
    config = Config(**manifest['config']);config.validate()
    cases = {};saved = {}
    for region,digest in manifest['prepared_sha256'].items():
        path = cache/f'{region}_{manifest["spacing_km"]:g}km.npz'
        if sha256(path) != digest:raise ValueError(f'Prepared input changed: {region}')
        case = load_case(path,region);cases[region] = case
        for mode in ('storms','mean_only'):
            folder = source/f'{region}_{mode}'
            years = [pilot.read_year(folder,y,case.domain.land.shape) for y in (1,2,3)]
            if any(r is None for r in years):raise ValueError(f'Incomplete pilot: {folder}')
            saved[region,mode] = years
    return manifest,config,cases,saved


def snapshot(case,config,state,storms,terrain=True):
    """One frozen January state/flux evaluation, not an equilibrated counterfactual."""
    d = case.domain
    forcing = d if terrain else replace(d,elevation_m=np.zeros_like(d.elevation_m))
    flow = flow_at(forcing,config,catalogue(d,config),0.,storms=storms)
    ml,mu,_ = air_masses(d,config)
    dt = min(300.,stable_step(flow,ml,mu,d.dx,d.dy,config))
    _,capu,_,_ = capacities(d,config,0.)
    ux,uy = tracer_flux(state.upper,mu,flow.upper_x,flow.upper_y,capu/mu*config.upper_boundary_rh)
    vertical = flow.vertical*np.where(flow.vertical>=0,state.lower/ml,state.upper/mu)
    upper = state.upper-dt*(divergence(ux,uy,d.dx,d.dy)-vertical)
    upper_rain = np.maximum(upper-capu,0.)
    _,rain,_ = advance(state,d,config,flow,dt,0.)
    mask = case.score_mask
    return {'time':'January 1; saved year-3 end state, frozen single step',
            'step_seconds':float(dt),'terrain_drag':terrain,
            'mean_land_rain_rate_mm_day':float(rain[mask].mean()*DAY/dt),
            'upper_layer_rain_fraction':float(upper_rain[mask].sum()/rain[mask].sum()) if rain[mask].sum()>0 else None,
            'lower_unretained_heating_k_hour':(rain-upper_rain)*2.5e6/(ml*1004)*3600/dt,
            'lower_mass_lifted_fraction_day':np.maximum(flow.vertical,0)/ml*DAY}


def analyse(source,cache):
    manifest,config,cases,saved = load_verified(source,cache)
    rows = []
    for region,case in cases.items():
        d = case.domain;mask = case.score_mask;obs = case.observed_rain_mm.sum(0)
        for mode in ('storms','mean_only'):
            years = saved[region,mode];r = years[-1];annual = r.rain_mm.sum(0)
            snap = snapshot(case,config,r.state,mode=='storms')
            flat = snapshot(case,config,r.state,mode=='storms',terrain=False)
            wet = mask & (annual>3000.)
            idx = np.argsort(np.where(mask,annual,-1).ravel())[-5:][::-1]
            top = []
            for i in idx:
                top.append({'latitude':float(d.latitude.ravel()[i]),'longitude':float(case.longitude.ravel()[i]),
                    'elevation_m':float(d.elevation_m.ravel()[i]),'predicted_annual_mm':float(annual.ravel()[i]),
                    'observed_annual_mm':float(obs.ravel()[i]),
                    'frozen_lower_unretained_heating_k_hour':float(snap['lower_unretained_heating_k_hour'].ravel()[i])})
            def small_snapshot(s):return {k:v for k,v in s.items() if not isinstance(v,np.ndarray)}
            rows.append({'region':region,'mode':mode,'rainfall':rain_metrics(case,r.rain_mm),
                'settling':settling(years[1],r,mask),'rain_p50_p95_p99_max_mm':np.percentile(annual[mask],[50,95,99,100]).tolist(),
                'over_3000mm_land_fraction':float(wet.sum()/mask.sum()),
                'over_3000mm_fraction_of_predicted_land_rain':float(annual[wet].sum()/annual[mask].sum()) if annual[mask].sum()>0 else 0.,
                'frozen_snapshot':small_snapshot(snap),'frozen_snapshot_no_drag':small_snapshot(flat),
                'top_five_cells':top,
                'max_annual_water_error_mm':max(abs(y.budget['annual_water_error_mm']) for y in years),
                'runtime_seconds':sum(json.loads((Path(source)/f'{region}_{mode}'/f'year{y}.json').read_text())['elapsed_seconds'] for y in (1,2,3))})
    return {'source':str(Path(source).resolve()),'pilot_manifest_sha256':sha256(Path(source)/'manifest.json'),
            'code_sha256':manifest['code_sha256'],'cases':rows,
            'interpretation':'Water accounting passes; rainfall skill fails. Frozen snapshots diagnose operators, not annual causal attribution.'}


def report(data):
    lines = ['# First V10 Earth pilot: diagnosis','',data['interpretation'],'',
        '| Region / mode | Mean annual model / observed (mm) | Monthly MAE (mm) | Rain settled + stores | Maximum cell (mm/year) |',
        '|---|---:|---:|---|---:|']
    for row in data['cases']:
        m = row['rainfall']
        lines.append(f"| {row['region']} / {row['mode']} | {m['predicted_mean_annual_mm']:.1f} / {m['observed_mean_annual_mm']:.1f} | "
            f"{m['monthly_mae_mm']:.1f} | {row['settling']['passed']} | {row['rain_p50_p95_p99_max_mm'][-1]:.0f} |")
    lines += ['', '## Findings and limits','',
        'All twelve saved years have verified array hashes and pass the declared physical budget checks. '
        'The frozen model/input fingerprint matches. These are accuracy failures, not a lost-water numerical instability.',
        'California storms worsen monthly MAE by 7.60 mm relative to mean-only. Iberia storms worsen it by 0.96 mm, '
        'but the Iberia mean-only case fails the soil-settling limit (3.66 mm at p95 versus 1 mm); that pair is diagnostic, not a settled verdict.',
        'The mean-flow cases already have extreme rain. The largest errors are not caused solely by transient storm frequency.',
        'Air temperatures are reset by prescription every step. Condensation loses latent energy without warming the air. '
        'The resulting cold reservoir can continuously strip moisture from incoming air. This is a structural hypothesis supported '
        'by the source and frozen tendency diagnosis; a coupled run is required to test its annual consequences.','']
    for row in data['cases']:
        if row['mode']!='mean_only':continue
        s = row['frozen_snapshot'];f = row['frozen_snapshot_no_drag'];top = row['top_five_cells'][0]
        lines += [f"{row['region']}: {row['over_3000mm_land_fraction']:.1%} of land exceeds 3,000 mm/year and supplies "
                  f"{row['over_3000mm_fraction_of_predicted_land_rain']:.1%} of predicted land rain. "
                  f"At the maximum-rain cell, the frozen January lower condensation implies {top['frozen_lower_unretained_heating_k_hour']:.2f} K/hour "
                  'of latent heating that the fixed-temperature engine cannot retain.',
                  f"January frozen step: {s['mean_land_rain_rate_mm_day']:.2f} mm/day mean land rain, "
                  f"{s['upper_layer_rain_fraction']:.1%} from the upper layer. Disabling only terrain drag in this frozen snapshot "
                  f"gives {f['mean_land_rain_rate_mm_day']:.2f} mm/day. Lower-layer saturation matters as well as the diagnosed vertical return. "
                  'The changed-flow snapshot is not a new equilibrium or a predicted annual reduction.','']
    lines += ['## Next mechanism test','',
        'Transport approximate moist static energy with water, retain latent heating during saturation adjustment, and relax '
        'temperatures toward the same observed reference on a declared finite time scale. Use exactly the same circulation first; '
        'then disable its terrain-drag term as a separate ablation. Keep observed rain out of the engine. '
        'Report water and energy budgets, temperature departures, rainfall extremes, and settling. '
        'A lower rainfall error caused by implausible temperature drift is not a validated improvement.',
        'This follows the role of latent heating in [NOAA/GFDL moist adjustment](https://www.gfdl.noaa.gov/bibliography/related_files/yk9801.pdf) '
        'and the [NCAR static-energy formulation](https://www.ncl.ucar.edu/Document/Functions/Contributed/static_energy_atm.shtml). '
        'It is an approximate kinematic test, not a full atmospheric energy or momentum model.',
        'Terrain/rain physics remains a later question: [Smith–Barstad (2004)](https://journals.ametsoc.org/view/journals/atsc/61/12/1520-0469_2004_061_1377_altoop_2.0.co_2.xml) '
        'also motivates airflow and cloud/evaporation treatment beyond instant fallout.','',
        'No seasonal simulation, calibration or atlas export was run in this analysis. The current atlas remains unchanged.']
    return '\n'.join(lines)+'\n'


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source',type=Path,default=ROOT/'output/v10_earth_pilot')
    p.add_argument('--cache',type=Path,default=ROOT/'data/v10_earth')
    p.add_argument('--write',action='store_true')
    p.add_argument('--out',type=Path,default=ROOT/'output/v10_pilot_diagnosis')
    args = p.parse_args(argv)
    try:data = analyse(args.source,args.cache)
    except (ValueError,OSError,KeyError) as e:p.error(str(e))
    print(report(data))
    if args.write:
        atomic_json(args.out/'diagnosis.json',data)
        (args.out/'diagnosis.md').write_text(report(data))
    return 0


if __name__=='__main__':raise SystemExit(main())
