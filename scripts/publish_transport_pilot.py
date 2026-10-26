"""Verified portable publication for successive fixed column-transport pilots."""
from pathlib import Path
import argparse
import html
import json
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT));sys.path.insert(0,str(ROOT/'scripts'))
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.colors import TwoSlopeNorm,LogNorm
from local_benchmark_protocol import file_hash,write_json
from rotclimate import earth


def publish(out):
    review=json.loads((out/'review.json').read_text());protocol=json.loads((out/'protocol.json').read_text());plan=protocol['plan']
    if not review['complete'] or review['physics_or_atlas_adoption']:raise ValueError('Need completed research-only pilot')
    for path,expected in protocol['sources'].items():
        if file_hash(ROOT/path)!=expected:raise ValueError('Changed source epoch: '+path)
    records={}
    for name in plan['profiles']:
        records[name]={}
        for region in plan['regions']:
            path=out/name/f'{region}.json';row=json.loads(path.read_text())
            if row['identity']!=review['identity']:raise ValueError('Changed record identity')
            if row['status']=='passed':
                if not row['numerics']['all_checks_passed'] or file_hash(path.with_suffix('.npz'))!=row['arrays_sha256']:
                    raise ValueError('Unverified successful result')
            elif row['status']!='failed':raise ValueError('Unknown solve status')
            if name=='reference' and (row['status']!='passed' or not row['legacy_exact']):raise ValueError('Missing original control')
            if name in plan.get('profile_control_archives',{}) and (row['status']!='passed' or not row['physical_control_exact']):
                raise ValueError('Missing historical control')
            records[name][region]=row
    stem=out.name.rsplit('_',1)[0];slug=stem.replace('_','-')
    title={'two_layer':'Moist inflow and upper return flow','mass_tracer':'Air-mass-aware water transport',
           'humidity_gate':'Rain activation and moisture delivery'}[stem]
    profiles=list(plan['profiles']);regions=plan['regions'];eligible=plan['eligible_profiles']
    labels={name:name.replace('_',' ') for name in profiles}
    labels.update(reference='r39',reference_damped='r39 numerical control',balanced_control='Balanced single layer',
        thermal_balanced_control='Balanced +1 km control',two_layer_control='Original two-layer control')
    parameter=plan.get('publication_parameter','moisture_upper_q_ratio')
    for name in eligible:
        value=plan['profiles'][name].get(parameter)
        prefix='Rain threshold RH' if parameter=='rh_threshold' else 'Upper/lower q'
        labels[name]=f'{prefix} = {value:g}' if value is not None else name.replace('_',' ')
    data=ROOT/'atlases/climate_accuracy/data'
    ratios=[[None if records[n][r]['status']!='passed' else records[n][r]['rain']['loss']/records['reference'][r]['rain']['loss']
             for n in profiles] for r in regions]
    fig,axes=plt.subplots(1,2,figsize=(14,6),constrained_layout=True)
    matrix=np.array([[np.nan if x is None else x for x in row] for row in ratios]);shown=np.log10(matrix)
    limit=max(.2,float(np.nanmax(np.abs(shown))))
    im=axes[0].imshow(shown,cmap='RdBu_r',norm=TwoSlopeNorm(vmin=-limit,vcenter=0,vmax=limit),aspect='auto')
    for i,j in np.ndindex(matrix.shape):
        axes[0].text(j,i,'FAIL' if not np.isfinite(matrix[i,j]) else f'{matrix[i,j]:.2f}',ha='center',va='center',fontsize=8,
            bbox=dict(facecolor='white',alpha=.75,edgecolor='none',pad=1))
    short=dict(reference='r39',reference_damped='Damped',balanced_control='Balanced\ncontrol',
        thermal_balanced_control='Balanced\n+1 km',two_layer_control='Two-layer\ncontrol',transport_control='Transport\ncontrol')
    symbol='RH' if parameter=='rh_threshold' else 'q'
    ticks=[f'{symbol}={plan["profiles"][n][parameter]:g}' if n in eligible else short.get(n,n.replace('_','\n')) for n in profiles]
    axes[0].set(xticks=np.arange(len(profiles)),xticklabels=ticks,yticks=np.arange(len(regions)),
        yticklabels=[r.replace('_',' ').title() for r in regions],title='Local rain loss / r39 · lower is better')
    axes[0].tick_params(axis='x',labelsize=8)
    fig.colorbar(im,ax=axes[0],shrink=.7,label='Log10 local rain-loss ratio')
    selected=['reference',list(plan.get('profile_control_archives',{}))[-1],*eligible]
    colors=['#285c80','#888888','#cf9142','#a14d68','#6c79ad']
    for name,color in zip(selected,colors):
        row=records[name]['north_india']
        if row['status']=='passed':axes[1].plot(row['monthly_rain']['simulated'],label=labels[name],color=color,lw=1.8)
    axes[1].plot(records['reference']['north_india']['monthly_rain']['observed'],color='#222',lw=2.5,label='WorldClim')
    axes[1].set(xticks=np.arange(12),xticklabels=list('JFMAMJJASOND'),title='North India · rainfall season',ylabel='mm / equal model month')
    axes[1].grid(alpha=.15);axes[1].legend(frameon=False,fontsize=8)
    fig.suptitle(title,fontsize=16)
    fig.supxlabel('Fixed Earth planet and geography; seven reused development regions, paired controls and unchanged error safeguards.\n'
        'Numerical validity, dry-air mass balance and rainfall accuracy are tested separately. No profile is adopted by this publication.',fontsize=9)
    first=data/f'{stem}_scores.png';fig.savefig(first,dpi=145);plt.close(fig)
    earth.REGIONS.update(json.loads((ROOT/'calibration/local_accuracy_20261023/regions_dev12.json').read_text()))
    map_control=plan.get('map_control',list(plan.get('profile_control_archives',{}))[-1]);map_candidate=eligible[len(eligible)//2]
    fig,axes=plt.subplots(2,3,figsize=(14,8),constrained_layout=True)
    for i,region in enumerate(['north_india','pacific_nw']):
        case=earth.region_case(region,plan['cell_km']);sl=case.grid.map_slice();lon,lat=case.lon[sl],case.grid.lat[sl]
        for ax,(name,key,label) in zip(axes[i],[('reference','observed','WorldClim'),(map_control,'simulated',labels[map_control]),
                                              (map_candidate,'simulated',labels[map_candidate])]):
            if records[name][region]['status']!='passed':
                ax.text(.5,.5,'FAILED · no accepted map',ha='center',transform=ax.transAxes);continue
            with np.load(out/name/f'{region}.npz') as z:
                value=np.where(z['valid'],np.maximum(z[key].sum(0),.001),np.nan);mean=float(z[key][:,z['valid']].sum(0).mean())
            im=ax.pcolormesh(lon,lat,value,shading='nearest',cmap='YlGnBu',norm=LogNorm(vmin=50,vmax=4000))
            ax.contour(lon,lat,case.grid.elev[sl],levels=[1500,3000],colors='#444',linewidths=.4,alpha=.5)
            ax.set(title=f'{region.replace("_"," ").title()} · {label}\n{mean:.0f} mm/year',xlabel='Longitude (°E)',ylabel='Latitude (°N)')
            ax.set_aspect(1/np.cos(np.radians(lat.mean())))
    fig.colorbar(im,ax=axes,shrink=.7,extend='both',label='Annual rain (mm/year) · same logarithmic scale')
    fig.suptitle(title+' · fixed spatial examples',fontsize=16)
    fig.supxlabel('Same scored56km cells. The fixed middle parameter value is shown, not a selected best map.\n'
        'All profiles and failures are retained; annual regional totals do not replace local monthly error.',fontsize=9)
    second=data/f'{stem}_maps.png';fig.savefig(second,dpi=145);plt.close(fig)
    images=[first,second];tracer_diagnostic=None;extra_html=''
    if stem=='mass_tracer':
        from scipy.ndimage import gaussian_filter
        from rotclimate.column_mass import ColumnMassProjection
        from rotclimate.layer_transport import return_branches
        from rotclimate.storms import conservative_exchange
        from rotclimate.transport import moisture_terms
        terrain=np.tile(np.linspace(0,4000,11),(9,1));projector=ColumnMassProjection(terrain,56000)
        u=np.full_like(terrain,6.);v=np.zeros_like(terrain);ub,vb,_=projector.project(u,v)
        layers,eu,ev=return_branches(u,v,ub,vb,1.);water=10*projector.mass
        diagnostics={}
        for label,mass in [('Column-water donors',None),('Common air mass',projector.mass)]:
            loss,mix=conservative_exchange(np.full_like(water,1e-5),lambda a:gaussian_filter(a,1,mode='reflect'),mass)
            terms=moisture_terms(water,eu,ev,56000,60000,0,0,loss,mix(water),form='flux',layers=layers,mass=mass)
            diagnostics[label]={key:float(np.nanmax(np.abs(terms[key]))) for key in ['advection','diffusion','storm_exchange']}
        tracer_diagnostic=dict(scope='Manufactured uniform-q terrain case, not a climate score',shape=[9,11],cell_km=56,
            terrain_m=[0,4000],water_scale_mm=10,upper_lower_q_ratio=1,maximum_absolute_terms_mm_day=diagnostics)
        write_json(out/'tracer_equilibrium.json',tracer_diagnostic)
        fig,ax=plt.subplots(figsize=(10,4.5),constrained_layout=True)
        x=np.arange(3)
        for offset,(label,values),color in zip([-.18,.18],diagnostics.items(),['#b77841','#318b91']):
            ax.bar(x+offset,np.maximum(list(values.values()),1e-15),width=.34,label=label,color=color)
        ax.set(xticks=x,xticklabels=['Advection','Diffusion','Storm exchange'],yscale='log',
            ylabel='Largest local |transport term| (mm/day)',title='Uniform mixing ratio should remain uniform over terrain')
        ax.legend(frameon=False);ax.grid(axis='y',alpha=.15)
        fig.supxlabel('No rain or physical sources; same stationary dry-air flow and water proportional to column mass.\n'
            'This verifies operator consistency, not observed rainfall skill. Values below1e-15 are clipped for the logarithmic axis.',fontsize=9)
        proof=data/'mass_tracer_equilibrium.png';fig.savefig(proof,dpi=145);plt.close(fig);images.append(proof)
        extra_html=f'<figure><a href="data/{proof.name}"><img src="data/{proof.name}" width="1450" height="653" loading="lazy" alt="Manufactured uniform mixing ratio: common-mass advection, diffusion and storm terms vanish to roundoff"></a><figcaption>The common air mass corrects a terrain tracer-consistency defect. Numerical equilibrium is separate from climate accuracy.</figcaption></figure>'
    compact={n:{r:{key:row.get(key) for key in ['status','error','rain','temperature','sst','column_speed','monthly_rain','circulation']}
                for r,row in group.items()} for n,group in records.items()}
    branches={n:{r:{key:value for key,value in row.get('numerics',{}).get('two_layer_transport',{}).items() if key!='steps'}
                 for r,row in group.items()} for n,group in records.items()}
    passed=sum(row['status']=='passed' for group in records.values() for row in group.values());attempted=sum(len(g) for g in records.values())
    decision='No profile passed all fixed safeguards' if not review['development_finalists'] else 'Screening qualifiers require subsequent Earth/world checks'
    summary=dict(complete=True,decision=decision,attempted_runs=attempted,passed_runs=passed,failed_runs=attempted-passed,
        profiles=profiles,labels=labels,regions=regions,screen=review['screen'],records=compact,branch_certificates=branches,
        local_rain_loss_ratio=ratios,physical_definition=plan['physical_definition'],scope=plan['publication'],
        selected_map_profile=map_candidate,tracer_equilibrium=tracer_diagnostic,physics_or_atlas_adoption=False,
        provenance=dict(protocol_sha256=file_hash(out/'protocol.json'),review_sha256=file_hash(out/'review.json'),publisher_sha256=file_hash(Path(__file__))),
        images_sha256={p.name:file_hash(p) for p in images})
    write_json(data/f'{stem}.json',summary)
    table=[]
    for n in profiles:
        row=records[n]['north_india']
        if row['status']=='passed':
            table.append(f'<tr><td>{html.escape(labels[n])}</td><td>{row["rain"]["sim_mean_annual_mm"]:.0f}</td><td>{row["rain"]["monthly_mae_mm"]:.2f}</td>'
                f'<td>{row["circulation"]["scores"]["q925_300"]["land"]["vector_rmse_ms"]:.2f}</td></tr>')
        else:table.append(f'<tr><td>{html.escape(labels[n])}</td><td colspan="3">FAILED</td></tr>')
    specific=''
    if stem=='mass_tracer':specific='<p>This follow-up uses the same air mass for donor W/M advection, mixing-ratio diffusion and storm exchange. The disabled path reproduces the preceding two-layer control exactly.</p>'
    if stem=='humidity_gate':specific='<p>Transport is held at the middle humidity ratio0.2. Only the rain-activation threshold changes to fixed0.5/0.6/0.7, testing whether delayed rainout improves delivery. This bounded plan was declared before its parent experiment finished; no extra humidity ratios or regional multipliers are added.</p>'
    section=f'''<!--{slug}-start--><section aria-labelledby="{slug}-h"><h2 id="{slug}-h">{title}</h2>
{specific}
<p>Moist lower inflow and a drier upper return are transported as separate conservative directional branches. Their combined dry-air flux retains the stationary column constraint. Total water still shares a fixed vertical humidity profile; vertical humidity and thermodynamics are not independently prognostic. Surface heat, evaporation and terrain lift retain surface winds. Earth planetary settings stay fixed.</p>
<p>The pilot attempts {attempted} integrations: {passed} pass strict numerics and {attempted-passed} fail. Original and historical physical controls must reproduce their archived fields before candidates. <strong>{decision}.</strong> No adopted profile, headline score or atlas climate is replaced by this research page.</p>
<figure><a href="data/{first.name}"><img src="data/{first.name}" width="2030" height="870" loading="lazy" alt="All fixed transport profiles: local regional rain-loss ratios and North India monthly rain"></a><figcaption>Every trial faces rain, temperature, regional, ocean, outside-wind, mass and separate-branch speed safeguards. Separate upwinding adds grid-dependent first-order mixing; it is not a measured physical diffusivity. Control details and all numerical certificates are in the download.</figcaption></figure>
<div class="table"><table><caption>North India, identical scored cells</caption><thead><tr><th>Profile</th><th>Annual rain mm</th><th>Monthly rain MAE mm</th><th>Wind RMSE m/s</th></tr></thead><tbody>{''.join(table)}</tbody></table></div>
<figure><a href="data/{second.name}"><img src="data/{second.name}" width="2030" height="1160" loading="lazy" alt="Observed, control and fixed middle-ratio transport rainfall maps in North India and Pacific Northwest"></a><figcaption>These fixed examples expose spatial tradeoffs. All ratios and failures remain in the results; closer annual totals can still hide worse local rain.</figcaption></figure>
{extra_html}
<p class="note">The model retains approximate hydrostatic mass, flat projected geometry, a fixed lower mass fraction and an imposed vertical humidity shape. Reanalysis constraints cover only a monthly925–300hPa partial column and omit transient moisture covariance. Reused development regions are not new independent validation.</p>
<p><a href="data/{stem}.json" download>Download {title.lower()} results</a> · <a href="../../reports/{stem.upper()}_20261026.md">Method, results and limitations</a></p></section><!--{slug}-end-->'''
    page=ROOT/'atlases/climate_accuracy/index.html';content=page.read_text();start,end=f'<!--{slug}-start-->',f'<!--{slug}-end-->'
    if start in content:
        before,rest=content.split(start,1);_,after=rest.split(end,1);content=before+section+after
    else:content=content.replace('</main>',section+'\n</main>')
    page.write_text(content)
    write_json(out/'publication.json',dict(status='published_research_only',page_sha256=file_hash(page),metadata_sha256=file_hash(data/f'{stem}.json'),
        images_sha256=summary['images_sha256'],publisher_sha256=file_hash(Path(__file__)),physics_or_atlas_adoption=False))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--out',type=Path,required=True)
    publish(parser.parse_args().out.resolve())
