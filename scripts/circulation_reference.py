"""Outside-reference circulation diagnostics; no production forcing or tuning.

Reuse the constrained, provenance-checked NCEP ASCII reader from the V10 lab.
All new geometry/aggregation is for the production model's projected grids.
"""
from pathlib import Path
import json
import ssl
import urllib.request

import numpy as np
from experiments import v10_forcing_audit as old
from rotclimate import earth
from scripts.local_benchmark_protocol import file_hash, write_json

VARIABLES = ('uwnd', 'vwnd', 'shum', 'hgt')


def acquire(root, plan, *, fetch=False):
    """Read verified old subsets and atomically acquire only new regional boxes."""
    root = Path(root)
    original = root/'data/v10_atmosphere'
    cache = root/'data/cache/circulation_reference_20261026'
    saved_path = cache/'downloads.json'
    original_records = json.loads((original/'downloads.json').read_text())
    saved = json.loads(saved_path.read_text()) if saved_path.exists() else {}
    texts, sources = {}, {}
    boxes = {**{n: old.BOXES[n] for n in plan['regions'] if n in old.BOXES},
             **plan['new_reference_boxes']}
    for var in VARIABLES:
        entries = [(f'{var}.das', old.BASE+f'{var}.mon.1981-2010.ltm.nc.das', None)]
        for region in plan['regions']:
            for index, box in enumerate(boxes[region]):
                y0, y1, x0, x1 = box
                query = f'{var}[0:1:11][0:1:{old.VARIABLES[var]-1}][{y0}:1:{y1}][{x0}:1:{x1}]'
                entries.append((f'{var}_{region}_{index}.ascii',
                    old.BASE+f'{var}.mon.1981-2010.ltm.nc.ascii?'+query, box))
        for name, url, box in entries:
            legacy = name in original_records
            path = (original if legacy else cache)/name
            records = original_records if legacy else saved
            if path.exists():
                if name not in records or records[name]['url'] != url or records[name]['sha256'] != file_hash(path):
                    raise ValueError('Reference provenance changed: '+str(path))
                payload = path.read_text()
            else:
                if not fetch or legacy:
                    raise ValueError('Reference missing; explicitly acquire with --fetch: '+str(path))
                print('Fetching NOAA regional reference: '+name, flush=True)
                request = urllib.request.Request(url, headers={'User-Agent': 'rotclimate-circulation-audit/1.0'})
                with urllib.request.urlopen(request, timeout=45, context=ssl.create_default_context()) as response:
                    binary = response.read(4*1024*1024+1)
                if len(binary) > 4*1024*1024:
                    raise ValueError('Oversized reference response')
                payload = binary.decode('utf-8')
                if box is None:
                    old.metadata(payload, var)
                else:
                    old.validate_subset(old.parse_ascii(payload, var), box, old.VARIABLES[var])
                cache.mkdir(parents=True, exist_ok=True)
                temporary = path.with_suffix('.tmp')
                temporary.write_text(payload); temporary.replace(path)
                saved[name] = dict(url=url, sha256=file_hash(path), bytes=path.stat().st_size)
                write_json(saved_path, saved)
            texts[name] = payload
            sources[str(path.relative_to(root))] = records.get(name, saved.get(name))
    fields = {}
    for var in VARIABLES:
        units = old.metadata(texts[f'{var}.das'], var)
        for region in plan['regions']:
            pieces = []
            for index, box in enumerate(boxes[region]):
                field = old.parse_ascii(texts[f'{var}_{region}_{index}.ascii'], var)
                old.validate_subset(field, box, old.VARIABLES[var])
                pieces.append(old.normalize(field, var, units))
            first = pieces[0]
            for other in pieces[1:]:
                for axis in ('pressure_hpa', 'latitude', 'time'):
                    if not np.array_equal(getattr(first, axis), getattr(other, axis)):
                        raise ValueError('Inconsistent split-grid axes')
            longitude = np.concatenate([f.longitude for f in pieces])
            order = np.argsort(longitude)
            fields[region, var] = old.Field(np.concatenate([f.values for f in pieces], axis=-1)[..., order],
                first.pressure_hpa, first.latitude, longitude[order], first.time)
    return fields, sources


def projection_jacobian(latitude, longitude, lat0, lon0):
    """Map physical east/north displacement to projected right/up displacement.

    The azimuthal equidistant projection is not conformal: normalizing its
    derivative vectors or applying only a rotation would lose metric factors.
    """
    latitude, longitude = np.broadcast_arrays(latitude, longitude)
    if (not np.isfinite(latitude).all() or not np.isfinite(longitude).all()
            or (np.abs(latitude) >= 89).any()):
        raise ValueError('Need finite nonpolar coordinates')
    step = 1e-4
    east = step/np.cos(np.radians(latitude))
    distance = earth.R_EARTH_KM*np.radians(step)*2
    xp, yp = earth.forward(latitude, longitude+east, lat0, lon0)
    xm, ym = earth.forward(latitude, longitude-east, lat0, lon0)
    ex, ey = (xp-xm)/distance, (yp-ym)/distance
    xp, yp = earth.forward(latitude+step, longitude, lat0, lon0)
    xm, ym = earth.forward(latitude-step, longitude, lat0, lon0)
    nx, ny = (xp-xm)/distance, (yp-ym)/distance
    determinant = ex*ny-nx*ey
    if not np.isfinite(determinant).all() or (determinant <= 0).any():
        raise ValueError('Singular or reversed projection')
    return ex, ey, nx, ny, determinant


def geographic_wind(u, v, geometry, *, mirrored=False):
    ex, ey, nx, ny, determinant = geometry
    north_map = -v if mirrored else v
    return (ny*u-nx*north_map)/determinant, (-ey*u+ex*north_map)/determinant


def column_targets(fields):
    """Matched native-grid pressure vectors and monthly-mean partial q-column."""
    base = fields['shum']
    for var, field in fields.items():
        for axis in ('latitude', 'longitude', 'time'):
            if not np.array_equal(getattr(base, axis), getattr(field, axis)):
                raise ValueError('Reference variables have unmatched horizontal/time axes')
    pressure = base.pressure_hpa
    if not np.array_equal(pressure, [1000, 925, 850, 700, 600, 500, 400, 300]):
        raise ValueError('Unexpected humidity pressure levels')
    level = lambda var, p: fields[var].values[:, list(fields[var].pressure_hpa).index(p)]
    targets = {str(p): np.stack([level('uwnd', p), level('vwnd', p)], axis=1) for p in (925, 850)}
    # The legacy normalizer returns mixing ratio r. Recover specific humidity q.
    ratio = base.values[:, 1:]
    q = ratio/(1+ratio)
    dp = pressure[1:][::-1]*100
    integrate = lambda a: np.trapezoid(a[:, ::-1], x=dp, axis=1)
    water = integrate(q)/9.80665
    if not np.isfinite(q).all() or (water <= 0).any():
        raise ValueError('Missing/nonpositive partial-column humidity')
    components = []
    for var in ('uwnd', 'vwnd'):
        wind = np.stack([level(var, p) for p in pressure[1:]], axis=1)
        components.append(integrate(q*wind)/(water*9.80665))
    targets['q925_300'] = np.stack(components, axis=1)
    return targets, water, level('hgt', 925)


def native_aggregation(latitude, longitude, area, inmap, land, terrain, field, h925):
    """Area footprint assignment; no interpolated replicas in the skill count."""
    dy = np.abs(field.latitude[:, None, None]-latitude)
    dx = np.abs((field.longitude[:, None, None]-longitude+180)%360-180)
    iy, ix = dy.argmin(0), dx.argmin(0)
    covered = (dy.min(0) <= 1.25) & (dx.min(0) <= 1.25)
    ids = iy*len(field.longitude)+ix
    count = len(field.latitude)*len(field.longitude)
    weights = np.where(inmap & covered, area, 0)
    total = np.bincount(ids.ravel(), weights=weights.ravel(), minlength=count)
    land_area = np.bincount(ids.ravel(), weights=(weights*land).ravel(), minlength=count)
    native_area = (earth.R_EARTH_KM**2*np.radians(2.5)*
        (np.sin(np.radians(field.latitude+1.25))-np.sin(np.radians(field.latitude-1.25))))
    native_area = np.repeat(native_area, len(field.longitude))
    maximum = np.full(count, -np.inf)
    np.maximum.at(maximum, ids[weights > 0], terrain[weights > 0])
    fraction = np.divide(land_area, total, out=np.zeros(count), where=total > 0)
    lowland = (h925.reshape(12, -1).min(0) > np.maximum(maximum, 0))
    valid = (total/native_area >= .8) & lowland
    masks = dict(land=valid & (fraction >= .8), ocean=valid & (fraction <= .2))
    def aggregate(values):
        values = np.asarray(values)
        shape = values.shape[:-2]
        result = np.stack([np.bincount(ids.ravel(), weights=(v*weights).ravel(), minlength=count)
                           for v in values.reshape((-1,)+ids.shape)])
        result = np.divide(result, total, out=np.zeros_like(result), where=total > 0)
        return result.reshape(shape+(count,))
    diagnostics = dict(native_cells=int(valid.sum()), covered_native_cells=int((total/native_area >= .8).sum()),
        mixed_excluded=int((valid & (fraction > .2) & (fraction < .8)).sum()),
        land_cells=int(masks['land'].sum()), ocean_cells=int(masks['ocean'].sum()))
    return aggregate, masks, total, diagnostics


def vector_scores(model, reference, area, month_days):
    """True-area and actual-month weighted paired monthly vector differences."""
    model, reference = np.asarray(model), np.asarray(reference)
    if model.shape != reference.shape or model.ndim != 3 or model.shape[:2] != (12, 2):
        raise ValueError('Expected matched12 x2 x native-cell vector arrays')
    if not np.isfinite(model).all() or not np.isfinite(reference).all() or not len(area) or (np.asarray(area) <= 0).any():
        raise ValueError('Need positive area and finite paired vectors')
    weights = np.asarray(month_days)[:, None]*np.asarray(area)[None]
    weights = weights/weights.sum()
    difference = model-reference
    speed = np.hypot(model[:, 0], model[:, 1])
    ref_speed = np.hypot(reference[:, 0], reference[:, 1])
    direction_valid = (speed >= 1) & (ref_speed >= 1)
    direction_weight = weights*direction_valid
    cosine = np.sum(model*reference, axis=1)/np.maximum(speed*ref_speed, 1e-30)
    mean = lambda a: np.sum(a*weights)
    return dict(native_cells=len(area), area_km2=float(np.sum(area)),
        vector_rmse_ms=float(np.sqrt(mean(np.sum(difference**2, axis=1)))),
        mean_vector_error_ms=float(mean(np.hypot(difference[:, 0], difference[:, 1]))),
        east_bias_ms=float(mean(difference[:, 0])), north_bias_ms=float(mean(difference[:, 1])),
        model_mean_vector_speed_ms=float(mean(speed)), reference_mean_vector_speed_ms=float(mean(ref_speed)),
        direction_weight_fraction=float(direction_weight.sum()),
        direction_cosine=None if not direction_weight.any() else float(np.sum(direction_weight*cosine)/direction_weight.sum()),
        monthly_model=np.average(model, axis=2, weights=area).tolist(),
        monthly_reference=np.average(reference, axis=2, weights=area).tolist())


def diagnose_model(case, params, model, result, reference):
    """The fixed native-grid diagnostic, reusable inside a later physics pilot.

    Requires traced cells to contain every interior domain cell in np.nonzero
    order. Only fully covered inmap native footprints contribute to scores.
    """
    from scripts.earth_calendar import observation_weights
    from rotclimate.numerics import matrix_product
    g = case.grid
    spec = earth.REGIONS[case.name]
    mirrored = spec['lat0'] < 0
    latitude = -g.lat if mirrored else g.lat
    geometry = projection_jacobian(latitude, case.lon, spec['lat0'], spec['lon0'])
    weights, durations, order = observation_weights(result.days, mirrored=mirrored)
    fields = {var: reference[case.name, var] for var in VARIABLES}
    targets, water, height = column_targets(fields)
    targets = {key: value[order].reshape(12, 2, -1) for key, value in targets.items()}
    area = g.cell_km**2/geometry[-1]
    interior = np.ones_like(g.land)
    interior[[0, -1], :] = False; interior[:, [0, -1]] = False
    if not all(np.array_equal(a, b) for a, b in zip(model.trace_cells, np.nonzero(interior))):
        raise ValueError('Circulation pilot needs the full ordered interior trace')
    aggregate, masks, native_area, coverage = native_aggregation(latitude, case.lon, area,
        g.inmap & interior, g.land, g.elev, fields['shum'], height)
    components = []
    for key in ('moisture_u', 'moisture_v'):
        full = np.zeros((len(result.days),)+g.land.shape)
        full[:, interior] = np.stack([step[key] for step in model.trace])
        components.append(full)
    east, north = geographic_wind(*components, geometry, mirrored=mirrored)
    native = aggregate(np.stack([matrix_product(weights, value.reshape(len(result.days), -1)).reshape((12,)+g.land.shape)
                                for value in (east, north)], axis=1))
    scores = {target: {kind: None if not selected.any() else vector_scores(native[:, :, selected], values[:, :, selected],
        native_area[selected], durations) for kind, selected in masks.items()} for target, values in targets.items()}
    saved = dict(circulation_model=native, circulation_area=native_area,
        **{'circulation_mask_'+kind: mask for kind, mask in masks.items()},
        **{'circulation_reference_'+key: value for key, value in targets.items()})
    return dict(scores=scores, coverage=coverage, original_month=order.tolist()), saved
