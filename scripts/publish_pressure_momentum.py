"""Publish the fixed initial-wind balance tradeoff without rainfall claims."""
from pathlib import Path
import argparse,json,shutil,sys
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from PIL import Image
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'scripts')]
from local_benchmark_protocol import file_hash,write_json


def publish(out):
    receipt=json.loads((out/'verification.json').read_text());plan=json.loads((out/'frozen_plan.json').read_text())
    literal=ROOT/'calibration/pressure_momentum_20261029/plan.json'
    if file_hash(literal)!=receipt['literal_plan_sha256'] or literal.read_bytes()!=(out/'frozen_plan.json').read_bytes():raise ValueError('Momentum declaration changed')
    for name,h in plan['sources'].items():
        if file_hash(ROOT/name)!=h:raise ValueError('Changed frozen momentum source: '+name)
    if receipt['static_initial_states_evaluated']!=30 or receipt['actual_earth_initialized_integrations_started']!=0 or receipt['adoption']:raise ValueError('Wrong diagnostic scope')
    combined={};groups={};max_optimality=0.
    for row in receipt['results']:
        region,scenario,name=row['region'],row['scenario'],row['candidate'];path=out/region/scenario/(name+'.npz')
        if file_hash(path)!=row['fields_sha256']:raise ValueError('Changed momentum fields')
        with np.load(path) as f:a={k:f[k] for k in f.files}
        np.testing.assert_allclose(max(abs(a['u']).max(),abs(a['v']).max()),row['peak_level_velocity_ms'],rtol=1e-12)
        np.testing.assert_allclose(np.sqrt(np.mean(a['temperature_tendency_k_s']**2))*86400,row['temperature_tendency_rms_k_day'],rtol=1e-12)
        np.testing.assert_allclose(abs(a['temperature_tendency_k_s']).max()*86400,row['maximum_temperature_tendency_k_day'],rtol=1e-12)
        c=row['certificate']
        if 'old_objective' in c:
            assert c['new_objective']<=c['old_objective']*(1+1e-12)
            max_optimality=max(max_optimality,c['relative_optimality_residual'])
        groups.setdefault((region,scenario),[]).append(row)
        combined.update({region+'_'+scenario+'_'+name+'_'+k:v for k,v in a.items()})
    if max_optimality>1e-9:raise ValueError('Momentum objective optimality failed')
    fig,axes=plt.subplots(2,3,figsize=(15,8))
    for col,region in enumerate(['north_india','mexico','pacific_nw']):
        for scenario,style in [('closed','--'),('prescribed_ports','-')]:
            rows=groups[region,scenario];x=[r['peak_level_velocity_ms'] for r in rows]
            residual=[r['mass_weighted_acceleration_norm']/rows[0]['mass_weighted_acceleration_norm'] for r in rows]
            axes[0,col].semilogy(x,np.maximum(residual,1e-16),style+'o',label=scenario.replace('_',' '))
            axes[1,col].semilogy(x,[r['temperature_tendency_rms_k_day'] for r in rows],style+'o')
            if scenario=='prescribed_ports':
                for r,y in zip(rows,[r['temperature_tendency_rms_k_day'] for r in rows]):
                    text={'archived_seed':'seed','regularized_3600':'1 h','regularized_21600':'6 h','regularized_86400':'24 h','formal_steady_drag':'steady'}[r['candidate']]
                    axes[1,col].annotate(text,(r['peak_level_velocity_ms'],y),xytext=(4,5),textcoords='offset points',fontsize=8)
        axes[0,col].set_title(region.replace('_',' '));axes[0,col].set_ylabel('Momentum residual / seed residual');axes[0,col].legend(fontsize=8)
        axes[1,col].set_ylabel('Instantaneous thermal tendency RMS (K/day)')
        for ax in axes[:,col]:ax.set_xlabel('Peak proposed level wind (m/s)');ax.grid(alpha=.2)
    fig.suptitle('Momentum-only initialization: smaller acceleration can mean worse thermal imbalance')
    fig.text(.5,.01,'30 static states • unchanged Earth rotation, drag, T and vapor • rates are not day-long forecasts • no coupled integration or rainfall score',ha='center',fontsize=9)
    fig.tight_layout(rect=(0,.04,1,.96));fig.savefig(out/'pressure_momentum.png',dpi=150);plt.close(fig)
    np.savez_compressed(out/'publication_fields.npz',**combined)
    result=dict(status='verified_thirty_static_momentum_states',new_earth_integrations=0,cumulative_earth_input_smoke_integrations=18,
        legacy_benchmark_attempts_added=0,recalibration=False,adoption=False,maximum_reported_relative_optimality_residual=max_optimality,
        scope='Source hashes, stored fields, declared scope and objective receipts checked; not an independent momentum discretization.',
        raw_fields_sha256=file_hash(out/'publication_fields.npz'),figure_sha256=file_hash(out/'pressure_momentum.png'),publisher_sha256=file_hash(Path(__file__)),receipt_sha256=file_hash(out/'verification.json'))
    dest=ROOT/'atlases/climate_accuracy/data';shutil.copyfile(out/'publication_fields.npz',dest/'pressure_momentum_fields.npz');shutil.copyfile(out/'pressure_momentum.png',dest/'pressure_momentum.png')
    write_json(dest/'pressure_momentum.json',dict(plan=plan,diagnostic=receipt,publication=result))
    with Image.open(out/'pressure_momentum.png') as im:width,height=im.size
    section=f'''<!--pressure-momentum-start--><section aria-labelledby="pressure-momentum-h"><h2 id="pressure-momentum-h">Initial momentum balance is not coupled climate balance</h2>
<p>A fixed diagnostic solves for initial winds while retaining the same temperature, water, Earth rotation, drag and boundary conditions. Three declared correction penalties (one, six and24 hours) expose the tradeoff between changing winds and reducing instantaneous momentum acceleration. The objective is convex with a unique solution; a local optimizer minimum does not explain this diagnostic's limitations.</p>
<figure><a href="data/pressure_momentum.png"><img src="data/pressure_momentum.png" width="{width}" height="{height}" loading="lazy" alt="For three Earth regions, reducing initial momentum residual requires larger winds and much larger instantaneous thermal tendencies"></a><figcaption>The30 static states include archived initial winds, three regularized corrections and a formal steady frozen-temperature solution, under two boundary setups. Thermal rates are instantaneous, before phase/convection; they are not predictions of a day's temperature change.</figcaption></figure>
<p><strong>Do not initialize the model with the formal steady winds.</strong> They reach207–250 m/s across these cases and leave very large thermal tendencies. For prescribed flow, the one-hour correction retains peak winds6.1–7.2 m/s but barely changes acceleration; a six-hour correction raises winds to29–34 m/s and thermal tendency RMS to9–15 K/day. Minimizing momentum alone can worsen the coupled initial state.</p>
<p class="note">No time integration, observations, rainfall optimization or adoption. The prior eighteen Earth-input smoke integrations and the legacy1934/1929 benchmark counts are unchanged. This is not full normal-mode initialization. The prototype excludes vertically averaged wind and nonlinear momentum dynamics; those restrictions must remain visible when interpreting the result. Normal atlas climate/biome/population fields are unchanged.</p>
<p><a href="data/pressure_momentum.json" download>Download frozen momentum diagnostic and all30 states</a> · <a href="data/pressure_momentum_fields.npz">Raw proposed winds and instantaneous tendencies</a> · <a href="../../reports/PRESSURE_MOMENTUM_20261029.md">Objective, limitations and next physics step</a></p></section><!--pressure-momentum-end-->'''
    page=ROOT/'atlases/climate_accuracy/index.html';text=page.read_text();start,end='<!--pressure-momentum-start-->','<!--pressure-momentum-end-->'
    if start in text:
        before,tail=text.split(start,1);_,after=tail.split(end,1);text=before+section+after
    else:text=text.replace('<!--research-list-start-->',section+'\n<!--research-list-start-->',1)
    page.write_text(text);write_json(out/'publication.json',result);print(json.dumps(result,indent=2))


if __name__=='__main__':
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--out',type=Path,required=True);publish(ap.parse_args().out.resolve())
