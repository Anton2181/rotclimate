"""Read the previously frozen raw-r43 diagnostic sample, without fitting it."""
from dataclasses import dataclass
import json

import numpy as np

from .models import ROOT, specification
from .export import climate_arrays, geometry, surface_months
from scripts.land_people import analyse, bucket, hargreaves, sunlight_top


@dataclass
class CalendarSample:
    climate: tuple  # temperature, precipitation, PET, reference initial soil
    irrigation: np.ndarray
    can_double: np.ndarray
    keep: np.ndarray
    rain_keep: np.ndarray
    baseline: dict
    indices: np.ndarray
    grid_shape: tuple
    previous: dict
    geography: dict


def load_frozen_calendar_sample():
    from scripts.local_benchmark_protocol import file_hash
    previous=json.loads((ROOT/'output/crop_calendar_audit_20261103/receipt.json').read_text())
    for name,expected in previous['inputs_sha256'].items():
        if file_hash(ROOT/name)!=expected:raise ValueError('Frozen sample input changed: '+name)
    data=ROOT/'atlases/earth_fit/data';meta=json.loads((data/'atlas.json').read_text())
    arrays=climate_arrays(data,meta);geo,key=geometry(meta,arrays['elev'].shape)
    if json.loads(json.dumps(key))!=previous['geography_inputs']:raise ValueError('Frozen geography changed')
    land=np.flatnonzero(geo['land_fraction']>0)
    selected=land[np.linspace(0,len(land)-1,previous['sample_cells'],dtype=int)]
    t,p,d,latitude=surface_months(meta,arrays)
    t,p,d=[a.reshape(12,-1)[:,selected].copy() for a in (t,p,d)]
    latitude=latitude.ravel()[selected];irr=geo['irr'].ravel()[selected];arable=geo['arable'].ravel()[selected]
    margin=specification()['margin_reliability'];cold=margin['cold_mean_temperature_c'];dry=margin['dry_rain_over_evaporation']
    baseline,_=analyse(t,p,latitude,meta['world']['tilt'],0,irr,arable,d,margins=(cold,dry))
    pet=hargreaves(t,d,sunlight_top(latitude,meta['world']['tilt'],0));soil=bucket(p,pet)
    keep=np.clip((t.mean(0)-cold[0])/(cold[1]-cold[0]),0,1)
    rain_keep=np.clip((baseline['aridity']-dry[0])/(dry[1]-dry[0]),0,1)
    return CalendarSample((t,p,pet,soil),irr,(irr>=.5)|(baseline['lgp_days']>=300),
                          keep,rain_keep,baseline,selected,geo['land_fraction'].shape,previous,key)
