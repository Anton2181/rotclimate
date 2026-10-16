"""Prepare and verify fixed event calendars; short independent probes only."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import numpy as np
from scripts import check_v10_event_forcing as run
from rotclimate_v10.earth import atomic_json, atomic_npz, sha256


def check():
    manufactured = run.fronts.probes()
    identity,inputs,setting,baselines,anchors = run.load_inputs()
    calendars = {};diagnostics = {};probes = [];regressions = []
    for region,(case,p,g,air,circulation) in inputs.items():
        print(region+': preparing circulation and matched-import tables (no state integration)',flush=True)
        arrays,diag = run.model.prepare_calendar(case,p,setting,g,air,circulation)
        calendars[region] = arrays;diagnostics[region] = diag
        events = run.model.core.nested_events(case.domain,setting,41,p.storm_domain_width_m)
        event_day = float(max(events,key=lambda event:event.strength).day)
        ticks = [float(np.floor(day*run.model.DAY/run.model.INTERVAL)*run.model.INTERVAL) for day in (0.,195.,event_day)]
        state = anchors[region][0]
        for amp in run.model.AMPLITUDES:
            for timing in run.model.TIMINGS:
                driver = run.model.Driver(arrays,case,p,setting,g,air,circulation,amp,timing)
                for t in ticks:
                    flow,boundary,_ = driver.at(t);dt = min(60.,run.model.base.stable_step(flow,g.mass,case.domain))
                    record = run.model.advance(state,case.domain,p,setting,flow,dt,t,air,geometry=g,boundary=boundary)
                    b = record[4]
                    predicted = float((run.model.incoming_coefficients(flow,case.domain)*boundary[:,arrays['boundary_mask']]).sum()*dt)
                    if abs(predicted-b['boundary_import_gross_mm']) > 1e-12:
                        raise ValueError('Prepared gross-influx coefficients disagree with step transport.')
                    probes.append({'region': region,'variant':run.model.variant_key(amp,timing),'time_s':t,'dt_s':dt,
                        'water_error_mm':b['water_error_mm'],'energy_error_j_m2':b['energy_error_j_m2'],
                        'theta_transport_error_kg_k_m2':b['theta_transport_error_kg_k_m2'],
                        'thermal_ledger_error_c':record[-1],'gross_influx_error_mm':predicted-b['boundary_import_gross_mm']})
        for mode in ('uniform','spatial'):
            for t in ticks:
                flow = run.model.core.flow_at(case.domain,p,setting,events,t,g,circulation[3],wind_mode=mode,circulation=circulation)
                dt = min(60.,run.model.base.stable_step(flow,g.mass,case.domain))
                q = run.model.core.boundary_ratio(case.domain,p,setting,g,air,t)
                old = run.model.core.advance(state,case.domain,p,setting,flow,dt,t,air,geometry=g)
                new = run.model.advance(state,case.domain,p,setting,flow,dt,t,air,geometry=g,boundary=q)
                for name in ('water','energy','soil'):
                    np.testing.assert_array_equal(getattr(old[0],name),getattr(new[0],name))
                for a,b in zip(old[1:4],new[1:4]):
                    np.testing.assert_array_equal(a,b)
                for a,b in zip(old[5:7],new[5:7]):
                    np.testing.assert_array_equal(a,b)
                if old[4] != new[4] or old[-1] != new[-1]:
                    raise ValueError('Explicit-boundary step differs from the frozen step.')
                regressions.append({'region':region,'wind':mode,'time_s':t,'dt_s':dt,'physical_arrays_and_budgets_identical':True})
    if run.source_id() != identity['code_sha256']:
        raise ValueError('Sources changed during event preflight.')
    data = {'schema':1,'identity':identity,'verified':True,'regional_diagnostics':diagnostics,
        'forcing_array_sha256':{region:run.parent.geometry_rules.array_id(a) for region,a in calendars.items()},
        'manufactured_probes':manufactured,'new_operator_probes':probes,'frozen_step_regression':regressions,
        'regional_climate_integrations':0,'downloads':0,'atlas_updated':False,
        'checks':'Full-year independent circulation/boundary queries, not state integration; two tiny manufactured steps and 48 independent regional <=60-second probes (36 new + 12 exact frozen-step regression).',
        'limits':'Synthetic event mechanism sensitivity; no observed event statistics, full thermal front or matched actual humidity distributions. Actual monthly gross import is enforced in future seasonal runs.'}
    return data,calendars


def markdown(data):
    lines = ['# Event-forcing preflight', '', data['checks'], '',
        '| Region | Max monthly incoming-water error | Max monthly mean velocity change | Max face component at lift 1 / 4 | Minimum step at lift 1 / 4 |',
        '|---|---:|---:|---:|---:|']
    for region,d in data['regional_diagnostics'].items():
        a,b = (d['variants'][key] for key in ('lift1_steady','lift4_steady'))
        lines.append(f"| {region} | {d['maximum_monthly_import_error_mm']:.2e} mm | {d['maximum_monthly_mean_face_velocity_change_m_s']:.2e} m/s | {a['maximum_face_component_speed_m_s']:.2f} / {b['maximum_face_component_speed_m_s']:.2f} m/s | {a['minimum_stable_step_s']:.1f} / {b['minimum_stable_step_s']:.1f} s |")
    lines += ['', '| Region | Coastal winter positive ascent, lift 1 → 4 | Annual boundary water dose | Normalization scale range |', '|---|---:|---:|---:|']
    winter = np.isin(np.arange(12),[0,1,2,3,10,11]);days = np.diff(run.model.EDGES)/run.model.DAY
    for region,d in data['regional_diagnostics'].items():
        ascent = [np.average(np.array(d['variants'][key]['monthly_coastal_positive_ascent_pa_s'])[winter],weights=days[winter]) for key in ('lift1_steady','lift4_steady')]
        scales = [v for row in d['variants'].values() for v in row['monthly_normalization_scale']]
        lines.append(f"| {region} | {ascent[0]:.5f} → {ascent[1]:.5f} Pa/s | {sum(d['monthly_import_target_mm']):.1f} mm / full domain | {min(scales):.3f}–{max(scales):.3f} |")
    lines += ['', data['limits'], '',
        'Two held-boundary controls run first and stop the batch if they materially differ '
        'from the old continuously interpolated-boundary climates. All cases retain zero '
        'prescribed incoming upper humidity; this assumption is not observed. No atlas '
        'publication or parameter search. No real seasonal run was launched during preflight.', '',
        'User-run seasonal command:', '', '```sh',
        'caffeinate -i .venv/bin/python -u scripts/check_v10_event_forcing.py --run', '```']
    return '\n'.join(lines)+'\n'


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--write',action='store_true');parser.add_argument('--out',type=Path,default=run.PREFLIGHT)
    args = parser.parse_args(argv);data,calendars = check()
    if args.write:
        manifest = args.out/'manifest.json'
        if manifest.exists():
            old = json.loads(manifest.read_text())
            if old['identity'] != data['identity'] or old['forcing_array_sha256'] != data['forcing_array_sha256']:
                raise ValueError('Preserve the old preflight; choose a new --out for changed source/forcing.')
            for region in calendars:
                if sha256(args.out/(region+'.npz')) != old['forcing_file_sha256'][region]:
                    raise ValueError('Existing prepared forcing changed.')
            data = old  # Do not rewrite immutable preflight artifacts referenced by runs.
        else:
            args.out.mkdir(parents=True,exist_ok=True)
            for region,arrays in calendars.items():
                atomic_npz(args.out/(region+'.npz'),**arrays)
            data['forcing_file_sha256'] = {region:sha256(args.out/(region+'.npz')) for region in calendars}
            atomic_json(manifest,data);(args.out/'review.md').write_text(markdown(data))
    print(markdown(data))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
