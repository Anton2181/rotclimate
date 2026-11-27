"""Private solar-bound hypothesis for two empirical wetness cooling terms.

C * lambda * delta_T is an implied cooling flux (W/m2) only after choosing
the EBM atmosphere+soil column as the regional effective heat capacity.
This is not a closed evaporation/surface energy budget.
"""
import numpy as np


def solar_wetness_budget(solar, latitude, wet, land, delta_wet, delta_sun,
                        p, capacity, albedo_p2):
    """Share ONE absorbed-shortwave bound; preserve negative (warming) terms."""
    rate = (solar / 480.0) ** p.land_coupling_insolation / (p.land_tau_days * 86400.0)
    if p.dry_coupling > 0:
        rate = rate * (1.0 + p.dry_coupling * (1.0 - wet))
    rate = rate + 1.0 / (p.land_radiative_days * 86400.0)
    conductance = capacity * p.land_heat_capacity * rate
    albedo = .295 + albedo_p2 * .5 * (3.0 * np.sin(np.deg2rad(latitude)) ** 2 - 1.0)
    bound = np.where(land, (1.0 - albedo) * solar, 0.0)
    positive = np.where(land, np.maximum(delta_wet, 0.0) + np.maximum(delta_sun, 0.0), 0.0)
    legacy = conductance * positive
    scale = np.ones_like(legacy)
    np.divide(bound, legacy, out=scale, where=legacy > 0)
    scale = np.minimum(scale, 1.0)
    return dict(scale=scale, rate=rate, conductance=conductance, bound=bound,
                legacy=legacy, applied=legacy * scale,
                delta_wet=delta_wet, delta_sun=delta_sun)


def patched_model(source):
    """Fail closed if source differs; production source is never edited."""
    def replace_once(old, new):
        nonlocal source
        assert source.count(old) == 1, old
        source = source.replace(old, new)
    replace_once('from .ebm import ZonalClimate',
                 'from .ebm import ZonalClimate, C_LAND, ALB_P2\nfrom .wet_energy import solar_wetness_budget\n\nWET_ENERGY_BUDGET = False  # private experiment only')
    old = '                Tl = Tl - p.wet_cooling * wet * np.maximum(Tl - Tl_mean, 0.0)'
    replace_once(old, '''                if WET_ENERGY_BUDGET:
                    assert p.soil_wet_cooling and p.soil_bucket_mm > 0
                    assert p.land_coupling_insolation > 0 and p.wet_sun > 0
                    S_energy = daily_insolation(lat, declination(d, p.tilt, p.winter_solstice_day, p.year_days),
                        p.solar_flux * distance_factor(d, p.eccentricity,
                        p.winter_solstice_day + p.perihelion_after_solstice, p.year_days))
                    dw = p.wet_cooling * wet * np.maximum(Tl - Tl_mean, 0.0)
                    ds = np.where(land, p.wet_sun * (wet - p.wet_sun_ref) * S_energy / LAND_COUPLING_SREF, 0.0)
                    wet_energy = solar_wetness_budget(S_energy, lat, wet, land, dw, ds, p, C_LAND, ALB_P2)
                    Tl = Tl - dw * wet_energy['scale']
                else:
                    Tl = Tl - p.wet_cooling * wet * np.maximum(Tl - Tl_mean, 0.0)''')
    old = '                Tl = Tl - np.where(land, p.wet_sun * (wet_s - p.wet_sun_ref) * S_w / LAND_COUPLING_SREF, 0.0)'
    replace_once(old, '''                if WET_ENERGY_BUDGET:
                    ds = np.where(land, p.wet_sun * (wet_s - p.wet_sun_ref) * S_w / LAND_COUPLING_SREF, 0.0)
                    np.testing.assert_array_equal(ds, wet_energy['delta_sun'])
                    Tl = Tl - np.where(ds > 0, ds * wet_energy['scale'], ds)
                else:
                    Tl = Tl - np.where(land, p.wet_sun * (wet_s - p.wet_sun_ref) * S_w / LAND_COUPLING_SREF, 0.0)''')
    old = '                lamT = np.where(land, lam_land, 1.0 / (p.ocean_tau_days * DAY))'
    replace_once(old, '''                if WET_ENERGY_BUDGET:
                    np.testing.assert_array_equal(lam_land, wet_energy['rate'])
                lamT = np.where(land, lam_land, 1.0 / (p.ocean_tau_days * DAY))''')
    return source
