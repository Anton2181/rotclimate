"""Check actual separated shear with complex-step derivatives and48node quadrature.

The certified floor interval is reused and checked at/inside/outside its roots.
No regional ClimateModel.run is called; the deterministic zonal EBM is rebuilt
from the frozen actual parameters to recover the candidate background field.
"""
import numpy as np
from rotclimate.config import Params
from rotclimate.ebm import ZonalClimate
from rotclimate.model import gauss
from rotclimate.separated_thermal_profile import parameters,active_interval


def raw(surface,background,x):
    k=287.05*.006/9.80665;gap=287.05/1004-k;delta=surface-background
    cap=np.divide(gap*surface,delta,out=np.full_like(surface,np.inf),where=np.real(delta)>0)
    exponent=np.where(np.real(cap)<1/-np.log(.75),cap,1/-np.log(.75))
    return (background+delta*np.exp(exponent*x))*np.exp(k*x)


def references(a,row):
    p=row['params'];zonal=ZonalClimate(Params(**p));surface=[];background=[]
    for step,day in enumerate(a['solved_days']):
        season=-np.cos(2*np.pi*(day-p['winter_solstice_day']-p['circulation_lag_days'])/p['year_days'])
        lapse=p['lapse_rate']*(1+p['lapse_seasonal']*season)
        surface.append(gauss(a['closure_T'][step]+lapse*a['elevation']/1000+273.15,500/56))
        background.append(gauss(zonal.zonal(a['latitude'],day)+273.15,500/56))
    return np.stack(surface),np.stack(background)


def check(a,row):
    surface,background=references(a,row);ps=101325*np.exp(-a['elevation']/8000)
    p=row['params'];f=2*7.292e-5*np.sin(np.radians(a['latitude']))*(-1 if p['retrograde'] else 1)
    f10=2*7.292e-5*np.sin(np.radians(10));nodes,weights=np.polynomial.legendre.leggauss(48);error=0.;root_error=0.
    for step,(aa,bb) in enumerate(zip(surface,background)):
        lo=np.log(.375*ps/101325);hi=np.log(.875*ps/101325)
        start,end=active_interval(lo,hi,parameters(aa,bb,6.));width=end-start;active=width>0
        for bound,edge in [(start,lo),(end,hi)]:
            roots=active&(np.abs(bound-edge)>1e-12)
            if roots.any():root_error=max(root_error,float(np.abs(raw(aa,bb,bound)[roots]-200).max()))
        inside=raw(aa,bb,(start+end)/2)
        assert np.all(inside[active]>=200-1e-9)
        for bound,edge in [(start,lo),(end,hi)]:
            outside=active&(np.abs(bound-edge)>1e-12)
            assert np.all(raw(aa,bb,(bound+edge)/2)[outside]<=200+1e-9)
        x=start[None]+(nodes[:,None,None]+1)*width[None]/2
        eps=1e-20
        da=np.imag(raw(aa.astype(complex)+1j*eps,bb.astype(complex),x))/eps
        db=np.imag(raw(aa.astype(complex),bb.astype(complex)+1j*eps,x))/eps
        ia=(weights[:,None,None]*da).sum(0)*width/2;ib=(weights[:,None,None]*db).sum(0)*width/2
        gx=(ia*np.gradient(aa,axis=1)+ib*np.gradient(bb,axis=1))/56000
        gn=-(ia*np.gradient(aa,axis=0)+ib*np.gradient(bb,axis=0))/56000
        coefficient=287.05*f/(f*f+f10*f10);expected=np.stack([-coefficient*gn,coefficient*gx])
        actual=a['winds'][step,1]-a['winds'][step,0];error=max(error,float(np.abs(actual-expected).max()))
        np.testing.assert_allclose(actual,expected,atol=1e-8,rtol=0)
        cert=row['numerics']['thermal_layer_winds']['steps'][step]
        np.testing.assert_allclose([aa.min(),aa.max(),bb.min(),bb.max()],
            [cert['minimum_reference_temperature_k'],cert['maximum_reference_temperature_k'],cert['minimum_background_temperature_k'],cert['maximum_background_temperature_k']],atol=1e-10,rtol=0)
    assert root_error<1e-8
    return dict(all_actual_shear_steps_checked=len(surface),maximum_independent_shear_error_ms=error,
        maximum_floor_root_temperature_error_k=root_error,derivative='complex step,48node quadrature; core floor intervals reused with root/interior/exterior checks',
        regional_climate_integrations=0,background='Deterministic frozen-parameter zonal EBM, not observations')
