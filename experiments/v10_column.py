"""Four-layer diagnostic column with separate terrain and storm return flows.

Same approximate MSE/instant rain-out closure as the frozen heat experiment.
Momentum/radiation are prescribed. Rain observations never enter this module.
"""
from dataclasses import dataclass,replace
import numpy as np
from rotclimate_v10.core import DAY,EDGES,Config,Domain,interpolate_months,divergence
from rotclimate_v10.weather import catalogue
from experiments.v10_thermodynamics import CP,LV,G,saturation,adjust,temperature

FRACTIONS = np.array([.1,.15,.15,.6])
SIGMA = np.array([.95,.825,.675,.3])


@dataclass(frozen=True)
class Settings:
    terrain: str = 'shallow'
    observed_wind: bool = True
    observed_temperature: bool = True
    observed_humidity: bool = True
    humidity_scale: float = 1.
    relaxation_lower_days: float = 2.
    relaxation_upper_days: float = 10.
    storm_rate_month: float = 4.
    storm_convergence_ms: float = .5
    storm_rotation_ms: float = 12.
    storm_radius_km: float = 350.
    terrain_drag_height_m: float = 1800.

    def validate(self):
        if self.terrain not in ('shallow','deep','none'):raise ValueError('Unknown terrain return.')
        numeric = [v for v in vars(self).values() if isinstance(v,(int,float))]
        if not np.isfinite(numeric).all():raise ValueError('Nonfinite column settings.')
        for k in ('humidity_scale','relaxation_lower_days','relaxation_upper_days','storm_radius_km','terrain_drag_height_m'):
            if getattr(self,k)<=0:raise ValueError('Positive column scale required.')
        if min(self.storm_rate_month,self.storm_convergence_ms,self.storm_rotation_ms)<0:raise ValueError('Negative storm magnitude.')


@dataclass
class Profile:
    offsets: np.ndarray  # 12 x layer, air minus offshore SST
    mixing_ratio: np.ndarray  # 12 x layer, kg water/kg dry air
    eastward: np.ndarray
    northward: np.ndarray
    height_m: np.ndarray  # layer, annual mean offshore geopotential height
    storm_domain_width_m: float | None = None

    def validate(self):
        if any(a.shape!=(12,4) or not np.isfinite(a).all() for a in (self.offsets,self.mixing_ratio,self.eastward,self.northward)):
            raise ValueError('Invalid four-layer reference profile.')
        if self.height_m.shape!=(4,) or not np.isfinite(self.height_m).all() or (np.diff(self.height_m)<=0).any():
            raise ValueError('Invalid representative heights.')
        if (self.mixing_ratio<0).any() or (self.mixing_ratio>.1).any():raise ValueError('Invalid reference humidity.')
        if self.storm_domain_width_m is not None and (not np.isfinite(self.storm_domain_width_m) or self.storm_domain_width_m<=0):
            raise ValueError('Invalid physical storm-domain width.')


@dataclass
class State:
    water: np.ndarray  # layer,y,x in mm
    energy: np.ndarray  # J/m², layer dry mass times approximate MSE
    soil: np.ndarray


@dataclass
class Flow:
    x: np.ndarray
    y: np.ndarray
    vertical: np.ndarray  # k-1 interfaces, lower -> upper
    continuity: float


def balanced(x,y,dx,dy):
    div = divergence(x,y,dx,dy)
    error = float(abs(div.sum(axis=0)).max())
    if error>1e-10:raise ValueError('Column air continuity failed.')
    return Flow(x,y,-np.cumsum(div,axis=0)[:-1],error)


def masses(d):
    ps = 101325*np.exp(-np.maximum(d.elevation_m,-400)/8400)
    return FRACTIONS[:,None,None]*ps[None]/G,ps


def geometry(d,profile):
    return d.elevation_m[None]+profile.height_m[:,None,None]


def targets(d,profile,s,time_s):
    surface = interpolate_months(d.temperature_c,time_s)
    if s.observed_temperature:offset = interpolate_months(profile.offsets,time_s)
    else:offset = -3.+(-35.+3.)*(profile.height_m-1121.66)/(8238.96-1121.66)
    return surface[None]+offset[:,None,None],surface


def boundary(d,profile,s,time_s,pressure):
    t,_ = targets(d,profile,s,time_s)
    if s.observed_humidity:
        q = np.broadcast_to(interpolate_months(profile.mixing_ratio,time_s)[:,None,None]*s.humidity_scale,t.shape).copy()
        # Land-boundary humidity is also capped by local saturation.
        q = np.minimum(q,saturation(t,pressure)*.95)
    else:
        rh = np.linspace(.8,.2,4)[:,None,None]
        q = saturation(t,pressure)*np.where(d.land[None],np.minimum(rh,.4),rh)*s.humidity_scale
        q = np.minimum(q,saturation(t,pressure)*.95)
    return q


def initial_state(d,profile,s):
    d.validate();profile.validate();s.validate()
    mass,ps = masses(d);z = geometry(d,profile);t,_ = targets(d,profile,s,0.)
    water = mass*np.minimum(boundary(d,profile,s,0.,SIGMA[:,None,None]*ps),.6*saturation(t,SIGMA[:,None,None]*ps))
    return State(water,mass*(CP*(t+273.15)+G*z)+LV*water,np.where(d.land,75.,0.))


def events(d,s,seed,width_m=None):
    generated = catalogue(d,Config(seed=seed,storm_rate_month=s.storm_rate_month))
    if width_m is not None:
        ratio = width_m/(d.land.shape[1]*d.dx)
        generated = [replace(event,x=event.x*ratio) for event in generated]
    return generated


def flow_at(d,profile,s,storms,time_s):
    ny,nx = d.land.shape;ref_mass = 101325/G
    if s.observed_wind:
        u = interpolate_months(profile.eastward,time_s);v = -interpolate_months(profile.northward,time_s)
        x = np.broadcast_to((FRACTIONS*ref_mass*u)[:,None,None],(4,ny,nx+1)).copy()
        y = np.broadcast_to((FRACTIONS*ref_mass*v)[:,None,None],(4,ny+1,nx)).copy()
    else:
        winter = np.cos(2*np.pi*(time_s/DAY-15)/365)
        background = 6*(.8+.2*winter)/(1+np.exp(-(d.latitude[:,0]-(28-3*winter))/2))
        x = np.broadcast_to(FRACTIONS[:,None,None]*ref_mass*background[None,:,None],(4,ny,nx+1)).copy()
        y = np.zeros((4,ny+1,nx))
    # Terrain diverts lower-layer mass into an adjacent layer, or a declared deep control.
    if s.terrain!='none':
        drag = 1/(1+(np.maximum(d.elevation_m,0)/s.terrain_drag_height_m)**2)
        dragx = np.pad(.5*(drag[:,:-1]+drag[:,1:]),((0,0),(1,1)),mode='edge')
        dragy = np.pad(.5*(drag[:-1]+drag[1:]),((1,1),(0,0)),mode='edge')
        dx = x[0]*(dragx-1);dy = y[0]*(dragy-1)
        destination = 1 if s.terrain=='shallow' else 3
        x[0] += dx;y[0] += dy;x[destination] -= dx;y[destination] -= dy
    # Synoptic disturbances retain a distinct full-depth return; terrain never uses it in shallow mode.
    xx,yy = np.meshgrid(np.arange(nx+1)*d.dx,np.arange(ny+1)*d.dy)
    xc,yc = np.meshgrid((np.arange(nx)+.5)*d.dx,(np.arange(ny)+.5)*d.dy)
    psi = np.zeros_like(xx);potential = np.zeros_like(xc);day = time_s/DAY%365
    for event in storms:
        age = (day-event.day+182.5)%365-182.5
        if abs(age)>6:continue
        life = event.strength*np.exp(-.5*(age/2)**2)
        cx = event.x+7*age*DAY;cy = (d.latitude[0,0]-event.latitude)*111195+.5*d.dy;r = s.storm_radius_km*1000
        psi -= s.storm_rotation_ms*r*life*np.exp(-((xx-cx)**2+(yy-cy)**2)/(2*r*r))
        potential -= s.storm_convergence_ms*r*life*np.exp(-((xc-cx)**2+(yc-cy)**2)/(2*r*r))
    x += FRACTIONS[:,None,None]*ref_mass*np.diff(psi,axis=0)[None]/d.dy
    y -= FRACTIONS[:,None,None]*ref_mass*np.diff(psi,axis=1)[None]/d.dx
    gx = np.empty((ny,nx+1));gy = np.empty((ny+1,nx))
    gx[:,1:-1] = np.diff(potential,axis=1)/d.dx;gx[:,0] = gx[:,1];gx[:,-1] = gx[:,-2]
    gy[1:-1] = np.diff(potential,axis=0)/d.dy;gy[0] = gy[1];gy[-1] = gy[-2]
    x[0] -= FRACTIONS[0]*ref_mass*gx;x[-1] += FRACTIONS[0]*ref_mass*gx
    y[0] -= FRACTIONS[0]*ref_mass*gy;y[-1] += FRACTIONS[0]*ref_mass*gy
    return balanced(x,y,d.dx,d.dy)


def stable_step(f,mass,d):
    out = ((np.maximum(f.x[...,1:],0)+np.maximum(-f.x[...,:-1],0))/d.dx
           +(np.maximum(f.y[...,1:,:],0)+np.maximum(-f.y[...,:-1,:],0))/d.dy)
    out[:-1] += np.maximum(f.vertical,0);out[1:] += np.maximum(-f.vertical,0)
    rate = float((out/mass).max())
    return min(3600.,.6/rate) if rate else 3600.


def flux(store,mass,x,y,b):
    q = store/mass;fx = np.empty_like(x);fy = np.empty_like(y)
    fx[...,1:-1] = x[...,1:-1]*np.where(x[...,1:-1]>=0,q[...,:-1],q[...,1:])
    fy[...,1:-1,:] = y[...,1:-1,:]*np.where(y[...,1:-1,:]>=0,q[...,:-1,:],q[...,1:,:])
    fx[...,0] = x[...,0]*np.where(x[...,0]>=0,b[...,0],q[...,0])
    fx[...,-1] = x[...,-1]*np.where(x[...,-1]>=0,q[...,-1],b[...,-1])
    fy[...,0,:] = y[...,0,:]*np.where(y[...,0,:]>=0,b[...,0,:],q[...,0,:])
    fy[...,-1,:] = y[...,-1,:]*np.where(y[...,-1,:]>=0,q[...,-1,:],b[...,-1,:])
    return fx,fy


def transport(store,mass,f,b,dt,d):
    fx,fy = flux(store,mass,f.x,f.y,b)
    derivative = divergence(fx,fy,d.dx,d.dy)
    exchange = f.vertical*np.where(f.vertical>=0,store[:-1]/mass[:-1],store[1:]/mass[1:])
    tendency = derivative.copy();tendency[:-1] += exchange;tendency[1:] -= exchange
    return store-dt*tendency,float(dt*derivative.sum(axis=0).mean())


def advance(state,d,profile,s,f,dt,time_s,physics=True):
    mass,ps = masses(d);p = SIGMA[:,None,None]*ps;z = geometry(d,profile)
    if dt<=0 or dt>stable_step(f,mass,d)*(1+1e-12):raise ValueError('Column CFL exceeded.')
    if not np.isfinite(state.water).all() or state.water.min()<0 or not np.isfinite(state.energy).all() or not np.isfinite(state.soil).all() or state.soil.min()<0:
        raise ValueError('Invalid column state.')
    bq = boundary(d,profile,s,time_s,p);target,surface = targets(d,profile,s,time_s)
    be = CP*(target+273.15)+G*z+LV*bq
    water,boundary_water = transport(state.water,mass,f,bq,dt,d)
    energy,boundary_energy = transport(state.energy,mass,f,be,dt,d)
    if water.min() < -1e-11:raise FloatingPointError('Negative water from column transport.')
    correction = np.maximum(-water,0);water += correction;energy += LV*correction
    soil = state.soil.copy();t = temperature(energy,mass,water,z)
    evap_ocean = np.zeros_like(soil);evap_land = np.zeros_like(soil);runoff = np.zeros_like(soil);rain = np.zeros_like(water)
    relax = np.zeros_like(energy)
    if physics:
        tau = np.array([s.relaxation_lower_days,s.relaxation_lower_days,s.relaxation_upper_days,s.relaxation_upper_days])[:,None,None]*DAY
        relax = mass*CP*(-np.expm1(-dt/tau))*(target-t);energy += relax
        t = temperature(energy,mass,water,z)
        speed = np.sqrt((.5*(f.x[0,:,1:]+f.x[0,:,:-1])/mass[0])**2+(.5*(f.y[0,1:]+f.y[0,:-1])/mass[0])**2+4)
        deficit = np.maximum(saturation(surface,ps)-water[0]/mass[0],0)
        evap_ocean = np.where(~d.land,np.minimum(1.2*.0012*speed*deficit*dt,5*dt/DAY),0.)
        winter = np.cos(2*np.pi*(time_s/DAY-15)/365)
        demand = 3*(1-.5*winter)*np.clip((surface+5)/25,0,1)*dt/DAY
        demand *= soil/150*np.clip(1-water[0]/np.maximum(mass[0]*saturation(t[0],p[0]),1e-12),0,1)
        evap_land = np.where(d.land,np.minimum(soil,demand),0);soil -= evap_land
        water[0] += evap_ocean+evap_land;energy[0] += LV*(evap_ocean+evap_land)
        water,rain,t = adjust(water,energy,mass,z,p)
        soil += np.where(d.land,rain.sum(0),0);runoff = np.maximum(soil-150,0);soil -= runoff
    wd = float((water.sum(0)+soil-state.water.sum(0)-state.soil).mean())
    ed = float((energy-state.energy).sum(0).mean())
    ocean_rain = float(np.where(~d.land,rain.sum(0),0).mean());rw = float(correction.sum(0).mean())
    latent = float(LV*(evap_ocean+evap_land).mean());heating = float(relax.sum(0).mean())
    b = {'ocean_evaporation_mm':float(evap_ocean.mean()),'land_evaporation_mm':float(evap_land.mean()),
         'rain_mm':float(rain.sum(0).mean()),'ocean_rain_mm':ocean_rain,'runoff_mm':float(runoff.mean()),
         'boundary_export_mm':boundary_water,'roundoff_correction_mm':rw,
         'surface_latent_input_j_m2':latent,'temperature_relaxation_j_m2':heating,
         'energy_boundary_export_j_m2':boundary_energy,'roundoff_energy_j_m2':LV*rw,
         'water_error_mm':wd-(float(evap_ocean.mean())-ocean_rain-float(runoff.mean())-boundary_water+rw),
         'energy_error_j_m2':ed-(latent+heating-boundary_energy+LV*rw)}
    if not np.isfinite(list(b.values())).all() or abs(b['water_error_mm'])>1e-9 or abs(b['energy_error_j_m2'])>1e-5:
        raise FloatingPointError('Four-layer water/static-energy budget failed.')
    saturation(t,p)
    return State(water,energy,soil),rain.sum(0),t,target,b


class BudgetStop(Exception):pass


def year(d,profile,s,seed,state,checkpoint=None,save_month=None,should_stop=lambda:False):
    """Monthly resumable year. A stop loses at most the unfinished month."""
    shape = d.land.shape
    if checkpoint is None:
        rain = np.zeros((12,)+shape);temperatures = np.zeros((12,4)+shape);refs = np.zeros_like(temperatures)
        totals = {};start_month = 0
        initial_water = float((state.water.sum(0)+state.soil).mean());initial_energy = float(state.energy.sum(0).mean())
        maxw = maxe = continuity = 0.;steps = 0
    else:
        state,rain,temperatures,refs,info = checkpoint
        totals = info['totals'].copy();start_month = info['month'];initial_water = info['initial_water'];initial_energy = info['initial_energy']
        maxw,maxe,continuity,steps = (info[k] for k in ('maxw','maxe','continuity','steps'))
    storms = events(d,s,seed,profile.storm_domain_width_m);mass,_ = masses(d)
    for month in range(start_month,12):
        t = float(EDGES[month]);f = None;next_forcing = t
        while t<EDGES[month+1]-1e-6:
            if steps%32==0 and should_stop():raise BudgetStop()
            if f is None or t>=next_forcing-1e-6:
                tick = np.floor((t+1e-6)/10800.)*10800.;next_forcing = tick+10800.
                f = flow_at(d,profile,s,storms,tick);limit = stable_step(f,mass,d)
            dt = min(limit,next_forcing-t,EDGES[month+1]-t)
            if dt<.01 or steps>=500000:raise RuntimeError('Bounded column step count exceeded.')
            state,p,temp,target,b = advance(state,d,profile,s,f,dt,t)
            rain[month] += p;temperatures[month] += temp*dt;refs[month] += target*dt
            for key,value in b.items():
                if key not in ('water_error_mm','energy_error_j_m2'):totals[key] = totals.get(key,0.)+value
            maxw = max(maxw,abs(b['water_error_mm']));maxe = max(maxe,abs(b['energy_error_j_m2']));continuity = max(continuity,f.continuity)
            t += dt;steps += 1
        duration = EDGES[month+1]-EDGES[month];temperatures[month] /= duration;refs[month] /= duration
        info = dict(month=month+1,totals=totals,initial_water=initial_water,initial_energy=initial_energy,maxw=maxw,maxe=maxe,continuity=continuity,steps=steps)
        if save_month:save_month(state,rain,temperatures,refs,info)
    wf = float((state.water.sum(0)+state.soil).mean());ef = float(state.energy.sum(0).mean())
    we = wf-initial_water-(totals['ocean_evaporation_mm']-totals['ocean_rain_mm']-totals['runoff_mm']-totals['boundary_export_mm']+totals['roundoff_correction_mm'])
    ee = ef-initial_energy-(totals['surface_latent_input_j_m2']+totals['temperature_relaxation_j_m2']-totals['energy_boundary_export_j_m2']+totals['roundoff_energy_j_m2'])
    if abs(we)>1e-6 or abs(ee)>1:raise FloatingPointError('Annual column budgets failed.')
    info['budget'] = dict(totals,annual_water_error_mm=we,annual_energy_error_j_m2=ee,max_step_water_error_mm=maxw,
                          max_step_energy_error_j_m2=maxe,max_air_continuity_kg_m2_s=continuity,steps=steps)
    return state,rain,temperatures,refs,info
