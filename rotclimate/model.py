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

from functools import lru_cache

import numpy as np
from scipy import ndimage as ndi

from .astronomy import daily_insolation, declination, distance_factor
from .config import Params
from .ebm import ZonalClimate
from .geography import Grid, build_grid
from .solver import AdvectionSolver
from .temperature import temperature_update, iterate_temperature, TemperatureConvergenceError

DAY = 86400.0


@lru_cache(maxsize=64)
def _gauss_kernel_fft(sigma: float, n: int, radius: int):
    from scipy import fft as sfft

    x = np.arange(-radius, radius + 1, dtype=float)
    k = np.exp(-0.5 * (x / sigma) ** 2)
    k /= k.sum()
    full = np.zeros(n)
    full[: radius + 1] = k[radius:]               # kernel centred on index 0 (circular)
    full[n - radius:] = k[:radius]
    return sfft.rfft(full)


def gauss(a: np.ndarray, sigma: float) -> np.ndarray:
    """Same result as ndi.gaussian_filter(a, sigma, mode="nearest") (truncate
    4), computed by FFT for the wide kernels (300-500 km) used every step,
    which is several times faster than a direct convolution. Edges are
    extended (as mode="nearest") to an FFT-friendly length; the kernel only
    reaches `radius` cells, so the extra extension does not change the result."""
    if sigma < 6.0:
        return ndi.gaussian_filter(a, sigma, mode="nearest")
    from scipy import fft as sfft

    radius = int(4.0 * sigma + 0.5)
    out = np.asarray(a, float)
    for axis in (0, 1):
        n0 = out.shape[axis]
        n = sfft.next_fast_len(n0 + 2 * radius, real=True)
        pad = [(0, 0), (0, 0)]
        pad[axis] = (radius, n - n0 - radius)
        b = np.pad(out, pad, mode="edge")
        kf = _gauss_kernel_fft(round(float(sigma), 9), n, radius)
        shape = [1, 1]
        shape[axis] = -1
        c = sfft.irfft(sfft.rfft(b, axis=axis) * kf.reshape(shape), n=n, axis=axis)
        out = c[radius:radius + n0] if axis == 0 else c[:, radius:radius + n0]
    return out


def w_sat(T):
    """Saturated precipitable water [mm] for a column with surface temp T [C]."""
    T = np.maximum(T, -45.0)
    es = 6.112 * np.exp(17.67 * T / (T + 243.5))            # hPa
    rho_v = es * 100.0 / (461.5 * (T + 273.15))             # kg m-3
    return rho_v * 2200.0                                    # vapour scale height


LAND_COUPLING_SREF = 480.0      # W m-2: summer subtropical sunshine, where land coupling has its fitted strength
LAND_RADIATIVE_DAYS = 30.0      # radiative relaxation of the air over land when the sun is low
UPWELLING_KM = 150.0            # how far offshore upwelled water cools the sea surface
CONTINENTAL_FETCH_DAYS = 4.0     # memory of the land the air has crossed (~1,700 km at 5 m/s)


def enclosed_directions(land, reach_cells, n_dir=16):
    """Share of n_dir compass directions in which a ray from each cell meets
    land within reach_cells (rays leaving the grid count as open)."""
    ny, nx = land.shape
    out = np.zeros((ny, nx))
    steps = max(1, int(np.ceil(reach_cells)))
    for k in range(n_dir):
        th = 2 * np.pi * k / n_dir
        hit = np.zeros((ny, nx), bool)
        for n in range(1, steps + 1):
            di, dj = int(round(-n * np.sin(th))), int(round(n * np.cos(th)))
            shifted = np.zeros((ny, nx), bool)
            ys, yd = (slice(di, ny), slice(0, ny - di)) if di >= 0 else (slice(0, ny + di), slice(-di, ny))
            xs, xd = (slice(dj, nx), slice(0, nx - dj)) if dj >= 0 else (slice(0, nx + dj), slice(-dj, nx))
            shifted[yd, xd] = land[ys, xs]
            hit |= shifted
        out += hit
    return out / n_dir


def eddy_exchange_rate(base_rate, storm, season, contrast=0.):
    """Regional seasonal exchange in 1/s; season +1 summer, -1 winter.

    Contrast scales the whole exchange, including the background floor. Its
    time-mean multiplier is one for a sinusoidal season, but the full annual
    exchange is not conserved because the storm envelope also varies.
    """
    rate = base_rate * (0.15 + storm) / DAY
    return rate if contrast == 0. else rate * (1. - contrast * season)


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
    moisture_budget: dict | None = None  # optional cropped diagnostic terms [nt, map_y, map_x]

    @property
    def nt(self):
        return len(self.days)


class ClimateModel:
    def __init__(self, params: Params, grid=None):
        if not np.isfinite(params.eddy_seasonality) or not 0 <= params.eddy_seasonality < 1:
            raise ValueError('eddy_seasonality must be in [0, 1)')
        if not np.isfinite(params.t_relaxation) or not 0 < params.t_relaxation <= 1:
            raise ValueError('t_relaxation must be in (0, 1]')
        if params.t_adaptive_retries not in (0,1,2):
            raise ValueError('t_adaptive_retries must be 0, 1 or 2')
        if not np.isfinite(params.moisture_relaxation) or not 0 < params.moisture_relaxation <= 1:
            raise ValueError('moisture_relaxation must be in (0, 1]')
        if not np.isfinite(params.moisture_residual_tol) or params.moisture_residual_tol < 0 or params.picard_iters < 1:
            raise ValueError('Moisture tolerance must be nonnegative and picard_iters positive')
        if params.moisture_residual_tol > 0 and params.transport_scheme != 'upwind':
            raise ValueError('Moisture convergence checking currently requires upwind transport')
        if params.moisture_require_convergence and params.moisture_residual_tol == 0:
            raise ValueError('Required moisture convergence needs a positive moisture_residual_tol')
        self.p = params
        self.g = build_grid(params) if grid is None else grid   # grid: e.g. real geography (earth.py)
        self.z = ZonalClimate(params)
        g = self.g
        self.solver = AdvectionSolver(g.ny, g.nx, g.dx_m, scheme=params.transport_scheme)
        self.solver.rtol = params.solver_rtol
        self.solver.max_iter = params.solver_max_iter
        self.solver.require_convergence = params.solver_require_convergence
        self._static_fields()

    # ------------------------------------------------------------------ static
    def _static_fields(self):
        g, p = self.g, self.p
        dx = g.dx_m
        land = g.land.astype(float)
        cells_per_100km = 100.0 / g.cell_km
        th = np.radians(p.north_bearing)

        def d_east(a):
            """Derivative per cell toward true east (the map's right when north is up)."""
            return np.cos(th) * np.gradient(a, axis=1) + np.sin(th) * np.gradient(a, axis=0)
        # which side of a landmass an ocean cell lies on: >0 => land to the east
        # (a continent's WEST coast), <0 => land to the west (EAST coast)
        Ls = ndi.gaussian_filter(land, 2.5 * cells_per_100km)
        gx = d_east(Ls) * cells_per_100km
        self.side = np.clip(gx / 0.08, -1, 1) * (~g.land)
        self.side = ndi.gaussian_filter(self.side, 1.0 * cells_per_100km)
        # broad "which side of the ocean basin" field over land AND sea: >0 on
        # and off continents' west coasts, <0 on and off their east coasts
        Lb = ndi.gaussian_filter(land, 4.0 * cells_per_100km)
        gb = ndi.gaussian_filter(d_east(Lb) * cells_per_100km, 2.0 * cells_per_100km)
        self.basin_side = np.clip(gb / max(np.abs(gb).max(), 1e-9) * 2.0, -1, 1)
        # enclosure of seas (fraction of land within ~400 km)
        self.enclosure = np.clip((ndi.gaussian_filter(land, 4 * cells_per_100km) - 0.15) / 0.6, 0, 1)
        if p.sea_enclosure == "rays":
            # e3: a straight coast has land within 400 km on one side only and
            # is no inland sea (the disc measure warmed the cold-current waters
            # off Chile and California by up to 5 C); count the directions in
            # which land closes the sea within ~1,000 km instead
            self.enclosure = np.clip((enclosed_directions(g.land, 1000.0 / g.cell_km) - 0.55) / 0.35, 0, 1)
        elif p.sea_enclosure != "disc":
            raise ValueError(f"unknown sea_enclosure {p.sea_enclosure!r}")
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
        # coastal upwelling geometry (e1): the offshore direction (map frame,
        # x right / y up) of sea cells near land and how close they are
        Lc = ndi.gaussian_filter(land, 1.0 * cells_per_100km)
        cx, cy = np.gradient(Lc, axis=1), -np.gradient(Lc, axis=0)       # toward land
        norm = np.hypot(cx, cy)
        ok = norm > 1e-3 / max(cells_per_100km, 1e-9)
        self.offshore = (np.where(ok, -cx / np.maximum(norm, 1e-12), 0.0),
                         np.where(ok, -cy / np.maximum(norm, 1e-12), 0.0))
        sea_dist = ndi.distance_transform_edt(~g.land) * g.cell_km
        self.upwelling_weight = np.where(g.land, 0.0, np.exp(-sea_dist / UPWELLING_KM)) * ok
        # e3: ocean basins at the scale of the subtropical highs
        self.ocean_basin = (ndi.gaussian_filter(1.0 - land, p.subtropical_high_scale_km / g.cell_km)
                            if p.subtropical_high > 0 else None)

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
        if p.north_bearing % 360.0:     # true east/north -> map right/up
            th = np.radians(p.north_bearing)
            u, v = u * np.cos(th) + v * np.sin(th), -u * np.sin(th) + v * np.cos(th)
        return u, v, phi_i, phi_h

    def thermal_wind(self, T_anom):
        """Friction-turned geostrophic wind around thermal highs and lows."""
        p, g = self.p, self.g
        sig = p.monsoon_scale_km / g.cell_km
        Ta = gauss(T_anom, sig)
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

    def subtropical_high_wind(self, s, phi_h):
        """e3: the subtropical highs are oceanic cells, not a zonal ridge
        (Rodwell & Hoskins 2001): pressure ~ ocean basin x a band around the
        Hadley edge. Their eastern flanks blow equatorward and onshore along
        west coasts (California, Chile, the Canaries, the Etesians), their
        western flanks poleward along east coasts (Gulf and East Asian summer
        southerlies). Friction-turned geostrophic wind as in thermal_wind;
        `subtropical_high` is about the peak speed in m/s."""
        p, g = self.p, self.g
        band = np.exp(-((self.lat - phi_h) / p.subtropical_high_width) ** 2)
        psi = band * self.ocean_basin * (1.0 + p.subtropical_high_seasonality * s)
        gx = -np.gradient(psi, axis=1) / g.dx_m            # toward low pressure
        gy = np.gradient(psi, axis=0) / g.dx_m
        k = p.subtropical_high * 2.5 * p.subtropical_high_scale_km * 1000.0
        a = np.deg2rad(90.0 - p.cross_isobar_deg) * np.clip(np.abs(self.lat) / 12.0, 0, 1)
        if p.retrograde:
            a = -a
        ca, sa = np.cos(a), np.sin(a)
        return k * (gx * ca + gy * sa), k * (-gx * sa + gy * ca)

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
    def run(self, steps: int | None = None, spinup: int = 8, progress=None,
            diagnose_moisture=False,temperature_retry=None) -> Result:
        p, g = self.p, self.g
        nt = steps or p.steps_per_year
        days = (np.arange(nt) + 0.5) * p.year_days / nt
        shape = (nt, g.ny, g.nx)
        out = {k: np.zeros(shape, np.float32) for k in ("T", "Tsl", "P", "W", "u", "v", "E")}
        budget = None
        if diagnose_moisture:
            if p.transport_scheme != 'upwind':
                raise ValueError('Moisture equation diagnostics currently require upwind transport')
            from .transport import moisture_terms
            cropped_shape = (nt,) + g.target[g.map_slice()].shape
            budget = {key: np.zeros(cropped_shape, np.float32) for key in
                      ('advection', 'diffusion', 'storm_exchange', 'residual', 'absolute_residual')}
        land = g.land
        ocean = ~land
        lat = self.lat
        h_km = g.elev / 1000.0
        dx = g.dx_m

        tau = np.where(land, p.land_tau_days, p.ocean_tau_days) * DAY
        lamT = 1.0 / tau
        T_prev = T_prev2 = None
        W_prev = None
        uv_prev = chi = None
        soilP = np.full(lat.shape, 1.5)
        self.t_iterations = []
        self.t_converged = []
        self.t_update_max = []
        self.t_update_inmap_max = []
        self.t_stages = []
        self.moisture_iterations = []
        self.moisture_converged = []
        self.moisture_scaled_residual = []
        dt_days = p.year_days / nt
        spinup = max(spinup, int(round(117.0 / dt_days)))      # ~4 months whatever the step
        soil_keep = np.exp(-dt_days / p.soil_memory_days) if p.soil_memory_days > 0 else 0.75
        order = list(range(nt - spinup, nt)) + list(range(nt))
        for n, k in enumerate(order):
            d = days[k]
            s = self.season_index(d, p.circulation_lag_days)
            Tl = self.z.land(lat, d) + p.land_offset
            if p.land_amplitude != 1.0 or p.wet_cooling > 0 or p.continentality > 0:
                Tl_mean = self.z.land_annual(lat) + p.land_offset
            if p.land_amplitude != 1.0:      # v4: continental seasonality
                Tl = Tl_mean + p.land_amplitude * (Tl - Tl_mean)
            if p.continentality > 0:
                # e1: the energy-balance land column is an average land at its
                # latitude. Air that has crossed more land swings more (east
                # coasts: cold winters, hot summers), sea air less (west coasts).
                # chi = land fraction carried along the winds (last step's, the
                # zonal belts on the first) with a CONTINENTAL_FETCH_DAYS memory.
                if uv_prev is None:
                    uc, vc, _, _ = self.zonal_wind(s)
                    uc, vc = uc * self.drag, vc * self.drag
                else:
                    uc, vc = uv_prev
                lamC = np.full(lat.shape, 1.0 / (CONTINENTAL_FETCH_DAYS * DAY))
                chi = self.solver.solve(uc, vc, p.heat_diffusion, lamC, lamC * g.land_frac, g.land_frac,
                                        guess=g.land_frac if chi is None else chi)
                Tl = Tl_mean + (Tl - Tl_mean) * np.clip(1.0 + p.continentality * (chi - 0.5), 0.2, 3.0)
            if p.wet_cooling > 0:            # v8: wet ground spends summer sunshine
                # on evaporation instead of heating the air (why humid summers
                # on Earth rarely pass 30 C); wetness = recent rain against a
                # rough potential evaporation (~6.5 mm/day at 30 C)
                pet = 0.5 + 0.2 * np.maximum(Tl, 0.0)
                wet = np.clip(soilP / pet, 0.0, 1.0)
                Tl = Tl - p.wet_cooling * wet * np.maximum(Tl - Tl_mean, 0.0)
            if p.land_coupling_insolation > 0:
                # physics e2: the land surface ties the air to its temperature
                # through sunshine-driven mixing, strongly in summer and weakly
                # in winter (radiative cooling alone, ~30 days), so winter air
                # masses keep where they came from (Held & Suarez 1994)
                S = daily_insolation(lat, declination(d, p.tilt, p.winter_solstice_day, p.year_days),
                                     distance_factor(d, p.eccentricity,
                                                     p.winter_solstice_day + p.perihelion_after_solstice,
                                                     p.year_days))
                lam_land = ((S / LAND_COUPLING_SREF) ** p.land_coupling_insolation / (p.land_tau_days * DAY)
                            + 1.0 / (LAND_RADIATIVE_DAYS * DAY))
                lamT = np.where(land, lam_land, 1.0 / (p.ocean_tau_days * DAY))
            To = self.z.ocean(lat, d) + p.sst_offset
            Tz = self.z.zonal(lat, d)
            SST = self.sst(d, To, Tl)
            if p.upwelling > 0:
                # e1: wind along a coast drives surface water 90 deg to its right
                # (left with reversed spin; Ekman); where that is offshore, cold
                # water wells up - strongest in summer under the subtropical
                # highs' equatorward winds on west coasts (California, Iberia,
                # NW Africa, Chile). Last step's winds; the zonal belts at first.
                if uv_prev is None:
                    ue, ve, _, _ = self.zonal_wind(s)
                else:
                    ue, ve = uv_prev
                ek_x, ek_y = (-ve, ue) if p.retrograde else (ve, -ue)
                index = gauss(ek_x * self.offshore[0] + ek_y * self.offshore[1], 100.0 / g.cell_km)
                SST = SST - p.upwelling * np.clip(index / 5.0, 0.0, 2.0) * self.upwelling_weight
            T_eq = np.where(land, Tl, SST)

            # ---- parts of the winds and storms that do not depend on temperature
            u0, v0, phi_i, phi_h = self.zonal_wind(s)
            if p.subtropical_high > 0:
                us, vs = self.subtropical_high_wind(s, phi_h)
                u0, v0 = u0 + us, v0 + vs
            # transient eddies (storms) mix heat and moisture between land and
            # sea regardless of the mean wind; modelled as exchange with the
            # surroundings (Gaussian of radius eddy_scale_km) at a rate that
            # peaks in the storm track
            storm = np.exp(-((lat - (phi_h + 13.0)) / p.storm_width) ** 2) * (1 - p.storm_seasonality * s)
            if p.storm_asym > 0:     # v5: storms breed off the warm-current coasts
                side = (1.0 if p.retrograde else -1.0) * self.basin_side
                storm = storm * np.clip(1.0 + p.storm_asym * side, 0.15, 2.0)
                # ... and reach further equatorward there
                shift = p.storm_reach * np.clip(side, 0, 1)
                storm = np.maximum(storm, np.exp(-((lat - (phi_h + 13.0 - shift)) / p.storm_width) ** 2)
                                   * (1 - p.storm_seasonality * s) * np.clip(side, 0, 1) * p.storm_asym)
            eddy = eddy_exchange_rate(p.eddy_rate, storm, s, p.eddy_seasonality)
            sigE = p.eddy_scale_km / g.cell_km

            # winds and temperature depend on temperature: iterate within the
            # step (t_iters > 1) instead of lagging one step behind
            # start from the previous step carried along its seasonal trend
            # (same converged answer, fewer passes)
            if T_prev is None:
                T_ref = T_eq
            elif T_prev2 is not None and p.t_iters > 1:
                T_ref = T_prev + (T_prev - T_prev2)
            else:
                T_ref = T_prev
            u=v=None
            def solve_temperature(T_state, first_iteration):
                nonlocal u,v
                # ---- winds
                T_anom = T_state - Tz
                ut, vt = self.thermal_wind(T_anom)
                u = (u0 + ut) * self.drag
                v = (v0 + vt) * self.drag
                lam = lamT
                if p.ocean_tau_stable > 0:
                    # e3: air warmer than the sea under it is stable: a shallow
                    # surface layer takes the sea's temperature within hours
                    # (desert air blowing over a cold current stays aloft,
                    # above the marine inversion); cold air over warm sea
                    # keeps the slower convective adjustment
                    warm = np.clip((T_state - T_eq) / 2.0, 0.0, 1.0) * ocean
                    lam = lamT + warm * (1.0 / (p.ocean_tau_stable * DAY) - lamT)

                # ---- temperature (sea-level equivalent), then lapse rate
                if p.eddy_rate > 0:
                    Tmix = gauss(T_state, sigE)
                    eh = eddy if p.eddy_heat == 1.0 else eddy * p.eddy_heat
                    return self.solver.solve(u, v, p.heat_diffusion, lam + eh,
                                            lam * T_eq + eh * Tmix, T_eq, guess=T_prev if first_iteration else T_state)
                else:
                    return self.solver.solve(u, v, p.heat_diffusion, lam, lam * T_eq, T_eq, guess=T_prev if first_iteration else T_state)
            retry_callback=(lambda info:temperature_retry(dict(seasonal_step=n+1,day=float(d),**info))) if temperature_retry else None
            temperature=iterate_temperature(solve_temperature,T_ref,p.t_iters,p.t_relaxation,p.t_adaptive_retries,
                                            on_retry=retry_callback)
            Tsl,update=temperature.temperature,temperature.update
            update_max=float(update.max())
            self.t_iterations.append(temperature.iterations)
            self.t_stages.append(temperature.stages)
            # Observe the existing stopping test without changing the solve.
            # Reaching the last allowed iteration is not necessarily failure:
            # it can satisfy the tolerance on that same iteration.
            self.t_converged.append(temperature.converged)
            self.t_update_max.append(update_max)
            self.t_update_inmap_max.append(float(update[g.inmap].max()))
            if not temperature.converged and p.t_require_convergence:
                raise TemperatureConvergenceError(n+1,d,temperature,update[g.inmap].max())
            T = Tsl - p.lapse_rate * h_km

            # ---- moisture
            # saturation is set by the temperature of the whole air column,
            # which is smoother than the surface (boundary-layer) temperature
            T_col = (0.4 * np.where(land, Tsl, SST)
                     + 0.6 * gauss(Tsl, self.col_sigma))
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
            sub = np.exp(-((lat - phi_h) / p.subsidence_width) ** 2)
            # subtropical highs sink hardest over the eastern side of ocean
            # basins on a prograde planet (dry west coasts: California,
            # Sahara coast); the asymmetry flips for retrograde spin
            asym = (-1.0 if p.retrograde else 1.0) * p.subsidence_asym * self.basin_side
            sub = sub * np.clip(1.0 + asym, 0.0, 2.0)
            # v7: the summer highs are the strong ones (monsoon heating next
            # door drives their sinking: Rodwell & Hoskins 2001)
            if p.subsidence_summer > 0:
                sub = sub * (1.0 + p.subsidence_summer * s)
            A_dyn = (p.background_ascent + p.storm_track * storm + p.convective * conv + p.orographic * up)
            A_dyn = A_dyn * np.clip(1 - p.subsidence * sub, 0.03, 1)
            if p.sverdrup > 0:       # physics e1: poleward flow rises, equatorward flow sinks
                th = np.radians(p.north_bearing)
                v_pole = gauss(u * np.sin(th) + v * np.cos(th), self.col_sigma)   # true northward, large scale
                A_dyn = A_dyn * np.clip(1 + p.sverdrup * v_pole / 5.0, 0.05, 3.0)
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
            from .moisture import solve_moisture
            exchange = eddy * np.exp(-h_km / 2.5) if p.eddy_rate > 0 else 0.0
            # physics e1: under the highs, dry air sinking from aloft replaces
            # moist low-level air (the column dries without raining)
            sink = p.subsidence_drying * sub / DAY if p.subsidence_drying > 0 else None
            closure = None
            if p.convective_rain > 0 or p.subcloud_evaporation > 0:     # physics e2 rain closure
                closure = dict(conv=p.convective_rain, r0=p.convective_rh, evap=p.subcloud_evaporation, T=T,
                               fT=np.clip((T_col - 15.0) / 10.0, 0.0, 1.0))
            solution = solve_moisture(self.solver, p, u, v, lamE, W_ocean, E_land, Ws,
                                      A_dyn, instab, bnd, W, exchange,
                                      (lambda water: gauss(water, sigE)) if p.eddy_rate > 0 else None, sink=sink,
                                      closure=closure)
            W, P = solution.water, solution.rain
            self.moisture_iterations.append(solution.iterations)
            self.moisture_converged.append(solution.converged)
            self.moisture_scaled_residual.append(solution.scaled_residual)
            if solution.converged is False and p.moisture_require_convergence:
                raise RuntimeError(f'Moisture equation failed at seasonal step {n+1}: '
                                   f'{solution.iterations} iterations, scaled residual '
                                   f'{solution.scaled_residual:.6g} > {p.moisture_residual_tol:g}')
            E = np.where(ocean, lamE * (W_ocean - W) * DAY, E_land * DAY)
            soilP = soil_keep * soilP + (1 - soil_keep) * P

            T_prev2, T_prev, W_prev = T_prev, Tsl, W
            uv_prev = (u, v)
            if n >= spinup:
                for key, val in (("T", T), ("Tsl", Tsl), ("P", P), ("W", W), ("u", u), ("v", v), ("E", E)):
                    out[key][k] = val
                if budget is not None:
                    exchange = eddy * np.exp(-h_km / 2.5) if p.eddy_rate > 0 else 0.0
                    mixed = gauss(W, sigE) if p.eddy_rate > 0 else W
                    E_net = E if sink is None else E - sink * W * DAY      # subsidence drying as negative evaporation
                    terms = moisture_terms(W, u, v, dx, p.moisture_diffusion, E_net, P, exchange, mixed)
                    for key, values in terms.items():
                        budget[key][k] = values[g.map_slice()]
            if progress:
                progress(n + 1, len(order))

        snow = snowpack(out["T"], out["P"], p.year_days / nt)
        return Result(params=p, grid=g, days=days, snow=snow, moisture_budget=budget, **out)


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
