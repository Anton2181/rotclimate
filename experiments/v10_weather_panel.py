"""Explicit weather-seed adapters; frozen physics and forcing algorithms retained."""
from __future__ import annotations
import numpy as np
from experiments import v10_event_forcing as core
from rotclimate_v10.core import CENTERS


def prepare_calendar(case,profile,setting,geometry,air,circulation,seed):
    projector = core.core.ColumnProjection(case.domain,circulation[0])
    events = core.core.nested_events(case.domain,setting,seed,profile.storm_domain_width_m)
    def flows(t):return core.native_flows(case,profile,setting,geometry,circulation,events,projector,t)
    def ratios(t):return core.core.boundary_ratio(case.domain,profile,setting,geometry,air,t)
    def caps(start,end):
        knots = CENTERS[(CENTERS>start)&(CENTERS<end)]
        targets = [core.coordinates.targets(case.domain,profile,setting,t,air)[0] for t in (start,*knots,end)]
        return .95*core.base.saturation(np.min(targets,axis=0),geometry.pressure)
    coast = case.domain.land&(case.coast_distance_km<150.)
    arrays,diagnostics = core.build_calendar(case.domain,geometry,flows,ratios,caps,coast)
    diagnostics.update(seed=seed,event_count=len(events))
    return arrays,diagnostics


class Driver(core.Driver):
    def __init__(self,arrays,case,profile,setting,geometry,air,circulation,amplitude,timing,seed):
        super().__init__(arrays,case,profile,setting,geometry,air,circulation,amplitude,timing)
        self.events = core.core.nested_events(case.domain,setting,seed,profile.storm_domain_width_m)
        self.seed = seed
