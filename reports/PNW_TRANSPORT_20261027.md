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

Status: complete; three exact diagnostic reruns passed. No fitting or adoption.


## Measured results

All three actual integrations passed and reproduced their parent rainfall cells
and temperature scores exactly. The original r39 also reproduced every archived
monthly float32temperature/rainfall cell. Runtime was35.7seconds. Acquisition
and corrected figure rendering add no additional climate integrations.

Only4ocean footprints (191,166km²) pass the full selection;0land footprints pass.
Fifteen native footprints have sufficient coverage, but terrain and mixed-coast
exclusions remove the rest. This is a small coastal sample, not a validated
circulation score for the land or the entire Pacific basin.

| Profile | Annual land rain mm | Ocean vector RMSE m/s | Mean modeled vector speed m/s | Eastward bias m/s |
|---|---:|---:|---:|---:|
|r39|732.06|4.186|9.827|+2.995|
|Previous reservoirs|2543.19|4.122|9.950|+3.585|
|Corrected convection/recycling|2394.06|4.126|9.955|+3.589|

Observed regional land rainfall averages897.46mm/year; the reference ocean mean
vector speed is6.355m/s. The models broadly reproduce the winter/summer direction
shift, but eastward flow is too strong, including in r39. The rain correction
barely changes this circulation, supporting a separate transport investigation.
The near-equality of wind RMSE despite very different rainfall is evidence that
neither this speed error alone nor the scalar rain correction explains the
whole rainfall problem. The error may also depend on native vertical structure,
mean-flow moisture convergence, storm exchange, terrain and open boundaries.

Previous and corrected reservoirs give partial ocean water11.321/11.355mm
versus11.989observed; partial q ratios0.23364/0.23366 versus0.29139observed.
PW MAE1.141/1.147mm and shape MAE0.06086/0.06184 change little. Thus PNW humidity
shape is too bottom-heavy while Iberia's is too top-heavy; imposing a universal
lower upper-humidity ratio would not fix both regions physically. This diagnostic
does not add a new post-result gate or select any coefficient.

## Figure correction audit

The initial monthly wind rendering selected the January east/north pair rather
than twelve eastward months. `scripts/plot_pnw_transport.py` corrects the component
axis from the frozen saved arrays, with a separate analytic12month regression
check. Raw diagnostic numbers, original figures, source/protocol and all three
climates remain preserved. `figures.json` records the corrected plotter, raw
review digest and replacement figures; no climate was rerun. The published page
uses the corrected12month plot and simpler coast rendering for legible arrows.

The complete series now contains857actual Earth attempts,853passes and4old
preserved failures. The new reference audit adds3reruns to the854attempts after
the parent closure campaign. Atlas climates, settlement/economy and headline
accuracy remain unchanged.
