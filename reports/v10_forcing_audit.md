# Heat experiment results: check circulation and atmospheric profiles next

The user completed all eight heat/terrain cases (24 simulated years) and one
extra unchanged year for the original Iberia mean-only control. The assistant
verified array checksums, water/static-energy budgets and both frozen source
fingerprints, then analysed saved fields and prescribed circulation only.
No new climate integration or calibration was launched by the assistant.

## Results

Storm cases, monthly rainfall MAE; lower is better:

| Region | Original fixed-temperature | Heat with terrain drag | Heat without drag |
|---|---:|---:|---:|
| California | 115.87 mm | 235.70 mm | 143.57 mm |
| Iberia | 89.57 mm | 122.99 mm | 76.10 mm |

None of the eight cases passes every declared screening criterion. All fail
the temperature-departure screen and seven fail rain/storage settling. The
one settled new case, California storms with drag, is clearly worse on rainfall;
its maximum cell receives 49,363 mm/year. Iberia without drag has a lower error,
but its settling/temperature checks fail, so it is not a validated improvement.
Do not extend all the failed cases or tune them to the painting now.

All four original controls now pass their unchanged settling criteria. Iberia
mean-only required year 4; its error stays essentially unchanged. The 24 heat
integrations totaled 450.9 seconds (7.52 minutes), excluding plotting and the
original control extension. Water error is at most 4.30e-12 mm/year and static
energy error 9.54e-6 J/m²/year across the saved coupled cases. Accurate accounting
does not imply accurate climate.

## What the failed hypothesis taught us

Retaining condensation heat is necessary in an energy model, but the tested
package of energy transport, latent feedback and finite relaxation did not
solve rainfall excess. The remaining prescribed circulation matters.

The model's two representative pressure levels, 0.875 and 0.375 of surface
pressure, are about 1.12 and 8.24 km above ground under its scale-height rule.
The terrain-drag return flow therefore exchanges air between layers 7.12 km
apart. A slowdown in mountain flow is treated as exchange with the deep upper
atmosphere, rather than resolved shallow uplift and return. The geometric issue
does not disappear merely because the dry-air/water budgets close.

At the prescribed temperature profile, the dry-static part of the resulting
vertical exchange gives monthly p95 upper-layer cooling magnitudes of
13.7–23.4 K/day in California and 6.5–13.0 K/day in Iberia. These are analytic
operator tendencies, excluding latent heating, horizontal transport and
relaxation; they are **not net simulated cooling or measured atmospheric
tendencies**. In the completed coupled drag cases, 60–70% of domain rain comes
from the upper layer. Without drag this share is 2–18%.

This supports separating shallow terrain circulation from deep synoptic ascent.
It does not yet establish a correct replacement or prove the prescribed mean
westerlies and vertical profiles are realistic. In particular, the existing
temperature targets are surface temperature minus fixed offsets of 3 and 35°C.
Departures from these targets are not themselves measured free-atmosphere
temperature errors. The upper target could be wrong. The screen was explicitly
provisional; independent pressure-level data should check it before a stronger
claim about temperature realism.

Reproducible saved-only diagnosis:

```sh
.venv/bin/python scripts/audit_v10_forcing.py --saved-only --run
```

Already generated: `output/v10_circulation_audit/audit.md` and `audit.json`.
This performs no climate integration and does not download atmospheric grids.

## Next user command: atmospheric reference audit

```sh
.venv/bin/python -u scripts/audit_v10_forcing.py --fetch --run
```

This fetches only bounded regional ASCII subsets from NOAA's public OPeNDAP
service. Six fields: air temperature, geopotential height, eastward/northward
wind, specific humidity and pressure velocity (omega). Twelve monthly values
at the product's pressure levels, for California and Iberia; the latter is
split across longitude zero. There are 18 regional subset requests plus six
small metadata requests. It does not download global NetCDF4 files, install
new packages, run a climate simulation, calibrate parameters or update the
atlas. Metadata and one eight-value air-temperature sample were checked while
preparing the reader; full regional reference downloads remain for the user.

The reader validates dimensions and every row/map, regional coordinates,
January–December ordering, unit/packing metadata, and the climatology period.
NOAA air temperature here is Celsius; humidity is **grams/kg of moist air**,
converted to kg/kg and then the model's water/dry-air mixing ratio. Omega is
Pascal/s. Missing values are retained as missing; a scored missing reference
causes an explicit failure rather than an invented substitute. HTTPS
certificate verification remains enabled, using the installed CA bundle.

Raw responses and URL/SHA256 provenance go under `data/v10_atmosphere/`.
Completed responses are reused after interruption; edited/unprovenanced caches
are rejected. Repeating the command does not refetch valid responses. Without
`--fetch`, `--run` requires existing reference inputs. Without `--run`, the
command prints a read-only plan and creates nothing.

Outputs under `output/v10_forcing_audit/`:

- `audit.md` and `audit.json`: checked heat results and atmospheric comparisons.
- `california_forcing.png`, `iberia_forcing.png`: monthly wind components,
  temperature profile, humidity and representative heights.
- `manifest.json`: audit/source/input provenance; changed experiments need a
  new `--out` directory.

## What the reference can establish

Use declared upwind ocean areas, 100–700 km from model land, excluding the
outer two model cells. Sample the native 2.5-degree reference grid horizontally
by nearest cell and interpolate vertically in log pressure to the nominal
ocean lower/upper model levels. Unique native-cell counts are reported; repeated
sampling onto the smaller model cells is not additional independent evidence.
Avoid below-ground pressure interpolation inland.

Compare wind direction and seasonal strength, the assumed humidity supply,
vertical temperature structure and layer heights. Reference omega is retained
in the machine-readable results, but a terrain-following cross-interface
flux is not directly physical pressure velocity over sloping interfaces. Do
not claim a terrain omega ratio without that coordinate conversion. Monthly
means do not measure transient moisture-flux covariance or storm rainfall.

The source is NCEP/NCAR Reanalysis 1, 1981–2010 monthly climatology, provided by
[NOAA PSL, Boulder, Colorado, USA](https://psl.noaa.gov/). See the
[official product metadata](https://psl.noaa.gov/thredds/dodsC/Datasets/ncep.reanalysis.derived/pressure/uwnd.mon.1981-2010.ltm.nc.html)
and [humidity units/period](https://psl.noaa.gov/thredds/dodsC/Datasets/ncep.reanalysis.derived/pressure/shum.mon.1981-2010.ltm.nc.html).
These are model/observation reanalysis estimates on a coarse grid, not direct
measurements at every point. Their normal period differs from WorldClim
1970–2000 and SST 1971–2000. Use this audit to assess structural assumptions,
not claim matched-period rainfall validation.

Only after examining the reference should we choose a shallow/multiple-layer
terrain scheme, revised mean-flow/boundary forcing, or corrected vertical
temperature targets. The current atlas, production V9, original V10, and heat
experiment sources/results are preserved. The user's Mediterranean and dry-zone
protection policy remains in force for future fantasy-map comparisons.

## Fast verification

Sixteen new tests cover constrained ASCII dimensions/row/map integrity, month
ordering, missing sentinels, humidity/temperature/omega units, log-pressure and
cyclic-longitude interpolation, small subset bounds, cache resume/tamper
rejection, offshore-only pressure sampling and read-only defaults. Together
with the existing physics, runner and protected-zone checks, 82 tests pass in
21 seconds. The assistant ran only these fast tests, saved-result verification
and analytic circulation/snapshot diagnosis.
