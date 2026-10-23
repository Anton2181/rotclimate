"""Published biophysical components and explicit c.200 AD settlement scenarios.

FAO-style crop capacity is inherited from the Harvest model. Malaria implements
Mordecai et al. (2013), equation 2 and Table 2, using a fixed normalization.
The population composite is a scenario model, not HYDE or GLUES reproduced.
"""
from functools import lru_cache
import json
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]


@lru_cache(maxsize=1)
def specification():
    return json.loads((ROOT/'data/harvest_model.json').read_text())


def trait(temperature, parameters):
    t = np.asarray(temperature, dtype=float)
    if parameters['form'] == 'briere':
        return (parameters['c'] * np.maximum(t, 0) * np.maximum(t-parameters['minimum'], 0)
                * np.sqrt(np.maximum(parameters['maximum']-t, 0)))
    return parameters['q']*t*t + parameters['r']*t + parameters['s']


def thermal_r0(temperature):
    """Temperature-dependent part of R0; human density/recovery cancel in normalization."""
    t = np.asarray(temperature, dtype=float)
    p = specification()['malaria_traits']
    a = trait(t, p['biting'])
    bc = np.clip(trait(t, p['competence_percent'])/100, 0, 1)
    daily = np.clip(trait(t, p['daily_survival']), 1e-12, 1-1e-12)
    # Table 2 gives survival p=exp(-mu): mortality is -log(p), not 1/log(p).
    mu = -np.log(daily)
    pdr = trait(t, p['parasite_development'])
    mdr = trait(t, p['mosquito_development'])
    pea = np.clip(trait(t, p['egg_adult_survival']), 0, 1)
    eggs = np.maximum(trait(t, p['eggs_per_day']), 0)
    result = np.sqrt(a*a*bc*np.exp(-mu/np.maximum(pdr, 1e-30))*eggs*pea*mdr/(mu**3))
    return np.where(np.isfinite(t), result, 0)


@lru_cache(maxsize=1)
def thermal_reference():
    t = np.linspace(0, 45, 4501)
    r = thermal_r0(t)
    return float(r.max()), float(t[r.argmax()])


def malaria_thermal(temperature):
    """Relative physiological suitability, 0–1, with one fixed global optimum."""
    return np.clip(thermal_r0(temperature)/thermal_reference()[0], 0, 1)


def malaria_fields(temperature, precipitation, irrigation):
    """Monthly thermal potential with a rainfall/irrigation moisture scenario."""
    from scripts.land_people import smoothstep
    t, p = np.asarray(temperature), np.asarray(precipitation)
    if t.shape != p.shape or t.shape[0] != 12:
        raise ValueError('Malaria needs matching twelve-month temperature and precipitation')
    spec = specification()
    moisture = np.maximum(smoothstep(p, 0, 80), np.asarray(irrigation)*spec['irrigation_mosquito_water'])
    monthly = malaria_thermal(t)*np.clip(moisture, 0, 1)
    return dict(malaria=monthly.mean(0), malaria_months=(monthly>=spec['malaria_season_threshold']).sum(0))


def biome_factor(codes, factors):
    codes = np.asarray(codes)
    # A coastal analysis cell may contain land while its centre is coded sea.
    # Use the declared outside-diagram fallback, including for forage fractions.
    out = np.full(codes.shape, factors.get('0',1.), dtype=float)
    for key, value in factors.items():
        out[codes == int(key)] = value
    return out


def occupation_reference():
    """Historical analogue quantiles; never use the fitted Han plains as a test."""
    regions = json.loads((ROOT/'data/settlement_reference_regions.json').read_text())
    ratios, evidence = [], []
    for name, region in regions.items():
        if region.get('fitted') or region['capacity_m'] <= 0:
            continue
        lo, hi = region['historical_m']
        ratio = np.sqrt(lo*hi)/region['capacity_m']
        ratios.append(min(1, ratio))
        evidence.append(dict(name=name, ratio=float(ratio), clipped_ratio=float(min(1, ratio)),
                             historical_m=region['historical_m'], source=region['source']))
    if not ratios:
        raise ValueError('No historical analogues available')
    scenarios = {key:float(np.quantile(ratios, q)) for key, q in specification()['occupation_quantiles'].items()}
    return dict(scenarios=scenarios, regions=evidence,
                note='Regional analogue quantiles, not confidence intervals or an independently validated population forecast.')


def harvest_reliability(lgp_days, irrigation, start_days, full_days, power=1.0):
    """Share of the mean crop capacity that the poor years leave: low-input
    farmers live at the harvests of the bad years, and where the growing
    season is short the rain varies most from year to year and dry farming
    fails (herding takes such land over). clip((LGP - start) / (full - start),
    0, 1) ** power, but irrigated land keeps its harvest (irrigation access,
    0-1, beside rivers)."""
    ramp = np.clip((np.asarray(lgp_days, float) - start_days) / max(full_days - start_days, 1e-9), 0, 1) ** power
    return np.maximum(ramp, np.clip(np.nan_to_num(np.asarray(irrigation, float)), 0, 1))


def margin_reliability(mean_temperature, aridity_index, irrigation, cold=None, dry=None):
    """Share of the mean crop capacity that low-input farming keeps on the
    margins: frost and a short frost-free season on cold land
    (clip((T - t0) / (t1 - t0), 0, 1), cold = (t0, t1) in C), failed rains on
    dry land (clip((P/PET - a0) / (a1 - a0), 0, 1), dry = (a0, a1)), irrigated
    land keeping its harvest from the dry factor. None turns a factor off."""
    r = np.ones(np.shape(mean_temperature))
    if cold is not None:
        r = r * np.clip((np.asarray(mean_temperature, float) - cold[0]) / (cold[1] - cold[0]), 0, 1)
    if dry is not None:
        rd = np.clip((np.asarray(aridity_index, float) - dry[0]) / (dry[1] - dry[0]), 0, 1)
        r = r * np.maximum(rd, np.clip(np.nan_to_num(np.asarray(irrigation, float)), 0, 1))
    return r


FOREST_SHARE = {1: 0.5, 3: 1.0, 4: 1.0, 7: 1.0, 9: 1.0}     # rotclimate.biomes codes: savanna half, forests whole


def lore_cores(width_px, height_px, shape):
    """The campaign's old heartlands (data/lore_cores.json) as (row, col) on an analysis grid."""
    spec = json.loads((ROOT/'data/lore_cores.json').read_text())
    return {c['name']: (c['y']*shape[0]/height_px, c['x']*shape[1]/width_px) for c in spec['cores']}


def core_term(land, biome, elevation_m, cell_km, cores_rc, scale_km=800.0, forest_cost=2.0, relief_cost=1.0,
              coarsen=3):
    """exp(-D / scale_km), D the cheapest travel to the nearest core: each km
    costs 1 on open land and at sea, forest_cost in forest, plus relief_cost x
    the local relief in km (the Earth-tested setting of scripts/population_cores.py:
    travel cost forest x2, relief 1/km, sea as land, L 800 km)."""
    from scipy import ndimage as ndi
    from scipy.sparse import coo_matrix
    from scipy.sparse.csgraph import dijkstra
    land = np.asarray(land, bool)
    forest = np.zeros(land.shape)
    for code, share in FOREST_SHARE.items():
        forest[np.asarray(biome) == code] = share
    e = np.nan_to_num(np.asarray(elevation_m, float))
    window = max(3, int(round(27.0/cell_km)) | 1)          # Earth's relief: 3 cells of 5' (~27 km)
    relief = np.clip(ndi.maximum_filter(e, window) - ndi.minimum_filter(e, window), 0, 3000)/1000.0
    c = coarsen
    ny, nx = land.shape[0]//c, land.shape[1]//c
    co = lambda a: a[:ny*c, :nx*c].reshape(ny, c, nx, c).mean((1, 3))
    lf = co(land.astype(float))
    cost = np.where(lf >= 0.5, 1.0+(forest_cost-1.0)*co(forest*land)/np.maximum(lf, 1e-9)
                    +relief_cost*co(relief*land)/np.maximum(lf, 1e-9), 1.0)
    step = cell_km*c
    idx = np.arange(ny*nx).reshape(ny, nx)
    rows, cols, w = [], [], []
    for di, dj in ((0, 1), (1, 0), (1, 1), (1, -1)):
        a = idx[max(0, -di):ny-max(0, di), max(0, -dj):nx-max(0, dj)]
        b = idx[max(0, di):ny-max(0, -di) or None, max(0, dj):nx-max(0, -dj) or None]
        wt = 0.5*(cost.ravel()[a]+cost.ravel()[b])*step*np.hypot(di, dj)
        rows += [a.ravel(), b.ravel()]; cols += [b.ravel(), a.ravel()]; w += [wt.ravel(), wt.ravel()]
    g = coo_matrix((np.concatenate(w), (np.concatenate(rows), np.concatenate(cols))), shape=(ny*nx, ny*nx)).tocsr()
    src = [int(min(r//c, ny-1))*nx+int(min(q//c, nx-1)) for r, q in cores_rc.values()]
    dist = dijkstra(g, indices=src, min_only=True).reshape(ny, nx)
    full = np.repeat(np.repeat(dist, c, 0), c, 1)
    out = np.empty(land.shape)
    out[:ny*c, :nx*c] = full
    out[ny*c:, :] = out[ny*c-1:ny*c, :]
    out[:, nx*c:] = out[:, nx*c-1:nx*c]
    return np.exp(-out/scale_km)


def settlement_fields(crop_capacity, npp, biome, arable, water_distance_km, malaria):
    """Return food components, population before occupation, and settlement index."""
    from scripts.land_people import FARMED_SHARE, NEED_KCAL
    spec = specification(); graze = spec['grazing']
    crop = np.maximum(np.asarray(crop_capacity, float), 0)
    clearance = biome_factor(biome, spec['biome_crop_realization'])
    forage = biome_factor(biome, graze['edible_forage_share'])
    reserved = np.clip(1-np.asarray(arable)*FARMED_SHARE, 0, 1)
    # 1 g dry matter / m2 = 1,000 kg dry matter / km2.
    grazing = (np.maximum(npp, 0)*1000*graze['aboveground_npp_share']*forage
               * graze['sustainable_use']*reserved*graze['human_kcal_per_kg_consumed_forage']/NEED_KCAL)
    access = (spec['river_access_floor']+(1-spec['river_access_floor'])
              * np.exp(-np.maximum(water_distance_km, 0)/spec['river_access_length_km']))
    health = 1-spec['maximum_malaria_penalty']*np.clip(malaria, 0, 1)
    usable = crop*clearance+grazing
    absent = usable*access
    potential = absent*health
    score_absent = 100*usable/(usable+spec['livability_food_reference_per_km2'])*access
    return dict(crop_capacity=crop, pastoral_capacity=grazing, food_capacity=crop+grazing,
                clearance=clearance, access=access, health=health,
                settlement_base=potential, settlement_no_malaria=absent,
                livability=score_absent*health, livability_no_malaria=score_absent)
