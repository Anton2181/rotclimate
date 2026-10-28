"""Experimental thermal-wind constraint for the two dry-mass branches.

The coupled model selects this only through an explicit default-off flag. This does
not solve vertical momentum, temperature, latent heating or equatorial flow.
The caller must supply a common-pressure layer-mean temperature, not a raw
terrain-cooled surface field. Horizontal gradients use the existing local
flat projected grid approximation.
"""
from dataclasses import dataclass
import numpy as np

# Match the existing dry-air mass geometry, not a fitted vertical shape.
LOWER_MASS_FRACTION=.25
LOWER_CENTROID_SIGMA=1.-LOWER_MASS_FRACTION/2.
UPPER_CENTROID_SIGMA=(1.-LOWER_MASS_FRACTION)/2.
DRY_AIR_GAS_CONSTANT=287.05
EARTH_OMEGA=7.292e-5
EQUATORIAL_F=2*EARTH_OMEGA*np.sin(np.radians(10.))


@dataclass
class ThermalLayerWinds:
    lower: tuple
    upper: tuple
    certificate: dict


def pressure_thermal_shear(temperature_k,cell_m,coriolis):
    """Upper-minus-lower geostrophic shear at fixed dry-mass centroids.

    Delta U = Rd ln(p_lower/p_upper)/f * k cross grad_p(Tbar).
    The two layer pressure centroids are0.875ps and0.375ps, so their ratio
    is7/3 everywhere. Tbar's horizontal gradient must be at common pressure;
    differentiating a sigma-surface temperature directly adds terrain errors.
    A constant vertical horizontal-temperature gradient is assumed. As in the
    current model, f/(f²+f10²) regularizes the equator; this damps midlatitude
    shear too and is a declared approximation, not equatorial dynamics.
    """
    t=np.asarray(temperature_k,float)
    if (t.ndim!=2 or min(t.shape)<3 or not np.isfinite(t).all() or (t<=0).any()
            or not np.isfinite(cell_m) or cell_m<=0):
        raise ValueError('Need finite positive common-pressure Kelvin field and spacing')
    f=np.broadcast_to(np.asarray(coriolis,float),t.shape)
    if not np.isfinite(f).all():raise ValueError('Need finite matching Coriolis field')
    east_gradient=np.gradient(t,axis=1)/cell_m
    north_gradient=-np.gradient(t,axis=0)/cell_m
    coefficient=DRY_AIR_GAS_CONSTANT*np.log(LOWER_CENTROID_SIGMA/UPPER_CENTROID_SIGMA)*f/(f*f+EQUATORIAL_F**2)
    return -coefficient*north_gradient,coefficient*east_gradient


def project_thermal_branches(projector,desired_lower,shear):
    """Closest two-layer flow preserving thermal shear and dry continuity.

    Desired upper flow is desired_lower+shear. Project their dry-mass mean,
    applying the same velocity correction to both branches, which preserves
    the prescribed difference. This minimizes sum(M_i*|delta U_i|²) subject
    to fixed shear and stationary dry-column divergence, with open borders.
    Actual water fractions and any imposed humidity ratio do not enter.
    Independent lower/upper water transport still needs its donor exchanges.
    """
    shape=projector.shape
    if len(desired_lower)!=2 or len(shear)!=2:
        raise ValueError('Need two components in each wind vector')
    arrays=[np.asarray(a,float) for pair in (desired_lower,shear) for a in pair]
    if len(arrays)!=4 or any(a.shape!=shape or not np.isfinite(a).all() for a in arrays):
        raise ValueError('Need matching finite lower wind and shear vectors')
    ul,vl,du,dv=arrays;eta=LOWER_MASS_FRACTION
    target_u=ul+(1-eta)*du;target_v=vl+(1-eta)*dv
    mean_u,mean_v,projection=projector.project(target_u,target_v)
    correction_u=mean_u-target_u;correction_v=mean_v-target_v
    lower=(ul+correction_u,vl+correction_v)
    upper=(ul+du+correction_u,vl+dv+correction_v)
    actual_u=eta*lower[0]+(1-eta)*upper[0]
    actual_v=eta*lower[1]+(1-eta)*upper[1]
    divergence=projector.divergence@np.r_[actual_u.ravel(),actual_v.ravel()]
    scale=max(1.,float(np.hypot(*lower).max()),float(np.hypot(*upper).max()))
    residual=float(np.abs(divergence).max())/scale
    shear_error=max(float(np.abs(upper[0]-lower[0]-du).max()),float(np.abs(upper[1]-lower[1]-dv).max()))
    if residual>1e-10 or shear_error>1e-12*scale:
        raise RuntimeError('Thermal branches failed dry continuity or shear preservation')
    certificate=dict(max_scaled_dry_column_residual=residual,maximum_shear_error_ms=shear_error,
        maximum_common_correction_ms=float(np.hypot(correction_u,correction_v).max()),
        lower_dry_mass_fraction=eta,pressure_centroid_ratio=LOWER_CENTROID_SIGMA/UPPER_CENTROID_SIGMA,
        projection=projection,scope='Isolated kinematic operator; fixed thermal shear and stationary dry continuity, no coupled climate or rainfall result')
    return ThermalLayerWinds(lower,upper,certificate)


def hydrostatic_thermal_shear(reference_temperature_k,surface_pressure_pa,cell_m,coriolis,*,lapse_k_km=6.):
    """Integrate fixed-pressure temperature gradients between local centroids.

    T(p)=max(A*(p/101325Pa)**kappa,200K), kappa=Rd*Gamma/g. A is the
    modeled common-reference temperature, NOT terrain-cooled surface T. The
    gradient is taken at fixed pressure first: grad_p(T)=indicator(T>200)*
    (p/p0)**kappa*grad(A). Only then integrate over local pressure bounds.
    Thus changing terrain/ps alone creates no thermal shear. Differentiating
    a mean evaluated at moving sigma bounds would create a spurious term.
    Constant environmental lapse, dry hydrostatic profile, fixed200K floor;
    no independent energy or equatorial momentum solution is implied.
    """
    t=np.asarray(reference_temperature_k,float);ps=np.asarray(surface_pressure_pa,float)
    if (t.ndim!=2 or min(t.shape)<3 or ps.shape!=t.shape or not np.isfinite(t).all()
            or (t<=0).any() or not np.isfinite(ps).all() or (ps<=0).any()
            or not np.isfinite(cell_m) or cell_m<=0 or not np.isfinite(lapse_k_km)
            or not 0<=lapse_k_km<=10):
        raise ValueError('Need positive matching common-reference temperature/pressure, spacing and lapse in[0,10]')
    f=np.broadcast_to(np.asarray(coriolis,float),t.shape)
    if not np.isfinite(f).all():raise ValueError('Need finite matching Coriolis field')
    kappa=DRY_AIR_GAS_CONSTANT*(lapse_k_km/1000)/9.80665
    log_lower=np.log(LOWER_CENTROID_SIGMA*ps/101325.)
    log_upper=np.log(UPPER_CENTROID_SIGMA*ps/101325.)
    if kappa==0:
        integral=np.where(t>200.,np.log(LOWER_CENTROID_SIGMA/UPPER_CENTROID_SIGMA),0.)
    else:
        floor_crossing=np.log(200./t)/kappa
        start=np.maximum(log_upper,floor_crossing)
        width=np.maximum(log_lower-start,0.)
        integral=np.exp(kappa*start)*np.expm1(kappa*width)/kappa
    tx=np.gradient(t,axis=1)/cell_m;ty=-np.gradient(t,axis=0)/cell_m
    coefficient=DRY_AIR_GAS_CONSTANT*integral*f/(f*f+EQUATORIAL_F**2)
    return (-coefficient*ty,coefficient*tx),dict(
        temperature_coordinate='common101325Pa reference; fixed-pressure gradient before moving-bound integration',
        thermal_lapse_k_km=float(lapse_k_km),thermal_floor_k=200.,reference_pressure_pa=101325.,
        minimum_reference_temperature_k=float(t.min()),maximum_reference_temperature_k=float(t.max()),
        minimum_active_pressure_integral=float(integral.min()),maximum_active_pressure_integral=float(integral.max()),
        fully_floor_limited_cells=int((integral==0).sum()))
