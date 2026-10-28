"""Physical heat-to-hydrostatic-thickness accounting, not a vertical eigenmode.

This gives the tendency of pressure thickness for piecewise uniform layer
temperature. It does not establish equivalence to the dry solver's chosen wave
speed/eigenfunction, or conserve a whole atmosphere's mechanical/thermal energy.
"""
from dataclasses import dataclass
import numpy as np

from .column_thermodynamics import CP, G, RD


@dataclass
class ThicknessHeating:
    forcing_m2_s3: np.ndarray
    temperature_tendency_k_s: np.ndarray
    layer_mass_kg_m2: np.ndarray
    column_heating_w_m2: np.ndarray
    certificate: dict


def pressure_layer_mass(pressure_edges_pa):
    edges = np.asarray(pressure_edges_pa,float)
    if (edges.ndim<1 or edges.shape[0]<2 or not np.isfinite(edges).all()
            or np.any(edges<=0) or np.any(np.diff(edges,axis=0)>=0)):
        raise ValueError("Need finite positive descending pressure interfaces")
    # Dilute pressure-mass approximation: dp/g is treated as dry air mass.
    return -np.diff(edges,axis=0)/G


def project_layer_heating(pressure_edges_pa, layer_heating_w_m2):
    """Qthickness=Rd sum[ln(pbottom/ptop) * Hlayer/(cp Mlayer)].

Hlayer is an explicitly accounted heat source W/m². Net column heat is kept
separately: vertically separated heating/cooling can have zero column sum and
still change thickness. This is fixed-pressure dry-temperature thickness;
direct virtual-temperature, pressure-boundary motion and geometric effects are
excluded. It must not be mistaken for a validated baroclinic eigenmode forcing.
"""
    edges = np.asarray(pressure_edges_pa,float)
    mass = pressure_layer_mass(edges)
    heat = np.asarray(layer_heating_w_m2,float)
    if heat.shape!=mass.shape or not np.isfinite(heat).all():
        raise ValueError("Need finite layer heating matching the pressure intervals")
    tendency = heat/(CP*mass)
    weights = RD*np.log(edges[:-1]/edges[1:])
    forcing = np.sum(weights*tendency,axis=0)
    error = CP*mass*tendency-heat
    cert = dict(maximum_heat_reconstruction_residual_w_m2=float(np.abs(error).max()),
        maximum_absolute_thickness_forcing_m2_s3=float(np.abs(forcing).max()),
        scope="Fixed-pressure piecewise-isothermal dry thickness tendency; not a solved vertical eigenmode or full atmospheric energy budget")
    return ThicknessHeating(forcing,tendency,mass,heat.sum(axis=0),cert)
