"""Explicit climate/resource adapter for the FORGE human kernel.

Miami NPP and assumed grass allocation, fruit decay and annual prey supply
replace the original ORCHIDEE vegetation/herbivore forcing. This adapter is
not a reproduction of that ecosystem model or an observed food inventory.
"""
from pathlib import Path
import json
import numpy as np

ROOT = Path(__file__).resolve().parents[1]


def specification():
    return json.loads((ROOT/'data/foraging_model.json').read_text())


def miami_npp(temperature, precipitation):
    """Annual productivity, g dry matter/m²/year, from twelve equal model bins."""
    t, p = np.asarray(temperature, float), np.asarray(precipitation, float)
    if (t.shape != p.shape or t.ndim < 2 or t.shape[0] != 12
            or not np.isfinite(t).all() or not np.isfinite(p).all() or (p < 0).any()):
        raise ValueError('Need matching finite twelve-month climate and nonnegative precipitation')
    return np.minimum(3000./(1.+np.exp(np.clip(1.315-.119*t.mean(0), -700, 700))),
                      3000.*(-np.expm1(-.000664*p.sum(0))))


def daily_resources(temperature, precipitation, annual_npp, adapter):
    """Return 365 daily plant/prey inputs in kg dry matter/km²/day.

    The daily plant weights preserve the annual edible resource budget exactly.
    Animal resources are one annual stock pulse; the kernel resets/discards
    remaining meat at the annual boundary. Plant decay is a kernel parameter.
    """
    t, p, npp = (np.asarray(a, float) for a in (temperature, precipitation, annual_npp))
    if (t.shape != p.shape or t.ndim < 2 or t.shape[0] != 12 or npp.shape != t.shape[1:]
            or not all(np.isfinite(a).all() for a in (t, p, npp)) or (p < 0).any() or (npp < 0).any()):
        raise ValueError('Need matching finite monthly climate and annual dry-matter NPP')
    grass = float(adapter['grass_npp_fraction'])
    prey_fraction = float(adapter['annual_meat_fraction_of_npp'])
    floor = float(adapter['phenology_temperature_floor_c'])
    span = float(adapter['phenology_temperature_span_c'])
    wet_half = float(adapter['phenology_rain_half_saturation_mm'])
    if (not 0 <= grass <= 1 or not 0 <= prey_fraction <= 1 or span <= 0 or wet_half <= 0
            or not np.isfinite([grass, prey_fraction, floor, span, wet_half]).all()):
        raise ValueError('Invalid explicit resource-adapter assumptions')
    below = np.maximum(.2, (88.3-.0534*p.sum(0))/100.)
    # g/m² -> 1,000 kg/km². These two plant allocation coefficients and
    # rainfall-dependent belowground fraction follow the FORGE supplement.
    plant_annual = npp*1000.*.015*(.065+below*grass)
    meat_annual = npp*1000.*prey_fraction
    monthly = np.clip((t-floor)/span, 0, 1)*p/(p+wet_half)
    positions = (np.arange(365)+.5)*12/365.-.5
    left = np.floor(positions).astype(int); fraction = positions-left
    fraction = fraction.reshape((365,)+(1,)*npp.ndim)
    weights = monthly[left % 12]*(1-fraction)+monthly[(left+1) % 12]*fraction
    normalizer = weights.sum(0)
    fallback = normalizer <= 0
    weights = np.divide(weights, normalizer, out=np.full_like(weights, 1/365.), where=normalizer > 0)
    plant = weights*plant_annual
    meat = np.zeros_like(plant); meat[0] = meat_annual
    np.testing.assert_allclose(plant.sum(0), plant_annual, rtol=2e-14, atol=1e-10)
    return dict(plant_supply=plant, meat_supply=meat,
                annual_plant_kgdm_km2=plant_annual, annual_meat_kgdm_km2=meat_annual,
                phenology_uniform_fallback=fallback)
