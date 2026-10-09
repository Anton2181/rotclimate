"""The 2-D seasonal climate model.

One model year = 73 five-day weeks.  For every week:

1. **Radiation / zonal climate** - the planet-wide EBM (ebm.py) gives the
   sea-surface temperature and the "deep continental" temperature at every
   latitude for that day, for the chosen axial tilt.
2. **Sea surface** - boundary currents warm or cool coasts (which side
   depends on the spin direction), enclosed seas get continental swings.
3. **Winds** - a three-cell circulation whose belts (ITCZ, subtropical
   highs, storm track) migrate with the seasons, plus thermally driven winds
   from land/sea temperature contrasts (monsoons, winter highs), turned by
   Coriolis (sign flips for retrograde spin) and slowed over mountains.
4. **Air temperature** - air masses are advected by the wind and relax to
   the local surface (sea or land) temperature; then cooled with height.
5. **Moisture** - precipitable water evaporates from warm seas, is carried
   by the wind, re-evaporates from wet land, and rains out according to
   relative humidity, convergence (ITCZ, monsoon lows), the storm track,
   subtropical subsidence and forced ascent over mountains.
6. **Snow** - accumulates when cold, melts by degree-days.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy import ndimage as ndi

from .config import Params
from .ebm import ZonalClimate
from .geography import Grid, build_grid
from .solver import AdvectionSolver

DAY = 86400.0


def w_sat(T):
    """Saturated precipitable water [mm] for a column with surface temp T [C]."""
    T = np.maximum(T, -45.0)
    es = 6.112 * np.exp(17.67 * T / (T + 243.5))            # hPa
    rho_v = es * 100.0 / (461.5 * (T + 273.15))             # kg m-3
    return rho_v * 2200.0                                    # vapour scale height


@dataclass
class Result:
    params: Params
    grid: Grid
    days: np.ndarray        # [nt] day-of-year (0-based) at step centre
    T: np.ndarray           # [nt, ny, nx] surface air temperature (C)
    Tsl: np.ndarray         # sea-level-equivalent temperature (C)
    P: np.ndarray           # precipitation (mm / day)
    W: np.ndarray           # precipitable water (mm)
    u: np.ndarray           # eastward wind (m/s)
    v: np.ndarray           # northward wind (m/s)
    snow: np.ndarray        # snow water equivalent (mm)
    E: np.ndarray           # evaporation (mm / day)

    @property
    def nt(self):
        return len(self.days)


class ClimateModel:
    def __init__(self, params: Params):
        self.p = params
        self.g = build_grid(params)
        self.z = ZonalClimate(params)
        g = self.g
        self.solver = AdvectionSolver(g.ny, g.nx, g.dx_m)
        self._static_fields()

    # ------------------------------------------------------------------ static
    def _static_fields(self):
        g, p = self.g, self.p
        dx = g.dx_m
        land = g.land.astype(float)
        cells_per_100km = 100.0 / g.cell_km
        # which side of a landmass an ocean cell lies on: >0 => land to the east
        # (a continent's WEST coast), <0 => land to the west (EAST coast)
        Ls = ndi.gaussian_filter(land, 2.5 * cells_per_100km)
        gx = np.gradient(Ls, axis=1) * cells_per_100km
        self.side = np.clip(gx / 0.08, -1, 1) * (~g.land)
        self.side = ndi.gaussian_filter(self.side, 1.0 * cells_per_100km)
        # broad "which side of the ocean basin" field over land AND sea: >0 on
        # and off continents' west coasts, <0 on and off their east coasts
        Lb = ndi.gaussian_filter(land, 4.0 * cells_per_100km)
        gb = ndi.gaussian_filter(np.gradient(Lb, axis=1) * cells_per_100km, 2.0 * cells_per_100km)
        self.basin_side = np.clip(gb / max(np.abs(gb).max(), 1e-9) * 2.0, -1, 1)
        # enclosure of seas (fraction of land within ~400 km)
        self.enclosure = np.clip((ndi.gaussian_filter(land, 4 * cells_per_100km) - 0.15) / 0.6, 0, 1)
        # small water bodies (lakes, narrow bays): mostly land within ~120 km
        self.lakeness = np.clip((ndi.gaussian_filter(land, 1.2 * cells_per_100km) - 0.35) / 0.5, 0, 1) * (~g.land)
        # terrain slopes (m/m), east and north components, on a smoothed surface
        hs = ndi.gaussian_filter(g.elev, 0.5 * cells_per_100km)
        self.dhdx = np.gradient(hs, axis=1) / dx
        self.dhdy = -np.gradient(hs, axis=0) / dx
        # wind slow-down over high/rough ground
        # resolution-independent: highest ground within ~28 km (one calibration cell)
        emax = ndi.maximum_filter(g.elev_max, size=max(1, int(round(28.0 / g.cell_km))))
        self.drag = 1.0 / (1.0 + p.terrain_drag * (emax / 1000.0) ** 2)
        self.conv_sigma = 28.0 / g.cell_km
        self.lat = g.lat
        self.col_sigma = 300.0 / g.cell_km

    # ------------------------------------------------------------------ helpers
    def season_index(self, day, lag=30.0):
        """+1 at (lagged) mid-summer, -1 at mid-winter."""
        p = self.p
        return -np.cos(2 * np.pi * (day - p.winter_solstice_day - lag) / p.year_days)

    def zonal_wind(self, s):
        p, lat = self.p, self.lat
        phi_i = p.itcz_mean + p.itcz_shift * s
        phi_h = p.hadley_edge + p.hadley_shift * s
        phi_p = phi_h + 30.0
        u = np.zeros_like(lat)
        v = np.zeros_like(lat)
        # northern trades
        m = (lat >= phi_i) & (lat < phi_h)
        xi = (lat - phi_i) / (phi_h - phi_i)
        u = np.where(m, -p.trade_speed * np.sin(np.pi * xi), u)
        v = np.where(m, -0.35 * p.trade_speed * np.sin(np.pi * xi), v)
        # southern trades (only reached if the padding goes that far south)
        phi_hs = -(p.hadley_edge - p.hadley_shift * s)
        m = (lat < phi_i) & (lat > phi_hs)
        xi = (phi_i - lat) / (phi_i - phi_hs)
        u = np.where(m, -p.trade_speed * np.sin(np.pi * xi), u)
        v = np.where(m, 0.35 * p.trade_speed * np.sin(np.pi * xi), v)
        # westerlies (stronger in winter)
        m = (lat >= phi_h) & (lat < phi_p)
        xi = (lat - phi_h) / (phi_p - phi_h)
        uw = p.westerly_speed * (1 - 0.25 * s)
        u = np.where(m, uw * np.sin(np.pi * xi), u)
        v = np.where(m, 0.15 * uw * np.sin(np.pi * xi), v)
        # polar easterlies
        m = lat >= phi_p
        xi = np.clip((lat - phi_p) / 30.0, 0, 1)
        u = np.where(m, -p.polar_speed * np.sin(np.pi * xi), u)
        v = np.where(m, -0.3 * p.polar_speed * np.sin(np.pi * xi), v)
        if p.retrograde:
            u = -u
        return u, v, phi_i, phi_h

    def thermal_wind(self, T_anom):
        """Friction-turned geostrophic wind around thermal highs and lows."""
        p, g = self.p, self.g
        sig = p.monsoon_scale_km / g.cell_km
        Ta = ndi.gaussian_filter(T_anom, sig, mode="nearest")
        gx = np.gradient(Ta, axis=1) / g.dx_m          # toward warm = toward low pressure
        gy = -np.gradient(Ta, axis=0) / g.dx_m
        k = p.monsoon_strength * 3.0e5
        a = np.deg2rad(90.0 - p.cross_isobar_deg) * np.clip(np.abs(self.lat) / 12.0, 0, 1)
        if p.retrograde:
            a = -a
        ca, sa = np.cos(a), np.sin(a)
        u = k * (gx * ca + gy * sa)                       # clockwise turn (NH prograde)
        v = k * (-gx * sa + gy * ca)
        return u, v

    def sst(self, day, To, Tl):
        p = self.p
        lat = self.lat
        # boundary currents: on a prograde planet the west coasts of continents
        # get cold currents in the subtropics and warm ones poleward of ~45 deg
        band = np.cos(np.pi * (np.clip(lat, 10, 75) - 15.0) / 60.0)
        sign = 1.0 if p.retrograde else -1.0
        cur = sign * p.current_strength * self.side * band
        sst = To + cur + self.enclosure * p.inland_sea_warming * 0.1 * (Tl - To)
        if p.lake_coupling > 0:     # physics v4: lakes / small seas follow the land
            sst = sst + p.lake_coupling * self.lakeness * (Tl - sst)
            sst = np.maximum(sst, -1.8)          # sea water freezes, ice insulates
        return sst

    # ------------------------------------------------------------------ run
    def run(self, steps: int | None = None, spinup: int = 8, progress=None) -> Result:
        p, g = self.p, self.g
        nt = steps or p.steps_per_year
        days = (np.arange(nt) + 0.5) * p.year_days / nt
        shape = (nt, g.ny, g.nx)
        out = {k: np.zeros(shape, np.float32) for k in ("T", "Tsl", "P", "W", "u", "v", "E")}
        land = g.land
        ocean = ~land
        lat = self.lat
        h_km = g.elev / 1000.0
        dx = g.dx_m

        tau = np.where(land, p.land_tau_days, p.ocean_tau_days) * DAY
        lamT = 1.0 / tau
        T_prev = None
        W_prev = None
        soilP = np.full(lat.shape, 1.5)
        self.t_iterations = []
        dt_days = p.year_days / nt
        spinup = max(spinup, int(round(117.0 / dt_days)))      # ~4 months whatever the step
        soil_keep = np.exp(-dt_days / p.soil_memory_days) if p.soil_memory_days > 0 else 0.75
        order = list(range(nt - spinup, nt)) + list(range(nt))
        for n, k in enumerate(order):
            d = days[k]
            s = self.season_index(d)
            Tl = self.z.land(lat, d) + p.land_offset
            if p.land_amplitude != 1.0:      # v4: continental seasonality
                Tl_mean = self.z.land_annual(lat) + p.land_offset
                Tl = Tl_mean + p.land_amplitude * (Tl - Tl_mean)
            To = self.z.ocean(lat, d) + p.sst_offset
            Tz = self.z.zonal(lat, d)
            SST = self.sst(d, To, Tl)
            T_eq = np.where(land, Tl, SST)

            # winds and temperature depend on temperature: iterate within the
            # step (t_iters > 1) instead of lagging one step behind
            T_ref = T_prev if T_prev is not None else T_eq
            for _it in range(max(1, p.t_iters)):
                # ---- winds
                u0, v0, phi_i, phi_h = self.zonal_wind(s)
                T_anom = T_ref - Tz
                ut, vt = self.thermal_wind(T_anom)
                u = (u0 + ut) * self.drag
                v = (v0 + vt) * self.drag

                # ---- temperature (sea-level equivalent), then lapse rate
                # transient eddies (storms) mix heat and moisture between land and
                # sea regardless of the mean wind; modelled as exchange with the
                # surroundings (Gaussian of radius eddy_scale_km) at a rate that
                # peaks in the storm track
                storm = np.exp(-((lat - (phi_h + 13.0)) / p.storm_width) ** 2) * (1 - 0.3 * s)
                if p.storm_asym > 0:     # v5: storms breed off the warm-current coasts
                    side = (1.0 if p.retrograde else -1.0) * self.basin_side
                    storm = storm * np.clip(1.0 + p.storm_asym * side, 0.15, 2.0)
                    # ... and reach further equatorward there
                    shift = p.storm_reach * np.clip(side, 0, 1)
                    storm = np.maximum(storm, np.exp(-((lat - (phi_h + 13.0 - shift)) / p.storm_width) ** 2)
                                       * (1 - 0.3 * s) * np.clip(side, 0, 1) * p.storm_asym)
                eddy = p.eddy_rate * (0.15 + storm) / DAY
                sigE = p.eddy_scale_km / g.cell_km
                if p.eddy_rate > 0:
                    Tmix = ndi.gaussian_filter(T_ref, sigE, mode="nearest")
                    Tsl = self.solver.solve(u, v, p.heat_diffusion, lamT + eddy,
                                            lamT * T_eq + eddy * Tmix, T_eq, guess=T_ref if _it else T_prev)
                else:
                    Tsl = self.solver.solve(u, v, p.heat_diffusion, lamT, lamT * T_eq, T_eq, guess=T_ref if _it else T_prev)
                done = _it > 0 and float(np.abs(Tsl - T_ref).max()) < 0.05
                T_ref = Tsl
                if done:
                    break
            self.t_iterations.append(_it + 1)
            T = Tsl - p.lapse_rate * h_km

            # ---- moisture
            # saturation is set by the temperature of the whole air column,
            # which is smoother than the surface (boundary-layer) temperature
            T_col = (0.4 * np.where(land, Tsl, SST)
                     + 0.6 * ndi.gaussian_filter(Tsl, self.col_sigma, mode="nearest"))
            if p.eddy_rate > 0:      # physics v3
                # the column over high ground is colder (lapse rate) but the
                # low-level moisture that cannot climb is diverted around the
                # mountain rather than squeezed out: compare like with like
                Ws = w_sat(T_col - 0.5 * p.lapse_rate * h_km)
            else:
                Ws = w_sat(T_col - p.lapse_rate * h_km) * np.exp(-h_km / 6.0)
            W_ocean = p.ocean_rh * w_sat(SST)
            div = (np.gradient(u, axis=1) - np.gradient(v, axis=0)) / dx
            conv = np.clip(-ndi.gaussian_filter(div, self.conv_sigma) / 2e-6, 0, 3)
            up = np.clip((u * self.dhdx + v * self.dhdy) / 0.05, 0, 4)
            sub = np.exp(-((lat - phi_h) / 6.0) ** 2)
            # subtropical highs sink hardest over the eastern side of ocean
            # basins on a prograde planet (dry west coasts: California,
            # Sahara coast); the asymmetry flips for retrograde spin
            asym = (-1.0 if p.retrograde else 1.0) * p.subsidence_asym * self.basin_side
            sub = sub * np.clip(1.0 + asym, 0.0, 2.0)
            A_dyn = (1 + p.storm_track * storm + p.convective * conv + p.orographic * up)
            A_dyn = A_dyn * np.clip(1 - p.subsidence * sub, 0.03, 1)
            lamE = np.where(ocean, 1.0 / (p.evap_tau_days * DAY), 0.0)
            bnd = np.where(ocean, W_ocean, 0.5 * Ws)
            W = W_prev if W_prev is not None else bnd
            energy = np.clip((T + 5.0) / 20.0, 0, 1)
            E_land = np.where(land, p.land_recycling * soilP * energy, 0.0) / DAY
            # v6: hot, moist low-level air is convectively unstable, so it rains
            # more efficiently than relative humidity alone suggests (gated by
            # moisture, so hot deserts stay dry)
            if p.instability > 0:
                moist = np.clip((W / np.maximum(Ws, 1e-6) - 0.3) / 0.3, 0, 1) if W_prev is not None else 0.0
                instab = 1.0 + p.instability * np.clip((T - 22.0) / 8.0, 0, 1.5) * moist
            else:
                instab = 1.0
            for _ in range(p.picard_iters):
                RH = W / Ws
                g_rh = np.clip((RH - p.rh_threshold) / (1 - p.rh_threshold), 0, 2) ** 1.5
                lamP = A_dyn * g_rh * instab / (p.precip_tau_days * DAY)
                lamP = lamP + np.maximum(RH - 1.0, 0) / RH / DAY
                if p.eddy_rate > 0:
                    Wmix = ndi.gaussian_filter(W, sigE, mode="nearest")
                    eq = eddy * np.exp(-h_km / 2.5)     # eddies carry vapour low down
                    W_new = self.solver.solve(u, v, p.moisture_diffusion, lamE + lamP + eq,
                                              lamE * W_ocean + E_land + eq * Wmix, bnd, guess=W)
                else:
                    W_new = self.solver.solve(u, v, p.moisture_diffusion, lamE + lamP,
                                              lamE * W_ocean + E_land, bnd, guess=W)
                W = 0.5 * (W + np.maximum(W_new, 0))
            RH = W / Ws
            g_rh = np.clip((RH - p.rh_threshold) / (1 - p.rh_threshold), 0, 2) ** 1.5
            lamP = A_dyn * g_rh * instab / (p.precip_tau_days * DAY) + np.maximum(RH - 1.0, 0) / RH / DAY
            P = lamP * W * DAY
            E = np.where(ocean, lamE * (W_ocean - W) * DAY, E_land * DAY)
            soilP = soil_keep * soilP + (1 - soil_keep) * P

            T_prev, W_prev = Tsl, W
            if n >= spinup:
                for key, val in (("T", T), ("Tsl", Tsl), ("P", P), ("W", W), ("u", u), ("v", v), ("E", E)):
                    out[key][k] = val
            if progress:
                progress(n + 1, len(order))

        snow = snowpack(out["T"], out["P"], p.year_days / nt)
        return Result(params=p, grid=g, days=days, snow=snow, **out)


def snowpack(T, P, step_days, years=3):
    """Degree-day snow model run to a periodic state."""
    nt = T.shape[0]
    swe = np.zeros(T.shape[1:], np.float32)
    out = np.zeros_like(T)
    for _ in range(years):
        for k in range(nt):
            frac = np.clip((1.5 - T[k]) / 3.0, 0, 1)
            swe += frac * P[k] * step_days
            swe -= np.minimum(swe, 3.5 * np.maximum(T[k], 0) * step_days)
            swe = np.minimum(swe, 3000.0)
            out[k] = swe
    return out
