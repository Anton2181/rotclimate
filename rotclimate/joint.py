"""Separate shared climate laws from an invented planet and numerical settings.

This is the input boundary for new constrained joint experiments, not a new
optimizer or a claim that the parameterized physics is a complete Earth GCM.
Historical earth.earth_params semantics remain untouched for reproducibility.
"""
from dataclasses import asdict, fields

from .config import Params

WORLD_FIELDS = frozenset("""
beyond_continuity_km beyond_east beyond_east_gap_km beyond_east_land beyond_north
beyond_north_gap_km beyond_north_land beyond_northeast_land beyond_relief_m beyond_seed
beyond_south beyond_south_gap_km beyond_south_land beyond_southeast_land beyond_style
beyond_west beyond_west_gap_km beyond_west_land ebm_land eccentricity far_pole_land
greenhouse_wm2 lat_center map_height_mi map_width_mi north_bearing pad_km
perihelion_after_solstice planet_radius retrograde solar_flux tier_tops tilt winter_solstice_day
year_days
""".split())

NUMERICAL_FIELDS = frozenset("""
downsample moisture_relaxation moisture_require_convergence moisture_residual_tol picard_iters
seasonal_require_convergence seasonal_spinup_years solver_max_iter solver_recover
solver_require_convergence solver_rtol steps_per_year t_adaptive_retries t_anderson t_iters
t_relaxation t_require_convergence transport_scheme
""".split())

SHARED_FIELDS = frozenset("""
background_ascent bl_drag_land bl_drag_ocean circulation_lag_days cloud_longwave cloud_radiation column_saturation_scheme
cloud_reference cold_high_storms continental_depth continental_depth_lat continental_mean
continentality continentality_lat convective convective_rain convective_rh
cross_equatorial_transport cross_isobar_deg cross_transport_ocean current_gyre current_scale_km
current_strength shelf_warm_currents zonal_land_friction ocean_column_air ocean_column_warm eddy_cap_contrast_k eddy_upwind_days divergence_drying dry_coupling dry_heating dry_heating_chi0 eddy_heat eddy_moisture_height_km
eddy_moisture_scale_km eddy_moisture_scheme eddy_rainout eddy_rate eddy_rh_cap eddy_scale_km
eddy_seasonality edge_continental_drying evap_tau_days far_fetch flux_convergence flux_scale_km
hadley_edge hadley_shift heat_diffusion high_drying inland_sea_warming instability itcz_mean
itcz_shift itcz_shift_ocean monsoon_westerly monsoon_pressure_hpa lake_coupling land_amplitude land_coupling_insolation land_edge_rh land_heat_capacity
land_offset land_radiative_days land_recycling land_stable_rate land_tau_days lapse_rate
lapse_seasonal lee_drying marine_contrast marine_inversion_m marine_layer marine_reach_km
maritime_mean moisture_diffusion moisture_mass_balance moisture_thermal_layer_winds moisture_thermal_anomaly_decay moisture_thermal_divergent_return moisture_two_layer moisture_upper_q_ratio moisture_mass_tracer moisture_reservoirs moisture_reservoir_mixing_days moisture_reservoir_rain_scheme moisture_reservoir_temperature_profile moisture_reservoir_lapse_k_km moisture_ocean_hydrostatic moisture_ocean_rh_taper moisture_wind_factor moisture_pressure_drag_ratio moisture_thermal_height_km moisture_transport_form monsoon_descent monsoon_heating
monsoon_rain0 monsoon_scale_km monsoon_strength ocean_heat_capacity ocean_mixed_seasonality
ocean_rh ocean_rh_warm ocean_sink ocean_tau_days ocean_tau_stable ocean_tau_unstable
ocean_transport orographic orographic_gust_ms orographic_scheme polar_speed precip_tau_days
rh_spread rh_threshold sea_enclosure sea_winter_mixing seasonal_column_lapse slp_large slp_local
slp_local_km slp_scale_km snow_albedo soil_bucket_mm soil_memory_days soil_wet_cooling
sst_offset sst_source wind_source storm_asym storm_reach storm_seasonality storm_track storm_width
subcloud_evaporation subgrid_orographic subpolar_current subsidence subsidence_asym
subsidence_drying subsidence_summer subsidence_width subtropical_high subtropical_high_scale_km
subtropical_high_seasonality subtropical_high_width sverdrup terrain_drag trade_land trade_speed
tropical_storm_km tropical_storms upslope_free_wind upwelling westerly_speed wet_cooling
wind_cap winter_mixing_deep
""".split())

# Fixed reference for the WorldClim-era Earth benchmark, not an assertion
# about 200 AD CO2. greenhouse_wm2 is an anomaly relative to this model baseline.
EARTH_FORCING = dict(tilt=23.44, retrograde=False, eccentricity=0.0167,
                     perihelion_after_solstice=13.0, year_days=365,
                     winter_solstice_day=354.5, solar_flux=1.0,
                     greenhouse_wm2=0.0, planet_radius=1.0,
                     north_bearing=0.0, ebm_land="earth")


def validate_partition():
    groups = [WORLD_FIELDS, NUMERICAL_FIELDS, SHARED_FIELDS]
    known = {field.name for field in fields(Params)}
    if any(a & b for i, a in enumerate(groups) for b in groups[i+1:]):
        raise ValueError("Joint parameter blocks overlap")
    classified = set().union(*groups)
    if classified != known:
        raise ValueError("Classify new joint parameters explicitly: " +
                         str(sorted(classified ^ known)))


def require_strict(params):
    if not (params.t_require_convergence and params.moisture_require_convergence
            and params.solver_require_convergence and params.moisture_residual_tol > 0):
        raise ValueError("Joint experiments require the verified numerical profile")
    if params.sst_source != "model":
        raise ValueError("Joint experiments require modelled SST; observed SST is diagnostic")
    if params.cloud_radiation > 0 and params.cloud_reference != "domain":
        raise ValueError("Joint cloud radiation requires the shared domain reference")


def earth_profile(physics):
    """Shared theta + numerical profile + fixed Earth forcing/geography.

    Pass this through earth.earth_params for the actual region/hemisphere.
    No invented-world geometry or forcing can enter the Earth benchmark.
    Regional remote-monsoon descent still uses observed global rain; this
    boundary does not turn conditional regional skill into coupled validation.
    """
    validate_partition()
    require_strict(physics)
    values = asdict(physics)
    overrides = {name: values[name] for name in SHARED_FIELDS | NUMERICAL_FIELDS}
    return Params().replace(**overrides).replace(**EARTH_FORCING)


def world_profile(physics, world):
    """Shared theta and numerics from physics; only declared world fields from world.

    The full world profile's stale physics and relaxed solver settings are
    deliberately excluded. Resolution changes must be explicit after composition.
    """
    validate_partition()
    require_strict(physics)
    values = asdict(world)
    return physics.replace(**{name: values[name] for name in WORLD_FIELDS})


def update_block(profile, block, changes):
    """Reject optimizer coordinates assigned to the wrong parameter object."""
    validate_partition()
    groups = dict(physics=SHARED_FIELDS, world=WORLD_FIELDS, numerics=NUMERICAL_FIELDS)
    if block not in groups:
        raise ValueError("Unknown joint parameter block: " + block)
    invalid = set(changes) - groups[block]
    if invalid:
        raise ValueError("Parameters outside " + block + " block: " + str(sorted(invalid)))
    return profile.replace(**changes)


def describe(physics, world):
    earth = earth_profile(physics)
    invented = world_profile(physics, world)
    p, w = asdict(physics), asdict(world)
    return dict(
        shared_physics={name: p[name] for name in sorted(SHARED_FIELDS)},
        world={name: w[name] for name in sorted(WORLD_FIELDS)},
        numerics={name: p[name] for name in sorted(NUMERICAL_FIELDS)},
        earth_profile=asdict(earth), world_profile=asdict(invented),
        ignored_world_profile_values={name: w[name] for name in sorted(SHARED_FIELDS | NUMERICAL_FIELDS)
                                      if w[name] != p[name]},
        earth_forcing=EARTH_FORCING.copy(),
        interpretation="Input separation only. Hard Earth skill, SST, numerical and world transfer gates "
                       "must still be declared and passed before adopting a joint fit. Earth remote "
                       "monsoon descent is observed-rain-forced; fantasy descent is generated.")
