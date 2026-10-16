"""Clock handling for future experiments; frozen integrations are unchanged."""
import numpy as np


def step_length(time_s, cfl_limit, forcing_end, month_end):
    values = np.array([time_s, cfl_limit, forcing_end, month_end], float)
    if not np.isfinite(values).all() or cfl_limit <= 0:
        raise ValueError('Nonfinite clock or nonpositive CFL limit.')
    dt = float(min(cfl_limit, forcing_end-time_s, month_end-time_s))
    # A tiny boundary remainder is legal; do not discard time or snap the state.
    if dt <= 0 or time_s+dt <= time_s:
        raise RuntimeError('Integration clock cannot make forward progress.')
    return dt
