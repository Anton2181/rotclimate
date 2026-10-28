"""Exploratory post-pilot thermal check, no fitting/forcing/new integrations.

Hypsometric reanalysis virtual temperature from fixed pressure-layer heights
is compared with the candidate wind profile on the SAME valid native masks.
It is not an independent validation region or a revised acceptance criterion.
"""
import numpy as np
from rotclimate.model import gauss
from rotclimate.numerics import matrix_product
from scripts.earth_calendar import observation_weights
from scripts.transport_native import references
from scripts.circulation_reference import projection_jacobian,native_aggregation,column_targets
from rotclimate import earth


def audit(a,row,case,plan):
    p=row['params'];g=case.grid;spec=earth.REGIONS[case.name];idx=a['scored_indices'];n=len(idx)
    times=a['solved_days'][idx];s=-np.cos(2*np.pi*(times-p['winter_solstice_day']-p['circulation_lag_days'])/p['year_days'])
    lapse=p['lapse_rate']*(1+p['lapse_seasonal']*s)
    tref=np.stack([gauss(t+lr*g.elev/1000+273.15,500/56) for t,lr in zip(a['closure_T'][idx],lapse)])
    ps=101325*np.exp(-g.elev/8000.);k=287.05*.006/9.80665
    q=a['water'][idx]/(a['layer_mass'][idx]*(101325/9.80665))
    weights,durations,order=observation_weights(a['days']);monthly=lambda v:matrix_product(weights,v.reshape(n,-1)).reshape((12,)+g.land.shape)
    ref=references(plan['transport_reference_plan']);fields={v:ref[case.name,v] for v in ('uwnd','vwnd','shum','hgt')};_,_,height=column_targets(fields)
    geo=projection_jacobian(g.lat,case.lon,spec['lat0'],spec['lon0']);area=g.cell_km**2/geo[-1]
    interior=np.ones_like(g.land);interior[[0,-1],:]=False;interior[:,[0,-1]]=False
    nodes,quad_weights=np.polynomial.legendre.leggauss(16)
    result={}
    for kind in ('land','ocean'):
        own=g.inmap&interior&((g.land&np.isfinite(case.obs_P).all(0)) if kind=='land' else ~g.land)
        aggregate,masks,native_area,_=native_aggregation(g.lat,case.lon,area,own,g.land,g.elev,fields['shum'],height)
        mask=a['native_'+kind+'_mask'];result[kind]=dict(native_cells=int(mask.sum()),layers={})
        if not mask.any():continue
        for bottom,top in [(925,700),(700,300)]:
            x=(np.log(bottom/1013.25)+np.log(top/1013.25))/2+nodes*(np.log(bottom/top)/2)
            pressure=101325*np.exp(x)
            temperature=np.maximum(tref[None]*np.exp(k*x)[:,None,None,None],200.)
            humidity=np.where(pressure[:,None,None,None]>=.75*ps[None,None],q[None,:,0],q[None,:,1])
            dry=(quad_weights[:,None,None,None]*temperature).sum(0)/2
            virtual=(quad_weights[:,None,None,None]*temperature*(1+.61*humidity)).sum(0)/2
            model=aggregate(monthly(virtual))[:,mask];model_dry=aggregate(monthly(dry))[:,mask]
            level=lambda pressure:fields['hgt'].values[order,list(fields['hgt'].pressure_hpa).index(pressure)].reshape(12,-1)
            observed=(9.80665*(level(top)-level(bottom))/(287.05*np.log(bottom/top)))[:,mask]
            ar=native_area[mask];w=durations[:,None]*ar[None];w=w/w.sum()
            latitude,longitude=np.meshgrid(fields['shum'].latitude,fields['shum'].longitude,indexing='ij')
            latitude=latitude.ravel()[mask];longitude=longitude.ravel()[mask]
            x=(longitude-longitude.mean())*111.195*np.cos(np.radians(latitude.mean()))/1000
            y=(latitude-latitude.mean())*111.195/1000
            design=np.stack([np.ones_like(x),x,y],axis=1);gradient=None
            if len(x)>=4 and np.linalg.matrix_rank(design)==3:
                weighted=design*np.sqrt(ar)[:,None]
                fit=lambda values:np.linalg.lstsq(weighted,values.T*np.sqrt(ar)[:,None],rcond=None)[0][1:].T
                gradient=dict(monthly_model_K_per_1000km=fit(model).tolist(),monthly_reference_K_per_1000km=fit(observed).tolist(),
                    definition='Exploratory area-weighted spatial plane on native cells, common intercept; diagnostic only, never a model parameter/input. At least4 cells and full rank required.')
            result[kind]['layers'][str(bottom)+'_'+str(top)]=dict(spatial_gradient=gradient,

                virtual_temperature_mae_k=float(np.sum(w*np.abs(model-observed))),
                virtual_temperature_bias_k=float(np.sum(w*(model-observed))),
                monthly_model_virtual_k=np.average(model,axis=-1,weights=ar).tolist(),
                monthly_model_dry_k=np.average(model_dry,axis=-1,weights=ar).tolist(),
                monthly_reference_virtual_k=np.average(observed,axis=-1,weights=ar).tolist(),
                native_model_virtual_k=model.tolist(),native_reference_virtual_k=observed.tolist())
    result['scope']='Exploratory after outcomes; candidate hydrostatic wind profile versus hypsometric mean virtual T. Same native footprints/calendar, first-order modeled humidity correction. Existing cached height reanalysis; not direct air-temperature observations, new validation, forcing, fitting or changed acceptance.'
    return result


def plot(out,regions):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig,axes=plt.subplots(4,2,figsize=(13,13),layout='constrained');months=np.arange(12)
    for row,(region,kind) in enumerate([('north_india','land'),('mexico','land'),('pacific_nw','ocean')]):
        data=regions[region]['hydro_thermal']['thermal_structure'][kind]
        for col,layer in enumerate(('925_700','700_300')):
            d=data['layers'][layer];ax=axes[row,col]
            ax.plot(months,d['monthly_reference_virtual_k'],color='#24272b',label='NCEP thickness-derived virtual T',lw=2)
            ax.plot(months,d['monthly_model_virtual_k'],color='#1c8490',label='Candidate wind profile, virtual T',lw=2)
            ax.plot(months,d['monthly_model_dry_k'],'--',color='#1c8490',label='Candidate wind profile, dry T',lw=1.4)
            ax.set(title=f"{region.replace('_',' ').title()} · {kind} · {data['native_cells']} cells · {layer.replace('_','–')} hPa",ylabel='Layer-mean temperature K',xticks=months,xticklabels=list('JFMAMJJASOND'));ax.grid(alpha=.2)
            if row==0 and col==0:ax.legend(fontsize=8)
    for col,layer in enumerate(('925_700','700_300')):
        ax=axes[3,col];d=regions['north_india']['hydro_thermal']['thermal_structure']['land']['layers'][layer]['spatial_gradient']
        if d is not None:
            for component,style in [(0,'-'),(1,'--')]:
                ax.plot(months,np.array(d['monthly_reference_K_per_1000km'])[:,component],style,color='#24272b',label='Reference '+['east','north'][component])
                ax.plot(months,np.array(d['monthly_model_K_per_1000km'])[:,component],style,color='#1c8490',label='Candidate '+['east','north'][component])
            ax.axhline(0,color='#777',lw=.7);ax.grid(alpha=.2);ax.set(title='India11land · spatial gradient · '+layer.replace('_','–')+' hPa',ylabel='Virtual T gradient K/1000km',xticks=months,xticklabels=list('JFMAMJJASOND'))
            if col==0:ax.legend(ncol=2,fontsize=8)
    fig.suptitle('Does the candidate wind-temperature profile represent the atmosphere?\nExploratory hypsometric check after the failed pilot; no calibration or new climate runs',fontsize=14)
    fig.savefig(out/'thermal_wind_temperature_structure.png',dpi=150);plt.close(fig)
