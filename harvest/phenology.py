"""Daily cereal development from Schaphoff et al. (2018), equations 73–79.

This is an isolated development clock, not LPJmL biomass/yield, winter-kill,
water stress or endogenous cultivar selection. Required heat and chilling are
explicit inputs. Reference: https://doi.org/10.5194/gmd-11-1343-2018 .
"""
from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class CerealParameters:
    heat_units: float
    base_temperature: float = 0.
    vernalization_days: float = 0.
    # Eq79: 1 is insensitive, 0 is fully responsive between pb and ps.
    photoperiod_floor: float = 1.
    photoperiod_base_hours: float | None = None
    photoperiod_saturation_hours: float | None = None
    senescence_fraction: float = .7  # temperate cereals, supplement Table S11

    def __post_init__(self):
        values=[self.heat_units,self.base_temperature,self.vernalization_days,
                self.photoperiod_floor,self.senescence_fraction]
        if not np.isfinite(values).all() or self.heat_units<=0 or not 0<=self.vernalization_days<=60:
            raise ValueError('Finite parameters, positive heat requirement and 0–60 vernalization days required')
        if not 0<=self.photoperiod_floor<=1 or not 0<self.senescence_fraction<=1:
            raise ValueError('Invalid photoperiod floor or senescence fraction')
        thresholds=(self.photoperiod_base_hours,self.photoperiod_saturation_hours)
        if self.photoperiod_floor<1 or any(v is not None for v in thresholds):
            if any(v is None for v in thresholds) or not np.isfinite(thresholds).all() or not 0<=thresholds[0]<thresholds[1]<=24:
                raise ValueError('Active photoperiod needs explicit increasing thresholds in 0–24 hours')


@dataclass
class CerealDevelopment:
    maturity_days: np.ndarray  # -1 means no physiological maturity in supplied days
    heat_accumulated: np.ndarray
    vernalization_accumulated: np.ndarray
    fraction: np.ndarray
    fraction_path: np.ndarray | None = None
    vernalization_path: np.ndarray | None = None


def vernalization_effectiveness(temperature):
    """Published trapezoid: [-4,3,10,17] °C, using daily mean temperature."""
    t=np.asarray(temperature,float)
    if not np.isfinite(t).all():raise ValueError('Finite temperatures required')
    return np.clip(np.minimum((t+4)/7,(17-t)/7),0,1)


def photoperiod_factor(daylength, parameters):
    daylength=np.asarray(daylength,float)
    if not np.isfinite(daylength).all() or np.any((daylength<0)|(daylength>24)):
        raise ValueError('Daylength must be finite and within 0–24 hours')
    if parameters.photoperiod_floor==1:return np.ones_like(daylength)
    ramp=np.clip((daylength-parameters.photoperiod_base_hours)/
                 (parameters.photoperiod_saturation_hours-parameters.photoperiod_base_hours),0,1)
    return parameters.photoperiod_floor+(1-parameters.photoperiod_floor)*ramp


def cereal_development(temperature, daylength, parameters, *, heat_units=None,
                       vernalization_days=None, record=False):
    """Integrate supplied daily means from sowing, one step per actual day.

    Eq78 is applied only before stage >0.2 and while chilling is incomplete.
    At <=10 accumulated vernalizing days progress is zero until requirements
    are met. This branch convention resolves the printed equation's zero
    denominator at PVD=10, consistent with the published v4 reference code.
    Photoperiod restriction ends after the senescence threshold. The default
    floor=1 matches the paper's reference assumption. Active photoperiod
    requires explicit cultivar thresholds; none are invented by default.
    Optional heat/chilling fields support a shared cultivar rule on many cells.
    """
    t=np.asarray(temperature,float)
    if t.ndim<1 or not len(t) or not np.isfinite(t).all():
        raise ValueError('Finite nonempty daily temperature series required')
    daylight=np.broadcast_to(np.asarray(daylength,float),t.shape)
    light=photoperiod_factor(daylight,parameters)
    required=np.broadcast_to(np.asarray(parameters.heat_units if heat_units is None else heat_units,float),t.shape[1:])
    chilling=np.broadcast_to(np.asarray(parameters.vernalization_days if vernalization_days is None else vernalization_days,float),t.shape[1:])
    if not np.isfinite(required).all() or np.any(required<=0) or not np.isfinite(chilling).all() or np.any((chilling<0)|(chilling>60)):
        raise ValueError('Invalid heat/chilling fields')
    hu=np.zeros(t.shape[1:]);vd=hu.copy();stage=hu.copy()
    maturity=np.full(hu.shape,-1,dtype=int)
    stages=[stage.copy()] if record else None
    vernal=[vd.copy()] if record else None
    for day,(temperature,photoperiod) in enumerate(zip(t,light),1):
        active=maturity<0
        vd+=np.where(active&(vd<chilling),vernalization_effectiveness(temperature),0.)
        restricted=(vd<chilling)&(stage<=.2)
        # The remaining denominator is strictly positive whenever vd>10
        # and vd<PVD. Avoid ever evaluating 0/0 for spring or PVD=10.
        denominator=chilling-10
        ratio=np.divide(vd-10,denominator,out=np.zeros_like(vd),where=denominator>0)
        vrf=np.where(restricted,np.where(vd<=10,0.,np.clip(ratio,0,1)),1.)
        prf=np.where(stage<=parameters.senescence_fraction,photoperiod,1.)
        hu+=np.where(active,np.maximum(temperature-parameters.base_temperature,0)*vrf*prf,0.)
        stage=np.minimum(hu/required,1.)
        maturity=np.where(active&(hu>=required),day,maturity)
        if record:stages.append(stage.copy());vernal.append(vd.copy())
    return CerealDevelopment(maturity,hu,vd,stage,
        None if stages is None else np.stack(stages),None if vernal is None else np.stack(vernal))
