"""Passive capture of isolated convection inputs/results, with frozen math bodies.

Observers receive copies only; they cannot mutate the integrator state or the
accepted closure output. Exceptions and nonconvergence retain their original
behavior. This does not change relaxation, neutral tolerance or iteration cap.
"""
from copy import deepcopy
from dataclasses import replace
import numpy as np
from .phase_backend import bind_dependencies


def observe_convection(backend,observer):
    if not callable(observer):raise ValueError('Need a convection observer callback')
    def adjustment(temperature_k,vapor_kg_m2,cell_mass_kg_m2,pressure_pa,**kwargs):
        result=backend.adjustment(temperature_k,vapor_kg_m2,cell_mass_kg_m2,pressure_pa,**kwargs)
        record={name:np.array(value,copy=True) for name,value in dict(input_temperature=temperature_k,input_vapor=vapor_kg_m2,cell_mass=cell_mass_kg_m2,pressure=pressure_pa,
            output_temperature=result.temperature_k,output_vapor=result.vapor_kg_m2,rain=result.ground_rain_kg_m2,rain_enthalpy=result.ground_rain_enthalpy_j_m2).items()}
        record.update(certificate=deepcopy(result.certificate),controls=deepcopy(kwargs))
        observer(record)
        return result
    convection=bind_dependencies(backend.advance_with_convection,adjust_convection=adjustment)
    coupled=bind_dependencies(backend.surface_coupled,advance_boundary_with_convection=convection)
    return replace(backend,adjustment=adjustment,advance_with_convection=convection,surface_coupled=coupled)
