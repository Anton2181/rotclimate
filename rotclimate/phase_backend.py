"""Bind phase dependencies in isolated copies of frozen prototype functions.

Original function bodies and module globals remain unchanged. This research
compatibility layer lets reference and candidate numerical roots run side by
side without duplicating the physics equations across another set of modules.
"""
from dataclasses import dataclass
from types import FunctionType
from functools import update_wrapper
from rotclimate.pressure_moist import enthalpy_phase
from rotclimate.open_mean_boundary import OpenMeanRigidLidModel
from rotclimate.convective_adjustment import adjust_convection
from rotclimate.pressure_boundary import advance_boundary_with_convection
from rotclimate.surface_coupling import advance_surface_forcing,advance_surface_coupled


def bind_dependencies(function,**dependencies):
    """Reuse trusted Python code with an explicit independent global namespace."""
    if not isinstance(function,FunctionType):raise TypeError('Need a Python function with a declared source body')
    if any(name not in function.__globals__ for name in dependencies):raise ValueError('Dependency name is absent from the original namespace')
    namespace=dict(function.__globals__);namespace.update(dependencies)
    bound=FunctionType(function.__code__,namespace,function.__name__,function.__defaults__,function.__closure__)
    bound.__kwdefaults__=None if function.__kwdefaults__ is None else dict(function.__kwdefaults__)
    bound.__annotations__=dict(function.__annotations__);update_wrapper(bound,function)
    return bound


@dataclass(frozen=True)
class PhaseBackend:
    name: str
    phase: object
    model_type: type
    adjustment: object
    advance_with_convection: object
    surface_forcing: object
    surface_coupled: object
    body_sources: dict


def make_phase_backend(phase=enthalpy_phase,*,name='reference'):
    if not callable(phase) or not isinstance(name,str) or not name:raise ValueError('Need a phase callable and explicit backend name')
    dynamics=bind_dependencies(OpenMeanRigidLidModel.advance,enthalpy_phase=phase)
    adjustment=bind_dependencies(adjust_convection,enthalpy_phase=phase)
    convection=bind_dependencies(advance_boundary_with_convection,enthalpy_phase=phase,adjust_convection=adjustment)
    forcing=bind_dependencies(advance_surface_forcing,enthalpy_phase=phase)
    coupled=bind_dependencies(advance_surface_coupled,advance_surface_forcing=forcing,advance_boundary_with_convection=convection)
    model_type=type('PhaseBoundOpenMeanModel',(OpenMeanRigidLidModel,),dict(advance=dynamics,phase_backend_name=name,__module__=__name__))
    originals=dict(dynamics=OpenMeanRigidLidModel.advance,adjustment=adjust_convection,convection=advance_boundary_with_convection,forcing=advance_surface_forcing,coupled=advance_surface_coupled)
    copies=dict(dynamics=dynamics,adjustment=adjustment,convection=convection,forcing=forcing,coupled=coupled)
    manifest={key:dict(module=f.__module__,function=f.__qualname__,same_code_object=copies[key].__code__ is f.__code__) for key,f in originals.items()}
    return PhaseBackend(name,phase,model_type,adjustment,convection,forcing,coupled,manifest)
