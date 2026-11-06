"""Equilibrium cereal yield under a farming regime, vectorised over map cells.

The qualified round-2 soil-fertility state (harvest/soil_fertility.py, selection
output/soil_fertility_round2_20261106/selection.json, Broadbalk 1926-1967 blind
pass) re-expressed for many cells at once on each cell's own 12-bin climatology:
RothC-26.3 carbon, SUNDIAL-style nitrogen (C:N 8.5), one mineral pool, uptake at
r_u x min(1, T/10) within a cumulative demand curve, Burns single-reservoir
leaching, grain = min(kappa x A0, N-limited). Every rule and constant is the
scalar model's, with two declared simplifications for map use:

  * drainage comes from a monthly single-store bucket (TAW of the root zone;
    evapotranspiration = kc x PET, limited by the water held), not the daily
    dual-coefficient ledger; kc 1.3 under crop and 0.8 bare reproduce the daily
    ledger's drainage on Rothamsted's climatology (149 vs 139 mm/yr; 1.0/0.5
    would drain 283);
  * the crop season is the L climate bins that end at the cell's harvest
    boundary (L = 10 for winter wheat at Rothamsted; on map cells 9 for wheat
    and 5 for barley), with the demand curve stretched over the season.

Each cell runs in its own agricultural year starting at its harvest boundary,
so all cells step together through relative bins 0..11. A regime is a repeating
sequence of years: 'crop', 'fallow' (bare) or 'clover'; manure (t FYM/ha) is
applied before sowing in crop years.
"""
from __future__ import annotations

import numpy as np

from harvest.soil_fertility import (CN_BIOHUM, GRAIN_N, K, RESIDUE_C, RESIDUE_CN, STAND_T, co2_ratio, max_tsmd,
                                    BIO_SHARE, DPM_SHARE_PLANT)

FYM_C_PER_T, FYM_N_PER_T = 3.0 / 35.0, 225.0 / 35.0
CLOVER_YEARLY, CLOVER_PLOUGHED = (0.8, 20.0), (2.0, 19.0)
WHEAT_CURVE = np.array([0.02, 0.05, 0.07, 0.09, 0.12, 0.20, 0.40, 0.70, 0.95, 1.00])   # 10 bins, amendment_round2.json
SPRING_CURVE = np.array([0.15, 0.55, 0.90, 1.00])


def stretched_curve(curve, length):
    """Cumulative demand share by the end of each of `length` season bins."""
    x = (np.arange(len(curve)) + 1) / len(curve)
    return np.interp((np.arange(length) + 1) / length, np.concatenate([[0.0], x]), np.concatenate([[0.0], curve]))


def rate_temperature(t):
    t = np.asarray(t, float)
    return np.where(t > -18.27 + 1e-9, 47.91 / (1.0 + np.exp(106.06 / np.maximum(t + 18.27, 1e-9))), 0.0)


def equilibrium_yield(T, P, PET, harvest_bin, A0, *, regime, manure_t=0.0, input_n, uptake_rate, kappa,
                      season_bins, curve, clay=23.4, taw_mm=195.0, water_mm=502.5, years=300, report_years=30,
                      start=None, kc_crop=1.3, kc_bare=0.8, stand_residues=False):
    """Mean grain per cropped hectare and per hectare of the whole rotation over the last
    `report_years` (a multiple of the regime length), per cell.

    T, P, PET: (12, N) climate bins; harvest_bin: (N,) boundary bin 0..11 (the first bin
    after harvest); A0: (N,) existing response, t/ha; season_bins: (N,) or int.
    """
    T, P, PET = (np.asarray(a, float) for a in (T, P, PET))
    n = T.shape[1]
    hb = np.asarray(harvest_bin, int) % 12
    L = np.broadcast_to(np.asarray(season_bins, int), (n,))
    A0 = np.asarray(A0, float)
    seq = list(regime)
    cyc = len(seq)
    if report_years % cyc:
        raise ValueError('report_years must be a multiple of the regime length')
    clay = float(clay)
    mx = max_tsmd(clay); x = co2_ratio(clay); keep = 1.0 / (x + 1.0)
    rows = np.arange(n)
    # climate in agricultural-year order: relative bin k -> calendar bin (hb + k) % 12
    order = (hb[None, :] + np.arange(12)[:, None]) % 12
    Tr, Pr, Er = (np.take_along_axis(a, order, axis=0) for a in (T, P, PET))
    a_temp = rate_temperature(Tr)
    g_up = np.clip(Tr, 0.0, None) / 10.0
    g_up = np.minimum(g_up, 1.0)
    # season masks: vegetated relative bins 12-L .. 11; cumulative demand share per bin
    k_idx = np.arange(12)[:, None]
    in_season = k_idx >= (12 - L[None, :])
    share = np.zeros((12, n))
    for Lv in np.unique(L):
        sel = L == Lv
        c = stretched_curve(curve, int(Lv))
        share[12 - Lv:, sel] = c[:, None]
    target = kappa * A0
    intercept = RESIDUE_C[0] * (np.minimum(1.0, target / STAND_T) if stand_residues else 1.0)
    demand_full = GRAIN_N * target + 1000.0 * (intercept + RESIDUE_C[1] * target) / RESIDUE_CN
    s = start or {}
    dpm = np.full(n, s.get('dpm', 0.12)); rpm = np.full(n, s.get('rpm', 4.5)); bio = np.full(n, s.get('bio', 0.6))
    hum = np.full(n, s.get('hum', 21.3)); dpm_n = np.full(n, s.get('dpm_n', 3.0)); rpm_n = np.full(n, s.get('rpm_n', 112.0))
    tsmd = np.zeros(n); mineral = np.zeros(n); water = np.full(n, taw_mm)
    grain_sum = np.zeros(n); crop_years = 0
    first_report = years - report_years
    for y in range(years):
        kind = seq[y % cyc]
        nxt = seq[(y + 1) % cyc]
        crop_n = np.zeros(n)
        for k in range(12):
            veg = in_season[k] if kind == 'crop' else (np.ones(n, bool) if kind == 'clover' else np.zeros(n, bool))
            # events at the start of the bin
            if kind == 'crop' and manure_t > 0:
                sow = k == (12 - L)                     # first season bin
                if sow.any():
                    c_in = np.where(sow, manure_t * FYM_C_PER_T, 0.0); n_in = np.where(sow, manure_t * FYM_N_PER_T, 0.0)
                    d_, r_, h_ = 0.49 * c_in, 0.49 * c_in, 0.02 * c_in
                    nh = 1000.0 * h_ / CN_BIOHUM; rest = np.maximum(n_in - nh, 0.0)
                    mineral += np.minimum(n_in - nh, 0.0)
                    dpm += d_; rpm += r_; hum += h_
                    dpm_n += rest * 0.5; rpm_n += rest * 0.5
            if kind == 'clover' and k == 9:
                for cc, cn in [CLOVER_YEARLY] + ([CLOVER_PLOUGHED] if nxt != 'clover' else []):
                    dpm += cc * DPM_SHARE_PLANT; rpm += cc * (1 - DPM_SHARE_PLANT)
                    nn = 1000.0 * cc / cn
                    dpm_n += nn * DPM_SHARE_PLANT; rpm_n += nn * (1 - DPM_SHARE_PLANT)
            # topsoil moisture deficit and rate factors (RothC)
            bal = Pr[k] - Er[k]
            limit = np.where(veg, mx, mx / 1.8)
            dry = bal < 0
            tsmd = np.where(dry, np.where(tsmd > limit, np.maximum(tsmd + bal, limit), tsmd), np.minimum(tsmd + bal, 0.0))
            b = np.where(tsmd >= 0.444 * mx, 1.0, 0.2 + 0.8 * (mx - tsmd) / (mx - 0.444 * mx))
            c = np.where(veg, 0.6, 1.0)
            abc = a_temp[k] * b * c
            f = {kk: 1.0 - np.exp(-abc * v / 12.0) for kk, v in K.items()}
            dec_bh = bio * f['bio'] + hum * f['hum']
            dec_d, dec_r = dpm * f['dpm'], rpm * f['rpm']
            n_d, n_r = dpm_n * f['dpm'], rpm_n * f['rpm']
            m0 = 1000.0 * dec_bh / CN_BIOHUM - 1000.0 * keep * dec_bh / CN_BIOHUM
            m1 = m0 + (n_d + n_r) - 1000.0 * keep * (dec_d + dec_r) / CN_BIOHUM
            avail = np.maximum(mineral, 0.0)
            scale = np.where(avail + m1 < 0, np.clip(np.divide(-avail - m0, m1 - m0, out=np.zeros(n), where=(m1 - m0) != 0), 0, 1), 1.0)
            net = m0 + scale * (m1 - m0)
            dd, dr = scale * dec_d, scale * dec_r
            formed = keep * (dec_bh + dd + dr)
            bio = bio - bio * f['bio'] + BIO_SHARE * formed
            hum = hum - hum * f['hum'] + (1.0 - BIO_SHARE) * formed
            dpm -= dd; rpm -= dr; dpm_n -= scale * n_d; rpm_n -= scale * n_r
            mineral += net + input_n / 12.0
            # uptake
            if kind == 'crop':
                cap = demand_full * share[k]
                u = np.where(veg, np.maximum(0.0, np.minimum(cap - crop_n, g_up[k] * uptake_rate * mineral)), 0.0)
                mineral -= u; crop_n += u
            # water bucket and leaching
            kc = np.where(veg, kc_crop, kc_bare)
            stress = np.minimum(1.0, water / (0.45 * taw_mm))
            et = np.minimum(kc * Er[k] * stress, water + Pr[k])
            water = water + Pr[k] - et
            drain = np.maximum(water - taw_mm, 0.0)
            water = np.minimum(water, taw_mm)
            leach = np.where(mineral > 0, mineral * drain / (drain + water_mm), 0.0)
            mineral -= leach
        if kind == 'crop':
            base = 1000.0 * RESIDUE_C[0] / RESIDUE_CN
            per_t = GRAIN_N + 1000.0 * RESIDUE_C[1] / RESIDUE_CN
            linear = np.maximum(0.0, (crop_n - base) / per_t)
            if stand_residues:
                knee = base + per_t * STAND_T
                linear = np.where(crop_n < knee, crop_n * STAND_T / knee, linear)
            grain = np.minimum(linear, kappa * A0)
            rc = RESIDUE_C[0] * (np.minimum(1.0, grain / STAND_T) if stand_residues else 1.0) + RESIDUE_C[1] * grain
            rn = np.maximum(crop_n - GRAIN_N * grain, 0.0)
            dpm += rc * DPM_SHARE_PLANT; rpm += rc * (1 - DPM_SHARE_PLANT)
            dpm_n += rn * DPM_SHARE_PLANT; rpm_n += rn * (1 - DPM_SHARE_PLANT)
            if y >= first_report:
                grain_sum += grain; crop_years += 1
    per_land = grain_sum / report_years
    per_crop = grain_sum / max(crop_years, 1)
    return dict(per_cropped_ha=per_crop, per_rotation_ha=per_land, soc_active=dpm + rpm + bio + hum,
                cropped_share=crop_years / report_years)
