"""Independent finite groundwater/pond/soil/forest scalar ledger.

Reuses only the earlier independent scalar soil equations. No groundwater
component or producer is imported by this reference.
"""
import math

import numpy as np

from audit_river_fields import scalar_soil

STOCKS=['top_mm','deep_mm','bound_mm','pond_mm','aquifer_mm']
FIELD_FLUXES=['infiltration_mm','delivered_mm','surface_evap_mm','bare_diffusion_mm','root_uptake_mm','root_potential_mm','pond_evap_mm','pond_release_mm','surface_overflow_mm','soil_drainage_mm','rain_excluded_mm','aquifer_recharge_mm','capillary_rise_mm','aquifer_loss_mm']
RIVER=['river_requested_m3','river_delivered_m3','river_loss_m3','river_outlet_m3']


def scalar_groundwater(a,initial=None):
    nf=len(a['area_m2']);nt=len(a['dt']);nn=a['source_m3'].shape[1]
    start=a['initial_5stocks'] if initial is None else initial
    stock=np.array([start[2],start[0],start[1]]).T.copy();pond=start[3].copy();aquifer=start[4].copy()
    result={name:[] for name in STOCKS+FIELD_FLUXES+RIVER};maxfield=0.;maxjoint=0.
    for t,days in enumerate(a['dt']):
        before=stock.sum(1)+pond+aquifer;loss=np.zeros(nf);rise=np.zeros(nf);charge=np.zeros(nf);rate=a['infiltration_rate'].copy()
        for i in range(nf):
            lost=min(aquifer[i],a['loss_rate'][t,i]*days);aquifer[i]-=lost;loss[i]=lost
            remaining=min(a['permission'][t,i]*days,aquifer[i],max(155-stock[i].sum(),0.))
            total=0.
            for index,cap in [(2,135.),(0,5.),(1,15.)]:
                delta=min(remaining,max(cap-stock[i,index],0.));stock[i,index]+=delta;remaining-=delta;total+=delta
            aquifer[i]-=total;rise[i]=total
            if a['recharge_mask'][t,i] and a['pond_mask'][t,i]:
                transfer=min(pond[i],max(a['aquifer_capacity_mm'][i]-aquifer[i],0.),a['recharge_rate'][t,i]*days,a['infiltration_rate'][i]*days)
                pond[i]-=transfer;aquifer[i]+=transfer;charge[i]=transfer;rate[i]-=transfer/days
        release=np.where(a['pond_mask'][t],0.,pond);pond-=release
        surface=pond+.8*a['rain_mm'][t];limit=np.minimum(np.maximum(155-stock.sum(1),0.),np.maximum(rate,0)*days)
        caps=np.where(a['pond_mask'][t],a['pond_capacity_mm'],0.)
        request=np.where(a['capture_mask'][t],np.maximum(limit+caps-surface,0.),0.)
        demand=np.array([math.fsum(request[i]*a['area_m2'][i]/1000 for i in range(nf) if a['field_nodes'][i]==node) for node in range(nn)])
        available=list(a['source_m3'][t]);delivered=np.zeros(nn);conveyance=np.zeros(nn);outlet=np.zeros(nn)
        for node in reversed(a['order']):
            withdrawal=min(available[node],demand[node]/a['efficiency']);useful=withdrawal*a['efficiency']
            delivered[node]=useful;conveyance[node]=withdrawal-useful;available[node]-=withdrawal
            downstream=a['receiver'][node]
            if downstream<0:outlet[node]=available[node]
            else:available[downstream]+=available[node]
        delivery=np.array([request[i]*delivered[node]/demand[node] if demand[node]>0 else 0. for i,node in enumerate(a['field_nodes'])]);surface+=delivery
        infiltration=np.minimum(surface,limit);surface-=infiltration
        pond=np.minimum(surface,caps);overflow=surface-pond;covered=pond>0
        pond_e=np.minimum(pond,a['eto_mm_day'][t]*days);pond-=pond_e
        flux={name:np.zeros(nf) for name in ['surface_evap_mm','bare_diffusion_mm','root_uptake_mm','soil_drainage_mm']}
        for i in range(nf):
            stock[i],values=scalar_soil(stock[i],infiltration[i],0. if covered[i] else a['eto_mm_day'][t,i],float(days),bool(a['crop_mask'][t,i]),.75,float(a['background']),.55)
            for name,value in values.items():flux[name][i]=value
        potential=np.where(a['crop_mask'][t],.75*a['eto_mm_day'][t]*days,0.)
        runoff=.2*a['rain_mm'][t]
        after=stock.sum(1)+pond+aquifer
        sinks=runoff+release+overflow+pond_e+loss+sum(flux.values())
        residual=before+a['rain_mm'][t]+delivery-after-sinks
        maxfield=max(maxfield,float(np.max(np.abs(residual))))
        joint=math.fsum((before[i]+a['rain_mm'][t,i]-after[i]-sinks[i])*a['area_m2'][i]/1000 for i in range(nf))+math.fsum(a['source_m3'][t])-math.fsum(conveyance)-math.fsum(outlet)
        maxjoint=max(maxjoint,abs(joint))
        assert maxfield<1e-8 and maxjoint<1e-7
        values=dict(top_mm=stock[:,1],deep_mm=stock[:,2],bound_mm=stock[:,0],pond_mm=pond,aquifer_mm=aquifer,infiltration_mm=infiltration,delivered_mm=delivery,root_potential_mm=potential,pond_evap_mm=pond_e,pond_release_mm=release,surface_overflow_mm=overflow,rain_excluded_mm=runoff,aquifer_recharge_mm=charge,capillary_rise_mm=rise,aquifer_loss_mm=loss,river_requested_m3=demand,river_delivered_m3=delivered,river_loss_m3=conveyance,river_outlet_m3=outlet,**flux)
        for name,value in values.items():result[name].append(np.array(value,copy=True))
    result={name:np.array(value) for name,value in result.items()}
    final=np.array([stock[:,1],stock[:,2],stock[:,0],pond,aquifer])
    return result,final,maxfield,maxjoint
