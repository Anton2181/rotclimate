"""Daily paid river delivery, finite ponding and shared-pool soil water.

Source volumes and net field water are distinct. Pond release, runoff and soil
drainage leave this ledger; no unmodelled return flow is credited downstream.
"""
from dataclasses import dataclass
import numpy as np
from .soil_drying import SoilState,soil_state,soil_step,surface_coefficients
from .flood_water import route_water_budget


@dataclass(frozen=True)
class BareStep:
    state: SoilState
    evaporation_mm: np.ndarray
    diffusion_mm: np.ndarray
    drainage_mm: np.ndarray


def bare_soil_step(profile,state,water_mm,eto_mm_day,background_coefficient,
                   *,kcmax=1.2,step_days=1.):
    """Surface ET and separately paid deep diffusive ET; no crop uptake.

    FAO31 verifies the supplied wet-profile ten-day case. Background flux after
    deep depletion is capped, not empirically inferred by that benchmark.
    """
    if isinstance(step_days,bool) or not np.isfinite(step_days) or not 0<step_days<=1:raise ValueError('Step duration in (0,1] days required')
    eto,bg=np.broadcast_arrays(np.asarray(eto_mm_day,float),np.asarray(background_coefficient,float))
    if not np.isfinite(eto).all() or not np.isfinite(bg).all() or np.any(eto<0) or np.any(bg<0):raise ValueError('Finite nonnegative ETo/background required')
    wet=soil_step(profile,state,water_mm,0.,0.,kcmax,.55,step_days=step_days)
    top,deep,bound=wet.state.top_mm,wet.state.deep_mm,wet.state.bound_mm
    _,ke=surface_coefficients(profile.tew_mm-(top+bound),profile.rew_mm,profile.tew_mm,bg,kcmax)
    evaporation=np.minimum(ke*eto*step_days,top+bound)
    top_after=np.maximum(top-evaporation,0.)
    bound_after=np.maximum(bound-np.maximum(evaporation-top,0.),0.)
    evaporation=(top-top_after)+(bound-bound_after)
    diffusion=np.minimum(bg*eto*step_days,deep)
    return BareStep(SoilState(top_after,deep-diffusion,bound_after),evaporation,diffusion,wet.drainage_mm)


@dataclass(frozen=True)
class FieldState:
    soil: SoilState
    pond_mm: np.ndarray


def field_year(profile,area_m2,field_nodes,source_m3,clock,rain_mm,eto_mm_day,
               crop_mask,capture_mask,pond_mask,*,crop_kcb,depletion_fraction=.55,
               bare_background=0.,pond_capacity_mm=0.,infiltration_mm_day=20.,
               efficiency=1.,pond_evap_coefficient=1.,crop_exposed_fraction=.25,
               kcmax=1.2,initial=None):
    """Run supplied step forcings and masks; defaults start with empty stocks.

    Rain is gross mm/step (0.8 effective), sources m3/step, ETo mm/day.
    Capture and crop may coexist for direct irrigation, but dryland crop cannot
    coexist with permission to retain a pond. The supplied clock fixes timing.
    """
    area=np.asarray(area_m2,float);nodes=np.asarray(field_nodes);source=np.asarray(source_m3,float)
    nt=len(clock.step_days);nf=len(area)
    if area.ndim!=1 or not np.isfinite(area).all() or np.any(area<=0):raise ValueError('Positive finite field areas required')
    if source.ndim!=2 or source.shape[0]!=nt:raise ValueError('One river source volume per step/node required')
    nn=source.shape[1]
    if nodes.shape!=(nf,) or nodes.dtype.kind not in 'iu' or np.any(nodes<0) or np.any(nodes>=nn):raise ValueError('Valid integer field/node binding required')
    # Forest metadata is supplied on the clock adapter, not inferred from fields.
    order=clock.river_order;receiver=clock.river_receiver
    validation=np.zeros((12,nn));route_water_budget(validation,validation,order,receiver,efficiency=efficiency)
    if not np.isin(nodes,np.asarray(order)).all():raise ValueError('Fields must attach to active river nodes')
    def forcing(value,nonnegative=True):
        value=np.broadcast_to(np.asarray(value,float),(nt,nf))
        if not np.isfinite(value).all() or (nonnegative and np.any(value<0)):raise ValueError('Finite nonnegative field forcing required')
        return value
    rain=forcing(rain_mm);eto=forcing(eto_mm_day);kcb=forcing(crop_kcb);p=forcing(depletion_fraction);background=forcing(bare_background)
    if np.any(p>=1):raise ValueError('Depletion fraction must be below one')
    if np.any(kcb>kcmax) or np.any(background>kcmax):raise ValueError('Basal coefficient exceeds Kcmax')
    masks=[]
    for value in (crop_mask,capture_mask,pond_mask):
        value=np.asarray(value)
        if value.dtype.kind!='b':raise ValueError('Boolean crop/capture/pond masks required')
        masks.append(np.broadcast_to(value,(nt,nf)))
    crop,capture,pond_allowed=masks
    if np.any(crop&pond_allowed):raise ValueError('Dryland crop cannot overlap pond permission')
    def spatial(value):
        value=np.broadcast_to(np.asarray(value,float),(nf,)).copy()
        if not np.isfinite(value).all() or np.any(value<0):raise ValueError('Finite nonnegative field parameter required')
        return value
    pondcap=spatial(pond_capacity_mm);infilrate=spatial(infiltration_mm_day);pondcoef=spatial(pond_evap_coefficient)
    # Broadcast initial profile/stocks through the normal validated soil API.
    if initial is None:initial=FieldState(soil_state(profile,np.zeros(nf)),np.zeros(nf))
    state=initial.soil;pond=spatial(initial.pond_mm)
    if np.any(pond>pondcap):raise ValueError('Initial pond exceeds capacity')
    check=soil_step(profile,state,np.zeros(nf),0.,0.,kcmax,.55)
    state=check.state
    initial_stock=dict(top_mm=state.top_mm.copy(),deep_mm=state.deep_mm.copy(),bound_mm=state.bound_mm.copy(),pond_mm=pond.copy())
    fields=('top_mm','deep_mm','bound_mm','pond_mm','infiltration_mm','delivered_mm','surface_evap_mm','bare_diffusion_mm','root_uptake_mm','root_potential_mm','pond_evap_mm','pond_release_mm','surface_overflow_mm','soil_drainage_mm','rain_excluded_mm')
    result={name:np.zeros((nt,nf)) for name in fields}
    for name in ('requested','delivered','loss','outlet'):result['river_'+name+'_m3']=np.zeros_like(source)
    capacity=np.broadcast_to(profile.taw_mm+profile.bound_capacity_mm,(nf,))
    for t,dt in enumerate(clock.step_days):
        release=np.where(pond_allowed[t],0.,pond);pond=pond-release
        surface=pond+.8*rain[t]
        room=np.maximum(capacity-state.total_mm,0.)
        infil_limit=np.minimum(room,infilrate*dt)
        permitted_cap=np.where(pond_allowed[t],pondcap,0.)
        request=np.where(capture[t],np.maximum(infil_limit+permitted_cap-surface,0.),0.)
        demand=np.zeros((12,nn));water=np.zeros_like(demand)
        demand[0]=np.bincount(nodes,weights=request*area/1000.,minlength=nn);water[0]=source[t]
        routed=route_water_budget(water,demand,order,receiver,efficiency=efficiency)
        ratio=np.divide(routed['delivered_m3'][0],demand[0],out=np.zeros(nn),where=demand[0]>0)
        delivered=request*ratio[nodes];surface=surface+delivered
        infiltration=np.minimum(surface,infil_limit);surface=surface-infiltration
        pond=np.minimum(surface,permitted_cap);overflow=surface-pond
        covered=pond>0
        pond_evap=np.minimum(pond,pondcoef*eto[t]*dt);pond=pond-pond_evap
        # Compute both modes from the same prior stock and select once per field.
        soil_eto=np.where(covered,0.,eto[t])
        grown=soil_step(profile,state,infiltration,soil_eto,kcb[t],kcmax,p[t],exposed_fraction=crop_exposed_fraction,step_days=float(dt))
        bare=bare_soil_step(profile,state,infiltration,soil_eto,background[t],kcmax=kcmax,step_days=float(dt))
        state=SoilState(*[np.where(crop[t],getattr(grown.state,name),getattr(bare.state,name)) for name in ('top_mm','deep_mm','bound_mm')])
        result['top_mm'][t]=state.top_mm;result['deep_mm'][t]=state.deep_mm;result['bound_mm'][t]=state.bound_mm;result['pond_mm'][t]=pond
        result['infiltration_mm'][t]=infiltration;result['delivered_mm'][t]=delivered
        result['surface_evap_mm'][t]=np.where(crop[t],grown.evaporation_mm,bare.evaporation_mm)
        result['bare_diffusion_mm'][t]=np.where(crop[t],0.,bare.diffusion_mm)
        result['root_uptake_mm'][t]=np.where(crop[t],grown.root_uptake_mm,0.)
        result['root_potential_mm'][t]=np.where(crop[t],kcb[t]*eto[t]*dt,0.)
        result['soil_drainage_mm'][t]=np.where(crop[t],grown.drainage_mm,bare.drainage_mm)
        for name,value in [('pond_evap_mm',pond_evap),('pond_release_mm',release),('surface_overflow_mm',overflow),('rain_excluded_mm',.2*rain[t])]:result[name][t]=value
        result['river_requested_m3'][t]=demand[0]
        for key,name in [('delivered','delivered_m3'),('loss','delivery_loss_m3'),('outlet','outlet_m3')]:result['river_'+key+'_m3'][t]=routed[name][0]
    result.update(initial=initial_stock,final=FieldState(state,pond.copy()))
    return result


@dataclass(frozen=True)
class RiverClock:
    """Bind an existing FieldClock to an explicit drainage forest."""
    clock: object
    river_order: object
    river_receiver: object

    @property
    def step_days(self):return self.clock.step_days


def periodic_fields(*args,max_years=50,tolerance_mm=1e-6,**kwargs):
    if 'initial' in kwargs:raise ValueError('Periodic replay starts empty')
    if isinstance(max_years,bool) or not isinstance(max_years,int) or max_years<1 or not np.isfinite(tolerance_mm) or tolerance_mm<=0:raise ValueError('Positive cycle count/tolerance required')
    initial=None
    for year in range(1,max_years+1):
        r=field_year(*args,initial=initial,**kwargs);last=r['final']
        residual=max(float(np.max(np.abs((getattr(last.soil,name) if name!='pond_mm' else last.pond_mm)-r['initial'][name]),initial=0)) for name in ('top_mm','deep_mm','bound_mm','pond_mm'))
        if residual<=tolerance_mm:break
        initial=last
    r.update(years=year,periodic=residual<=tolerance_mm,periodic_residual_mm=residual)
    return r
