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


def plot_westerly_circulation(records,plan,labels,path):
    """Plot the new PNW native diagnostics with explicit missing-data marks."""
    names=[plan['extra_circulation_control'],*plan['eligible_profiles']]
    group=plan['extra_circulation_groups']['pacific_nw']
    fig,axes=plt.subplots(1,3,figsize=(16,5.8),constrained_layout=True)
    colors=['#777777',*plt.colormaps['tab10'](np.linspace(0,1,len(names)-1))]
    scores={};status={};reference_wind=reference_humidity=None
    def monthly(value,shape):
        try:array=np.asarray(value,float)
        except (TypeError,ValueError):return None
        return array if array.shape==shape and np.isfinite(array).all() else None
    for name,color in zip(names,colors):
        row=records.get(name,{}).get('pacific_nw',{})
        extra=row.get('extra_circulation') or {}
        wind=extra.get('scores',{}).get('q925_300',{}).get(group)
        humidity=extra.get('humidity',{}).get('scores',{}).get(group)
        issues=[]
        if row.get('status')!='passed':
            issues.append('FAILED solve or missing completed record');wind=humidity=None
        scores[name]=(wind,humidity)
        model=monthly(None if wind is None else wind.get('monthly_model'),(12,2))
        observed=monthly(None if wind is None else wind.get('monthly_reference'),(12,2))
        if model is not None:
            # Scores store twelve months by east/north component.
            axes[0].plot(model[:,0],label=labels[name],color=color,lw=1.8)
        else:
            issues.append('FAILED wind series')
            axes[0].plot([],[],label=labels[name]+' · MISSING',color=color,ls=':')
        if reference_wind is None and observed is not None:reference_wind=observed[:,0]
        model=monthly(None if humidity is None else humidity.get('monthly_model_q_ratio'),(12,))
        observed=monthly(None if humidity is None else humidity.get('monthly_reference_q_ratio'),(12,))
        if model is not None:axes[1].plot(model,label=labels[name],color=color,lw=1.8)
        else:
            issues.append('FAILED humidity series')
            axes[1].plot([],[],label=labels[name]+' · MISSING',color=color,ls=':')
        if reference_humidity is None and observed is not None:reference_humidity=observed
        status[name]=issues
    if reference_wind is not None:axes[0].plot(reference_wind,color='#222',lw=2.5,label='NCEP/NCAR925–300 hPa')
    else:axes[0].text(.5,.5,'FAILED · observed wind missing',ha='center',transform=axes[0].transAxes)
    if reference_humidity is not None:axes[1].plot(reference_humidity,color='#222',lw=2.5,label='NCEP/NCAR')
    else:axes[1].text(.5,.5,'FAILED · observed humidity missing',ha='center',transform=axes[1].transAxes)
    axes[0].set(title='PNW native ocean · eastward moisture wind',ylabel='Eastward speed (m/s)')
    axes[1].set(title='PNW native ocean · partial humidity shape',ylabel='Mean q700–300 / mean q925–700')
    for ax in axes[:2]:
        ax.set(xticks=range(12),xticklabels=list('JFMAMJJASOND'));ax.grid(alpha=.15)
        ax.legend(frameon=False,fontsize=7)
    baseline=scores[names[0]];x=np.arange(len(names));width=.24;maximum_ratio=1.02
    metrics=[(0,'vector_rmse_ms','Vector RMSE','#547fa8'),
             (1,'partial_water_mae_mm','PW MAE','#5c9a7c'),
             (1,'partial_q_ratio_mae','q-shape MAE','#ba8658')]
    for offset,(index,key,label,color) in zip([-width,0,width],metrics):
        values=[]
        for name in names:
            own=scores[name][index];control=baseline[index]
            numerator=None if own is None else own.get(key)
            denominator=None if control is None else control.get(key)
            if (numerator is None or denominator is None or not np.isfinite([numerator,denominator]).all()
                    or numerator<0 or denominator<=0):
                values.append(np.nan);status[name].append('FAILED '+label+' ratio')
            else:values.append(numerator/denominator)
        axes[2].bar(x+offset,values,width=width,color=color,label=label)
        maximum_ratio=max(maximum_ratio,max((v for v in values if np.isfinite(v)),default=0))
        for i,value in enumerate(values):
            if not np.isfinite(value):axes[2].text(i+offset,.03,'FAIL',rotation=90,ha='center',va='bottom',fontsize=6,color=color)
    wind_limit=plan['extra_circulation_max_ratio'];humidity_limit=plan['extra_humidity_max_ratio']
    axes[2].axhline(wind_limit,color='#315f91',ls='--',lw=1.2,label=f'{wind_limit:.2f} wind target')
    axes[2].axhline(humidity_limit,color='#925524',ls=':',lw=1.5,label=f'{humidity_limit:.2f} humidity limit')
    ticks=[plan.get('publication_ticks',{}).get(n,labels[n])+('\nMISSING / FAIL' if status[n] else '') for n in names]
    axes[2].set(xticks=x,xticklabels=ticks,title='Separate native circulation and humidity guards',
        ylabel='Observed error / fresh corrected control',ylim=(0,1.35*maximum_ratio))
    axes[2].tick_params(axis='x',labelsize=8);axes[2].grid(axis='y',alpha=.15);axes[2].legend(frameon=False,fontsize=7)
    fig.suptitle('Shared westerlies · Pacific Northwest transport and humidity',fontsize=16)
    fig.supxlabel('All three fixed amplitudes and the corrected original-westerly control; four native ocean footprints, no accepted land footprint.\n'
        'Wind requires a 10% vector-RMSE reduction; each humidity MAE may increase at most 2%. Monthly partial reanalysis is not exact vapor flux.',fontsize=9)
    fig.savefig(path,dpi=145);plt.close(fig)
    return status


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
                if region in plan.get('extra_circulation_regions',[]):
                    extra=path.with_name(region+'_extra.npz')
                    if not extra.exists() or file_hash(extra)!=row.get('extra_circulation_arrays_sha256'):
                        raise ValueError('Unverified extra native circulation arrays')
            elif row['status']!='failed':raise ValueError('Unknown solve status')
            if name=='reference' and (row['status']!='passed' or not row['legacy_exact']):raise ValueError('Missing original control')
            if name in plan.get('profile_control_archives',{}) and (row['status']!='passed' or not row['physical_control_exact']):
                raise ValueError('Missing historical control')
            records[name][region]=row
    stem=plan.get('publication_stem',out.name.split('_20261026',1)[0]);slug=stem.replace('_','-')
    title={'two_layer':'Moist inflow and upper return flow','mass_tracer':'Air-mass-aware water transport',
           'humidity_gate':'Rain activation and moisture delivery',
           'shared_wind':'Shared wind calibration on conservative transport',
           'storm_path':'Storm paths and local condensation',
           'pressure_column':'Hydrostatic saturation and rainfall',
           'independent_water':'Independent lower and upper atmospheric water',
           'column_rain':'Column convection and falling-rain evaporation',
           'westerly_fit':'Shared westerlies and climate calibration'}[stem]
    profiles=list(plan['profiles']);regions=plan['regions'];eligible=plan['eligible_profiles']
    labels={name:name.replace('_',' ') for name in profiles}
    labels.update(reference='r39',reference_damped='r39 numerical control',balanced_control='Balanced single layer',
        thermal_balanced_control='Balanced +1 km control',two_layer_control='Original two-layer control',
        transport_control='Common-mass transport control')
    labels.update(plan.get('publication_labels',{}))
    parameter=plan.get('publication_parameter','moisture_upper_q_ratio')
    for name in eligible:
        value=plan['profiles'][name].get(parameter)
        prefix='Rain threshold RH' if parameter=='rh_threshold' else 'Upper/lower q'
        labels[name]=(plan['publication_labels'][name] if stem in ('pressure_column','independent_water','column_rain','westerly_fit') else
                      f'Wind trial {eligible.index(name)+1}' if stem=='shared_wind' else
                      'Short hops, no condensation' if name=='hops_only' else
                      f'Crest coefficient = {value:g}' if parameter=='eddy_rainout' else
                      f'{prefix} = {value:g}' if value is not None else name.replace('_',' '))
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
    symbol='RH' if parameter=='rh_threshold' else 'C' if parameter=='eddy_rainout' else 'q'
    short.update(pressure_control='Pressure\ncontrol')
    ticks=[]
    for n in profiles:
        if n in plan.get('publication_ticks',{}):tick=plan['publication_ticks'][n]
        elif n not in eligible:tick=short.get(n,n.replace('_','\n'))
        elif stem=='independent_water':tick='No vertical\nmixing' if plan['profiles'][n][parameter]==0 else '5day vertical\nmixing'
        elif stem=='pressure_column':tick=f'{plan["profiles"][n]["column_saturation_scheme"].split("-")[-1].title()}\nRH={plan["profiles"][n]["ocean_rh"]:.2f}'
        elif stem=='shared_wind':tick=f'Wind {eligible.index(n)+1}'
        elif n=='hops_only':tick='Hops only'
        else:tick=f'{symbol}={plan["profiles"][n][parameter]:g}'
        ticks.append(tick)
    axes[0].set(xticks=np.arange(len(profiles)),xticklabels=ticks,yticks=np.arange(len(regions)),
        yticklabels=[r.replace('_',' ').title() for r in regions],title='Local rain loss / r39 · lower is better')
    axes[0].tick_params(axis='x',labelsize=8)
    fig.colorbar(im,ax=axes[0],shrink=.7,label='Log10 local rain-loss ratio')
    selected=['reference',plan.get('map_control',list(plan.get('profile_control_archives',{}))[-1]),*eligible]
    colors=['#285c80','#888888',*plt.colormaps['tab10'](np.linspace(0,1,len(eligible)))]
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
    fig.supxlabel('Same scored56km cells. The middle trial in the fixed design is shown; it was not selected by accuracy.\n'
        'All profiles and failures are retained; annual regional totals do not replace local monthly error.',fontsize=9)
    second=data/f'{stem}_maps.png';fig.savefig(second,dpi=145);plt.close(fig)
    images=[first,second];tracer_diagnostic=None;extra_html='';water_budgets=None
    reservoir_certificates=None;pnw_plot_status=None
    if stem in ('independent_water','column_rain','westerly_fit'):
        reservoir_certificates={n:{r:row.get('numerics',{}).get('moisture_reservoirs')
            for r,row in group.items()} for n,group in records.items()}
        fig,axes=plt.subplots(1,3,figsize=(15,5.6),constrained_layout=True)
        names=plan.get('humidity_plot_profiles',(['transport_control','reservoir_control',*eligible] if stem=='column_rain' else ['transport_control','pressure_control',*eligible]));reference=None
        for name in names:
            row=records[name]['iberia']
            score=row.get('circulation',{}).get('humidity',{}).get('scores',{}).get('ocean')
            if row['status']!='passed' or score is None:continue
            reference=score
            axes[0].plot(score['monthly_model_water_mm'],label=labels[name])
            axes[1].plot(score['monthly_model_q_ratio'],label=labels[name])
        if reference is not None:
            axes[0].plot(reference['monthly_reference_water_mm'],color='#222',lw=2.5,label='NCEP/NCAR')
            axes[1].plot(reference['monthly_reference_q_ratio'],color='#222',lw=2.5,label='NCEP/NCAR')
        for ax in axes[:2]:ax.set(xticks=range(12),xticklabels=list('JFMAMJJASOND'));ax.grid(alpha=.15)
        axes[0].set(title='Iberia ocean · matched925–300hPa water',ylabel='Partial precipitable water (mm)')
        axes[1].set(title='Vertical shape on identical pressure intervals',ylabel='Mean q700–300 / mean q925–700')
        axes[0].legend(frameon=False,fontsize=7)
        baseline=records['transport_control']['iberia']['circulation']['humidity']['scores']['ocean']
        for i,name in enumerate(names):
            score=records[name]['iberia'].get('circulation',{}).get('humidity',{}).get('scores',{}).get('ocean')
            if records[name]['iberia']['status']!='passed' or score is None:continue
            axes[2].bar(i-.17,score['partial_water_mae_mm']/baseline['partial_water_mae_mm'],width=.34,color='#547fa8',label='PW MAE' if i==0 else None)
            axes[2].bar(i+.17,score['partial_q_ratio_mae']/baseline['partial_q_ratio_mae'],width=.34,color='#ba8658',label='Shape MAE' if i==0 else None)
        axes[2].axhline(plan['humidity_max_ratio'],color='#555',ls='--',lw=1,label='1.02 protection limit')
        axes[2].set(xticks=range(len(names)),xticklabels=plan.get('humidity_plot_ticks',(['Fixed q','Previous','Corrected\nno mix','Corrected\n5-day mix'] if stem=='column_rain' else ['Fixed q','Pressure','No mix','5day mix'])),
            title='Separate observed-humidity error safeguards',ylabel='MAE / fixed-profile transport control')
        axes[2].legend(frameon=False,fontsize=8)
        fig.suptitle(('Shared westerly amplitudes' if stem=='westerly_fit' else 'Corrected rain closure' if stem=='column_rain' else 'Independent water')+' · actual coupled Earth humidity',fontsize=16)
        fig.supxlabel('Matched native ocean footprints, true areas and Gregorian month weights; no observed humidity enters the solver.\n'
            'Partial pressure intervals differ from full dry-layer masses. Coarse model-assisted reanalysis is a reused development constraint.',fontsize=9)
        third=data/f'{stem}_humidity.png';fig.savefig(third,dpi=145);plt.close(fig);images.append(third)
        extra_html=f'<figure><a href="data/{third.name}"><img src="data/{third.name}" width="2175" height="812" loading="lazy" alt="Actual coupled partial ocean water, vertical humidity shape and separate observed error protections"></a><figcaption>Matched pressure ranges exclude air below925hPa and above300hPa. Each observed-water and shape MAE must remain within2% of the common-mass fixed-profile control. A closer rainfall total cannot pay for worse humidity physics.</figcaption></figure>'
    if stem=='westerly_fit':
        fourth=data/f'{stem}_pnw_circulation.png'
        pnw_plot_status=plot_westerly_circulation(records,plan,labels,fourth);images.append(fourth)
        extra_html+=f'<figure><a href="data/{fourth.name}"><img src="data/{fourth.name}" width="2320" height="841" loading="lazy" alt="Pacific Northwest native ocean monthly eastward wind, partial humidity shape and separate wind and humidity error ratios for every fixed westerly trial"></a><figcaption>Every fixed amplitude is shown against the fresh corrected original-westerly control. Wind vector RMSE must fall to at most 90% of that control; partial water and vertical-shape MAEs each may reach at most 102%. These distinct limits use only four reused native ocean footprints. Missing or failed diagnostics are marked; full screening failures remain in the download. The native partial-column reference and modeled whole-column moisture wind differ in vertical coverage and omit transient moisture covariance.</figcaption></figure>'
    if stem=='shared_wind':
        # Signed terms of the actual solved equation, not an independent
        # causal decomposition of nonlinear parameter changes.
        keys=['advection','diffusion','storm_exchange','evaporation','other_column_drying','monsoon_drying','convergence_import']
        water_budgets={}
        for name in profiles:
            water_budgets[name]={}
            for region in regions:
                if records[name][region]['status']!='passed':continue
                with np.load(out/name/f'{region}.npz') as z:
                    water_budgets[name][region]={key:float(z[key][:,z['valid']].sum(0).mean())
                        for key in [*(k for k in keys if k!='other_column_drying'),'column_drying','simulated','observed','residual']}
                    # Monsoon drying is already included in total column
                    # drying. Partition it rather than counting it twice.
                    b=water_budgets[name][region]
                    b['other_column_drying']=b['column_drying']-b['monsoon_drying']
        fig,axes=plt.subplots(1,3,figsize=(14,7.2))
        colors=['#467aaf','#a1b9cd','#b18bba','#79a56e','#dfb484','#b37460','#d9c763']
        for ax,region in zip(axes,['north_india','mexico','pacific_nw']):
            names=['reference','transport_control'];positive=np.zeros(2);negative=np.zeros(2)
            for key,color in zip(keys,colors):
                values=np.array([water_budgets[n][region][key] for n in names])
                ax.bar(np.arange(2),np.maximum(values,0),bottom=positive,color=color,label=key.replace('_',' '))
                ax.bar(np.arange(2),np.minimum(values,0),bottom=negative,color=color)
                positive+=np.maximum(values,0);negative+=np.minimum(values,0)
            ax.plot(np.arange(2),[water_budgets[n][region]['simulated'] for n in names],'D',color='#222',label='Simulated rain')
            ax.axhline(water_budgets['reference'][region]['observed'],color='#222',ls='--',lw=1.2,label='Observed rain')
            ax.axhline(0,color='#888',lw=.6)
            ax.set(xticks=[0,1],xticklabels=['r39','Common-mass\ntransport'],title=region.replace('_',' ').title(),
                   ylabel='Signed annual equation terms (mm/year)')
            low=min(float(negative.min()),0.);high=max(float(positive.max()),water_budgets['reference'][region]['observed'])
            ax.set_ylim(low-.05*(high-low),high+.05*(high-low))
            ax.grid(axis='y',alpha=.12)
        handles,legend=axes[0].get_legend_handles_labels()
        fig.legend(handles,legend,loc='lower center',bbox_to_anchor=(.5,.045),ncol=3,fontsize=8,frameon=False)
        fig.suptitle('Where the modeled rainfall water comes from',fontsize=16)
        fig.text(.5,.008,'Positive terms supply vapor; negative terms remove or export it. Their signed sum equals modeled rain plus residual.\n'
            'Concentration-form r39 advection is not a conservative moisture flux. These budgets diagnose the equations; they are not causal attribution.',fontsize=8,ha='center')
        fig.tight_layout(rect=[0,.17,1,.95])
        proof=data/'shared_wind_water_budget.png';fig.savefig(proof,dpi=145);plt.close(fig);images.append(proof)
        extra_html=f'<figure><a href="data/{proof.name}"><img src="data/{proof.name}" width="2030" height="943" loading="lazy" alt="Signed modeled water budgets: mean advection dominates excess coastal rain while storm exchange exports water"></a><figcaption>Excess coastal rain in the corrected two-branch control is supported mainly by mean-flow import; storm mixing exports water there. The signed terms are actual equation diagnostics, not causal shares of a nonlinear change. Legacy r39 concentration advection does not conserve vapor. All profiles and seven regional budgets are retained in the download.</figcaption></figure>'
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
    storm_condensation=None
    if stem=='storm_path':
        storm_condensation={n:{r:dict(steps=len(row['numerics']['storm_exchange']['steps']),
            maximum_full_domain_condensation_cell_mm_day=max((s.get('condensation_cell_mm_day',0.)
                for s in row['numerics']['storm_exchange']['steps']),default=0.))
            for r,row in records[n].items() if row['status']=='passed'} for n in eligible}
        if any(row['maximum_full_domain_condensation_cell_mm_day']!=0 for row in storm_condensation['hops_only'].values()):
            raise ValueError('Hops-only control actually condensed; cannot publish as geometry-only attribution')
    compact={n:{r:{key:row.get(key) for key in ['status','error','rain','temperature','sst','column_speed','monthly_rain','circulation','extra_circulation']}
                for r,row in group.items()} for n,group in records.items()}
    branches={n:{r:{key:value for key,value in row.get('numerics',{}).get('two_layer_transport',{}).items() if key!='steps'}
                 for r,row in group.items()} for n,group in records.items()}
    pressure_certificates=({n:{r:row.get('numerics',{}).get('column_thermodynamics') for r,row in group.items()}
                           for n,group in records.items()} if stem=='pressure_column' else None)
    passed=sum(row['status']=='passed' for group in records.values() for row in group.values());attempted=sum(len(g) for g in records.values())
    decision=('Screening qualifiers require subsequent Earth/world checks' if any(r.get('qualifies') for r in review['screen'].values())
              else 'No profile passed all fixed safeguards')
    summary=dict(complete=True,decision=decision,attempted_runs=attempted,passed_runs=passed,failed_runs=attempted-passed,
        profiles=profiles,labels=labels,parameter_updates=plan['profiles'],sampling=plan.get('sampling'),
        regions=regions,screen=review['screen'],records=compact,branch_certificates=branches,
        pressure_column_certificates=pressure_certificates,
        independent_water_certificates=reservoir_certificates,
        pnw_circulation_plot_status=pnw_plot_status,
        local_rain_loss_ratio=ratios,physical_definition=plan['physical_definition'],scope=plan['publication'],
        selected_map_profile=map_candidate,tracer_equilibrium=tracer_diagnostic,signed_water_budgets_mm_year=water_budgets,
        water_budget_drying_definition='column_drying includes monsoon_drying; other_column_drying is their difference. Only disjoint terms are stacked.',
        storm_condensation_certificates=storm_condensation,physics_or_atlas_adoption=False,
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
    if stem=='shared_wind':specific='<p>Eight fixed Sobol samples vary land/ocean friction, trade/westerly speed and large/local thermal-pressure amplitudes. Common-mass water transport, vertical humidity ratio0.2,1km thermal shear, rainfall closure and Earth planetary forcing remain fixed. The download records all six parameter values for every trial; eight samples do not establish an optimum.</p>'
    if stem=='storm_path':specific='<p>Shared winds and corrected common-mass transport stay fixed. Six shorter conservative storm hops first run without any actual condensation, then with fixed crest coefficients0.5/0.75. Vapor above local capacity condenses where it forms; only surviving vapor takes later hops. The download retains actual condensation certificates so changing transport geometry is distinguished from rainout. This is an unresolved storm closure, not a resolved cloud trajectory.</p>'
    if stem=='pressure_column':specific='<p>The coupled model replaces the fixed vapor scale with hydrostatic specific-saturation integration. Two thermal profiles (existing environmental lapse or saturated moist adiabat) each use three fixed effective ocean column humidities0.45/0.60/original0.754746. Same pressure profile sets rain, sea-equilibrium and storm-crest capacities. Full terrain lapse, prescribed200K upper thermal boundary and water top100hPa are explicit approximations. The existing fixed transport humidity ratio remains; no independent vertical temperature or latent heating is added. All six combinations were declared before outcomes; no planetary forcing or accuracy threshold changes.</p>'
    if stem=='independent_water':specific='<p>Lower and upper water are solved independently in the coupled seasonal model, with donor vertical exchange, lower-only ocean/land evaporation, layer rain, drying and conservative storms. Both actual layer equations and their sum must pass strict residual checks. Calibrated total capacity stays fixed; a normalized moist hydrostatic profile only partitions capacity and boundary supply, without resetting actual humidity. The old fixed humidity ratio is inactive. The two declared closures add no extra mixing or symmetric5day mixing.</p>'
    if stem=='column_rain':specific='<p>The empirical convection law uses total column humidity once, while local dynamical rain and overflow retain layer humidities. Falling rain evaporates according to the actual lower air. Upper rain removes its gross water from the upper reservoir and routes the evaporated fraction into lower vapor; the internal transfer cancels exactly in the column ledger. Total proportional-profile ground rain remains compatible with the old law. All coefficients, winds, planetary settings, capacities and source/sink schemes stay fixed. The two trials retain the existing no/5-day mixing settings; no parcel model or vertical energy feedback is added.</p>'
    if stem=='westerly_fit':specific='<p>Only the globally shared peak background westerly amplitude changes: fixed5.0/6.25/7.5m/s versus8.76m/s. The background poleward component and seasonal factor remain fixed; terrain, pressure flow, thermal shear, temperature and sea state respond through the coupled model. Corrected rain/recycling, independent no-mixing moisture, all other coefficients and planetary settings remain fixed. New native PNW wind and humidity constraints supplement every earlier guard. This is a bounded sensitivity bracket, not three measured column speeds or an optimum.</p>'
    transport_scope=('The independent steady water states share a stationary dry-air column with25% lower and75% upper mass. Actual spatial water fractions feed donor faces and diagnostic vapor winds. There is no independently solved vertical temperature, latent heating or atmospheric time storage.' if stem in ('independent_water','column_rain','westerly_fit') else 'Moist lower inflow and a drier upper return are transported as separate conservative directional branches. Their combined dry-air flux retains the stationary column constraint. Total water still shares a fixed vertical humidity profile; vertical humidity and thermodynamics are not independently prognostic. Surface heat, evaporation and terrain lift retain surface winds. Earth planetary settings stay fixed.')
    humidity_scope=('independently solved humidity in two broad dry layers' if stem in ('independent_water','column_rain','westerly_fit') else 'an imposed vertical humidity shape')
    section=f'''<!--{slug}-start--><section aria-labelledby="{slug}-h"><h2 id="{slug}-h">{title}</h2>
{specific}
<p>{transport_scope}</p>
<p>The pilot attempts {attempted} integrations: {passed} pass strict numerics and {attempted-passed} fail. Original and historical physical controls must reproduce their archived fields before candidates. <strong>{decision}.</strong> No adopted profile, headline score or atlas climate is replaced by this research page.</p>
<figure><a href="data/{first.name}"><img src="data/{first.name}" width="2030" height="870" loading="lazy" alt="All fixed transport profiles: local regional rain-loss ratios and North India monthly rain"></a><figcaption>Every trial faces rain, temperature, regional, ocean, outside-wind, mass and separate-branch speed safeguards. Separate upwinding adds grid-dependent first-order mixing; it is not a measured physical diffusivity. Control details and all numerical certificates are in the download.</figcaption></figure>
<div class="table"><table><caption>North India, identical scored cells</caption><thead><tr><th>Profile</th><th>Annual rain mm</th><th>Monthly rain MAE mm</th><th>Wind RMSE m/s</th></tr></thead><tbody>{''.join(table)}</tbody></table></div>
<figure><a href="data/{second.name}"><img src="data/{second.name}" width="2030" height="1160" loading="lazy" alt="Observed, control and fixed middle-ratio transport rainfall maps in North India and Pacific Northwest"></a><figcaption>These fixed examples expose spatial tradeoffs. All ratios and failures remain in the results; closer annual totals can still hide worse local rain.</figcaption></figure>
{extra_html}
<p class="note">The model retains approximate hydrostatic mass, flat projected geometry, a fixed lower mass fraction and {humidity_scope}. Reanalysis constraints cover only a monthly925–300hPa partial column and omit transient moisture covariance. Reused development regions are not new independent validation.</p>
<p><a href="data/{stem}.json" download>Download {title.lower()} results</a> · <a href="../../reports/{stem.upper()}_{plan.get("publication_date","20261026")}.md">Method, results and limitations</a></p></section><!--{slug}-end-->'''
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
