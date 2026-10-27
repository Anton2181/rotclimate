# Pacific Northwest native circulation audit — 27 October 2026

The reservoir experiments inherit excessive Pacific Northwest advective supply
from the earlier conservative-transport implementation. This separate audit
compares actual circulation and humidity with coarse external pressure-level
reanalysis, before choosing a wind or boundary correction. It fits no parameter,
changes no atmospheric forcing and adopts no climate.

The predeclared plan is `calibration/pnw_transport_20261027/plan.json`: three
actual reruns of r39, previous no-mixing reservoirs and corrected no-mixing
convection/recycling. All use the parent's56km model, geography and parameters.
Their rainfall cells and temperature statistics must reproduce the frozen
parent exactly. The original r39 additionally reproduces its original archived
monthly float32temperature/rainfall cells. Reruns count as three actual Earth
integrations, separately from the42case parent comparison.

NOAA PSL NCEP/NCAR1981–2010 monthly normals supply pressure-level east/north
winds, specific humidity and925hPa geopotential. The new geographic subset uses
native2.5degree indices14–22latitude,92–102longitude, covering the PNW and nearby
Pacific. The established reader verifies URLs, hashes, variable metadata,
coordinates, levels, units and finite ranges. Specific humidity is recovered
from its normalized mixing ratio before pressure integration.

The same native footprint aggregation and full projection Jacobian as earlier
audits transform model vectors to geographic east/north. Require at least80%
covered footprint, at most20% land for ocean or at least80% land for land, and
all reference925hPa heights above modeled terrain. Humidity diagnostics further
exclude any model925hPa below-ground footprint. Use Gregorian month durations
and physical areas, rather than treating fine model cells as independent
observations. Plot fixed DJF/JJA native vectors and every monthly profile.

Reference q-weighted925–300hPa wind is a partial column and a product of monthly
means; it omits transient q'u' transport. Modeled moisture winds diagnose a
whole column and do not provide pressure-resolved circulation. The mismatch is
explicit: this is a useful circulation check, not an exact measured moisture
flux or a causal attribution of rainfall error. Partial modeled humidity uses
piecewise-uniform q in the two broad layers over matched pressure intervals.
Coarse reanalysis is model-assisted;1981–2010 differs from the WorldClim rainfall
period1970–2000. No native observed vector or humidity enters the simulation.

Status: source/reference plan declared before new diagnostic scores; pending.
