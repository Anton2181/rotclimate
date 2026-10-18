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
OMEGA = 7.292e-5                 # e5: rotation rate (1/s) for the boundary-layer wind balance
RHO_AIR = 1.2                    # e5: kg/m3
MONSOON_MAX_MS = 6.0             # e4b: cap of the heating-driven meridional wind
MONSOON_SMOOTH_KM = 600.0        # e4b: scale of the rain heating that drives it
MARINE_SOFTNESS_M = 150.0        # e4: softness of the marine layer's terrain test
MARINE_SST_KM = 100.0            # e4: the coastal sea temperature: Gaussian mean of nearby sea
EDDY_RAINOUT_STEPS = 6           # e3: steps of the eddy moisture mixing that each meet the terrain
CONTINENTAL_FETCH_DAYS = 4.0     # memory of the land the air has crossed (~1,700 km at 5 m/s)


def lowest_crest_from_sea(land, barrier):
    """For every cell, the lowest possible highest barrier on any 8-connected
    path from the sea to it, the cell itself included (Priority-Flood,
    Barnes et al. 2014). Sea cells are 0."""
    import heapq

    ny, nx = land.shape
    z = np.where(land, np.inf, 0.0)
    heap = [(0.0, i, j) for i, j in zip(*np.nonzero(~land))]
    heapq.heapify(heap)
    while heap:
        h, i, j = heapq.heappop(heap)
        if h > z[i, j]:
            continue
        for di in (-1, 0, 1):
            for dj in (-1, 0, 1):
                a, b = i + di, j + dj
                if (di or dj) and 0 <= a < ny and 0 <= b < nx:
                    nh = max(h, barrier[a, b])
                    if nh < z[a, b]:
                        z[a, b] = nh
                        heapq.heappush(heap, (nh, a, b))
    return z


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
        # e4: sub-grid marine air on coasts under a subtropical inversion
        # (Rahn & Garreaud 2010; Iacobellis & Cayan 2013): the share of each
        # land cell within sea-breeze reach of the sea (cell mean of
        # exp(-d / reach), the coast taken one cell width from the centre of
        # the first land row) on ground the marine layer can reach: below the
        # inversion and behind no crest above it (lowest crest on any path
        # from the sea; crests from the cells' mean and highest ground)
        self.trace_cells = None          # (rows, cols) at which run() records the rain step (diagnostics)
        self.marine_geom = None
        if p.marine_layer > 0:
            L, D = p.marine_reach_km, g.cell_km
            a = np.maximum(ndi.distance_transform_edt(g.land) * D - D, 0.0)
            reach = (L / D) * (np.exp(-a / L) - np.exp(-(a + D) / L))
            barrier = np.where(g.land, g.elev + 0.5 * (np.maximum(g.elev_max, g.elev) - g.elev), 0.0)
            crest = lowest_crest_from_sea(g.land, barrier)
            up = ndi.minimum_filter(np.where(np.isfinite(crest), crest, 1e9), size=3, mode="nearest")
            z_test = np.maximum(np.minimum(up, crest), g.elev)
            below = 1.0 / (1.0 + np.exp(-(p.marine_inversion_m - z_test) / MARINE_SOFTNESS_M))
            self.marine_geom = np.where(g.land, reach * below, 0.0)
        # e5: boundary-layer friction for the pressure-driven wind (smoothed
        # across coasts over ~100 km)
        self.bl_drag = ndi.gaussian_filter(np.where(g.land, p.bl_drag_land, p.bl_drag_ocean), cells_per_100km,
                                           mode="nearest")
        # e4b: land fraction at the scale of continents (summer trade weakening)
        self.land_broad = ndi.gaussian_filter(land, 1500.0 / g.cell_km, mode="nearest") if p.trade_land > 0 else None
        # e3: ocean basins at the scale of the subtropical highs
        self.ocean_basin = (ndi.gaussian_filter(1.0 - land, p.subtropical_high_scale_km / g.cell_km)
                            if p.subtropical_high > 0 else None)

    # ------------------------------------------------------------------ helpers
    def _lat_mean(self, field):
        """Mean of a field over the grid's 1-degree latitude bands, mapped back
        onto the grid (the latitude's own mean in this domain)."""
        if not hasattr(self, "_lat_bins"):
            b = np.floor(self.lat).astype(int)
            b -= b.min()
            self._lat_bins = b
            self._lat_count = np.maximum(np.bincount(b.ravel()), 1)
        b = self._lat_bins
        return (np.bincount(b.ravel(), weights=field.ravel(), minlength=len(self._lat_count))
                / self._lat_count)[b]

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
        # northern trades (e4b: weaker over big land masses in summer, where
        # heat lows and monsoon inflow replace them)
        trade = p.trade_speed
        if p.trade_land > 0:
            trade = trade * (1.0 - p.trade_land * max(s, 0.0) * self.land_broad)
        m = (lat >= phi_i) & (lat < phi_h)
        xi = (lat - phi_i) / (phi_h - phi_i)
        u = np.where(m, -trade * np.sin(np.pi * xi), u)
        v = np.where(m, -0.35 * trade * np.sin(np.pi * xi), v)
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

    def pressure_wind(self, T_anom):
        """e5: surface wind from a sea-level pressure diagnosed from the
        temperature anomaly (warm air, low pressure), as in CLIMBER-2/X:
        p = -(slp_large * G_L(T*) + slp_local * (G_l(T*) - G_L(T*))), a
        planetary-wave scale (~2 hPa/K, Blinova) and a boundary-layer scale
        (sea breezes, heat lows); then the mixed-layer momentum balance
        f k x U + eps U = -grad p / rho (Stevens et al. 2002; Back & Bretherton
        2009): cross-isobar angle atan(eps / f) from the surface friction (sea
        ~20 deg, land ~45 deg at 40 deg latitude), regular at the equator."""
        p, g = self.p, self.g
        big = gauss(T_anom, p.slp_scale_km / g.cell_km)
        local = gauss(T_anom, p.slp_local_km / g.cell_km) - big
        pres = -100.0 * (p.slp_large * big + p.slp_local * local)              # Pa
        px = np.gradient(pres, axis=1) / g.dx_m
        py = -np.gradient(pres, axis=0) / g.dx_m
        f = 2.0 * OMEGA * np.sin(np.radians(self.lat)) * (-1.0 if p.retrograde else 1.0)
        eps = self.bl_drag
        den = RHO_AIR * (eps ** 2 + f ** 2)
        return -(eps * px + f * py) / den, (f * px - eps * py) / den

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
        self.trace = []
        dx = g.dx_m

        tau = np.where(land, p.land_tau_days, p.ocean_tau_days) * DAY
        lamT = 1.0 / tau
        T_prev = T_prev2 = None
        W_prev = None
        uv_prev = chi = None
        cloud_prev = None               # e4: last step's cloud cover and column water (land radiation)
        heating_prev = None             # e4b: last step's warm-season rain (monsoon inflow)
        soilP = np.full(lat.shape, 1.5)
        soil_w = np.where(land, 0.5 * p.soil_bucket_mm, 0.0)    # e8: soil water (mm)
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
                # e6: air entering the grid has crossed the world beyond it; on
                # Earth that world is known (the westward land share with a
                # ~1,700 km memory, WorldClim), so the edge carries it instead
                # of the edge cell's own land
                edge = g.land_frac
                if p.far_fetch > 0 and g.chi_far is not None:
                    edge = g.land_frac + p.far_fetch * (g.chi_far - g.land_frac)
                chi = self.solver.solve(uc, vc, p.heat_diffusion, lamC, lamC * g.land_frac, edge,
                                        guess=edge if chi is None else chi)
                Tl = Tl_mean + (Tl - Tl_mean) * np.clip(1.0 + p.continentality * (chi - 0.5), 0.2, 3.0)
            if p.wet_cooling > 0:            # v8: wet ground spends summer sunshine
                # on evaporation instead of heating the air (why humid summers
                # on Earth rarely pass 30 C); wetness = recent rain against a
                # rough potential evaporation (~6.5 mm/day at 30 C)
                pet = 0.5 + 0.2 * np.maximum(Tl, 0.0)
                wet = np.clip(soilP / pet, 0.0, 1.0)
                Tl = Tl - p.wet_cooling * wet * np.maximum(Tl - Tl_mean, 0.0)
            if (p.cloud_radiation > 0 or p.cloud_longwave > 0) and cloud_prev is not None:
                # e4: the latitude-mean land column carries its latitude's mean
                # cloudiness. Where this step's sky is clearer than that mean,
                # more sunshine reaches the ground (dry interiors: Ghausi et
                # al. 2023) and, with dry air, more heat escapes to space
                # (clear-sky emissivity, Prata 1996: winter cold pools, the
                # Siberian High); cloudier and moister places the reverse.
                # Cloud cover from last step's humidity and rain (SPEEDY).
                fc, Wc = cloud_prev
                fbar = self._lat_mean(fc)
                dT = np.zeros_like(Tl)
                if p.cloud_radiation > 0:
                    S = daily_insolation(lat, declination(d, p.tilt, p.winter_solstice_day, p.year_days),
                                         distance_factor(d, p.eccentricity,
                                                         p.winter_solstice_day + p.perihelion_after_solstice,
                                                         p.year_days))
                    dT -= p.cloud_radiation * (fc - fbar) * S / LAND_COUPLING_SREF
                if p.cloud_longwave > 0:
                    def clear_loss(f, w):
                        x = np.maximum(w, 0.0) / 10.0                  # column water in cm
                        eps = 1.0 - (1.0 + x) * np.exp(-np.sqrt(1.2 + 3.0 * x))
                        return (1.0 - f) * (1.0 - eps)
                    sigT4 = 5.67e-8 * (np.maximum(Tl, -60.0) + 273.15) ** 4
                    dT -= p.cloud_longwave * sigT4 * (clear_loss(fc, Wc) - clear_loss(fbar, self._lat_mean(Wc))) / 10.0
                Tl = Tl + np.clip(dT, -15.0, 10.0)
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
            uM = vM = None
            if p.monsoon_heating > 0 and heating_prev is not None:
                # e4b: latent heating aloft drives low-level flow toward it by
                # the Sverdrup balance, beta*v = f*dw/dz (Rodwell & Hoskins
                # 2001): poleward inflow under heavy warm-season rain (the
                # East Asian south-westerlies), equatorward flow under dry
                # skies (Etesians, Portuguese and Californian northerlies).
                # ~1 m/s * tan(lat) per mm/day of rain beyond monsoon_rain0;
                # it carries heat and moisture but does not feed the
                # convergence that makes rain (no runaway).
                vN = p.monsoon_heating * np.tan(np.radians(np.clip(np.abs(lat), 0.0, 60.0))) \
                    * (heating_prev - p.monsoon_rain0)
                vN = np.clip(vN, -MONSOON_MAX_MS, MONSOON_MAX_MS) * np.sign(lat)
                th = np.radians(p.north_bearing)
                uM, vM = vN * np.sin(th), vN * np.cos(th)
                u0, v0 = u0 + uM, v0 + vM
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
                if p.slp_large > 0 or p.slp_local > 0:
                    ut, vt = self.pressure_wind(T_anom)      # physics e5
                else:
                    ut, vt = self.thermal_wind(T_anom)
                if p.wind_cap > 0:
                    # e6: surface winds are friction-limited; without a ceiling,
                    # strong small-scale heat lows feed back on themselves
                    # (wind -> sharper contrast -> more wind) and the
                    # temperature-wind iteration runs away on some coastlines.
                    # Unchanged below half the cap, saturating at the cap.
                    sp = np.hypot(ut, vt)
                    knee = 0.5 * p.wind_cap
                    over = (sp - knee) / (p.wind_cap - knee)
                    f_cap = np.where(sp > knee, (knee + (p.wind_cap - knee) * np.tanh(np.maximum(over, 0.0)))
                                     / np.maximum(sp, 1e-9), 1.0)
                    ut, vt = ut * f_cap, vt * f_cap
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
            T_rep, Tsl_rep = T, Tsl
            if self.marine_geom is not None:
                # e4: a two-tile coast: marine air under the inversion (the
                # nearby sea's temperature) and continental air (the solved
                # T, which keeps driving winds, humidity and rain). The marine
                # share grows with how much warmer the land air is than the
                # sea (none in winter)
                sea = ocean.astype(float)
                sig = MARINE_SST_KM / g.cell_km
                sst_c = gauss(np.where(ocean, SST, 0.0), sig) / np.maximum(gauss(sea, sig), 1e-6)
                inv = np.clip((Tsl - sst_c) / p.marine_contrast, 0.0, 1.0)
                F = p.marine_layer * inv * self.marine_geom
                T_m = sst_c - p.lapse_rate * h_km
                T_rep = T - F * np.maximum(T - T_m, 0.0)
                Tsl_rep = T_rep + p.lapse_rate * h_km

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
            if uM is None:
                div = (np.gradient(u, axis=1) - np.gradient(v, axis=0)) / dx
            else:
                ur, vr = u - uM * self.drag, v - vM * self.drag
                div = (np.gradient(ur, axis=1) - np.gradient(vr, axis=0)) / dx
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
            if p.divergence_drying > 0:
                # e5: diverging low-level air sinks and dries the column, the
                # counterpart of the convergence term
                dvg = np.clip(ndi.gaussian_filter(div, self.conv_sigma) / 2e-6, 0, 3)
                A_dyn = A_dyn * np.exp(-p.divergence_drying * dvg)
            if p.sverdrup > 0:       # physics e1: poleward flow rises, equatorward flow sinks
                th = np.radians(p.north_bearing)
                v_pole = gauss(u * np.sin(th) + v * np.cos(th), self.col_sigma)   # true northward, large scale
                A_dyn = A_dyn * np.clip(1 + p.sverdrup * v_pole / 5.0, 0.05, 3.0)
            lamE = np.where(ocean, 1.0 / (p.evap_tau_days * DAY), 0.0)
            bnd = np.where(ocean, W_ocean, 0.5 * Ws)
            W = W_prev if W_prev is not None else bnd
            energy = np.clip((T + 5.0) / 20.0, 0, 1)
            if p.soil_bucket_mm > 0:
                # e8: land evaporates what the sun can evaporate while the soil
                # holds water (Priestley & Taylor 1972 with net radiation ~ half
                # the sunshine at the top of the air less 25 W/m2), slowing as
                # the soil dries below 75 % of what it holds (Manabe 1969);
                # winter rain stored in the soil feeds the summer air
                S_toa = daily_insolation(lat, declination(d, p.tilt, p.winter_solstice_day, p.year_days),
                                         distance_factor(d, p.eccentricity,
                                                         p.winter_solstice_day + p.perihelion_after_solstice,
                                                         p.year_days))
                Ts = np.clip(T, -40.0, 50.0)
                es = 0.6108 * np.exp(17.27 * Ts / (Ts + 237.3))
                slope = 4098.0 * es / (Ts + 237.3) ** 2
                pet = 1.26 * slope / (slope + 0.066) * np.maximum(0.5 * S_toa - 25.0, 0.0) / 28.4       # mm/day
                beta = np.clip(soil_w / (0.75 * p.soil_bucket_mm), 0.0, 1.0)
                E_land = np.where(land, np.minimum(p.land_recycling * pet * beta, soil_w / dt_days), 0.0) / DAY
            else:
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
            mix = (lambda water: gauss(water, sigE)) if p.eddy_rate > 0 else None
            if p.eddy_rate > 0 and p.eddy_moisture_height_km > 0:
                # e4: eddies mix specific humidity above the ground, not column
                # water: mix the sea-level equivalent and convert back, so a
                # basin behind a range does not receive sea-level columns at
                # inflated humidity (CLIMBER-X; UVic's undepleted vapour over
                # high land)
                # The neighbours' humidity is averaged by the air they hold
                # above their ground (mass-weighted), so a mountain column adds
                # little: target = c * G(W) / G(c), c = exp(-z / H). Mixing the
                # bare sea-level equivalents flooded the Turan lowlands with
                # Pamir moisture (the model's mountain columns hold more than
                # physical ones).
                col = np.exp(-h_km / p.eddy_moisture_height_km)
                gcol = np.maximum(gauss(col, sigE), 1e-6)
                mix = lambda water, col=col, gcol=gcol: col * gauss(water, sigE) / gcol
            if p.eddy_rate > 0 and p.eddy_rainout > 0:
                # e3: storm eddies carry water vapour by many short steps, not
                # one jump: a step over a ridge can hold no more than the
                # crest's saturation, the rest rains out on the windward side.
                # The single Gaussian let moisture tunnel through the Sierra
                # Nevada (Reno 416 mm a year against 241 observed).
                crest = w_sat(T_col - p.lapse_rate * h_km) / p.eddy_rainout
                n_steps = EDDY_RAINOUT_STEPS

                def mix(water, crest=crest, n_steps=n_steps):
                    for _ in range(n_steps):
                        water = np.minimum(gauss(water, sigE / np.sqrt(n_steps)), crest)
                    return water
            solution = solve_moisture(self.solver, p, u, v, lamE, W_ocean, E_land, Ws,
                                      A_dyn, instab, bnd, W, exchange, mix, sink=sink, closure=closure)
            W, P = solution.water, solution.rain
            self.moisture_iterations.append(solution.iterations)
            self.moisture_converged.append(solution.converged)
            self.moisture_scaled_residual.append(solution.scaled_residual)
            if solution.converged is False and p.moisture_require_convergence:
                raise RuntimeError(f'Moisture equation failed at seasonal step {n+1}: '
                                   f'{solution.iterations} iterations, scaled residual '
                                   f'{solution.scaled_residual:.6g} > {p.moisture_residual_tol:g}')
            E = np.where(ocean, lamE * (W_ocean - W) * DAY, E_land * DAY)
            if self.trace_cells is not None and n >= spinup:
                # diagnostics only: the rain step's inputs at a few cells
                ti, tj = self.trace_cells
                raw = p.background_ascent + p.storm_track * storm + p.convective * conv + p.orographic * up
                cell = lambda a: np.broadcast_to(np.asarray(a, float), lat.shape)[ti, tj].copy()
                self.trace.append(dict(
                    day=float(d), T=cell(T), W=cell(W), Ws=cell(Ws), P=cell(P), E=cell(E), soil=cell(soilP), bucket=cell(soil_w),
                    u=cell(u), v=cell(v), background=cell(p.background_ascent), storm=cell(p.storm_track * storm),
                    conv=cell(p.convective * conv), orog=cell(p.orographic * up),
                    damp=cell(A_dyn / np.maximum(raw, 1e-9)), instab=cell(instab)))
            soilP = soil_keep * soilP + (1 - soil_keep) * P
            if p.soil_bucket_mm > 0:
                soil_w = np.where(land, np.clip(soil_w + (P - E) * dt_days, 0.0, p.soil_bucket_mm), 0.0)

            T_prev2, T_prev, W_prev = T_prev, Tsl, W
            if p.monsoon_heating > 0:
                warm = np.clip((Tsl - 20.0) / 5.0, 0.0, 1.0)
                heating_prev = gauss(P * warm, MONSOON_SMOOTH_KM / g.cell_km)
            if p.cloud_radiation > 0 or p.cloud_longwave > 0:
                rh = np.clip(W / np.maximum(Ws, 1e-6), 0.0, 1.0)
                cloud_prev = (np.clip(0.2 * np.sqrt(np.clip(P, 0.0, 10.0)) + np.clip((rh - 0.3) / 0.7, 0.0, 1.0) ** 2,
                                      0.0, 1.0), W)
            uv_prev = (u, v)
            if n >= spinup:
                for key, val in (("T", T_rep), ("Tsl", Tsl_rep), ("P", P), ("W", W), ("u", u), ("v", v), ("E", E)):
                    out[key][k] = val
                if budget is not None:
                    exchange = eddy * np.exp(-h_km / 2.5) if p.eddy_rate > 0 else 0.0
                    mixed = mix(W) if mix is not None else W
                    E_net = E if sink is None else E - sink * W * DAY      # subsidence drying as negative evaporation
                    terms = moisture_terms(W, u, v, dx, p.moisture_diffusion, E_net, P, exchange, mixed)
                    for key, values in terms.items():
                        budget[key][k] = values[g.map_slice()]
            if progress:
                progress(n + 1, len(order))

        snow = snowpack(out["T"], out["P"], p.year_days / nt)
        return Result(params=p, grid=g, days=days, snow=snow, moisture_budget=budget, **out)


def _run_one(params):
    return ClimateModel(params).run()


def run_ensemble(params: Params, seeds, workers: int = 1) -> Result:
    """The mean climate over several random layouts of the unknown
    surroundings (beyond_seed): the climate to expect when nothing is known
    about the world beyond the map, rather than that of one invented coastline.
    The grid (identical inside the map) is the first layout's; outside the map
    the averaged fields mix different geographies and are not meaningful."""
    plist = [params.replace(beyond_seed=int(s)) for s in seeds]
    if workers > 1 and len(plist) > 1:
        import multiprocessing as mp
        with mp.get_context("fork").Pool(min(workers, len(plist))) as pool:
            runs = pool.map(_run_one, plist)
    else:
        runs = [_run_one(q) for q in plist]
    keys = ("T", "Tsl", "P", "W", "u", "v", "E", "snow")
    mean = {k: np.mean([getattr(r, k) for r in runs], axis=0).astype(np.float32) for k in keys}
    return Result(params=runs[0].params, grid=runs[0].grid, days=runs[0].days, **mean)


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
