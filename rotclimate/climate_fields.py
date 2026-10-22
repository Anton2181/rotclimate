"""Temperature corrections shared by the solver and all climate exports."""
import numpy as np


def lapse_at_days(params, days):
    """Near-surface lapse rate (K/km), with the circulation's seasonal phase."""
    days = np.asarray(days, dtype=float)
    season = -np.cos(2 * np.pi * (days - params.winter_solstice_day
                                - params.circulation_lag_days) / params.year_days)
    return params.lapse_rate * (1 + params.lapse_seasonal * season)
