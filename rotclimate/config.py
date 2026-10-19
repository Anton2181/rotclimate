"""Model parameters.

Every free choice the climate model makes lives here, so that the calibration
loop can search over them and every rendered map can be reproduced from a
saved JSON file.
"""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field, fields
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
DATA = REPO / "data"
SOURCE = DATA / "source"
OUTPUT = REPO / "output"


def apply_numerics(params, *, saved=False, defaults=None, downsample=None, steps=None, picard=None):
    """Preserve verified moisture settings unless numerics are explicitly overridden.

    Old profiles retain each CLI's historical defaults. Positive moisture
    tolerance opts into the saved profile automatically, so a strict solve
    cannot silently be shortened back to two iterations.
    """
    values = {} if saved or params.moisture_residual_tol > 0 else dict(defaults or {})
    values.update({key: value for key, value in
                   [('downsample', downsample), ('steps_per_year', steps), ('picard_iters', picard)]
                   if value is not None})
    return params.replace(**values)


@dataclass
class Params:
    # ---------------------------------------------------------------- planet
    lat_center: float = 34.0          # latitude of the map centre [deg N]
    north_bearing: float = 0.0        # direction of true north, degrees clockwise from the top of the map
    tilt: float = 23.44               # axial tilt [deg]
    retrograde: bool = False          # spin opposite to Earth (flips Coriolis)
    eccentricity: float = 0.0167
    perihelion_after_solstice: float = 13.0  # days after the winter solstice
    year_days: int = 365
    # day-of-year (0-based, day 0 = Titian Marigold 1) of the winter solstice.
    # Day 22 puts the solstice in "early winter", the equinox in "middle
    # spring", the summer solstice in "early summer" etc. - see calendar.py
    winter_solstice_day: float = 22.0

    # ---------------------------------------------------------------- map
    # the map is drawn on pointy-top hexes with 15-mile sides (30 mi corner
    # to corner, 26 mi across the flats, ~585 sq mi); measured from the hex
    # lines (scripts/prepare_sources.py): 1.1434 mi/px across, 1.1427 down
    map_width_mi: float = 2286.8
    map_height_mi: float = 1058.2
    # unknown terrain tiers -> top elevation of each tier [m]
    # (lowland green, hill cream, upland orange, mountain red)
    tier_tops: tuple = (350.0, 900.0, 1800.0, 3300.0)
    lapse_rate: float = 6.0           # K / km (environmental)

    # What lies beyond each edge of the map is unknown.
    # beyond_style 'procedural' (default): edge features continue and fade
    # over beyond_continuity_km, then seeded fractal land/sea with a land
    # *fraction* per side (0 = open ocean, 1 = continent) and low hills.
    beyond_style: str = "procedural"
    beyond_north_land: float = 0.6
    beyond_south_land: float = 0.6
    beyond_west_land: float = 0.3
    beyond_east_land: float = 0.3
    beyond_southeast_land: float = -1.0   # v6: east half of the south edge (-1 = same as south)
    beyond_northeast_land: float = -1.0   # v6: east half of the north edge (-1 = same as north)
    beyond_continuity_km: float = 300.0
    beyond_relief_m: float = 400.0
    beyond_seed: int = 1
    # legacy 'blocks' style (rounds 0-2): per side 'ocean' | 'land' |
    # 'extend', with *_gap_km of open sea before the unknown coast.
    beyond_north: str = "extend"
    beyond_south: str = "extend"
    beyond_west: str = "ocean"
    beyond_east: str = "ocean"
    beyond_north_gap_km: float = 0.0
    beyond_south_gap_km: float = 0.0
    beyond_west_gap_km: float = 0.0
    beyond_east_gap_km: float = 0.0
    pad_km: float = 1100.0

    # ---------------------------------------------------------------- energy
    land_tau_days: float = 3.0        # air-mass adjustment time over land
    ocean_tau_days: float = 1.5       # ... over sea
    heat_diffusion: float = 4.0e4     # m^2/s, horizontal mixing of air
    current_strength: float = 4.0     # K, boundary current SST anomaly
    current_scale_km: float = 250.0   # e12: smoothing scale (km) of the land that decides which side of a sea a cell is on
    sst_offset: float = 0.0           # K, global SST tweak
    land_offset: float = 0.0          # K, global land-column tweak
    inland_sea_warming: float = 2.0   # enclosed seas take 0.1*this of the land's swing
    lake_coupling: float = 0.0        # v4: lakes/small seas follow land temp (0 = off)
    sea_winter_mixing: float = 0.0    # e19: share of an enclosed sea's or lake's winter cooling toward the land that deep mixing cancels (0 = symmetric)
    land_amplitude: float = 1.0       # v4: scale of the continental seasonal swing
    storm_asym: float = 0.0           # v5: storm track stronger on the warm-current side
    storm_reach: float = 0.0          # v5: ... and this many degrees further equatorward
    instability: float = 0.0          # v6: extra rain efficiency in hot, moist air
    # time-step independence: soil-moisture memory in days (0 = the legacy
    # 0.75-per-step rule) and the most temperature/wind iterations within
    # each step (stops once nothing moves by 0.05 C; 1 = legacy one-step lag)
    soil_memory_days: float = 0.0
    t_iters: int = 1
    t_relaxation: float = 1.0        # fraction of temperature fixed-point update; 1 preserves legacy runs
    t_adaptive_retries: int = 0      # optional bounded retries with smaller damping
    t_require_convergence: bool = False

    # ---------------------------------------------------------------- winds
    hadley_edge: float = 30.0         # annual-mean subtropical high latitude
    hadley_shift: float = 5.0         # seasonal poleward shift in summer
    itcz_mean: float = 5.0
    itcz_shift: float = 10.0
    trade_speed: float = 6.0          # m/s
    westerly_speed: float = 7.0       # m/s
    polar_speed: float = 3.0
    monsoon_strength: float = 1.0     # thermal-low wind scaling
    monsoon_scale_km: float = 500.0   # smoothing of the thermal pressure field
    cross_isobar_deg: float = 35.0    # friction turning toward low pressure
    terrain_drag: float = 0.5         # wind slow-down over high ground

    # ---------------------------------------------------------------- water
    ocean_rh: float = 0.80
    evap_tau_days: float = 2.0
    land_recycling: float = 0.35      # fraction of land P re-evaporated
    precip_tau_days: float = 6.0      # background rain-out time scale
    rh_threshold: float = 0.45
    rh_spread: float = 0.0            # e22: day-to-day spread (s.d.) of column humidity the rain gate is averaged over (0 = the mean alone)
    storm_track: float = 1.6          # extra-tropical cyclone rain factor
    storm_width: float = 9.0          # deg
    convective: float = 2.0           # convergence-driven rain factor
    orographic: float = 2.5           # upslope rain factor
    subsidence: float = 0.75          # subtropical-high suppression (0..1)
    subsidence_asym: float = 0.0      # east/west-of-basin asymmetry of the highs
    subsidence_summer: float = 0.0    # v7: highs sink harder in summer: x (1 + this * season)
    wet_cooling: float = 0.0          # v8: share of the summer warmth that wet ground evaporates away
    # physics e1 (fitted on Earth): Sverdrup balance (beta v = f dw/dz) - low-level
    # flow toward the pole rises, flow toward the equator sinks: rain x
    # clip(1 + sverdrup * v_poleward / 5 m/s, 0.05, 3), v smoothed over ~300 km
    sverdrup: float = 0.0
    subsidence_width: float = 6.0     # e1: latitude half-width of the subtropical highs' sinking (deg)
    storm_seasonality: float = 0.3    # e1: storm track weaker in summer: x (1 - this * season)
    circulation_lag_days: float = 30.0  # e1: how far the highs, storm track and ITCZ lag the sun (days)
    subsidence_drying: float = 0.0    # e1: dry air sinking in the highs replaces moist air: loss of this x sink strength per day
    land_heat_capacity: float = 1.0   # e1: x the EBM land column's heat capacity (how far land seasons lag the sun)
    continentality: float = 0.0       # e1: land seasons x (1 + this * (upwind land share - 0.5))
    continental_depth: float = 0.0    # e23: extra seasonal amplitude where the westerlies crossed ~5,000 km of land (none at half land or less)
    upwelling: float = 0.0            # e1: coastal sea cooling (C) per 5 m/s of offshore Ekman transport
    # physics e2 (from the literature review of the remaining Earth failures)
    background_ascent: float = 1.0    # e2: the rain dynamics' baseline (the "1 +"); 0 = rain needs ascent
    convective_rain: float = 0.0      # e2: convective rain (mm/day) at column humidity convective_rh, x e^(11.4 dr)
    convective_rh: float = 0.6        # e2: ... its reference column relative humidity
    subcloud_evaporation: float = 0.0  # e2: rain evaporating below the cloud base: x exp(-this * z_LCL / 3 km)
    land_coupling_insolation: float = 0.0  # e2: land air coupling x (sunshine / 480 W m-2)^this (+ 1/30 d)
    ebm_land: str = "uniform"         # planet's land by latitude: uniform 30 %, or "earth" (Earth mode)
    sea_enclosure: str = "disc"       # inland-sea measure: "disc" (land within 400 km) or "rays" (e3)
    ocean_tau_stable: float = 0.0     # e3: days for air warmer than the sea to cool to it (0 = ocean_tau_days)
    eddy_heat: float = 1.0            # e3: storm-eddy exchange of heat as a share of that of moisture
    eddy_moisture_height_km: float = 0.0  # e4: eddies mix W*exp(z/H) (sea-level equivalent), H in km (0 = off)
    cloud_radiation: float = 0.0      # e4: K of land warming per unit of cloud deficit vs the latitude mean at 480 W m-2
    cloud_longwave: float = 0.0       # e4: scale of the clear-sky longwave anomaly (dry, clear air cools), 1 = physical
    snow_albedo: float = 0.0          # e16: K of land cooling under full snow cover per 480 W m-2 of sunshine
    flux_convergence: float = 0.0     # e17: share of column water brought in by low-level convergence into warm columns (0 = off)
    slp_large: float = 0.0            # e5: hPa of low pressure per K of warm anomaly, planetary scale (0 with slp_local 0 = off)
    slp_local: float = 0.0            # e5: hPa/K at the boundary-layer scale (sea breezes, heat lows)
    slp_scale_km: float = 2000.0      # e5: smoothing of the planetary-scale pressure
    slp_local_km: float = 150.0       # e5: smoothing of the boundary-layer-scale pressure
    bl_drag_ocean: float = 3.5e-5     # e5: boundary-layer friction over sea (1/s)
    bl_drag_land: float = 1.0e-4      # e5: boundary-layer friction over land (1/s)
    divergence_drying: float = 0.0    # e5: rain x exp(-this * low-level divergence index)
    monsoon_heating: float = 0.0      # e4b: m/s per mm/day x tan(lat) of meridional inflow toward warm rain (0 = off)
    monsoon_rain0: float = 1.0        # e4b: warm-season rain (mm/day) with no inflow; drier skies drive outflow
    trade_land: float = 0.0           # e4b: summer weakening of the trades over continental-scale land (0-1)
    far_fetch: float = 0.0            # e6: weight of the far-field upwind land share at the domain edge (0 = local land)
    wind_cap: float = 0.0             # e6: m/s ceiling of the temperature-driven wind, soft above half of it (0 = none)
    soil_bucket_mm: float = 0.0       # e8: soil water a land cell holds for energy-limited evaporation (0 = recent-rain recycling)
    soil_wet_cooling: bool = False    # e8b: wet_cooling judges wetness by the bucket's soil water, not recent rain
    ocean_sink: float = 1.0           # e11: fraction of sea uptake kept when air is moister than the sea's equilibrium (1 = symmetric)
    land_edge_rh: float = 0.5         # column humidity (of saturation) of air entering the grid over land
    high_drying: float = 0.0          # e10: rain-making ascent x exp(-this x hPa of the pressure winds' high anomaly)
    marine_layer: float = 0.0         # e4: max share of a coastal cell under marine air (0 = off)
    marine_reach_km: float = 40.0     # e4: sea-breeze reach of the marine air
    marine_inversion_m: float = 700.0  # e4: inversion height: ground above it (or behind a crest above it) is continental
    marine_contrast: float = 5.0      # e4: land-minus-sea warmth (K) for a full marine layer
    eddy_rainout: float = 0.0         # e3: eddy moisture steps capped at crest saturation / this (0 = off)
    subtropical_high: float = 0.0     # e3: m/s, wind around the subtropical highs that sit over the oceans
    subtropical_high_scale_km: float = 1000.0  # e3: smoothing of the ocean basins those highs fill
    subtropical_high_width: float = 10.0       # e3: deg of latitude around the subtropical ridge
    subtropical_high_seasonality: float = 0.5  # e3: summer strength x (1 + this), winter x (1 - this)
    moisture_diffusion: float = 6.0e4  # m^2/s
    eddy_rate: float = 0.0            # 1/day, storm-eddy exchange (0 = off)
    eddy_seasonality: float = 0.0     # extra winter strength / summer weakness (0 preserves existing fits)
    eddy_scale_km: float = 450.0

    # ---------------------------------------------------------------- numerics
    downsample: int = 8               # source pixels per model cell
    steps_per_year: int = 73          # 73 x 5-day weeks
    picard_iters: int = 3
    moisture_relaxation: float = 0.5  # retains legacy half-updates
    moisture_residual_tol: float = 0.0  # 0 retains fixed Picard count; >0 checks local equation
    moisture_require_convergence: bool = False
    transport_scheme: str = "upwind"  # optional 'exponential' fitted advection-diffusion
    solver_rtol: float = 1e-3        # linear sweep update / maximum boundary magnitude
    solver_max_iter: int = 400
    solver_require_convergence: bool = False  # strict profiles reject capped solves

    def to_json(self, path: Path | str) -> None:
        Path(path).write_text(json.dumps(asdict(self), indent=2))

    @classmethod
    def from_json(cls, path: Path | str) -> "Params":
        d = json.loads(Path(path).read_text())
        known = {f.name for f in fields(cls)}
        d = {k: (tuple(v) if isinstance(v, list) else v) for k, v in d.items() if k in known}
        d.setdefault("beyond_style", "blocks")   # files from before procedural surroundings
        return cls(**d)

    def replace(self, **kw) -> "Params":
        d = asdict(self)
        d.update(kw)
        return Params(**d)
