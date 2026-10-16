"""Small NOAA pressure-profile inputs for diagnosis, not new climate forcing.

Public NCEP/NCAR 1981–2010 monthly climatology, regional OPeNDAP ASCII
subsets. No NetCDF4 dependency or global gridded downloads. The constrained
reader validates dimensions, row indices, coordinate maps, period and units.
"""
from __future__ import annotations
from dataclasses import dataclass
import json
from pathlib import Path
import re
import ssl
import urllib.request

import numpy as np
from scipy.ndimage import distance_transform_edt

from rotclimate_v10.core import DAY,EDGES,CENTERS,air_masses,interpolate_months
from rotclimate_v10.earth import atomic_json,sha256
from rotclimate_v10.weather import catalogue,flow_at
from experiments.v10_thermodynamics import CP,G,levels

BASE = 'https://psl.noaa.gov/thredds/dodsC/Datasets/ncep.reanalysis.derived/pressure/'
VARIABLES = {'air':17,'hgt':17,'uwnd':17,'vwnd':17,'shum':8,'omega':12}
# Inclusive global 2.5-degree index ranges. Iberia straddles longitude zero.
BOXES = {'california':[(18,24,90,100)], 'iberia':[(17,25,136,143),(17,25,0,5)]}
UPWIND = {'california':(-133.,-124.,32.,43.),'iberia':(-19.,-10.,30.,45.)}


@dataclass
class Field:
    values: np.ndarray  # time, pressure, latitude, longitude
    pressure_hpa: np.ndarray
    latitude: np.ndarray
    longitude: np.ndarray
    time: np.ndarray


def parse_ascii(text,variable):
    if len(text)>4*1024*1024:raise ValueError('Oversized OPeNDAP response.')
    marker = re.search(r'\n-{10,}\s*\n',text)
    if marker is None:raise ValueError('Not an OPeNDAP ASCII response.')
    body = text[marker.end():]
    heading = re.search(r'^'+re.escape(variable)+r'\.'+re.escape(variable)+r'((?:\[\d+\]){4})\s*$',body,re.M)
    if heading is None:raise ValueError('Missing four-dimensional data grid.')
    shape = tuple(map(int,re.findall(r'\d+',heading.group(1))))
    if any(n<=0 for n in shape) or np.prod(shape)>500000:raise ValueError('Invalid data dimensions.')
    data = np.empty(shape);seen = set()
    tail = body[heading.end():]
    for line in tail.splitlines():
        if re.match(r'^'+re.escape(variable)+r'\.',line):break
        if not line.strip():continue
        match = re.fullmatch(r'\[(\d+)\]\[(\d+)\]\[(\d+)\],\s*(.*)',line.strip())
        if match is None:raise ValueError('Malformed data row.')
        index = tuple(map(int,match.group(1,2,3)))
        if index in seen or any(i>=n for i,n in zip(index,shape[:3])):raise ValueError('Duplicate/out-of-range data row.')
        tokens = match.group(4).split(',')
        if len(tokens)!=shape[-1]:raise ValueError('Truncated data row.')
        data[index] = [float(t.strip()) for t in tokens];seen.add(index)
    if len(seen)!=int(np.prod(shape[:3])):raise ValueError('Incomplete data grid.')
    axes = []
    for name,size in zip(('time','level','lat','lon'),shape):
        match = re.search(r'^'+re.escape(variable)+r'\.'+name+r'\['+str(size)+r'\]\s*\n(.*?)(?=\n\s*\n|\Z)',body,re.M|re.S)
        if match is None:raise ValueError(f'Missing coordinate map: {name}')
        axis = np.array([float(x.strip()) for x in match.group(1).replace('\n',',').split(',') if x.strip()])
        if len(axis)!=size or not np.isfinite(axis).all():raise ValueError('Invalid coordinate values.')
        axes.append(axis)
    if len(axes[0])==12 and not np.allclose(axes[0]-axes[0][0],EDGES[:12]/DAY,atol=1e-7,rtol=0):
        raise ValueError('Monthly climatology must be ordered January through December.')
    if (np.diff(axes[1])>=0).any() or (axes[1]<=0).any() or (np.diff(axes[2])>=0).any() or (np.diff(axes[3])<=0).any():
        raise ValueError('Unexpected coordinate ordering.')
    if abs(axes[2]).max()>90 or axes[3].min()<0 or axes[3].max()>=360:raise ValueError('Invalid geographic coordinates.')
    data[~np.isfinite(data)|(abs(data)>1e30)] = np.nan
    return Field(data,axes[1],axes[2],axes[3],axes[0])


def metadata(text,variable):
    if not re.search(r'String\s+climo_period\s+"1981/01/01\s*-\s*2010/12/31"',text):
        raise ValueError('Reference must declare the 1981–2010 climatology.')
    match = re.search(r'\b'+re.escape(variable)+r'\s*\{([^{}]*)\}',text,re.S)
    if match is None:raise ValueError('Missing variable metadata.')
    attrs = match.group(1)
    units = re.search(r'String\s+units\s+"([^"]+)"',attrs)
    if units is None:raise ValueError('Missing physical units.')
    scale = re.search(r'\w+\s+scale_factor\s+([^;]+);',attrs)
    offset = re.search(r'\w+\s+add_offset\s+([^;]+);',attrs)
    if (scale and float(scale.group(1))!=1) or (offset and float(offset.group(1))!=0):
        raise ValueError('This reader expects the verified non-packed OPeNDAP products.')
    return units.group(1)


def normalize(field,variable,units):
    a = field.values.copy()
    if variable=='air':
        if units in ('K','degK'):a -= 273.15
        elif units!='degC':raise ValueError('Unsupported air-temperature units.')
    elif variable=='shum':
        if units in ('grams/kg','g/kg'):a /= 1000.
        elif units not in ('kg/kg','Kg/Kg'):raise ValueError('Unsupported specific-humidity units.')
        # Permit tiny rounding negatives; the raw response retains their exact values.
        if (a < -1e-8).any() or (a>.1).any():raise ValueError('Implausible specific humidity.')
        a = np.maximum(a,0)
        a = a/(1-a)  # q specific humidity -> r mixing ratio used by the model
    else:
        expected = {'hgt':('m',),'uwnd':('m/s',),'vwnd':('m/s',),'omega':('Pa/s','Pascal/s','pascal/s','Pascals/sec')}
        if units not in expected[variable]:raise ValueError(f'Unsupported {variable} units: {units}')
    ranges = {'air':(-150,70),'hgt':(-1000,50000),'uwnd':(-200,200),'vwnd':(-200,200),'shum':(0,.12),'omega':(-10,10)}
    lo,hi = ranges[variable]
    if ((a<lo)|(a>hi)).any():raise ValueError(f'Implausible {variable} values; check units.')
    return Field(a,field.pressure_hpa,field.latitude,field.longitude,field.time)


def request_plan():
    plan = []
    for var,nlevels in VARIABLES.items():
        url = BASE+f'{var}.mon.1981-2010.ltm.nc'
        plan.append((f'{var}.das',url+'.das',var,None))
        for region,boxes in BOXES.items():
            for k,(y0,y1,x0,x1) in enumerate(boxes):
                query = f'{var}[0:1:11][0:1:{nlevels-1}][{y0}:1:{y1}][{x0}:1:{x1}]'
                plan.append((f'{var}_{region}_{k}.ascii',url+'.ascii?'+query,var,(y0,y1,x0,x1)))
    return plan


def acquire(cache,fetch=False,progress=print):
    """Cache each small response atomically, with source URL and SHA256."""
    cache = Path(cache);record = cache/'downloads.json'
    saved = json.loads(record.read_text()) if record.exists() else {}
    context = ssl.create_default_context()
    try:
        import certifi
        context.load_verify_locations(cafile=certifi.where())
    except ImportError:pass
    all_text = {}
    for name,url,var,box in request_plan():
        path = cache/name
        if path.exists():
            if name not in saved or saved[name]['url']!=url or saved[name]['sha256']!=sha256(path):
                raise ValueError('Atmospheric input cache changed or lacks provenance; use a new --reference-cache directory.')
            payload = path.read_text()
        else:
            if not fetch:raise ValueError('Atmospheric reference missing; run with --fetch --run.')
            progress(f'Fetching small NOAA regional reference: {name}',flush=True)
            req = urllib.request.Request(url,headers={'User-Agent':'rotclimate-atmosphere-audit/1.0'})
            with urllib.request.urlopen(req,timeout=60,context=context) as response:
                binary = response.read(4*1024*1024+1)
            if len(binary)>4*1024*1024:raise ValueError('Reference response exceeds its 4 MB bound.')
            payload = binary.decode('utf-8')
            if box is None:metadata(payload,var)
            else:validate_subset(parse_ascii(payload,var),box,VARIABLES[var])
            cache.mkdir(parents=True,exist_ok=True);temporary = path.with_suffix(path.suffix+'.part')
            temporary.write_text(payload);temporary.replace(path)
            saved[name] = {'url':url,'sha256':sha256(path),'bytes':path.stat().st_size}
            atomic_json(record,saved)
        all_text[name] = payload
    return all_text,saved


def validate_subset(field,box,nlevels):
    y0,y1,x0,x1 = box
    if field.values.shape != (12,nlevels,y1-y0+1,x1-x0+1):raise ValueError('Server did not honour the requested subset.')
    if not np.array_equal(field.latitude,90-2.5*np.arange(y0,y1+1)) or not np.array_equal(field.longitude,2.5*np.arange(x0,x1+1)):
        raise ValueError('Server returned the wrong regional coordinates.')


def fields_from_cache(texts):
    result = {}
    for var,nlevels in VARIABLES.items():
        units = metadata(texts[f'{var}.das'],var)
        for region,boxes in BOXES.items():
            pieces = []
            for k,box in enumerate(boxes):
                f = parse_ascii(texts[f'{var}_{region}_{k}.ascii'],var);validate_subset(f,box,nlevels)
                pieces.append(normalize(f,var,units))
            first = pieces[0]
            if any(not np.array_equal(f.pressure_hpa,first.pressure_hpa) or not np.array_equal(f.latitude,first.latitude)
                   or not np.array_equal(f.time,first.time) for f in pieces):raise ValueError('Inconsistent split-grid axes.')
            lon = np.concatenate([f.longitude for f in pieces]);order = np.argsort(lon)
            result[region,var] = Field(np.concatenate([f.values for f in pieces],axis=-1)[...,order],first.pressure_hpa,
                                      first.latitude,lon[order],first.time)
    return result


def at_pressure(field,longitude,latitude,pressure_hpa):
    """Nearest native horizontal cell, log-pressure interpolation, no extrapolation."""
    lat_index = abs(field.latitude[:,None,None]-latitude).argmin(0)
    delta = (field.longitude[:,None,None]-longitude%360+180)%360-180
    lon_index = abs(delta).argmin(0)
    values = field.values[:,:,lat_index,lon_index]
    pressure = np.broadcast_to(pressure_hpa,longitude.shape)
    if (pressure>field.pressure_hpa.max()).any() or (pressure<field.pressure_hpa.min()).any():
        raise ValueError('Requested pressure outside reference levels.')
    xp = np.log(field.pressure_hpa[::-1]);x = np.log(pressure)
    k = np.clip(np.searchsorted(xp,x)-1,0,len(xp)-2)
    f = (x-xp[k])/(xp[k+1]-xp[k])
    ordered = values[:,::-1]
    a = np.take_along_axis(ordered,np.broadcast_to(k,(12,1)+k.shape),axis=1)[:,0]
    b = np.take_along_axis(ordered,np.broadcast_to(k+1,(12,1)+k.shape),axis=1)[:,0]
    sampled = (1-f)*a+f*b
    return sampled,lat_index,lon_index


def offshore_mask(case):
    d = case.domain
    west,east,south,north = UPWIND[d.name]
    distance = distance_transform_edt(~d.land,sampling=(d.dy,d.dx))/1000.
    mask = (~d.land)&(distance>=100)&(distance<=700)&(case.longitude>=west)&(case.longitude<=east)&(d.latitude>=south)&(d.latitude<=north)
    mask[:2] = False;mask[-2:] = False;mask[:,:2] = False;mask[:,-2:] = False
    if not mask.any():raise ValueError('No upwind ocean cells in declared audit area.')
    return mask


def circulation_geometry(case,config):
    """Analytic prescribed-flow diagnosis only; no climate state integration."""
    d = case.domain;ml,mu,_ = air_masses(d,config);zl,zu = levels(d,config)
    dry_gap = CP*(config.upper_temperature_offset_c-config.lower_temperature_offset_c)+G*(zu-zl)
    cooling = [];u = [];v = []
    events = catalogue(d,config)
    for t in CENTERS:
        f = flow_at(d,config,events,t,storms=False)
        # Reference-profile dry contribution from J*(s_lower-s_upper)/upper_mass.
        tendency = -np.maximum(f.vertical,0)*dry_gap/(mu*CP)*DAY
        cooling.append(float(np.percentile(abs(tendency[case.score_mask]),95)))
        u.append(.5*(f.lower_x[:,1:]+f.lower_x[:,:-1])/ml)
        v.append(-.5*(f.lower_y[1:]+f.lower_y[:-1])/ml)  # geographic north positive
    return {'representative_height_gap_m':float(np.median(zu-zl)),
            'upper_reference_dry_cooling_p95_k_day':cooling,
            'warning':'Dry vertical-exchange contribution at the prescribed reference profile only, not net cooling or an annual heat source.'},np.stack(u),np.stack(v)


def reference_comparison(case,config,fields):
    d = case.domain;mask = offshore_mask(case);_,_,ps = air_masses(d,config)
    geometry,model_u,model_v = circulation_geometry(case,config)
    month_targets = np.stack([interpolate_months(d.temperature_c,t) for t in CENTERS])
    comparison = {'geometry':geometry,'ocean_model_cells':int(mask.sum()),'levels':{}}
    for name,fraction,offset,rh in (('lower',config.lower_pressure_fraction,config.lower_temperature_offset_c,config.ocean_boundary_rh),
                                    ('upper',config.upper_pressure_fraction,config.upper_temperature_offset_c,config.upper_boundary_rh)):
        sampled = {};native = None
        for variable in VARIABLES:
            # Only flat-ocean cells are scored; never request below-ground inland levels.
            pressure = float(np.median(ps[mask]*fraction/100))
            values,iy,ix = at_pressure(fields[d.name,variable],case.longitude,d.latitude,pressure)
            if not np.isfinite(values[:,mask]).all():raise ValueError(f'Missing scored offshore {variable} reference.')
            sampled[variable] = values[:,mask].mean(1).tolist()
            if variable=='air':native = len(set(zip(iy[mask].tolist(),ix[mask].tolist())))
        from rotclimate_v10.core import saturation_ratio
        target = month_targets+offset
        model_r = saturation_ratio(target,ps*fraction)*rh
        sampled.update(reference_unique_native_cells=native,model_target_temperature_c=target[:,mask].mean(1).tolist(),
            model_boundary_mixing_ratio_g_kg=(1000*model_r[:,mask].mean(1)).tolist(),
            reference_mixing_ratio_g_kg=(1000*np.array(sampled.pop('shum'))).tolist(),
            nominal_ocean_pressure_hpa=float(np.median(ps[mask]*fraction/100)))
        sampled['model_height_m'] = float(-8400*np.log(fraction))
        comparison['levels'][name] = sampled
    comparison['model_lower_zonal_wind_ms'] = model_u[:,mask].mean(1).tolist()
    comparison['model_lower_northward_wind_ms'] = model_v[:,mask].mean(1).tolist()
    # Direct omega comparison only over flat ocean; -gJ is not physical omega over sloping sigma surfaces.
    comparison['limitations'] = ('2.5-degree 1981–2010 reanalysis versus 1970–2000 land/1971–2000 sea normals; '
        'nearest horizontal cells and log-pressure interpolation. Monthly means do not measure transient storm covariance. '
        'Native cells are repeated on the model grid, not independent samples. No terrain omega-ratio claim or precipitation scoring.')
    return comparison
