"""Idealized repeatable synoptic forcing, independent of observed/painted rain.

This is kinematic circulation, not a solved general-circulation model. Curl
column fluxes enforce mass continuity exactly; drag/convergence in the lower
layer induce a compensated upper and vertical return flow.
"""
from dataclasses import dataclass
import numpy as np

from .core import DAY,MONTH_DAYS,CENTERS,balanced_flow


@dataclass(frozen=True)
class Event:
    day: float
    x: float
    latitude: float
    strength: float


def catalogue(domain,config):
    rng = np.random.default_rng(config.seed)
    width = domain.land.shape[1]*domain.dx
    events = []
    edges = np.r_[0,np.cumsum(MONTH_DAYS)]
    for month in range(12):
        winter = np.cos(2*np.pi*(CENTERS[month]/DAY-15)/365.)
        count = rng.poisson(config.storm_rate_month*(1+config.storm_seasonality*winter)*MONTH_DAYS[month]/30.)
        for _ in range(count):
            day = float(rng.uniform(edges[month],edges[month+1]))
            lat = .5*(config.winter_track_lat+config.summer_track_lat)-.5*(config.summer_track_lat-config.winter_track_lat)*winter
            events.append(Event(day,float(rng.uniform(.2,.8)*width),float(lat+rng.normal(0,2.)),float(rng.uniform(.7,1.3))))
    return events


def flow_at(domain,config,events,time_s,storms=True):
    ny,nx = domain.land.shape
    x,y = np.meshgrid(np.arange(nx+1)*domain.dx,np.arange(ny+1)*domain.dy)
    xc,yc = np.meshgrid((np.arange(nx)+.5)*domain.dx,(np.arange(ny)+.5)*domain.dy)
    psi = np.zeros_like(x);potential = np.zeros_like(xc)
    day = time_s/DAY%365
    winter = np.cos(2*np.pi*(day-15)/365.)
    if storms:
        for event in events:
            phase = (day-event.day+182.5)%365-182.5
            if abs(phase) > 3*config.storm_lifetime_days:
                continue
            life = event.strength*np.exp(-.5*(phase/config.storm_lifetime_days)**2)
            cx = event.x+config.rotation_sign*config.storm_translation_ms*phase*DAY
            cy = (domain.latitude[0,0]-event.latitude)*111195.+.5*domain.dy
            r = config.storm_radius_km*1000.
            psi -= config.rotation_sign*config.storm_rotation_ms*r*life*np.exp(-((x-cx)**2+(y-cy)**2)/(2*r*r))
            potential -= config.storm_convergence_ms*r*life*np.exp(-((xc-cx)**2+(yc-cy)**2)/(2*r*r))
    # C = curl(psi) + zonal flow(y): divergence-free on the discrete faces.
    ref_mass = 101325./9.80665
    latitude = domain.latitude[:,0]
    hadley = 28.-3.*winter
    background = config.rotation_sign*config.background_wind_ms*(.8+.2*winter)/(1+np.exp(-(latitude-hadley)/2))
    cx = ref_mass*(np.diff(psi,axis=0)/domain.dy+background[:,None])
    cy = -ref_mass*np.diff(psi,axis=1)/domain.dx
    gx = np.empty_like(cx);gy = np.empty_like(cy)
    gx[:,1:-1] = np.diff(potential,axis=1)/domain.dx
    gx[:,0],gx[:,-1] = gx[:,1],gx[:,-2]
    gy[1:-1,:] = np.diff(potential,axis=0)/domain.dy
    gy[0,:],gy[-1,:] = gy[1,:],gy[-2,:]
    drag = 1/(1+(np.maximum(domain.elevation_m,0)/config.terrain_drag_height_m)**2)
    dragx = np.pad(.5*(drag[:,:-1]+drag[:,1:]),((0,0),(1,1)),mode='edge')
    dragy = np.pad(.5*(drag[:-1,:]+drag[1:,:]),((1,1),(0,0)),mode='edge')
    lx = config.lower_fraction*(cx-ref_mass*gx)*dragx
    ly = config.lower_fraction*(cy-ref_mass*gy)*dragy
    return balanced_flow(lx,ly,cx,cy,domain.dx,domain.dy)
