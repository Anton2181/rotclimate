"""Verify the completed paired event experiment; saved climate fields only."""
from __future__ import annotations
import argparse
from dataclasses import asdict
import json
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import numpy as np
from scripts import check_v10_event_forcing as run
from rotclimate_v10.core import DAY
from rotclimate_v10.earth import atomic_json,atomic_npz,sha256
RESPONSE_KEYS = ('monthly_mae_mm','annual_rain_mm','coast_winter_mm','interior_winter_mm','coast_summer_mm','interior_summer_mm')


def load_verified(source=ROOT/'output/v10_event_forcing'):
    protocol,inputs,setting,baselines,anchors,calendars = run.prepare()
    state = json.loads((source/'state.json').read_text())
    if json.loads((source/'manifest.json').read_text()) != protocol or state['status'] != 'complete':
        raise ValueError('Need an unchanged completed event-forcing protocol.')
    if set(state['cases']) != {job['key'] for job in protocol['jobs']}:
        raise ValueError('Completed event case set differs from the declared plan.')
    records = {};seconds = 0.;cycles = 0;errors = []
    for job in protocol['jobs']:
        key = job['key'];region = job['region'];case,p,g,air,c = inputs[region]
        folder = source/'cases'/key;row = state['cases'][key]
        identity = {**job,'settings':asdict(setting),'seed':41,
            'input_sha256':protocol['inputs'][region], 'forcing_array_sha256':protocol['forcing_array_sha256'][region]}
        if json.loads((folder/'config.json').read_text()) != identity or sha256(folder/'config.json') != row['case_config_sha256']:
            raise ValueError('Event case config changed.')
        if json.loads((folder/'summary.json').read_text()) != row:
            raise ValueError('Event case summary changed.')
        count = row['years'];evidence = {f'year{n}.{ext}' for n in range(1,count+1) for ext in ('json','npz')}
        if not 3 <= count <= 6 or set(row['evidence_sha256']) != evidence:
            raise ValueError('Incomplete event annual evidence declaration.')
        for name,digest in row['evidence_sha256'].items():
            if sha256(folder/name) != digest:
                raise ValueError('Completed event annual evidence changed.')
        initial = run.model.core.initial_state(case.domain,p,setting,g,air)
        previous = None;check = {'passed':False}
        for year in range(1,count+1):
            record = run.parent.read_checkpoint(folder,year,case.domain.land.shape,completed=True)
            if record is None:
                raise ValueError('Missing completed event annual fields.')
            run.validate_control_record(record,calendars[region]['monthly_import_target_mm'])
            errors.append(run.review.verify_annual(record,initial,case))
            changes = np.array(record[-1]['diagnostics']['temperature_changes_scored_land_c']).sum(axis=(0,1))
            t0 = run.model.base.temperature(initial.energy,g.mass,initial.water,g.height_m)
            t1 = run.model.base.temperature(record[0].energy,g.mass,record[0].water,g.height_m)
            if not np.allclose(changes,(t1-t0)[:,case.score_mask].mean(1),atol=1e-8,rtol=0):
                raise ValueError('Event annual thermal ledger disagrees with physical states.')
            if previous is not None:
                check = run.parent.settling(previous,record,case,g)
            if year < count and year >= 3 and check['passed']:
                raise ValueError('Event case continued beyond its first declared settling point.')
            initial = record[0];previous = record;seconds += record[-1]['elapsed_seconds'];cycles += 1
        computed = run.parent.night.summarize(record,case,check,count)
        computed['response'] = run.parent.review.run.review.run.rain_vector(case,record[1])
        target = run.koppen_maps.classify_months(case.domain.temperature_c,case.observed_rain_mm,case.score_mask)
        simulated = run.koppen_maps.classify_months(case.domain.temperature_c,record[1],case.score_mask)
        computed['koppen_fixed_surface_temperature'] = run.koppen_maps.comparison(target,simulated,case.score_mask)
        computed['maximum_monthly_import_error_mm'] = float(abs(np.array(record[-1]['diagnostics']['monthly_boundary_import_gross_mm'])-calendars[region]['monthly_import_target_mm']).max())
        if job['anchor']:
            computed['anchor_check'] = run.compare_anchor(record,anchors[region],baselines[region],case)
            computed['anchor_check']['passed'] &= check['passed']
            if not computed['anchor_check']['passed']:
                raise ValueError('Completed event batch has a failed discretization control.')
        if any(computed[k] != row[k] for k in computed):
            raise ValueError('Event summary disagrees with recomputed physical fields.')
        records[key] = record
    if run.source_id() != protocol['code_sha256']:
        raise ValueError('Sources changed during the event review.')
    return protocol,state,inputs,setting,records,calendars,seconds,cycles,errors


def differences(a,b):
    return {key:b['response'][key]-a['response'][key] for key in RESPONSE_KEYS}


def atmospheric_budget_difference(a,b):
    """Difference accounting, not attribution of the extra rain's water source."""
    terms = {'boundary_import':b['boundary_import_gross_mm']-a['boundary_import_gross_mm'],
        'ocean_evaporation':b['ocean_evaporation_mm']-a['ocean_evaporation_mm'],
        'land_recycling':b['land_evaporation_mm']-a['land_evaporation_mm'],
        'reduced_export':a['boundary_export_gross_mm']-b['boundary_export_gross_mm'],
        'roundoff':b['roundoff_correction_mm']-a['roundoff_correction_mm']}
    rain = b['rain_mm']-a['rain_mm']
    return {'domain_rain_change_mm':rain,'signed_ledger_terms_mm':terms,
        'implied_atmospheric_storage_change_difference_mm':sum(terms.values())-rain,
        'note':'All values are full-domain atmospheric mm. Land evaporation is recycled water. Ledger differences are not source fractions or causal attribution; storage changes need not vanish exactly.'}


def analyse(source):
    protocol,state,inputs,setting,records,calendars,seconds,cycles,errors = load_verified(source)
    rows = {};contrasts = {};arrays = {};fields = {}
    for region,(case,p,g,air,c) in inputs.items():
        maps = {'target':run.koppen_maps.classify_months(case.domain.temperature_c,case.observed_rain_mm,case.score_mask)}
        fields[region] = (case,maps);arrays[region+'_target'] = maps['target'];arrays[region+'_mask'] = case.score_mask
        arrays[region+'_longitude'] = case.longitude;arrays[region+'_latitude'] = case.domain.latitude
        for job in (job for job in protocol['jobs'] if job['region'] == region):
            key = job['key'];row = state['cases'][key];record = records[key]
            layer = np.array(record[-1]['diagnostics']['layer_rain_scored_land_mm']).sum(0)
            b = row['budget'];r = row['response']
            rows[key] = {'response':r,'annual_layer_rain_mm':layer.tolist(),'budget':b,
                'koppen':row['koppen_fixed_surface_temperature'],
                'supply':run.review.supply_balance(b),'settled':row['settling']['passed'],
                'temperature_departure_p95_c':row['temperature_departure_p95_c'],
                'broad_screen_passed':row['eligible'], 'maximum_monthly_import_error_mm':row['maximum_monthly_import_error_mm'],
                'error_change':run.review.error_changes(records[region+'_lift1_steady'][1],record[1],case.observed_rain_mm,case.score_mask),
                'mean_energy_flux_w_m2':{name:b[name]/(365*DAY) for name in ('surface_latent_input_j_m2','temperature_relaxation_j_m2','energy_boundary_export_j_m2','prescribed_flow_work_j_m2')}}
            if job['anchor']:
                rows[key]['anchor_check'] = row['anchor_check']
            classes = run.koppen_maps.classify_months(case.domain.temperature_c,record[1],case.score_mask)
            arrays[key+'_koppen'] = classes
            if (job['amplitude'],job['timing']) in ((1.,'steady'),(16.,'aligned')):
                maps['baseline' if job['amplitude'] == 1 else 'event'] = classes
        region_rows = {k:v for k,v in rows.items() if k.startswith(region+'_')}
        base = region_rows[region+'_lift1_steady'];event = region_rows[region+'_lift16_aligned']
        delta_layer = np.array(event['annual_layer_rain_mm'])-base['annual_layer_rain_mm']
        total = delta_layer.sum();deficit = base['response']['coast_winter_reference_mm']-base['response']['coast_winter_mm']
        contrasts[region] = {'lifting':{timing:differences(region_rows[region+'_lift1_'+timing],region_rows[region+'_lift16_'+timing]) for timing in run.model.TIMINGS},
            'aligned_minus_shifted':{str(int(amp)):differences(region_rows[region+f'_lift{int(amp)}_shifted'],region_rows[region+f'_lift{int(amp)}_aligned']) for amp in run.model.AMPLITUDES},
            'chosen_mechanism_minus_baseline':differences(base,event),
            'coastal_winter_deficit_fraction_closed':(event['response']['coast_winter_mm']-base['response']['coast_winter_mm'])/deficit,
            'layer_rain_change_mm':delta_layer.tolist(),
            'middle_three_layers_fraction_of_rain_increase':float(delta_layer[1:4].sum()/total),
            'atmospheric_budget_change':atmospheric_budget_difference(base['budget'],event['budget'])}
        contrasts[region]['lifting_timing_interaction'] = {key:contrasts[region]['aligned_minus_shifted']['16'][key]-contrasts[region]['aligned_minus_shifted']['1'][key] for key in RESPONSE_KEYS}
    data = {'source_code_sha256':protocol['code_sha256'],'source_manifest_sha256':sha256(source/'manifest.json'),
        'source_state_sha256':sha256(source/'state.json'),'analysis_script_sha256':sha256(Path(__file__)),
        'sources_verified':True,'completed_cases':len(rows),'cycles':cycles,'integration_minutes':seconds/60,
        'all_settled':all(row['settled'] for row in rows.values()),
        'both_anchors_passed':all(rows[region+'_lift1_steady']['anchor_check']['passed'] for region in inputs),
        'maximum_absolute_recomputed_errors':{name:max(abs(e[name]) for e in errors) for name in errors[0]},
        'maximum_integrated_monthly_import_error_mm':max(row['maximum_monthly_import_error_mm'] for row in rows.values()),
        'cases':rows,'contrasts':contrasts,
        'interpretation':'Twelve fixed cases; last settled synthetic year, not independent weather samples. Gross incoming vapor is matched but evaporation, recycling and actual humidity distributions can change. Fixed-T Koppen uses the same observed WorldClim monthly surface temperature. No automatic climate selection.',
        'new_climate_integrations':0,'atlas_updated':False}
    return data,fields,arrays,records


def markdown(data):
    lines = ['# Completed matched-import event experiment','',
        f"{data['completed_cases']}/12 cases, {data['cycles']} cycles, {data['integration_minutes']:.2f} saved integration minutes. All settle; both held-boundary controls pass. Physical, thermal and monthly dose ledgers verify.", '',
        '| Region | Coastal winter rain: baseline → lift16 + linked moisture | Reference | Original coastal deficit closed | Mediterranean still arid |',
        '|---|---:|---:|---:|---:|']
    for region in data['contrasts']:
        a,b = (data['cases'][region+'_'+name] for name in ('lift1_steady','lift16_aligned'))
        lines.append(f"| {region} | {a['response']['coast_winter_mm']:.1f} → {b['response']['coast_winter_mm']:.1f} mm | {b['response']['coast_winter_reference_mm']:.1f} mm | {data['contrasts'][region]['coastal_winter_deficit_fraction_closed']:.1%} | {b['koppen']['target_mediterranean_to_arid']:.1%} |")
    lines += ['', 'Stronger intermittent convergence produces useful additional coastal winter '
        'rain and reduces monthly error in both regions. It closes only a small part '
        'of the original deficit. This is not yet a Mediterranean climate fix.', '',
        '| Region | Stronger lift alone: extra coastal winter | Linked vs shifted moisture at lift1 | Linked vs shifted at lift16 | Rain increase formed in middle three layers |',
        '|---|---:|---:|---:|---:|']
    for region,c in data['contrasts'].items():
        lines.append(f"| {region} | {c['lifting']['steady']['coast_winter_mm']:+.2f} mm | {c['aligned_minus_shifted']['1']['coast_winter_mm']:+.2f} mm | {c['aligned_minus_shifted']['16']['coast_winter_mm']:+.2f} mm | {c['middle_three_layers_fraction_of_rain_increase']:.1%} |")
    lines += ['', 'The timing effects are small and not uniformly positive at the original '
        'lifting amplitude. One synthetic catalogue and saturation/dose normalization '
        'do not establish a robust observed moisture-covariance gain. Most new rain '
        'forms in the middle three layers (representative sea-level pressures roughly '
        '836/684/454 hPa; lower hybrid pressures vary over terrain), unlike the '
        'previous upper-humidity perturbation whose increment mostly formed at 150 hPa.', '',
        '## Water accounting', '',
        '| Region | Domain rain increase | Ocean evaporation change | Land recycling change | Reduced export | Remaining export / all vapor input |',
        '|---|---:|---:|---:|---:|---:|']
    for region,c in data['contrasts'].items():
        b = c['atmospheric_budget_change'];t = b['signed_ledger_terms_mm'];event = data['cases'][region+'_lift16_aligned']
        lines.append(f"| {region} | {b['domain_rain_change_mm']:+.2f} mm | {t['ocean_evaporation']:+.2f} mm | {t['land_recycling']:+.2f} mm | {t['reduced_export']:+.2f} mm | {event['supply']['export_to_supply']:.1%} |")
    lines += ['', 'These are signed **full-domain atmospheric ledger differences**, including '
        'ocean and unscored land; they are not the water-source fractions of extra land '
        'rain. Boundary import is fixed, but ocean evaporation increases and land '
        'recycling responds to wetting. Atmospheric storage/roundoff close the small '
        'remaining difference. Most vapor input is still exported without precipitation.', '',
        '![Coastal and interior monthly rain](rainfall_comparison.png)', '',
        '![Köppen comparison at fixed surface temperature](koppen_comparison.png)', '',
        'Map columns are observed-rain target, lift1/steady control and the predeclared '
        'lift16/aligned mechanism case. They are not selected by best class score. '
        'Both sides share observed surface temperature, the project classifier and '
        'evaluation mask. Neighboring western US / Mediterranean / North African '
        'land is included. Arid means B climates; these are cell counts, not country '
        'areas or independent weather replicates. Atlas unchanged.', '',
        '## Next diagnostic', '',
        'Do not start another amplitude, timing or seed search. Replay the already '
        'completed final year of four fixed cases (the baseline and linked lift16 '
        'case in each region), collecting coastal vapor budgets and joint humidity/'
        'ascent/process diagnostics. Start from each saved preceding-year state, '
        'require exact physical reproduction, and save restartable diagnostic output '
        'separately. This should distinguish dry rising air, poorly placed lifting '
        'and thermal relaxation erasing condensation opportunities before considering '
        'another physics change. A diagnostic stage condensation opportunity is not '
        'the rainfall of an alternative climate.', '',
        'No new regional integration, download, calibration or atlas update was '
        'launched for this review. Reproduce from saved fields:', '', '```sh',
        '.venv/bin/python scripts/review_v10_event_forcing.py --write', '```']
    return '\n'.join(lines)+'\n'


def plot(data,fields,records,out):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.patches import Patch
    from matplotlib.ticker import FuncFormatter
    maps = run.koppen_maps
    fig,axes = plt.subplots(2,2,figsize=(12.5,8),constrained_layout=True)
    styles = [('lift1_steady','Control','#8a8f93','--'),('lift16_steady','Stronger lift','#217899','-'),
        ('lift16_aligned','Lift + linked moisture','#7952a0','-'),('lift16_shifted','Lift + shifted moisture','#b06b2d',':')]
    for row,(region,(case,_)) in enumerate(fields.items()):
        for col,(label,mask) in enumerate((('Coast <150 km',case.score_mask&(case.coast_distance_km<150)),('Interior >300 km',case.score_mask&(case.coast_distance_km>300)))):
            ax = axes[row,col];x = np.arange(1,13)
            ax.plot(x,case.observed_rain_mm[:,mask].mean(1),'o-',color='#233740',label='Observed',lw=2)
            for key,name,color,style in styles:
                ax.plot(x,records[region+'_'+key][1][:,mask].mean(1),style,color=color,label=name,lw=1.8)
            ax.set(title=region.title()+' · '+label,ylabel='Rain (mm / month)',xticks=x,ylim=(0,None));ax.grid(alpha=.2);ax.legend(frameon=False,fontsize=8)
    fig.suptitle('Intermittent lifting helps, but coastal winter rainfall remains far too low',fontsize=14)
    for ext in ('png','svg'):fig.savefig(out/('rainfall_comparison.'+ext),dpi=170,facecolor='#fbfcfc')
    plt.close(fig)
    fig,axes = plt.subplots(2,3,figsize=(15.4,11.8));fig.subplots_adjust(left=.055,right=.99,top=.875,bottom=.22,wspace=.16,hspace=.28)
    fig.suptitle('Event-forcing test: most Mediterranean climate is still arid',y=.975,fontsize=20,fontweight='bold')
    fig.text(.52,.94,'Same observed surface temperature · reference rain versus simulated rain · 60 km cells',ha='center',fontsize=11)
    fig.text(.52,.917,'Matched monthly gross incoming water · same mean dry circulation · seed 41',ha='center',fontsize=10)
    present = set();labels = {'target':'Earth target','baseline':'Original lift · steady moisture','event':'Stronger lift · linked moisture'}
    for row,(region,(case,classes)) in enumerate(fields.items()):
        mask = case.score_mask;land = case.domain.land;lon = case.longitude[0];lat = case.domain.latitude[:,0]
        dx = float(np.diff(lon).mean());dy = float(abs(np.diff(lat).mean()))
        extent = (lon[0]-dx/2,lon[-1]+dx/2,lat[-1]-dy/2,lat[0]+dy/2)
        xlim = (case.longitude[mask].min()-1.7*dx,case.longitude[mask].max()+1.7*dx)
        ylim = (case.domain.latitude[mask].min()-1.1*dy,case.domain.latitude[mask].max()+1.1*dy)
        for column,key in enumerate(('target','baseline','event')):
            ax = axes[row,column];image = np.empty(land.shape+(3,),float);image[:] = np.array([226,239,243])/255
            image[land] = np.array([222,226,226])/255;image[mask] = np.array([maps.koppen.COLORS[maps.koppen.CODES[i]] for i in classes[key][mask]])/255
            present.update(maps.koppen.CODES[i] for i in classes[key][mask])
            ax.imshow(image,extent=extent,origin='upper',interpolation='nearest')
            ax.contour(case.longitude,case.domain.latitude,land.astype(float),levels=[.5],colors=['#52676d'],linewidths=.45)
            ax.set(xlim=xlim,ylim=ylim,title=labels[key]);ax.set_aspect(1/np.cos(np.deg2rad(case.domain.latitude[mask].mean())))
            ax.xaxis.set_major_formatter(FuncFormatter(lambda x,pos:f'{abs(x):g}°'+('W' if x<0 else 'E')))
            ax.yaxis.set_major_formatter(FuncFormatter(lambda y,pos:f'{y:g}°N'));ax.tick_params(labelsize=8)
            for name,x,y in maps.LANDMARKS[region]:
                if xlim[0]<x<xlim[1] and ylim[0]<y<ylim[1]:
                    ax.plot(x,y,'o',ms=2.5,color='#14232a');ax.annotate(name,(x,y),xytext=(4,4),textcoords='offset points',fontsize=7,bbox=dict(facecolor='white',alpha=.75,edgecolor='none',pad=1))
            if key == 'target':caption = f'{case.observed_rain_mm.sum(0)[mask].mean():.0f} mm/year · observed rain'
            else:
                r = data['cases'][region+('_lift1_steady' if key == 'baseline' else '_lift16_aligned')];k = r['koppen']
                caption = f"{r['response']['annual_rain_mm']:.0f} mm/year · {k['exact_class_agreement']:.0%} match · {k['target_mediterranean_to_arid']:.0%} Cs → arid"
            ax.set_xlabel(caption,fontsize=9,labelpad=8)
        axes[row,0].set_ylabel(maps.REGION_NAMES[region],fontsize=11,fontweight='semibold',labelpad=14)
    handles = [Patch(facecolor=np.array(maps.koppen.COLORS[c])/255,label=c+' · '+maps.koppen.DESCRIPTIONS[c]) for c in maps.koppen.CODES if c in present]
    handles.append(Patch(facecolor='#dee2e2',label='Gray · outside shared evaluation mask'))
    fig.legend(handles=handles,loc='lower center',bbox_to_anchor=(.52,.047),ncol=4,frameon=False,fontsize=8.3)
    fig.text(.52,.022,'WorldClim 1970–2000 target; fixed-temperature rainfall diagnostic. Last settled synthetic year; no atlas update.',ha='center',fontsize=9)
    for ext in ('png','svg'):fig.savefig(out/('koppen_comparison.'+ext),dpi=170,facecolor='#fbfcfc')
    plt.close(fig)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source',type=Path,default=ROOT/'output/v10_event_forcing')
    parser.add_argument('--out',type=Path,default=ROOT/'output/v10_event_review');parser.add_argument('--write',action='store_true')
    args = parser.parse_args(argv);data,fields,arrays,records = analyse(args.source)
    if args.write:
        a,b = args.out.resolve(),args.source.resolve()
        if a == b or a in b.parents or b in a.parents:raise ValueError('Preserve original experiment output.')
        args.out.mkdir(parents=True,exist_ok=True);atomic_json(args.out/'review.json',data)
        atomic_npz(args.out/'koppen_fields.npz',**arrays);(args.out/'review.md').write_text(markdown(data))
        plot(data,fields,records,args.out)
    print(markdown(data));return 0


if __name__ == '__main__':raise SystemExit(main())
