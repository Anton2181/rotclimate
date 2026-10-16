"""Manufactured open-strip transport with exact time-averaged incoming supply."""
from __future__ import annotations
from types import SimpleNamespace
import numpy as np
from experiments import v10_boundary_transport as model


def strip(cells,direction=1):
    if isinstance(cells,bool) or not isinstance(cells,(int,np.integer)) or not 8<=cells<=1024 or direction not in (-1,1):
        raise ValueError('Use 8–1024 strip cells and direction +/-1.')
    mass=np.ones((1,1,cells));d=SimpleNamespace(land=np.ones((1,cells),bool),dx=1./cells,dy=1.)
    g=SimpleNamespace(mass=mass,pressure=np.full_like(mass,90000.),height_m=np.zeros_like(mass))
    flow=model.base.balanced(np.full((1,1,cells+1),float(direction)),np.zeros((1,2,cells)),d.dx,d.dy)
    return d,g,flow


def wave(cells,scheme,direction=1,courant=.5):
    if scheme not in ('upwind','coupled_fct') or courant not in (.25,.5):raise ValueError('Unknown manufactured wave comparison.')
    d,g,flow=strip(cells,direction);x=(np.arange(cells)+.5)/cells;pi=model.thermal.exner(g.pressure)
    wave=np.sin(2*np.pi*x)*np.sinc(1/cells)
    theta=(300.+8.*wave).reshape(g.mass.shape);q=(.004+.001*wave).reshape(g.mass.shape)
    water=g.mass*q;energy=g.mass*(model.base.CP*pi*theta)+model.base.LV*water
    initial=model.base.State(water.copy(),energy.copy(),np.zeros(d.land.shape));state=initial
    work=0.;input_water=output_water=input_heat=output_heat=0.;steps=int(cells/courant);dt=courant/cells
    operator=model.thermal.thermal_transport if scheme=='upwind' else model.thermal_transport
    boundary_x=0. if direction==1 else 1.
    for step in range(steps):
        t=step*dt
        # Exact face-concentration average over the interval, common to both schemes.
        incoming_wave=np.sin(2*np.pi*(boundary_x-direction*(t+.5*dt)))*np.sinc(dt)
        btheta=300.+8*incoming_wave;bq=np.full_like(water,.004+.001*incoming_wave)
        target=pi*btheta-273.15
        oldq=state.water/g.mass;oldt=model.base.temperature(state.energy,g.mass,state.water,g.height_m)+273.15
        out_index=-1 if direction==1 else 0
        input_water+=dt*float(bq[0,0,0]);output_water+=dt*float(oldq[0,0,out_index])
        input_heat+=dt*float(model.base.CP*(target[0,0,0]+273.15)+model.base.LV*bq[0,0,0])
        output_heat+=dt*float(model.base.CP*oldt[0,0,out_index]+model.base.LV*oldq[0,0,out_index])
        w,e,wd,ed,pwork,changes,theta_error=operator(state,flow,dt,d,g,target,bq)
        if abs(theta_error)>1e-8:raise FloatingPointError('Manufactured wave theta/boundary ledger failed.')
        state=model.base.State(w,e,state.soil.copy());work+=float(pwork.sum(0).mean())
    final_theta=(model.base.temperature(state.energy,g.mass,state.water,g.height_m)+273.15)/pi
    rw=float((state.water-initial.water).sum(0).mean()-input_water+output_water)
    rh=float((state.energy-initial.energy).sum(0).mean()-input_heat+output_heat-work)
    if abs(rw)>1e-11 or abs(rh)>1e-6:raise FloatingPointError('Manufactured open-wave independent boundary budget failed.')
    return {'cells':cells,'scheme':scheme,'direction':direction,'courant':courant,'steps':steps,
        'theta_mae_k':float(abs(final_theta-theta).mean()),'vapor_mae_g_kg':float(abs(state.water/g.mass-q).mean()*1000.),
        'gross_incoming_vapor':input_water,'exact_gross_incoming_vapor':.004,'gross_outgoing_vapor':output_water,
        'water_error':rw,'energy_error':rh,'prescribed_work':work,
        'initial_theta':theta,'final_theta':final_theta,'initial_vapor':q,'final_vapor':state.water/g.mass}
