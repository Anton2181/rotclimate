"""Open-boundary extension of the saved coupled transport prototype.

External faces retain frozen donor-cell inflow/outflow with zero correction.
Only interior faces get shared theta/vapor flux correction. Boundary heat and
water are explicit; fixed dry mass requires total local air continuity. No
reservoir cells, post-update clipping or changed incoming supply are used.
"""
from __future__ import annotations

from dataclasses import dataclass
import numpy as np
from experiments import v10_flux_transport as parent

lab=parent.lab
base=lab.base
thermal=parent.thermal


@dataclass(frozen=True)
class Mesh(parent.Mesh):
    boundary_cell: np.ndarray
    boundary_rate: np.ndarray  # positive outward

    def boundary_divergence(self, amount):
        a=np.asarray(amount,float)
        if a.shape[-1]!=len(self.boundary_cell):raise ValueError('Boundary amount shape mismatch.')
        flat=a.reshape((-1,len(self.boundary_cell)))
        result=np.array([np.bincount(self.boundary_cell,weights=f,minlength=len(self.mass)) for f in flat])
        return result.reshape(a.shape[:-1]+(len(self.mass),))

    def total_divergence(self,inside,outside):
        return self.divergence(inside)+self.boundary_divergence(outside)

    def outgoing_rate(self):
        return super().outgoing_rate()+self.boundary_divergence(np.maximum(self.boundary_rate,0.))

    def validate(self):
        n=len(self.mass)
        if self.mass.shape!=(n,) or not n or np.prod(self.shape)!=n or not np.isfinite(self.mass).all() or (self.mass<=0).any():
            raise ValueError('Positive finite masses and matching mesh shape required.')
        if any(a.ndim!=1 or len(a)!=len(self.rate) for a in (self.tail,self.head,self.horizontal)) or self.rate.ndim!=1 or not len(self.rate) or not np.isfinite(self.rate).all():
            raise ValueError('Invalid interior face arrays.')
        if self.tail.dtype.kind not in 'iu' or self.head.dtype.kind not in 'iu' or min(self.tail.min(),self.head.min())<0 or max(self.tail.max(),self.head.max())>=n or (self.tail==self.head).any():
            raise ValueError('Invalid interior connectivity.')
        if self.boundary_cell.ndim!=1 or self.boundary_rate.shape!=self.boundary_cell.shape or not len(self.boundary_cell) or self.boundary_cell.dtype.kind not in 'iu' or self.boundary_cell.min()<0 or self.boundary_cell.max()>=n or not np.isfinite(self.boundary_rate).all():
            raise ValueError('Invalid boundary faces.')
        scale=max(1.,abs(self.rate).max(),abs(self.boundary_rate).max())
        if abs(self.total_divergence(self.rate,self.boundary_rate)).max()>1e-12*scale:
            raise ValueError('Fixed-mass transport requires local dry-air continuity including boundaries.')


def build_mesh(domain,geometry,flow):
    mass=geometry.mass;k,ny,nx=mass.shape
    if flow.x.shape!=(k,ny,nx+1) or flow.y.shape!=(k,ny+1,nx) or flow.vertical.shape!=(k-1,ny,nx):
        raise ValueError('Invalid transport flow shape.')
    if not np.isfinite([domain.dx,domain.dy]).all() or min(domain.dx,domain.dy)<=0:
        raise ValueError('Positive finite horizontal spacing required.')
    ids=np.arange(mass.size).reshape(mass.shape)
    tail=(ids[...,:-1],ids[:,:-1,:],ids[:-1]);head=(ids[...,1:],ids[:,1:,:],ids[1:])
    rate=(flow.x[...,1:-1]/domain.dx,flow.y[:,1:-1,:]/domain.dy,flow.vertical)
    bc=(ids[...,0],ids[...,-1],ids[:,0,:],ids[:,-1,:])
    br=(-flow.x[...,0]/domain.dx,flow.x[...,-1]/domain.dx,-flow.y[:,0,:]/domain.dy,flow.y[:,-1,:]/domain.dy)
    mesh=Mesh(mass.ravel().copy(),np.concatenate([a.ravel() for a in tail]),np.concatenate([a.ravel() for a in head]),
        np.concatenate([a.ravel() for a in rate]),np.concatenate([np.full(a.size,i<2) for i,a in enumerate(rate)]),mass.shape,
        np.concatenate([a.ravel() for a in bc]),np.concatenate([a.ravel() for a in br]))
    mesh.validate();return mesh


def transport(values,boundary,mesh,dt,bounded=2):
    """Correct interior transfers; prescribed external flux stays first order."""
    mesh.validate();c=np.asarray(values,float);b=np.asarray(boundary,float)
    if c.ndim!=2 or c.shape[1]!=len(mesh.mass) or b.shape!=(len(c),len(mesh.boundary_cell)) or not np.isfinite(c).all() or not np.isfinite(b).all() or isinstance(bounded,bool) or not isinstance(bounded,(int,np.integer)) or not 1<=bounded<=len(c):
        raise ValueError('Invalid tracer/boundary array or bounded-field count.')
    if (c[:bounded]<0).any() or (b[:bounded]<0).any():raise ValueError('Bounded fields must be nonnegative.')
    courant=dt*mesh.outgoing_rate()/mesh.mass
    if not np.isfinite(dt) or dt<=0 or courant.max()>.6*(1+1e-12):raise ValueError('Step exceeds the existing .6 outgoing CFL.')
    a,z,f=mesh.tail,mesh.head,mesh.rate
    outside=dt*mesh.boundary_rate*np.where(mesh.boundary_rate<0,b,c[:,mesh.boundary_cell])
    low_amount=dt*f*np.where(f>=0,c[:,a],c[:,z])
    centered=f*.5*(c[:,a]+c[:,z])
    midpoint=c-.5*(dt*mesh.divergence(centered)+mesh.boundary_divergence(outside))/mesh.mass
    high_amount=dt*f*.5*(midpoint[:,a]+midpoint[:,z])
    low=c-mesh.total_divergence(low_amount,outside)/mesh.mass
    correction=high_amount-low_amount
    lo=np.minimum(c[:bounded],low[:bounded]);hi=np.maximum(c[:bounded],low[:bounded])
    incoming=mesh.boundary_rate<0
    for i in range(bounded):
        np.minimum.at(lo[i],a,c[i,z]);np.minimum.at(lo[i],z,c[i,a])
        np.maximum.at(hi[i],a,c[i,z]);np.maximum.at(hi[i],z,c[i,a])
        np.minimum.at(lo[i],mesh.boundary_cell[incoming],b[i,incoming])
        np.maximum.at(hi[i],mesh.boundary_cell[incoming],b[i,incoming])
    supply_scale=abs(b[:bounded,incoming]).max(1) if incoming.any() else np.zeros(bounded)
    allowance=64*np.finfo(float).eps*np.maximum.reduce([abs(c[:bounded]).max(1),abs(low[:bounded]).max(1),supply_scale])
    lo=np.maximum(0.,lo-allowance[:,None]);hi+=allowance[:,None]
    anti=correction[:bounded]
    plus=np.array([np.bincount(a,weights=np.maximum(-v,0.),minlength=len(mesh.mass))+np.bincount(z,weights=np.maximum(v,0.),minlength=len(mesh.mass)) for v in anti])
    minus=np.array([np.bincount(a,weights=np.maximum(v,0.),minlength=len(mesh.mass))+np.bincount(z,weights=np.maximum(-v,0.),minlength=len(mesh.mass)) for v in anti])
    rp=np.minimum(1.,np.divide(mesh.mass*np.maximum(hi-low[:bounded],0.),plus,out=np.ones_like(plus),where=plus>0))
    rm=np.minimum(1.,np.divide(mesh.mass*np.maximum(low[:bounded]-lo,0.),minus,out=np.ones_like(minus),where=minus>0))
    limits=np.where(anti>=0,np.minimum(rm[:,a],rp[:,z]),np.minimum(rp[:,a],rm[:,z]))
    face=np.where(anti==0,1.,limits).min(0)*(1-8*np.finfo(float).eps)
    amount=low_amount+face*correction
    after=c-mesh.total_divergence(amount,outside)/mesh.mass
    error=np.sum(mesh.mass*(after-c),axis=1)+outside.sum(1)
    bound_error=max(float((lo-after[:bounded]).max()),float((after[:bounded]-hi).max()),0.)
    scale=max(1.,abs(mesh.mass*c).sum(),abs(outside).sum())
    if not np.isfinite(after).all() or bound_error>2e-12*max(1.,abs(c[:bounded]).max(),supply_scale.max()) or abs(error).max()>2e-12*scale:
        raise FloatingPointError('Open transport bounds or boundary budget failed.')
    return after,amount,outside,{'maximum_courant':float(courant.max()),'maximum_bound_error':bound_error,
        'conservation_error':error,'face_coefficient':face,'roundoff_bound_allowance':allowance,
        'incoming_amount':-outside[:,incoming].sum(1),'outgoing_amount':outside[:,~incoming].sum(1)}


def thermal_transport(state,flow,dt,domain,geometry,target,boundary_q):
    g=geometry;mass=g.mass;pi=thermal.exner(g.pressure)
    if target.shape!=mass.shape or boundary_q.shape!=mass.shape or not np.isfinite(target).all() or not np.isfinite(boundary_q).all() or (boundary_q<0).any():
        raise ValueError('Explicit finite thermal/vapor boundary fields required.')
    mesh=build_mesh(domain,g,flow)
    t=base.temperature(state.energy,mass,state.water,g.height_m)+273.15
    theta=t/pi;q=state.water/mass;bt=target+273.15
    if (theta<=0).any() or (bt<=0).any() or (q<0).any():raise ValueError('Positive theta/T and nonnegative vapor required.')
    values=np.array([theta.ravel(),q.ravel(),(state.energy/mass).ravel(),t.ravel()])
    boundary=np.array([(bt/pi).ravel(),boundary_q.ravel(),(base.CP*bt+base.G*g.height_m+base.LV*boundary_q).ravel(),bt.ravel()])[:,mesh.boundary_cell]
    after,amount,outside,_=transport(values,boundary,mesh,dt)
    new_theta=after[0].reshape(mass.shape);water=mass*after[1].reshape(mass.shape)
    if water.min()<0:raise FloatingPointError('Corrected transport produced negative vapor.')
    energy=mass*(base.CP*pi*new_theta+base.G*g.height_m)+base.LV*water
    passive=mass*after[2].reshape(mass.shape);work=energy-passive
    changes=np.zeros((len(thermal.PROCESSES),)+mass.shape)
    horizontal=mesh.divergence(amount[3]*mesh.horizontal)+mesh.boundary_divergence(outside[3])
    md=mesh.divergence(mesh.rate*mesh.horizontal)+mesh.boundary_divergence(mesh.boundary_rate)
    vertical=mesh.divergence(amount[3]*(~mesh.horizontal));mv=mesh.divergence(mesh.rate*(~mesh.horizontal))
    changes[0]=(-horizontal.reshape(mass.shape)+dt*t*md.reshape(mass.shape))/mass
    changes[1]=(-vertical.reshape(mass.shape)+dt*t*mv.reshape(mass.shape))/mass
    changes[2]=pi*new_theta-t-changes[0]-changes[1]
    wd=(mesh.divergence(amount[1]*mesh.horizontal)+mesh.boundary_divergence(outside[1])).reshape(mass.shape)/dt
    ed=(mesh.divergence(amount[2]*mesh.horizontal)+mesh.boundary_divergence(outside[2])).reshape(mass.shape)/dt
    theta_error=float((mass*(new_theta-theta)).sum(0).mean()+outside[0].sum()/np.prod(domain.land.shape))
    return water,energy,wd,ed,work,changes,theta_error
