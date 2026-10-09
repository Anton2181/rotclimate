"""Orbital geometry and top-of-atmosphere insolation."""
from __future__ import annotations

import numpy as np

S0 = 1361.0  # W m-2, solar constant (Earth-like star and distance)


def declination(day, tilt, winter_solstice_day, year_days=365):
    """Solar declination [deg] for the (northern) hemisphere the map sits in."""
    return -tilt * np.cos(2 * np.pi * (np.asarray(day, float) - winter_solstice_day) / year_days)


def distance_factor(day, eccentricity, perihelion_day, year_days=365):
    """(a / r)^2 for a slightly eccentric orbit."""
    m = 2 * np.pi * (np.asarray(day, float) - perihelion_day) / year_days
    return (1 + eccentricity * np.cos(m)) ** 2 / (1 - eccentricity**2) ** 2


def daily_insolation(lat_deg, decl_deg, dist_factor=1.0):
    """Daily-mean TOA insolation [W m-2] (broadcasts over lat & declination)."""
    phi = np.deg2rad(lat_deg)
    dec = np.deg2rad(decl_deg)
    x = np.clip(-np.tan(phi) * np.tan(dec), -1.0, 1.0)
    h0 = np.arccos(x)
    q = S0 / np.pi * dist_factor * (h0 * np.sin(phi) * np.sin(dec) + np.cos(phi) * np.cos(dec) * np.sin(h0))
    return np.maximum(q, 0.0)


def day_length_hours(lat_deg, decl_deg):
    phi = np.deg2rad(lat_deg)
    dec = np.deg2rad(decl_deg)
    x = np.clip(-np.tan(phi) * np.tan(dec), -1.0, 1.0)
    return 24.0 * np.arccos(x) / np.pi


def insolation_table(params, lats, days):
    """Q[day, lat] for the parameter set."""
    dec = declination(days, params.tilt, params.winter_solstice_day, params.year_days)
    df = distance_factor(days, params.eccentricity,
                         params.winter_solstice_day + params.perihelion_after_solstice,
                         params.year_days)
    return daily_insolation(np.asarray(lats)[None, :], dec[:, None], df[:, None])
