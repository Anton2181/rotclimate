# V10 water and storm prototype: first Earth pilot

14 October 2026. The user authorized the larger physics avenue. An isolated
prototype and bounded pilot are implemented in `rotclimate_v10/` and
`scripts/run_v10_pilot.py`. No regional integration or calibration was run by
the assistant. The production atlas and frozen v9 sources/inputs are unchanged.

Follow-up: the user completed this pilot. Water accounting passes but rainfall
skill fails; the next isolated heat/terrain experiment is described in
[the results and next run](v10_heat_check.md). This document preserves the
original pilot protocol.

## Run this next

From the project directory:

```sh
caffeinate -i .venv/bin/python -u scripts/run_v10_pilot.py --fetch --run
```

This downloads about 46 MB of public data, prepares two regions at 60 km,
and runs four cases sequentially: California and Iberia, each with passing
storms and with mean flow alone. There is no search or parameter fitting.
Each case has three complete 365-day years with the same weather repeated.
Year 1 warms up the stores; comparing years 2 and 3 tests whether one versus
two warm-up years changes the final rainfall. These are not independent weather
samples. All four cases use identical model settings and the same storm seed.

Runtime for the new engine has not been measured on an Earth domain. Monthly
progress prints elapsed time and an estimate for the rest of the current year.
The estimate is based on completed months and can change with storm activity.
There is no reason yet to reserve another eight-hour parameter sweep.

Completed years are saved atomically. Repeating the same command resumes those
years after verifying code, configuration, input hashes and physical budgets.
An interrupted, unfinished year restarts. A code/input change requires a new
`--out` directory; caches cannot silently mix model versions. Physical failures
are recorded, and other independent cases continue. A failed or unsettled case
cannot be used as a successful physics comparison.

Outputs in `output/v10_earth_pilot/`:

- `summary.md` and `summary.json`: rainfall comparisons and settling status.
- `california_rainfall.png` and `iberia_rainfall.png`: monthly rain and error maps.
- Four case folders: yearly state/rain arrays, full annual water ledgers,
  per-year checksums, summaries and monthly `progress.json` for status checks.
- `manifest.json`: exact experiment provenance. Raw data, source URLs/hashes
  and prepared-region hashes are retained under `data/v10_earth/`.

Without `--run`, the command prints its plan without creating files, downloading
or simulating. `--fetch` is optional after the data have been obtained. No atlas
export is included in this first Earth experiment.

## What changed physically

The old approximate seasonal water solve is replaced here by explicit transient
transport through two atmospheric layers. Horizontal dry-air fluxes and a
diagnosed vertical exchange satisfy each layer's mass balance; the column flux
is the discrete curl of a streamfunction plus zonal background flow. The upper
layer provides the return flow needed to compensate lower-layer convergence.
Water moves as a mixing ratio with those exact air fluxes, using donor-cell
finite volumes and a positive CFL limit. Convergence is not a water source.

Idealized disturbances move along a prescribed seasonal track, with stronger
winter activity. Terrain reduces lower-layer flow and induces compensated
vertical/upper flow. This is a **kinematically forced regional water model**:
it does not solve momentum, pressure, atmospheric energy, or ocean dynamics.
Its tracks and background circulation remain hypotheses to evaluate.

Ocean evaporation uses a wind/humidity bulk relation with a declared cap. Land
evaporation is limited by a finite soil store, humidity and prescribed seasonal
demand. Saturation excess in either layer rains out immediately. Land rain fills
the soil and overflows as runoff; sea rain returns to the external ocean.
There is no snow, cloud-water transport, delayed fallout or latent-heat feedback
yet. There is also no unresolved exchange term in this first pilot.

All water stores are nonnegative. Per step, in domain-mean millimetres:

```
change in atmospheric vapour + soil water
  = ocean evaporation - ocean rain - runoff - boundary export
    + explicitly recorded roundoff correction
```

Land evaporation and land rain are internal transfers. Imports have negative
boundary export. Per-step error must be <=1e-9 mm; independent annual inventory
closure must be <=1e-6 mm. Column air-continuity error must be <=1e-10 kg/m²/s.
Roundoff correction is separately reported, never described as physical water.
Passing these checks establishes accounting, not realistic climate.

## Forcing and independent reference

**Temperature is observed forcing, not a model prediction.** Monthly WorldClim
land temperatures and NOAA sea temperatures set saturation capacities. We are
isolating whether water transport delivers plausible rainfall before adding a
new temperature/energy model. No temperature skill or full climate-zone skill
will be claimed from this experiment.

Observed precipitation is stored separately from the model `Domain`; transport,
weather, evaporation and condensation never receive it. It is read only by
the scoring/reporting stage. No painted fantasy-zone masks enter this pilot.

Sources:

- [WorldClim 2.1](https://www.worldclim.org/data/worldclim21.html): 10-arcminute
  land elevation and 1970–2000 monthly mean temperature/rainfall. Public
  [download index](https://geodata.ucdavis.edu/climate/worldclim/2_1/base/).
- [NOAA OISST V2](https://psl.noaa.gov/data/gridded/data.noaa.oisst.v2.html):
  1971–2000 long-term monthly SST. Data provided by NOAA PSL, Boulder, Colorado,
  USA, from [its website](https://psl.noaa.gov/). The one-year climatology-period
  mismatch is declared. The official 1.56 MB file and its small remote metadata
  responses were checked; the gridded data were left for the user to download.

The reader supports the official packed classic NetCDF format, including scale,
offset and missing values. GeoTIFF sampling uses georeferencing and nodata tags;
valid negative land elevations remain land. Nearest-cell sampling onto a uniform
regional Cartesian grid is a pilot approximation, not conservative remapping.
Ocean SST holes are nearest-filled. Missing land-temperature samples are marked,
filled for forcing and excluded from scoring. Two model cells at each boundary
are excluded from scoring. These choices and the fixed boundary humidities
limit what regional skill can establish; regional boundary/resolution sensitivity
will be needed before stronger claims.

## How to judge the pilot

Primary diagnostics: annual rain bias/RMSE, monthly rain MAE, October–March rain
fraction error, and coastal (<150 km) versus inland (>300 km) annual rain.
Seasonal fractions exclude observed annual rain below 50 mm and model rain
below 1 mm, whose fractions are unstable; their scored-cell count and model
near-zero-rain count are reported explicitly. Continuous rainfall is the target,
not merely a Köppen label. Regional averages include all scored land, including
dry interiors; maps should be read alongside the averages.

Settling requires years 2/3 differences at the 95th percentile of <=1 mm/month
and <=5 mm/year over scored land, and <=1 mm for each final water-store field.
These are declared development tolerances, not a physical uncertainty estimate.

First ask whether explicit storms improve wet-season rainfall and the spatial
wet-coast/dry-interior contrast against mean-only circulation, without budget
errors. California is the initial development case; Iberia is a transfer check
using exactly the same physics, not a separately tuned result. A single shared
weather seed is not an ensemble or a final held-out statistical validation.
Report negative results as well as improvements. If unsettled, extend settling
as a separate experiment before interpreting accuracy differences.

Only after the Earth diagnostics support the mechanism should we connect it to
the fantasy geography and compare with saved v9 fields. The user's Mediterranean
and dry-zone protections remain in force. A later qualifying fantasy result can
update the atlas; this Earth pilot cannot justify that update by itself.

## Fast verification

25 new focused tests cover both vertical donor signs, uniform mixing-ratio
preservation with compensated divergent flow, open/closed water budgets,
positive stores, manufactured transport refinement, terrain/weather mass
continuity, Gregorian months, packed SST and TIFF input, checkpoint integrity,
interruption recovery, read-only defaults and a full reporting workflow with
fake integrations. The relevant v9 policy/audit tests also pass: 49 total.
Only a tiny manufactured zero-flow integration was executed in testing; no
real regional climate simulation, calibration or atlas export was launched.
