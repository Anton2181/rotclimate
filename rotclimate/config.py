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
    # optional eroded height map at source resolution built on these tier ramps (scripts/terrain_erosion.py build;
    # repository-relative path); empty = the tier ramps themselves
    terrain_file: str = ""
    lapse_rate: float = 6.0           # K / km (environmental)
    lapse_seasonal: float = 0.0       # e25: lapse rate x (1 + this x season index): steeper in summer, flatter in winter
    lapse_tropical: float = 0.0       # e146: extra K/km in the tropics (full to lapse_tropical_lat0, none by lat1); 0 = off
    lapse_tropical_lat0: float = 12.0
    lapse_tropical_lat1: float = 30.0
    relief_lapse: float = 0.0         # e147: extra K/km on height above the smoothed surrounding land; 0 = off
    relief_sigma_km: float = 150.0
    relief_lapse_lat0: float = 12.0   # e147: full equatorward of this |lat| ...
    relief_lapse_lat1: float = 40.0   # ... none poleward of this
    plateau_heating: float = 0.0     # e134: K x season index x broad-plateau weight added to air on high ground (summer warm, winter cold); 0 = off
    plateau_heating_km: float = 1.5  # e134: smoothed (300 km) ground height where the weight starts (full 2 km higher)
    plateau_heating_cell: bool = False  # e134b: also weight by the cell's own height above plateau_heating_km
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
    shelf_warm_currents: float = 0.0  # e56: share of the subtropical warm boundary current kept off shallow shelves (x (1 - deep-sea share))
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
    descent_warming: float = 0.0      # e131: K of land warming per mm/day of the e49 monsoon descent (compression of the sinking air; 0 = off)
    descent_warming_cap: float = 8.0  # e131: ceiling on that warming (K)
    monsoon_descent: float = 0.0      # e49: column drying (1/day) per mm/day of the monsoon heating that drives descent here (0 = off)
    winter_mixing_deep: bool = False  # e50: only deep seas overturn in winter (sea_winter_mixing x depth share); shelf seas follow the air
    ocean_tau_unstable: float = 0.0   # e51: days for air colder than the sea under it to take the sea's temperature (convective; 0 = ocean_tau_days)
    ocean_unstable_cap: float = 0.0   # e51b: K/day ceiling on e51's convective warming (a deep outbreak layer warms slowly; never below ocean_tau_days; 0 = no ceiling)
    land_stable_rate: float = 0.0     # e52: 1/day at which air warmer than the ground's equilibrium cools to it (stable winter layer; 0 = the land's own rate)
    land_stable_inland_rate: float = 0.0  # e52b: extra 1/day of e52 stable cooling x land share upwind (westerlies) over land_stable_fetch_km; 0 = off
    land_stable_fetch_km: float = 1000.0  # e52b: memory of the upwind land share
    land_stable_barrier_rate: float = 0.0  # e52c: extra 1/day of e52 stable cooling x clip(upwind crest above the cell / land_stable_barrier_km); 0 = off
    land_stable_barrier_km: float = 1.5  # e52c: crest height (km above the cell) for the full rate
    land_stable_barrier_fetch_km: float = 800.0  # e52c: how far upwind to look for the crest
    instability: float = 0.0          # v6: extra rain efficiency in hot, moist air
    heat_low_drying: float = 0.0      # e80: subsidence drying x exp(-this x hPa) under the heat lows the pressure winds build (last pass, negative pressure); 0 = off
    heat_low_branch: bool = False     # e80b: apply the e80 damping also to the e70b branch drying
    edge_inner: float = 0.0           # e81: land-edge inflow humidity = blend toward the RH of the nearest interior column (last step): 0 = fixed land_edge_rh (r45), 1 = zero-gradient
    edge_inner_warm_c: float = -99.0  # e115: e81 only where the inner ground is warmer than this (5 K ramp) and wet over the year; -99 = everywhere
    edge_pw_source: str = "observed"  # e116z: "observed" (NCEP at each cell, Earth only) or "zonal" (the globe's land mean at the cell's latitude; world-legal)
    edge_obs_pw: float = 0.0          # e116 (Earth cases only): land-edge inflow column water blends toward the observed (NCEP) monthly precipitable water; 0 = off
    dyn_omega: float = 0.0           # e144 (Earth cases only): large-scale rain ascent falls by up to this fraction under observed 500 hPa sinking; 0 = off
    dyn_omega0: float = 0.02         # e144: sinking [Pa/s] where the damping starts
    dyn_omega1: float = 0.04         # e144: sinking [Pa/s] where it is full
    dyn_omega_lat0: float = 0.0      # e144b: damping fades from full at lat0 to none at lat1 (deg); lat1 <= lat0 = no fade
    dyn_omega_lat1: float = 0.0
    dyn_omega_rh0: float = 0.0       # e144c: damp only where previous W/Ws exceeds this (ramping over 0.1); 0 = everywhere
    obs_pw_nudge: float = 0.0        # e143 (Earth cases only): land column water relaxes toward NCEP monthly PW at this rate [1/day]; 0 = off
    obs_pw_nudge_dry_only: float = 0.0  # e143: >0 nudges only columns wetter than observed, ramping in over this fraction of obs PW
    obs_pw_nudge_excess: float = 0.0  # e143c: dry-only nudge starts where W exceeds (1 + excess) x observed PW
    obs_pw_nudge_wet: float = 0.0     # e145: land columns drier than (1 - wet_excess) x observed PW gain toward it at this rate [1/day]; 0 = off
    obs_pw_nudge_wet_excess: float = 0.2
    obs_pw_nudge_wet_lat0: float = 0.0  # e145b: wet nudge fades from full at lat0 to none at lat1 (deg); lat1 <= lat0 = no fade
    obs_pw_nudge_wet_lat1: float = 0.0
    obs_pw_nudge_rh0: float = 0.0     # e143b: nudge only where previous W/Ws exceeds this (ramping over 0.1); 0 = everywhere
    obs_pw_nudge_h0: float = 0.0      # e143b: nudge fades out between h0 and h1 km elevation; h1 <= h0 = no fade
    obs_pw_nudge_h1: float = 0.0
    soil_init_fraction: float = 0.5   # e82: starting soil water as a share of the bucket (0.5 = r45)
    trade_heat_low: float = 0.0       # e83: same-hemisphere trades x (1 - this x clip(poleward pressure fall / monsoon_pressure_hpa, 0, 1)): trades give way to heat-low inflow; 0 = off
    edge_carry: float = 0.0           # e79: land-edge inflow carries the water of a column at T_col + this x max(latitude mean - T_col, 0), capped at local saturation, instead of a fixed RH of the local column; 0 = r44
    ice_saturation: float = 0.0       # e78: below 0 C the rain-maker judges the column against saturation over ice (es_ice/es_water)^this; 0 = water everywhere (r44)
    instability_cap: float = 0.0      # e84: the v6 instability boost x (1 - this x clip((chi - instability_cap_chi0) / (1 - chi0), 0, 1)), chi = share of the air that crossed land (desert air aloft caps convection); 0 = off
    instability_cap_chi0: float = 0.5
    storm_convection: float = 0.0     # e77: extra rain efficiency x storm index x warmth (15-23 C ramp) x moisture: summer showers under troughs and fronts, not under the subtropical highs; 0 = off
    instability_t0: float = 22.0      # e76: surface temperature (C) where the v6 instability boost starts (22 = v6; lower lets mid-latitude summers convect)
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
    tilt_scaling: float = 1.0         # e137: circulation latitudes follow the axial tilt: seasonal swings x (tilt / 23.44)^this, fixed bands x (tilt / 23.44)^(this x lat_band_tilt_exponent); Earth (23.44) exactly unchanged; 0 = off
    lat_band_tilt_exponent: float = 0.5  # e137: fixed latitude bands (Hadley edge, current bands, ramps) depend on tilt more weakly than the seasonal swings (declared, not fitted: one Earth tilt cannot fit it)
    hadley_edge: float = 30.0         # annual-mean subtropical high latitude
    hadley_shift: float = 5.0         # seasonal poleward shift in summer
    itcz_mean: float = 5.0
    itcz_shift: float = 10.0
    itcz_shift_ocean: float = -1.0    # e55: the ITCZ's seasonal shift over open ocean (deg); land_broad blends to itcz_shift over broad land; < 0 = itcz_shift everywhere
    itcz_mean_land: float = -99.0     # e106: the ITCZ's annual-mean latitude over broad land (land_broad blends from itcz_mean over open ocean); -99 = itcz_mean everywhere
    itcz_mirror_south: bool = False   # e112: Earth cases only - mirror itcz_mean / itcz_mean_land for southern regions run mirrored
    monsoon_westerly: float = 0.0     # e55: share of the trade speed by which air crossing the equator turns westerly before the ITCZ (Coriolis)
    monsoon_pressure_hpa: float = 0.0  # e55b: ... only where the model's own pressure falls poleward, fully at this many hPa per 1,000 km; 0 = everywhere
    monsoon_westerly_floor: float = 0.0  # e109: minimum share of monsoon_westerly applied where the poleward pressure fall is too weak (Coriolis turning without a heat low on the map); 0 = off
    monsoon_obs_pressure: float = 0.0  # e140: share (0-1) of the e55 gate's poleward pressure fall taken from NCEP sea-level pressure (Earth grids only; region maps miss heat lows off the map); 0 = off
    trade_obs_pressure: float = 0.0    # e140: the same for the e83 trade weakening
    convective_omega: float = 0.0      # e141: share (0-1) by which observed 500 hPa sinking caps convection (instability, closure, heated-land RH) on Earth grids; 0 = off
    convective_omega_ref: float = 0.03 # e141: omega (Pa/s) of full cap
    convective_omega_lat0: float = 0.0  # e141b: the cap is full equatorward of this latitude...
    convective_omega_lat1: float = 0.0  # ...and gone poleward of this one; lat1 <= lat0 = everywhere
    convective_omega_sea_chi: float = 0.0  # e141c: the latitude fade acts only on air off the sea (continental fetch chi below this; full at chi 0); 0 = fade everywhere
    monsoon_descent_tropics: float = 0.0     # e142: extra monsoon-descent drying, full equatorward of lat0, gone poleward of lat1; 0 = off
    monsoon_descent_tropics_lat0: float = 20.0
    monsoon_descent_tropics_lat1: float = 25.0
    trade_speed: float = 6.0          # m/s
    westerly_speed: float = 7.0       # m/s
    polar_speed: float = 3.0
    monsoon_strength: float = 1.0     # thermal-low wind scaling
    monsoon_scale_km: float = 500.0   # smoothing of the thermal pressure field
    cross_isobar_deg: float = 35.0    # friction turning toward low pressure
    terrain_drag: float = 0.5         # wind slow-down over high ground

    # ---------------------------------------------------------------- water
    ocean_rh: float = 0.80
    ocean_column_air: float = 0.0     # e58: share of the way the sea's column water moves from saturation at the SST to saturation at a colder column temperature (0.4 SST + 0.6 air over ~300 km)
    ocean_column_warm: float = 0.0    # e59: the same toward a warmer column temperature (summer air over cooler seas)
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
    dry_heating_warm_c: float = -99.0 # e54c: ... only on warm ground: x clip((land equilibrium - this) / 8 K, 0, 1); -99 = always
    dry_heating_arid: float = -1.0    # e54e: ... only where the soil is dry all year: x clip((one-year mean dryness - this) / (1 - this), 0, 1); -1 = always
    dry_heating_mean_c: float = -99.0 # e54d: ... only in warm climates: x clip((annual-mean land equilibrium - this) / 8 K, 0, 1); -99 = always
    dry_heating_cold_sst: float = -99.0  # e113: ... not near a sea colder than this (C, 3 K ramp; cold-current deserts); -99 = off
    dry_heating_cold_km: float = 300.0   # e113: inland fade of that exemption (km)
    root_gain: float = 0.0           # e114: extra bucket depth (x soil_bucket_mm) under rain-forest rain; 0 = off
    root_p0: float = 1200.0          # e114: annual rain (mm) where the extra depth starts
    root_p1: float = 800.0           # e114: ... and the rain above root_p0 for the full extra depth
    root_lat0: float = 0.0           # e114b: extra depth full equatorward of this |lat| (deg)...
    root_lat1: float = 0.0           # ...and none poleward of this; lat1 <= lat0 = no fade
    root_abs_beta: bool = False      # e114c: wetness judged against soil_bucket_mm, not the deepened store
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
    current_cold_lat0: float = 0.0    # e132: cold currents (cur < 0) fade to nothing at this |latitude| (0 = off) ...
    current_cold_lat1: float = 15.0   # e132: ... and are full from this |latitude| (eastern-boundary currents turn west into the equatorial currents)
    current_warm_lat0: float = 0.0    # e132b: warm currents (cur > 0) likewise fade to nothing at this |latitude| (0 = off) ...
    current_warm_lat1: float = 15.0   # e132b: ... and are full from this |latitude|
    upwelling: float = 0.0            # e1: coastal sea cooling (C) per 5 m/s of offshore Ekman transport
    # physics e2 (from the literature review of the remaining Earth failures)
    background_ascent: float = 1.0    # e2: the rain dynamics' baseline (the "1 +"); 0 = rain needs ascent
    convective_rain: float = 0.0      # e2: convective rain (mm/day) at column humidity convective_rh, x e^(11.4 dr)
    convective_rh: float = 0.6        # e2: ... its reference column relative humidity
    subcloud_evaporation: float = 0.0  # e2: rain evaporating below the cloud base: x exp(-this * z_LCL / 3 km)
    land_coupling_insolation: float = 0.0  # e2: land air coupling x (sunshine / 480 W m-2)^this (+ 1/30 d)
    ebm_land: str = "uniform"         # planet's land by latitude: uniform 30 %, or "earth" (Earth mode)
    wet_sun: float = 0.0              # e69: K of land cooling per unit of soil wetness above wet_sun_ref at 480 W m-2 of sunshine (drier: warming)
    wet_sun_ref: float = 0.5          # e69: the average land's soil wetness (bucket share of 75 %)
    rain_shading: float = 0.0         # e105: K of land cooling under heavy rain cloud at 480 W m-2 of sunshine, x (1 - exp(-recent rain / rain_shading_mm)); 0 = off
    rain_shading_mm: float = 5.0      # e105: mm/day of recent (300 km smoothed) rain at which the shading is 63 % of full
    rain_shading_wet_pow: float = 0.0 # e105b: x (one-year mean soil wetness) ** this: only lands wet all year sit under cloud for months; 0 = off
    storm_baroclinic: float = 0.0     # e68: storm band centred (by this share) on each meridian's baroclinic zone instead of the planet's latitude
    storm_baroclinic_cold_c: float = -99.0  # e68: count the contrast only where the smoothed air is below this (C; -99 = everywhere)
    storm_baroclinic_max_deg: float = 0.0  # e68: at most this many degrees from the planet's storm latitude (0 = no limit)
    storm_baroclinic_humid_rh: float = 0.0  # e68h: count the contrast only where the smoothed column is humid (full 0.2 above this relative humidity; 0 = everywhere)
    storm_plateau: float = 0.0        # e72: while the storm band would run into a high plateau upwind, pull it (by this share x plateau size) to the plateau's equatorward edge (0 = off)
    storm_plateau_m: float = 2500.0   # e72: plateau = land above this height (smoothed over ~150 km)
    storm_plateau_km: float = 3000.0  # e72: downwind e-folding distance of the plateau's steering
    storm_plateau_offset_deg: float = 3.0  # e72: the band runs this far poleward of the plateau's equatorward edge
    storm_plateau_area_km2: float = 1.5e6  # e72: plateau area for 63 % of the full steering (1 - exp(-area / this))
    storm_plateau_season: float = 9.0  # e72b: <= 1 replaces the band-meets-plateau trigger with the cold season: full pull below season index (this - 0.25), none above (this + 0.25); 9 = e72 trigger
    storm_plateau_global: bool = False  # e72c: on Earth regions, take the plateau upwind from the global elevation ring (earth.plateau_profile), not the region's window
    storm_plateau_reach_deg: float = 0.0  # e72d: pull only rows within this many degrees poleward of the plateau's poleward edge (full to reach - 5, none beyond); 0 = whole column (e72c)
    itcz_plateau_gain: float = 0.0    # e85: deg added to the summer ITCZ excursion x the plateau anchor (high plateau directly poleward, within ~itcz_plateau_lon_deg of longitude: Tibet north of India); 0 = off
    itcz_plateau_area_km2: float = 1.5e6  # e85: plateau area for 63 % of the full anchor (1 - exp(-area / this))
    itcz_plateau_lon_deg: float = 10.0  # e85: Gaussian half-width in longitude over which the plateau anchors the belt
    itcz_plateau_m: float = 0.0      # e87: plateau height for the e85 anchor (0 = storm_plateau_m): the Mexican plateau and Rockies (1.5-2.5 km) anchor the North American monsoon
    onset_suppression: float = 0.0   # e86: over land, x (1 - this x ramp) on the v6 warm-moist convective boost, ramp 0 -> 1 from (ITCZ - onset_gap_deg) to 5 deg poleward of it; 0 = off
    onset_base: float = 0.0           # e135: the e86 onset ramp also scales the base rain rate over land by (1 - this x ramp); 0 = off
    itcz_land_lag_days: float = -1.0  # e134: the rain belt over broad land follows the sun with this lag (days) instead of circulation_lag_days; <0 = off
    itcz_land_sharp: float = 1.0      # e136: over broad land the summer half of the belt's swing goes as s**this (>1: the belt holds south, then jumps; the West African 'monsoon jump'); 1 = off
    onset_base_lat: float = 22.0      # e135: ... only equatorward of this |latitude| (5-degree fade): the cap is the Saharan air layer over the tropical monsoons
    onset_gap_deg: float = 5.0        # e86: the rain belt runs this far equatorward of the land ITCZ (Saharan air layer over the shallow monsoon)
    slope_convection: float = 0.0     # e88: added warm-moist convective boost over sun-heated mountain slopes x clip(subgrid relief / slope_convection_km) x clip((T - 18) / 8) x moisture; 0 = off
    slope_convection_km: float = 1.0  # e88: subgrid relief (km) for the full slope trigger
    convective_rh_heat: float = 0.0   # e92: over land the convective closure's critical column RH falls by this x clip((T - 18) / 8, 0, 1):
                                      # surface heating, not column humidity alone, sets land convection; oceans unchanged; 0 = off
    convective_rh_gate: float = 0.0   # e93: e92's threshold drop x (1 - this x the e86 ramp): not poleward of the rain belt (dry air aloft); 0 = off
    convective_rh_gate_dry: float = 0.0   # e117: e93's gate x clip(chi_dry / this, 0, 1): the cap only in air off dry land (needs convective_rh_chi_dry); 0 = off
    convective_rh_gate_vwind: float = 0.0   # e118: e93's gate x clip(1 - poleward low-level wind / this, 0, 1) (m/s, 500 km smoothing); 0 = off
    convective_rh_gate_pole: float = 0.0   # e119: e93's gate x clip(dry land averaged 1,500 km poleward / this, 0, 1); 0 = off
    convective_rh_chi0: float = 0.0   # e93: e92's threshold drop x (1 - clip((chi - this) / (1 - this), 0, 1)): not in air that crossed land (desert air aloft); 0 = off
    convective_rh_chi_dry: float = 0.0  # e103: e93's chi blends toward a dry-land chi (land x annual soil dryness, carried the same way): wet forest air is not desert air aloft; 0 = off
    convective_cap_land: float = 0.0  # e104: over land the e2 closure's rate (mm/day) -> cap x tanh(rate / cap): no coastal 20+ mm/day deluge at column RH 0.64 (Maranhao); 0 = off
    convective_descent: float = 0.0   # e94: the e49 monsoon descent caps convection: cap = clip(descent / convective_descent_ref, 0, 1); the v6 boost and the e2
                                      # convective rate x (1 - this x cap), e93's threshold drop x (1 - cap) (Rodwell-Hoskins deserts: Arabia, Iran); 0 = off
    convective_descent_ref: float = 0.5  # e94: descent (mm/day of driving monsoon heating) at which the cap is full
    inflow_gain: float = 0.0          # e91: warm-sea inflow: land columns within reach of a warm sea relax toward marine humidity where the low-level
                                      # wind blows onshore; rate = this x the sea's evaporation rate x exp(-km from sea / inflow_km) x warm x onshore; 0 = off
    inflow_km: float = 300.0          # e91: inland e-folding distance (km)
    inflow_sst: float = 26.0          # e91: nearest-sea temperature (C) at which inflow starts (full 3 C above)
    inflow_rh: float = 0.0            # e91: target column humidity (fraction of land saturation); 0 = ocean_rh
    soil_feedback: float = 0.0        # e90: land recycling x (1 + this x clip((soil water / bucket - 0.5) / 0.5, 0, 1)): a wet monsoon land re-evaporates more of its rain; 0 = off
    continental_sea_air: float = 0.0  # e67: sea surface follows the (lagged) air over it x the continental share of that air
    continental_sea_lag_days: float = 60.0  # e67: the mixed layer's memory of that air
    warm_current_seasonality: float = 0.0  # e66: warm currents' sea-surface anomaly x (1 - k x season): mostly a winter effect
    ebm_land_scale: float = 1.0       # w2 (world): the planet's land fraction by latitude = Earth's x this (clipped 0.02-0.95)
    ebm_land_ice: float = 1.0         # e65: share of the latitude-mean land column's seasonal snow albedo kept (1 = all; ice sheets keep all)
    ocean_transport: float = 0.0      # e27: the oceans' own poleward heat transport, x the air's diffusion (0 = none)
    ocean_heat_capacity: float = 1.0  # mixed-layer heat capacity x ~26 m of water (the zonal sea's seasonal swing and lag)
    ocean_mixed_seasonality: float = 0.0  # e29: mixed layer shallower in summer, deeper in winter (heat capacity x (1 -/+ this))
    sst_zonal_obs: float = 0.0        # e138: share (0-1) of the regional zonal sea taken from the WOA18 zonal mean at the real latitude and season (the EBM's sea, with sst_offset, keeps the rest); 0 = off
    sst_zonal_obs_lat0: float = 0.0   # e138b: the blend ramps in from this real (Earth-equivalent) latitude...
    sst_zonal_obs_lat1: float = 0.0   # ...to full share here; lat1 <= lat0 = uniform blend
    sst_damping: float = 0.0  # e98: the regional sea's seasonal swing x (1 - this x ramp(|lat| from 10 deg to sst_damping_lat)); EBM untouched
    sst_damping_lat: float = 50.0  # e98: latitude where sst_damping is full
    sst_tropical: float = 0.0  # e102: K added to the regional zonal sea equatorward of 25 deg, fading to none at sst_tropical_lat; 0 = off
    sst_tropical_lat: float = 40.0  # e102: latitude where sst_tropical has faded out
    ocean_capacity_polar: float = 0.0  # e97: mixed-layer heat capacity x (1 + this x sin^2 lat): deeper winter mixing poleward
    cross_equatorial_transport: float = 0.0  # e30: northward ocean heat transport across the equator, PW (Earth ~0.4; 0 = none)
    cross_transport_ocean: float = 0.0  # e30b: share of that heat released into the sea only (0 = whole column, 1 = sea only)
    continental_mean: float = 0.0  # e31: annual-mean cooling (C) of deep continental land poleward of ~30-50 deg (long winter nights)
    continental_depth_lat: float = 0.0  # e32: e23's deep-continent amplification ramps in from this latitude to +20 deg (0 = everywhere, as before)
    continentality_lat: float = 0.0  # e33: the continental (chi > 0.5) widening of the seasons ramps in from this latitude to +20 deg (0 = everywhere)
    subgrid_orographic: float = 0.0  # e34: ascent from sub-grid hills, x relief (km) x wind speed / 5 m/s (0 = none)
    lee_drying: float = 0.0  # e35: descending lee air dries the column, rain ascent x exp(-this x downslope) (0 = none)
    subsidence_branch: float = 0.0    # e70: sinking along the Hadley cell's whole descending branch (ITCZ + gap to the edge), x this (0 = only the band at the edge)
    subsidence_warming: float = 0.0   # e71: K of land warming by the descending branch's compression (the e70 plateau), x (1 + subsidence_summer x season)
    subsidence_warming_taper: float = 0.0  # e71b: degrees over which the warming fades to zero at the Hadley edge (0 = none)
    subsidence_warming_wet: float = 0.0    # e71c: share of the warming that wet ground loses (rain means rising air)
    subsidence_warming_chi0: float = 0.0   # e71d: only air that has crossed land carries the warmth down: x clip((chi - this) / (1 - this), 0, 1); 0 = everywhere
    subsidence_warming_rain: float = 0.0   # e71e: x exp(-recent smoothed rain / this, mm/day): no warming under rising (raining) air; 0 = off
    subsidence_warming_top_m: float = 0.0  # e71f: none above this elevation, full 1,000 m below it (summer plateaus rise); 0 = off
    subsidence_branch_drying: float = 0.0  # e70b: column drying (1/day) along the descending branch's core, fading over 10 deg to the Hadley edge (0 = off)
    subsidence_branch_dry_rain: float = 0.0  # e70c: e70b x exp(-recent smoothed rain / this, mm/day): no dry-air descent under rising air; 0 = off
    subsidence_branch_gate_winter: float = 0.0  # e110: share of the e70c rain gate removed where the ITCZ lies across the equator; 0 = off
    subsidence_branch_gate_winter_deg: float = 5.0  # e110: ITCZ latitude (deg, other hemisphere) over which the removal ramps in
    subsidence_branch_gate_lat: float = 0.0  # e110b: also remove the gate equatorward of this latitude (5 deg ramp); 0 = off
    subsidence_branch_gap: float = 8.0  # e70: degrees poleward of the ITCZ where the descending branch's sinking begins
    subsidence_warming_gap_land: float = -1.0  # e107: e71's warming starts this far poleward of the ITCZ over broad land (land_broad blends from subsidence_branch_gap over sea); < 0 = subsidence_branch_gap everywhere
    subsidence_warming_land_minlat: float = 0.0  # e107b: the e107 land start never runs equatorward of this latitude (deg; 0 = no floor)
    heat_barrier_km: float = 0.0     # e108: heat exchange between neighbouring cells scaled by exp(-|elevation step| / this); 0 = off
    dry_coupling: float = 0.0  # e36: dry ground couples the air to the land faster, sunshine coupling x (1 + this x dryness) (0 = none)
    sea_enclosure: str = "disc"       # inland-sea measure: "disc" (land within 400 km) or "rays" (e3)
    ocean_tau_stable: float = 0.0     # e3: days for air warmer than the sea to cool to it (0 = ocean_tau_days)
    eddy_heat: float = 1.0            # e3: storm-eddy exchange of heat as a share of that of moisture
    eddy_heat_terrain_km: float = 0.0  # e100: eddies mix heat through low ground: each cell's weight in the eddy mean x exp(-elevation / this); 0 = off
    eddy_heat_terrain_relative: float = 0.0  # e100b: 1 = eddy_heat_terrain_km blocks only ground above the receiving cell (0 = absolute e100)
    eddy_heat_terrain_offset_km: float = 0.0  # e100c: relative mode only: ground less than this above the cell does not block
    eddy_moisture_height_km: float = 0.0  # e4: eddies mix W*exp(z/H) (sea-level equivalent), H in km (0 = off)
    cloud_radiation: float = 0.0      # e4: K of land warming per unit of cloud deficit vs the latitude mean at 480 W m-2
    cloud_longwave: float = 0.0       # e4: scale of the clear-sky longwave anomaly (dry, clear air cools), 1 = physical
    lw_ref_rh: float = 0.0            # e120: cloud_longwave's reference column = this x w_sat(zonal land T) instead of the domain's latitude mean; 0 = off
    land_phase_days: float = 0.0  # e121: land seasonal phase shift x (0.5 - advected land share), days (> 0 = maritime earlier)
    continental_depth_highland_m: float = 0.0  # e122: continental_depth fades to 0 from this smoothed elevation to +1,000 m (0 = off)
    maritime_mean_lat: float = 0.0  # e123: maritime_mean ramps in from this |lat| to +15 deg (0 = everywhere)
    maritime_mean_warm_only: bool = False  # e124: maritime_mean shifts the centre only toward a warmer sea mean
    maritime_mean_clip: bool = False  # e131: cap the maritime_mean weight at 1 (centre never past the sea mean)
    continentality_maritime: float = 1.0
    sst_damping_heat_only: bool = False
    sea_ice: float = 0.0
    sea_ice_melt_days: float = 0.0
    sea_ice_land_gate: float = 0.0   # e139: e127b ice gate air moved toward the air over land within ~400 km (only colder) by this x land share; 0 = off
    sea_ice_air_c: float = -99.0
    cloud_reference: str = "domain"   # e43: cloud_radiation against the domain's own latitude mean ("domain") or the whole globe's land ("earth", Earth grids)
    snow_albedo: float = 0.0          # e16: K of land cooling under full snow cover per 480 W m-2 of sunshine
    snow_inversion: float = 0.0       # e128: K of 2 m cooling under full snow cover in full darkness (surface inversion)
    snow_inversion_s: float = 200.0   # e128: daily-mean insolation (W m-2) above which no inversion persists
    snow_melt_sun: float = 0.0       # e138: mm/day of snowmelt per 480 W m-2 of daily sunshine (radiation melt), ramping in from snow_melt_sun_c; 0 = off
    snow_melt_sun_c: float = -6.0    # e138: air temperature (C) where radiation melt starts (full 3 K above)
    pole_frozen_sea: float = 0.0      # e129: weight of winter-frozen sea in the poleward cold-air source (pole_land); 0 = land only
    continental_mean_season: float = 0.0   # e130: continental_mean shift x (1 - this x season index): more in winter, less in summer (0 = year-round)
    continental_mean_season_lag: float = 0.0   # e130: days after the winter solstice of the strongest shift
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
    zonal_land_friction: float = 0.0  # e57: share by which surface friction over land slows the zonal belts (land smoothed over ~300 km; the pressure wind has its own land drag, e5)
    heat_land_friction: float = 0.0   # e62: as e57, but only in the wind that carries heat (the surface layer); the wind that carries water keeps its own share (water_land_friction)
    shelf_air_coupling: float = 0.0   # e64: shallow seas (the shelf share of e50's depth rule) take this share of the gap to the lagged air above them
    shelf_air_enclosed: bool = False  # e64b: ... only on enclosed shallow seas (x the enclosure share)
    shelf_air_lag_days: float = 45.0  # e64: ... the air felt with this memory (a 30-60 m water column's lag)
    inland_sea_lag_days: float = 0.0  # e63: enclosed seas and lakes follow the land's equilibrium with this memory (their own mixed layer's lag; 0 = at once)
    water_land_friction: float = 0.0  # e62: as e57, but only in the wind that carries water, lifts it over terrain and makes convergence (~850 hPa, little slowed by the ground)
    far_fetch: float = 0.0            # e6: weight of the far-field upwind land share at the domain edge (0 = local land)
    wind_cap: float = 0.0             # e6: m/s ceiling of the temperature-driven wind, soft above half of it (0 = none)
    soil_bucket_mm: float = 0.0       # e8: soil water a land cell holds for energy-limited evaporation (0 = recent-rain recycling)
    soil_wet_cooling: bool = False    # e8b: wet_cooling judges wetness by the bucket's soil water, not recent rain
    ocean_sink: float = 1.0           # e11: fraction of sea uptake kept when air is moister than the sea's equilibrium (1 = symmetric)
    land_edge_rh: float = 0.5         # column humidity (of saturation) of air entering the grid over land
    edge_itcz_rh: float = 0.0         # e133: share (0-1) of the way from the edge RH to edge_itcz_rh_max for land-edge inflow at the model's ITCZ, Gaussian in latitude; 0 = off
    edge_itcz_rh_max: float = 0.8     # e133: RH of air entering over land in the rain belt
    edge_itcz_width: float = 10.0     # e133: Gaussian half-width (deg latitude) about the ITCZ
    edge_itcz_poleward_width: float = 0.0  # e133b: Gaussian half-width (deg) on the poleward side of the ITCZ; 0 = symmetric
    edge_continental_drying: float = 0.0   # e24: land-edge inflow humidity cut by this share where the westerlies crossed ~5,000 km of land
    high_drying: float = 0.0          # e10: rain-making ascent x exp(-this x hPa of the pressure winds' high anomaly)
    marine_layer: float = 0.0         # e4: max share of a coastal cell under marine air (0 = off)
    marine_reach_km: float = 40.0     # e4: sea-breeze reach of the marine air
    marine_inversion_m: float = 700.0  # e4: inversion height: ground above it (or behind a crest above it) is continental
    marine_contrast: float = 5.0      # e4: land-minus-sea warmth (K) for a full marine layer
    eddy_barrier_km: float = 0.0      # e75: eddy water reaching a cell is capped at saturation at the highest ground this far upwind (eddy-scale mean wind) when that ground stands above the cell; 0 = off
    eddy_barrier_crest: float = 0.0   # e75b: barrier height = mean ground + this x (cell's highest ground - mean): 0 = cell means, 1 = crests
    eddy_barrier_dz_km: float = 0.5   # e75: the cap acts fully once the upwind barrier stands this much above the cell (linear below)
    eddy_rainout: float = 0.0         # e3: eddy moisture steps capped at crest saturation / this (0 = off)
    eddy_rainout_padded: bool = False  # e74b: the e3 steps run on one field padded by the full kernel's reach (edge values), then cropped, so an unbinding cap equals the plain eddy mix; False = each step pads its own edges (e3 as run before 15 Nov 2026)
    eddy_rainout_accounted: bool = False  # e74c: with eddy_rainout_padded, the water each step clips at the crest rains there (passed to the solver as storm condensate) instead of vanishing
    eddy_rainout_relief_km: float = 0.0  # e74: the e3 crest cap acts only where the ground stands above its eddy-scale surroundings, fully at this many km (cap / clip(relief / this, 1e-6, 1)); 0 = everywhere (e3)
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
    eddy_upwind_days: float = 0.0     # e61: eddies draw their water from upwind: the mixing source moves against the eddy-scale mean wind by this many days of travel (0 = isotropic)
    eddy_cap_contrast_k: float = 0.0  # e60: e38b only where a column is colder (sea-level equivalent) than the eddies' surroundings, in full this many K colder (0 = everywhere)
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
    moisture_flux_scheme: str = "upwind"  # opt-in "exponential" face fitting; single-column flux only
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
