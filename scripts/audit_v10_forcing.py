"""Diagnose completed heat experiments; optionally compare NOAA air profiles.

Default is read-only. --saved-only --run audits saved runs and analytic winds.
--fetch --run obtains small public regional atmospheric subsets and audits
model assumptions. Neither mode performs a climate integration or calibration.
"""
from __future__ import annotations
import argparse
from dataclasses import asdict
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import numpy as np
from scripts import check_v10_thermodynamics as heat
from scripts.diagnose_v10_pilot import load_verified
from experiments import v10_forcing_audit as reference
from rotclimate_v10.earth import atomic_json,sha256
from rotclimate_v10.integrate import rain_metrics


def saved_analysis(source,heat_source,cache):
    manifest,config,cases,_ = load_verified(source,cache)
    root = Path(heat_source);hm = json.loads((root/'manifest.json').read_text())
    if hm['code_sha256']!=heat.source_hash() or hm['original_code_sha256']!=manifest['code_sha256']:
        raise ValueError('Frozen heat/pilot sources do not match these results.')
    if hm['baseline_manifest_sha256']!=sha256(Path(source)/'manifest.json') or hm['config']!=asdict(config):
        raise ValueError('Mismatched frozen baseline/configuration.')
    for relative,digest in hm['original_checkpoints'].items():
        if sha256(Path(source)/relative)!=digest:raise ValueError('Frozen original checkpoint changed.')
    summary = json.loads((root/'summary.json').read_text())
    expected = {f'{region}_{mode}_{proposal}' for region in cases for mode in ('storms','mean_only') for proposal in heat.PROPOSALS}
    if summary['failures'] or set(summary['cases'])!=expected:raise ValueError('Need all eight completed heat cases for this diagnosis.')
    rows = {};total_seconds = 0.
    for name in sorted(expected):
        row = summary['cases'][name];case = cases[row['region']]
        proposal = 'heat_no_drag' if name.endswith('_heat_no_drag') else 'heat'
        if row['closure']!=asdict(heat.PROPOSALS[proposal]):
            raise ValueError('Incorrect declared closure.')
        years = []
        for year in (1,2,3):
            result = heat.read_year(root/name,year,case.domain.land.shape)
            if result is None:raise ValueError('Incomplete heat checkpoint.')
            years.append(result)
            total_seconds += json.loads((root/name/f'year{year}.json').read_text())['elapsed_seconds']
        r = years[-1];b = r.budget
        rows[name] = {'region':row['region'],'mode':row['mode'],'closure':row['closure'],
            'rainfall':rain_metrics(case,r.rain_mm),'temperature':heat.temperature_diagnostics(r,case,config),
            'settling':heat.stability(years[1],r,case,config),
            'upper_rain_fraction_domain':float(b['upper_rain_mm']/b['rain_mm']),
            'annual_rain_max_mm':float(r.rain_mm.sum(0)[case.score_mask].max()),
            'max_annual_water_error_mm':max(abs(y.budget['annual_water_error_mm']) for y in years),
            'max_annual_energy_error_j_m2':max(abs(y.budget['annual_energy_error_j_m2']) for y in years)}
    # Verify the original control extension as well as the new coupled fields.
    control_status = {}
    for key,row in summary['baselines'].items():
        region,mode = row['region'],row['mode'];case = cases[region]
        y = row['year']
        if y not in (3,4,5):raise ValueError('Unexpected baseline extension year.')
        previous = heat.pilot.read_year(Path(source)/key,2,case.domain.land.shape)
        current = heat.pilot.read_year(Path(source)/key,3,case.domain.land.shape)
        for year in range(4,y+1):
            previous = current
            current = heat.pilot.read_year(root/f'{key}_unchanged_extension',year,case.domain.land.shape)
            if current is None:raise ValueError('Missing baseline extension checkpoint.')
        status = heat.settling(previous,current,case.score_mask)
        if status['passed']!=row['settling']['passed']:raise ValueError('Baseline settling record does not match arrays.')
        control_status[key] = {'year':y,'settling':status,'rainfall':rain_metrics(case,current.rain_mm)}
    geometry = {name:reference.circulation_geometry(case,config)[0] for name,case in cases.items()}
    data = {'cases':rows,'geometry':geometry,'integration_seconds_saved':total_seconds,
        'heat_manifest_sha256':sha256(root/'manifest.json'),'pilot_manifest_sha256':sha256(Path(source)/'manifest.json'),
        'sources_verified':True,'controls':control_status,'new_climate_integrations':0,'atlas_updated':False,'reference':{}}
    return data,cases,config


def markdown(data):
    lines = ['# V10 heat result and circulation audit','',
        'All completed heat cases and frozen pilot provenance were verified. No new climate integration or calibration was performed.','',
        '| Region / case | Mean annual rain (mm) | Monthly rain MAE (mm) | Lower / upper T departure p95 (°C) | Settled |',
        '|---|---:|---:|---:|---|']
    for name,row in data['cases'].items():
        t = row['temperature'];r = row['rainfall']
        lines.append(f"| {name} | {r['predicted_mean_annual_mm']:.0f} | {r['monthly_mae_mm']:.2f} | "
            f"{t['lower']['monthly_abs_departure_p95_c']:.2f} / {t['upper']['monthly_abs_departure_p95_c']:.2f} | {row['settling']['passed']} |")
    failed_temp = sum(not row['temperature']['provisional_guard_passed'] for row in data['cases'].values())
    failed_settling = sum(not row['settling']['passed'] for row in data['cases'].values())
    baseline_mae = data['controls']['california_storms']['rainfall']['monthly_mae_mm']
    coupled_mae = data['cases']['california_storms_heat']['rainfall']['monthly_mae_mm']
    settled_controls = sum(row['settling']['passed'] for row in data['controls'].values())
    lines += ['', f"{failed_temp}/{len(data['cases'])} cases fail the declared temperature-departure screen; "
        f"{failed_settling}/{len(data['cases'])} fail rain/storage settling. California storms with drag: monthly rainfall MAE "
        f"{baseline_mae:.2f} → {coupled_mae:.2f} mm. Temperature departures are from an assumed vertical profile, "
        'not independently observed temperatures at those levels. The atmospheric reference is needed to check the screen itself.','',
        f"{settled_controls}/{len(data['controls'])} original controls now meet the unchanged settling checks; "
        'any extra unchanged years were verified from their saved arrays. '
        'The 24 new heat integrations took about '+f"{data['integration_seconds_saved']/60:.2f}"+' minutes in saved timings.','',
        '## Structural finding','',
        'The prescribed lower/upper representative heights differ by 7.12 km. Terrain slowdown in the lower flux '
        'is compensated by direct exchange with the upper layer. This treats a mountain-induced flux adjustment '
        'as deep atmospheric exchange, rather than resolving shallow uplift/return. With coupled static energy, '
        'moving lower-layer air to that height can strongly cool the upper layer before latent heating and other terms.','']
    for region,g in data['geometry'].items():
        cooling = g['upper_reference_dry_cooling_p95_k_day']
        lines.append(f"{region}: the monthly p95 absolute dry vertical-exchange contribution at the prescribed reference profile "
            f"ranges {min(cooling):.1f}–{max(cooling):.1f} K/day. This is an operator diagnostic, not net atmospheric cooling, "
            'a measured reanalysis tendency, or a newly simulated climate.')
    drag = [r['upper_rain_fraction_domain'] for r in data['cases'].values() if r['closure']['terrain_drag']]
    nodrag = [r['upper_rain_fraction_domain'] for r in data['cases'].values() if not r['closure']['terrain_drag']]
    lines += ['', f"The coupled drag cases produce {min(drag):.1%}–{max(drag):.1%} of domain rain in the upper layer. "
        f"Without drag that share is {min(nodrag):.1%}–{max(nodrag):.1%}. "
        'The cases still fail the declared screening criteria. '
        'Heat retention alone did not solve the rainfall excess; the simplified circulation/vertical representation needs an independent check.','',
        '## Atmospheric reference','']
    if data['reference']:
        for region,r in data['reference'].items():
            low = r['levels']['lower'];high = r['levels']['upper']
            def season(a,indices):return float(np.asarray(a)[indices].mean())
            lines += [f"### {region}", '',
                f"Offshore ocean mask: {r['ocean_model_cells']} model cells; {low['reference_unique_native_cells']} unique native reference cells. "
                'Nearest horizontal cells and log-pressure interpolation, not an independent sample at every model cell.','',
                '| Lower-level mean | Winter (Dec–Feb) | Summer (Jun–Aug) |','|---|---:|---:|']
            for title,array in (('Model eastward wind (m/s)',r['model_lower_zonal_wind_ms']),
                                ('Reference eastward wind (m/s)',low['uwnd']),('Reference northward wind (m/s)',low['vwnd']),
                                ('Model target temperature (°C)',low['model_target_temperature_c']),('Reference air temperature (°C)',low['air']),
                                ('Model boundary mixing ratio (g/kg)',low['model_boundary_mixing_ratio_g_kg']),
                                ('Reference mixing ratio (g/kg)',low['reference_mixing_ratio_g_kg'])):
                lines.append(f'| {title} | {season(array,[11,0,1]):.2f} | {season(array,[5,6,7]):.2f} |')
            lines += ['',r['limitations'],'']
        lines += ['Reference: NCEP/NCAR Reanalysis 1 monthly 1981–2010 climatology, data provided by '
            '[NOAA PSL, Boulder, Colorado, USA](https://psl.noaa.gov/). '
            '[Verified atmospheric-product metadata](https://psl.noaa.gov/thredds/dodsC/Datasets/ncep.reanalysis.derived/pressure/uwnd.mon.1981-2010.ltm.nc.html).',
            'These are reanalysis estimates, not direct independent observations at every grid point. '
            'The normal period differs from the existing rainfall benchmark; this is an audit of structure, not a quantitative validation of rainfall skill.']
    else:
        lines += ['No independent atmospheric grids were downloaded in this saved-only diagnosis. The prepared reference audit will '
            'compare monthly ocean-side wind vectors, humidity and vertical temperature/height profiles before another model redesign.']
    lines += ['', '## Next decision','',
        'Defer further extensions or fitting of these heat cases. First check the assumed mean circulation and vertical '
        'thermodynamic structure against the atmospheric reference. Use that evidence to choose between shallow/multiple-layer '
        'terrain circulation and revised mean-flow/boundary forcing. Separate terrain uplift from deep synoptic ascent. '
        'Keep all observed rainfall out of the forcing; no new climate integration or atlas publication is part of this audit.']
    return '\n'.join(lines)+'\n'


def plot(data,out):
    if not data['reference']:return
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    for region,r in data['reference'].items():
        fig,axes = plt.subplots(2,2,figsize=(11,7),constrained_layout=True);x = np.arange(1,13)
        low = r['levels']['lower'];upper = r['levels']['upper']
        axes[0,0].plot(x,r['model_lower_zonal_wind_ms'],label='Model eastward')
        axes[0,0].plot(x,low['uwnd'],label='Reference eastward');axes[0,0].plot(x,low['vwnd'],label='Reference northward')
        axes[0,0].axhline(0,color='k',linewidth=.5);axes[0,0].set(ylabel='m/s',title='Lower-level mean wind');axes[0,0].legend()
        for name,a in (('lower',low),('upper',upper)):
            axes[0,1].plot(x,a['model_target_temperature_c'],label='Model '+name)
            axes[0,1].plot(x,a['air'],'--',label='Reference '+name)
        axes[0,1].set(ylabel='°C',title='Temperature profile');axes[0,1].legend()
        axes[1,0].plot(x,low['model_boundary_mixing_ratio_g_kg'],label='Model boundary')
        axes[1,0].plot(x,low['reference_mixing_ratio_g_kg'],label='Reference')
        axes[1,0].set(ylabel='g/kg dry air',title='Lower-level water mixing ratio');axes[1,0].legend()
        axes[1,1].plot(x,low['hgt'],label='Reference lower');axes[1,1].plot(x,upper['hgt'],label='Reference upper')
        axes[1,1].axhline(low['model_height_m'],label='Model lower',linestyle=':')
        axes[1,1].axhline(upper['model_height_m'],label='Model upper',linestyle=':')
        axes[1,1].set(ylabel='m',title='Representative level heights');axes[1,1].legend()
        for ax in axes.flat:ax.set_xlabel('Month')
        fig.suptitle(region+' offshore circulation audit — reference period 1981–2010; no climate run')
        fig.savefig(out/f'{region}_forcing.png',dpi=140);plt.close(fig)


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--run',action='store_true');p.add_argument('--fetch',action='store_true');p.add_argument('--saved-only',action='store_true')
    p.add_argument('--source',type=Path,default=ROOT/'output/v10_earth_pilot')
    p.add_argument('--heat-source',type=Path,default=ROOT/'output/v10_heat_check')
    p.add_argument('--cache',type=Path,default=ROOT/'data/v10_earth')
    p.add_argument('--reference-cache',type=Path,default=ROOT/'data/v10_atmosphere')
    p.add_argument('--out',type=Path)
    args = p.parse_args(argv)
    if args.fetch and (not args.run or args.saved_only):p.error('--fetch requires --run and cannot be combined with --saved-only.')
    print('Atmospheric structure audit: saved results + regional NOAA monthly wind, air temperature, height, humidity and omega.')
    print('No calibration, climate integration, or atlas update. Only small regional ASCII subsets are downloaded with --fetch.')
    if not args.run:
        print('Read-only plan. Run: .venv/bin/python -u scripts/audit_v10_forcing.py --fetch --run');return 0
    try:
        data,cases,config = saved_analysis(args.source,args.heat_source,args.cache)
        provenance = {}
        if not args.saved_only:
            texts,provenance = reference.acquire(args.reference_cache,args.fetch)
            fields = reference.fields_from_cache(texts)
            data['reference'] = {name:reference.reference_comparison(case,config,fields) for name,case in cases.items()}
        out = args.out or ROOT/('output/v10_circulation_audit' if args.saved_only else 'output/v10_forcing_audit')
        out = out.resolve()
        for source in (args.source.resolve(),args.heat_source.resolve(),args.cache.resolve(),args.reference_cache.resolve()):
            if out==source or source in out.parents:raise ValueError('Use a separate output directory to preserve existing inputs/runs.')
        code = hashlib.sha256((Path(__file__).read_bytes()+Path(reference.__file__).read_bytes()+heat.source_hash().encode())).hexdigest()
        expected = {'code_sha256':code,'heat_manifest_sha256':data['heat_manifest_sha256'],
                    'pilot_manifest_sha256':data['pilot_manifest_sha256'],'reference_downloads':provenance,'saved_only':args.saved_only}
        manifest = out/'manifest.json'
        if manifest.exists():
            if json.loads(manifest.read_text())!=expected:raise ValueError('Audit provenance changed; choose a new --out directory.')
        elif out.exists() and any(out.iterdir()):raise ValueError('Nonempty audit output lacks provenance; choose a new --out directory.')
        else:atomic_json(manifest,expected)
        atomic_json(out/'audit.json',data);(out/'audit.md').write_text(markdown(data));plot(data,out)
        print(f'Completed audit: {out/"audit.md"}');return 0
    except (ValueError,OSError,KeyError,FloatingPointError) as e:
        print(f'Cannot complete audit: {e}',file=sys.stderr);return 2


if __name__=='__main__':raise SystemExit(main())
