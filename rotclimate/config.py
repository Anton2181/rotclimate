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
    solar_flux: float = 1.0           # starlight at the planet, x Earth's 1,361 W m-2 (a world property: the star)
    greenhouse_wm2: float = 0.0       # extra greenhouse forcing on the outgoing longwave, W m-2 (doubled CO2 ~3.7)
    planet_radius: float = 1.0        # x Earth's radius, with Earth's gravity, day and year (a denser planet); maps only
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
    lapse_seasonal: float = 0.0       # e25: lapse rate x (1 + this x season index): steeper in summer, flatter in winter
    seasonal_column_lapse: bool = False  # opt-in: use that season's lapse in column/crest saturation too
    column_saturation_scheme: str = 'legacy'  # opt-in pressure-lapse / pressure-moist hydrostatic saturation

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
    far_pole_land: float = -1.0       # land share poleward of the grid that winter cold air comes from (e31); -1 = the edge's own land carried on
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
    land_radiative_days: float = 30.0 # e2: land-air coupling time without sunshine (night, winter), days
    ocean_tau_days: float = 1.5       # ... over sea
    heat_diffusion: float = 4.0e4     # m^2/s, horizontal mixing of air
    current_strength: float = 4.0     # K, boundary current SST anomaly
    current_scale_km: float = 250.0   # e12: smoothing scale (km) of the land that decides which side of a sea a cell is on
    subpolar_current: float = 0.0     # e26: K, warm west-coast / cold east-coast currents of the subpolar gyres (poleward of ~42 deg)
    current_gyre: float = 0.0         # e42: share of the cold west-coast current that needs open sea poleward into the westerlies (0 = off)
    sst_offset: float = 0.0           # K, global SST tweak
    sst_source: str = "model"         # "observed": Earth grids use WOA18 monthly SST (diagnostic upper bound)
    wind_source: str = "model"        # "observed": Earth grids use reanalysis monthly surface winds (grid.obs_wind; diagnostic upper bound)
    land_offset: float = 0.0          # K, global land-column tweak
    inland_sea_warming: float = 2.0   # enclosed seas take 0.1*this of the land's swing
    lake_coupling: float = 0.0        # v4: lakes/small seas follow land temp (0 = off)
    sea_winter_mixing: float = 0.0    # e19: share of an enclosed sea's or lake's winter cooling toward the land that deep mixing cancels (0 = symmetric)
    land_amplitude: float = 1.0       # v4: scale of the continental seasonal swing
    storm_asym: float = 0.0           # v5: storm track stronger on the warm-current side
    storm_reach: float = 0.0          # v5: ... and this many degrees further equatorward
    tropical_storms: float = 0.0      # e47: storms over seas warmer than ~26-28 C (storm-track equivalent; 0 = off)
    tropical_storm_km: float = 600.0  # e47: ... and their reach inland from that sea
    cold_high_storms: float = 0.0     # e48: storms steered around the thermal highs, exp(-k x hPa) (0 = off)
    monsoon_descent: float = 0.0      # e49: column drying (1/day) per mm/day of the monsoon heating that drives descent here (0 = off)
    winter_mixing_deep: bool = False  # e50: only deep seas overturn in winter (sea_winter_mixing x depth share); shelf seas follow the air
    ocean_tau_unstable: float = 0.0   # e51: days for air colder than the sea under it to take the sea's temperature (convective; 0 = ocean_tau_days)
    land_stable_rate: float = 0.0     # e52: 1/day at which air warmer than the ground's equilibrium cools to it (stable winter layer; 0 = the land's own rate)
    instability: float = 0.0          # v6: extra rain efficiency in hot, moist air
    # time-step independence: soil-moisture memory in days (0 = the legacy
    # 0.75-per-step rule) and the most temperature/wind iterations within
    # each step (stops once nothing moves by 0.05 C; 1 = legacy one-step lag)
    soil_memory_days: float = 0.0
    t_iters: int = 1
    t_relaxation: float = 1.0        # fraction of temperature fixed-point update; 1 preserves legacy runs
    t_adaptive_retries: int = 0      # optional bounded retries with smaller damping
    t_anderson: bool = False        # accelerate retry stages; retain the full-update stopping test
    t_require_convergence: bool = False

    # ---------------------------------------------------------------- winds
    hadley_edge: float = 30.0         # annual-mean subtropical high latitude
    hadley_shift: float = 5.0         # seasonal poleward shift in summer
    itcz_mean: float = 5.0
    itcz_shift: float = 10.0
    itcz_shift_ocean: float = -1.0    # e55: the ITCZ's seasonal shift over open ocean (deg); land_broad blends to itcz_shift over broad land; < 0 = itcz_shift everywhere
    monsoon_westerly: float = 0.0     # e55: share of the trade speed by which air crossing the equator turns westerly before the ITCZ (Coriolis)
    monsoon_pressure_hpa: float = 0.0  # e55b: ... only where the model's own pressure falls poleward, fully at this many hPa per 1,000 km; 0 = everywhere
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
    orographic_scheme: str = "legacy"  # opt-in terrain-quadrature requires prepared fine DEM slopes
    orographic_gust_ms: float = 0.0   # opt-in weather wind std per horizontal component at unit storm strength [m/s]
    subsidence: float = 0.75          # subtropical-high suppression (0..1)
    subsidence_asym: float = 0.0      # east/west-of-basin asymmetry of the highs
    subsidence_summer: float = 0.0    # v7: highs sink harder in summer: x (1 + this * season)
    wet_cooling: float = 0.0          # v8: share of the summer warmth that wet ground evaporates away
    dry_heating: float = 0.0          # e54: K of land warmth on bone-dry soil under 480 W/m2 of sunshine, x (1 - soil wetness)
    dry_heating_chi0: float = 0.0     # e54b: ... only in continental air: x clip((chi - this) / (1 - this), 0, 1); 0 = everywhere
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
    maritime_mean: float = 0.0        # e28: maritime land swings around the nearby sea's annual mean (share x (1 - chi); 0 = the zonal land mean)
    upwelling: float = 0.0            # e1: coastal sea cooling (C) per 5 m/s of offshore Ekman transport
    # physics e2 (from the literature review of the remaining Earth failures)
    background_ascent: float = 1.0    # e2: the rain dynamics' baseline (the "1 +"); 0 = rain needs ascent
    convective_rain: float = 0.0      # e2: convective rain (mm/day) at column humidity convective_rh, x e^(11.4 dr)
    convective_rh: float = 0.6        # e2: ... its reference column relative humidity
    subcloud_evaporation: float = 0.0  # e2: rain evaporating below the cloud base: x exp(-this * z_LCL / 3 km)
    land_coupling_insolation: float = 0.0  # e2: land air coupling x (sunshine / 480 W m-2)^this (+ 1/30 d)
    ebm_land: str = "uniform"         # planet's land by latitude: uniform 30 %, or "earth" (Earth mode)
    ocean_transport: float = 0.0      # e27: the oceans' own poleward heat transport, x the air's diffusion (0 = none)
    ocean_heat_capacity: float = 1.0  # mixed-layer heat capacity x ~26 m of water (the zonal sea's seasonal swing and lag)
    ocean_mixed_seasonality: float = 0.0  # e29: mixed layer shallower in summer, deeper in winter (heat capacity x (1 -/+ this))
    cross_equatorial_transport: float = 0.0  # e30: northward ocean heat transport across the equator, PW (Earth ~0.4; 0 = none)
    cross_transport_ocean: float = 0.0  # e30b: share of that heat released into the sea only (0 = whole column, 1 = sea only)
    continental_mean: float = 0.0  # e31: annual-mean cooling (C) of deep continental land poleward of ~30-50 deg (long winter nights)
    continental_depth_lat: float = 0.0  # e32: e23's deep-continent amplification ramps in from this latitude to +20 deg (0 = everywhere, as before)
    continentality_lat: float = 0.0  # e33: the continental (chi > 0.5) widening of the seasons ramps in from this latitude to +20 deg (0 = everywhere)
    subgrid_orographic: float = 0.0  # e34: ascent from sub-grid hills, x relief (km) x wind speed / 5 m/s (0 = none)
    lee_drying: float = 0.0  # e35: descending lee air dries the column, rain ascent x exp(-this x downslope) (0 = none)
    dry_coupling: float = 0.0  # e36: dry ground couples the air to the land faster, sunshine coupling x (1 + this x dryness) (0 = none)
    sea_enclosure: str = "disc"       # inland-sea measure: "disc" (land within 400 km) or "rays" (e3)
    ocean_tau_stable: float = 0.0     # e3: days for air warmer than the sea to cool to it (0 = ocean_tau_days)
    eddy_heat: float = 1.0            # e3: storm-eddy exchange of heat as a share of that of moisture
    eddy_moisture_height_km: float = 0.0  # e4: eddies mix W*exp(z/H) (sea-level equivalent), H in km (0 = off)
    cloud_radiation: float = 0.0      # e4: K of land warming per unit of cloud deficit vs the latitude mean at 480 W m-2
    cloud_longwave: float = 0.0       # e4: scale of the clear-sky longwave anomaly (dry, clear air cools), 1 = physical
    cloud_reference: str = "domain"   # e43: cloud_radiation against the domain's own latitude mean ("domain") or the whole globe's land ("earth", Earth grids)
    snow_albedo: float = 0.0          # e16: K of land cooling under full snow cover per 480 W m-2 of sunshine
    flux_convergence: float = 0.0     # e17: share of column water brought in by low-level convergence into warm columns (0 = off)
    flux_scale_km: float = 300.0      # e44: scale (km) of the low-level convergence that brings water in (e17 used 300)
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
    edge_continental_drying: float = 0.0   # e24: land-edge inflow humidity cut by this share where the westerlies crossed ~5,000 km of land
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
    eddy_moisture_scale_km: float = 0.0  # e38: reach of the eddies' water exchange, km (0 = eddy_scale_km)
    upslope_free_wind: float = 0.0  # e39: share of the terrain drag removed from the wind that lifts air up slopes (0 = dragged wind)
    eddy_rh_cap: float = 0.0  # e38b: air the eddies move onto colder ground keeps at most its relative humidity (0 = off, 1 = full)
    ocean_rh_warm: float = 0.0  # e40: extra column humidity over seas warmer than 25 C, reached at 29 C (0 = off)
    moisture_wind_factor: float = 1.0  # e41: the wind that carries column water, x the surface wind (1 = unchanged)
    moisture_pressure_drag_ratio: float = 1.0  # opt-in column/surface Rayleigh drag; 1 = legacy aligned flow
    moisture_thermal_height_km: float = 0.0  # opt-in thermal-wind shear to an effective vapor height (0 = off)
    moisture_mass_balance: bool = False  # opt-in stationary dry-column projection of the moisture wind
    moisture_thermal_divergent_return: bool = False  # opt-in separate divergent return and thermal rotation
    moisture_thermal_anomaly_decay: bool = False  # opt-in stable surface/zonal thermal separation
    moisture_thermal_layer_winds: bool = False  # opt-in hydrostatic shear with common dry-mass projection
    moisture_two_layer: bool = False  # opt-in separate moist inflow and compensating upper transport
    moisture_upper_q_ratio: float = .15  # q_upper/q_lower for fixed two-branch humidity profile
    moisture_mass_tracer: bool = False  # opt-in common air mass for vapor advection, diffusion and storms
    moisture_reservoirs: bool = False  # opt-in independent lower/upper water, instead of a forced humidity ratio
    moisture_reservoir_mixing_days: float = 5.0  # symmetric vertical q exchange; 0 disables turbulent mixing
    moisture_reservoir_rain_scheme: str = "layer"  # historical layer closure, or column-convection with lower-air rain evaporation
    moisture_reservoir_temperature_profile: str = "moist"  # normalized capacity/supply shape: saturated moist or environmental lapse
    moisture_reservoir_lapse_k_km: float = 6.5  # environmental capacity lapse, independent of surface-elevation cooling
    moisture_ocean_hydrostatic: bool = False  # opt-in absolute ocean target from the selected hydrostatic thermal profile
    moisture_ocean_rh_taper: float = 0.0  # pressure-dependent RH shape; 0 uniform, .5 partial, 1 full tropospheric taper
    moisture_transport_form: str = "concentration"  # opt-in "flux": conservative face transport; requires flux_convergence=0
    eddy_moisture_scheme: str = "legacy"  # opt-in "conservative" or "conservative-rainout" (budgeted short storm hops)

    # ---------------------------------------------------------------- numerics
    downsample: int = 8               # source pixels per model cell
    steps_per_year: int = 73          # 73 x 5-day weeks
    seasonal_spinup_years: int = 0    # extra complete years before recording; 0 preserves existing fits
    seasonal_require_convergence: bool = False  # require repeatable annual T/rain/vapor/soil/snow cycles
    picard_iters: int = 3
    moisture_relaxation: float = 0.5  # retains legacy half-updates
    moisture_residual_tol: float = 0.0  # 0 retains fixed Picard count; >0 checks local equation
    moisture_require_convergence: bool = False
    transport_scheme: str = "upwind"  # optional 'exponential' fitted advection-diffusion
    solver_rtol: float = 1e-3        # linear sweep update / maximum boundary magnitude
    solver_max_iter: int = 400
    solver_require_convergence: bool = False  # strict profiles reject capped solves
    solver_recover: bool = False    # retry capped sweeps with Gauss-Seidel, then a checked direct solve

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
