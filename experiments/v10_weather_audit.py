"""Bounded six-hourly NOAA reference audit, never climate forcing or rain fitting.

Four Jan/Jul windows in 1990/2000. Native offshore pressure-level statistics
separate mean(q*v) from mean(q)*mean(v), without pooling space and time.
"""
from __future__ import annotations
import calendar
from datetime import datetime
import json
from pathlib import Path
import re
import ssl
import time
import urllib.error
import urllib.request
import numpy as np
from experiments import v10_forcing_audit as monthly
from experiments.v10_column import saturation, G
from rotclimate_v10.earth import atomic_json, sha256
BASE = 'https://psl.noaa.gov/thredds/dodsC/Datasets/ncep.reanalysis/pressure/'
VARIABLES = ('air', 'shum', 'uwnd', 'vwnd')
WINDOWS = ((1990, 1), (1990, 7), (2000, 1), (2000, 7))
LEVELS = np.array([925., 850., 700., 600., 500., 400., 300.])
FILE_CAP = 4*1024*1024
CACHE_CAP = 96*1024*1024


class ServerPaused(RuntimeError):
    pass


def time_slice(year, month):
    start = (datetime(year, month, 1)-datetime(year, 1, 1)).days*4
    count = calendar.monthrange(year, month)[1]*4
    return start, start+count-1, count


def request_plan():
    plan = []
    for year in sorted({year for year, _ in WINDOWS}):
        for variable in VARIABLES:
            plan.append({'name': f'{variable}_{year}.das', 'url': BASE+f'{variable}.{year}.nc.das',
                'variable': variable, 'year': year, 'kind': 'metadata'})
    for year, month in WINDOWS:
        first, last, count = time_slice(year, month)
        for variable in VARIABLES:
            for region, boxes in monthly.BOXES.items():
                for piece, box in enumerate(boxes):
                    y0, y1, x0, x1 = box
                    query = f'{variable}[{first}:1:{last}][1:1:7][{y0}:1:{y1}][{x0}:1:{x1}]'
                    plan.append({'name': f'{variable}_{year}_{month:02d}_{region}_{piece}.ascii',
                        'url': BASE+f'{variable}.{year}.nc.ascii?'+query, 'kind': 'data',
                        'variable': variable, 'year': year, 'month': month,
                        'region': region, 'piece': piece, 'box': list(box), 'count': count})
    return plan


def attribute_block(text, name):
    match = re.search(r'\b'+re.escape(name)+r'\s*\{([^{}]*)\}', text, re.S)
    if match is None:
        raise ValueError('Missing reference attribute block: '+name)
    return match.group(1)


def string_attribute(block, name):
    match = re.search(r'\bString\s+'+re.escape(name)+r'\s+"([^"]+)"\s*;', block)
    if match is None:
        raise ValueError('Missing reference string attribute: '+name)
    return match.group(1)


def numeric_attribute(block, name, default=None):
    match = re.search(r'\b(?:Float32|Float64|Int16|Int32|Byte|UInt16|UInt32)\s+'+re.escape(name)+r'\s+([^;]+);', block)
    if match is None:
        return default
    values = np.array([float(v.strip()) for v in match.group(1).split(',')])
    if len(values) != 1 or not np.isfinite(values).all():
        raise ValueError('Expected scalar attribute: '+name)
    return float(values[0])


def metadata(text, variable):
    if len(text) > 65536 or not re.search(r'String\s+dataset_title\s+"NCEP-NCAR Reanalysis 1"', text) or 'climo_period' in text:
        raise ValueError('Need annual NCEP/NCAR Reanalysis 1 metadata, not a climatology or another product.')
    block = attribute_block(text, variable)
    if string_attribute(block, 'statistic') != 'Individual Obs':
        raise ValueError('Need individual six-hourly analyses, not daily/monthly means.')
    unit = string_attribute(block, 'units')
    allowed = {'air': ('K', 'degK', 'degC'), 'shum': ('kg/kg', 'Kg/Kg', 'g/kg', 'grams/kg'),
        'uwnd': ('m/s',), 'vwnd': ('m/s',)}
    if unit not in allowed[variable]:
        raise ValueError('Unsupported reference units.')
    time_units = string_attribute(attribute_block(text, 'time'), 'units')
    if string_attribute(attribute_block(text, 'level'), 'units') not in ('mb', 'millibar', 'hPa'):
        raise ValueError('Pressure-level units must be hPa/millibar.')
    match = re.fullmatch(r'(hours|days) since 1800-0?1-0?1 0{1,2}:0{1,2}:0{1,2}(?:\.0+)?', time_units)
    if match is None:
        raise ValueError('Unsupported six-hourly reference time origin.')
    return {'units': unit, 'time_factor_hours': 1. if match[1] == 'hours' else 24.,
        'scale': numeric_attribute(block, 'scale_factor', 1.),
        'offset': numeric_attribute(block, 'add_offset', 0.),
        'missing': numeric_attribute(block, 'missing_value'),
        'fill': numeric_attribute(block, '_FillValue')}


def decode(text, attrs, job):
    variable = job['variable']
    field = monthly.parse_ascii(text, variable)
    y0, y1, x0, x1 = job['box'];n = job['count']
    expected_time = (datetime(job['year'], job['month'], 1)-datetime(1800, 1, 1)).total_seconds()/3600+6*np.arange(n)
    if field.values.shape != (n, 7, y1-y0+1, x1-x0+1) or not np.array_equal(field.pressure_hpa, LEVELS):
        raise ValueError('Six-hourly response shape or pressure levels differ from request.')
    if not np.array_equal(field.latitude, 90-2.5*np.arange(y0, y1+1)) or not np.array_equal(field.longitude, 2.5*np.arange(x0, x1+1)):
        raise ValueError('Six-hourly response has wrong geographic axes.')
    if not np.allclose(field.time*attrs['time_factor_hours'], expected_time, atol=1e-6, rtol=0):
        raise ValueError('Six-hourly dates/order do not match the declared window.')
    values = field.values.copy()
    for name in ('missing', 'fill'):
        missing = attrs[name]
        if missing is not None:
            values[np.isclose(values, missing, rtol=1e-6, atol=0)] = np.nan
    values = values*attrs['scale']+attrs['offset']
    if variable == 'air' and attrs['units'] in ('K', 'degK'):
        values -= 273.15
    if variable == 'shum' and attrs['units'] in ('g/kg', 'grams/kg'):
        values /= 1000.
    limits = {'air': (-150, 70), 'shum': (-1e-8, .1), 'uwnd': (-200, 200), 'vwnd': (-200, 200)}
    lo, hi = limits[variable]
    if ((values < lo)|(values > hi)).any():
        raise ValueError('Implausible decoded values; do not guess units/packing.')
    if variable == 'shum':
        values = np.maximum(values, 0.)  # Only validated <=1e-8 rounding negatives.
    return monthly.Field(values, field.pressure_hpa, field.latitude, field.longitude, expected_time)


def acquire(cache, fetch=False, progress=print, should_stop=lambda: False, spacing_seconds=3.):
    cache = Path(cache);index = cache/'downloads.json'
    saved = json.loads(index.read_text()) if index.exists() else {}
    result = {};attributes = {}
    context = ssl.create_default_context()
    try:
        import certifi
        context.load_verify_locations(cafile=certifi.where())
    except ImportError:
        pass
    total = 0
    last_request = None
    for job in request_plan():
        if should_stop():
            raise ServerPaused('Invocation budget reached; completed cache entries preserved. Resume with the same command.')
        path = cache/job['name']
        if path.exists():
            entry = saved.get(job['name'], {})
            if entry.get('url') != job['url'] or entry.get('sha256') != sha256(path):
                raise ValueError('Weather cache lacks matching provenance; preserve it and use a new cache.')
            binary = path.read_bytes()
        else:
            if not fetch:
                raise ValueError('Weather reference missing; user may run with --fetch --run.')
            if last_request is not None:
                time.sleep(max(0., spacing_seconds-(time.monotonic()-last_request)))
            progress('Fetch '+job['name'], flush=True)
            request = urllib.request.Request(job['url'], headers={'User-Agent': 'rotclimate-weather-diagnosis/1.0'})
            try:
                last_request = time.monotonic()
                with urllib.request.urlopen(request, context=context, timeout=45) as response:
                    binary = response.read(FILE_CAP+1)
            except urllib.error.HTTPError as error:
                if error.code in (429, 503):
                    delay = error.headers.get('Retry-After', 'not specified')
                    raise ServerPaused(f'NOAA returned HTTP {error.code}; Retry-After: {delay}. No immediate retry; cached files preserved. Rerun later.') from error
                raise
        if len(binary) > FILE_CAP:
            raise ValueError('Reference response exceeds the per-file size cap.')
        total += len(binary)
        if total > CACHE_CAP:
            raise ValueError('Declared weather reference exceeds the 96 MB audit cap.')
        text = binary.decode('utf-8')
        if job['kind'] == 'metadata':
            attributes[job['variable'], job['year']] = metadata(text, job['variable'])
            parsed = text
        else:
            parsed = decode(text, attributes[job['variable'], job['year']], job)
        if not path.exists():
            cache.mkdir(parents=True, exist_ok=True)
            temporary = path.with_suffix(path.suffix+'.part')
            temporary.write_bytes(binary);temporary.replace(path)
            saved[job['name']] = {'url': job['url'], 'sha256': sha256(path), 'bytes': len(binary)}
            atomic_json(index, saved)
        result[job['name']] = parsed
    return result, saved


def merged_fields(records, year, month, region):
    fields = {}
    for variable in VARIABLES:
        pieces = [records[f'{variable}_{year}_{month:02d}_{region}_{i}.ascii'] for i in range(len(monthly.BOXES[region]))]
        first = pieces[0]
        if any(not np.array_equal(part.time, first.time) or not np.array_equal(part.pressure_hpa, first.pressure_hpa) or not np.array_equal(part.latitude, first.latitude) for part in pieces):
            raise ValueError('Split weather fields have different axes.')
        lon = np.concatenate([part.longitude for part in pieces]);order = np.argsort(lon)
        fields[variable] = monthly.Field(np.concatenate([part.values for part in pieces], axis=-1)[..., order],
            first.pressure_hpa, first.latitude, lon[order], first.time)
    reference = fields['air']
    if any(not np.array_equal(field.time, reference.time) or not np.array_equal(field.latitude, reference.latitude) or not np.array_equal(field.longitude, reference.longitude) or not np.array_equal(field.pressure_hpa, reference.pressure_hpa) for field in fields.values()):
        raise ValueError('Temperature/moisture/wind sampling is not synchronized.')
    return fields


def offshore_points(case, field):
    lon, lat = np.meshgrid((field.longitude+180)%360-180, field.latitude)
    model_lon = case.longitude[0];model_lat = case.domain.latitude[:, 0]
    ix = abs(model_lon[None, None, :]-lon[:, :, None]).argmin(2)
    iy = abs(model_lat[None, None, :]-lat[:, :, None]).argmin(2)
    west, east, south, north = monthly.UPWIND[case.domain.name]
    selected = monthly.offshore_mask(case)[iy, ix] & (lon >= west)&(lon <= east)&(lat >= south)&(lat <= north)
    selected &= (lon >= model_lon.min())&(lon <= model_lon.max())&(lat >= model_lat.min())&(lat <= model_lat.max())
    if selected.sum() < 3:
        raise ValueError('Need at least three declared upwind native marine cells.')
    weights = np.cos(np.deg2rad(lat[selected]));weights /= weights.sum()
    return selected, weights, np.column_stack([lon[selected], lat[selected]])


def integrate(values, pressure=LEVELS):
    """Trapezoidal 925–300 hPa integral / g; level axis is -2."""
    dp = -np.diff(pressure)*100
    return np.sum(.5*(values[..., :-1, :]+values[..., 1:, :])*dp[:, None], axis=-2)/G


def diagnose(fields, selected, weights):
    q, u, v, t = [fields[name].values[:, :, selected] for name in ('shum', 'uwnd', 'vwnd', 'air')]
    if not all(np.isfinite(a).all() for a in (q, u, v, t)):
        raise ValueError('Missing marine weather samples; do not silently alter the sampled population.')
    def box(values):
        return np.sum(values*weights, axis=-1)
    def vector_flux(wind):
        full = float(box(integrate((q*wind).mean(0))))
        product = float(box(integrate(q.mean(0)*wind.mean(0))))
        return {'full_mean_kg_m_s': full, 'product_of_means_kg_m_s': product,
            'temporal_covariance_kg_m_s': full-product}
    flux = {'eastward': vector_flux(u), 'northward': vector_flux(v)}
    series = box(integrate(q*u))
    count = max(1, int(np.ceil(len(series)*.1)))
    peak = np.argsort(series)[-count:]
    positive = np.maximum(series, 0.)
    q925, t925 = box(q[:, 0]), box(t[:, 0])
    covariance = float(np.mean((q925-q925.mean())*(t925-t925.mean())))
    ratio = q/(1-q)
    rh = ratio/saturation(t, LEVELS[None, :, None]*100)
    return {'samples': int(len(series)), 'native_marine_cells': int(selected.sum()),
        'pressure_bounds_hpa': [925., 300.], 'transport': flux,
        'top_eastward_transport_samples': count,
        'positive_eastward_transport_share_in_top_decile': float(positive[peak].sum()/positive.sum()) if positive.sum() > 0 else None,
        'top_decile_925hpa_specific_humidity_anomaly_g_kg': float(1000*(q925[peak].mean()-q925.mean())),
        'top_decile_925hpa_temperature_anomaly_c': float(t925[peak].mean()-t925.mean()),
        'box_q925_temperature_covariance_kg_kg_k': covariance,
        'liquid_reference_rh_p10_p50_p90_by_level': np.percentile(rh, [10, 50, 90], axis=(0, 2)).tolist(),
        'note': 'Area-average pointwise temporal flux contrasts in a marine box, not boundary imports or rainfall. Top eastward transport is a composite, not an objectively identified cyclone. q is specific humidity. Only 925–300 hPa is integrated.'}
