# Wind and SST interact strongly; corrected column water still rains too readily

The observed-SST mode now bypasses the modeled heat-only damping addback. A
coupled known-temperature test reproduced the previous discrepancy, then passed:
actual heat-equilibrium and moisture temperatures equal prescribed SST. Toggling
the irrelevant modeled damping flag under observed SST produces byte-identical
physical/budget arrays. The modeled-SST regression retains the intended separate
heat/moisture temperatures.58 source tests and6 WOA checks pass (64total), no
failures/errors/skips after the fix. Pre-fix failure and raw logs are preserved.

All12 predeclared regional integrations pass original numerical certificates
and strict0.01 local equations (largest scaled residual0.009974). Six modeled-
SST controls reproduce every shared parent physical/monthly/raw/budget array
byte-exact. Thus this diagnostic correction changes no retained modeled-SST
physics. No scientific retry, fitting or numerical adjustment occurred.

Preparation verifies all12 raw WOA monthly source hashes against its1degree
surface cache and archives that normalized reference. Full padded-grid SST and
properly projected NCEP surface winds are hashed/read-only and remain unchanged.
All modeled sea cells are captured, not just scored land. In each observed-SST
case actual pre-ice surface, heat-equilibrium target and moisture SST equal the
prescribed monthly-center interpolation exactly. These cases have no prescribed
sea temperature low enough to activate ice. Independent review rederives WOA
sampling, verifies the complete cached sea mask, actual winds, exact controls,
input/source provenance, parameter differences and all signed local accounts.

## Regional responses

| Region | Wind | Modeled → observed SST rain mm/year | T MAE C | Rain loss |
|---|---|---:|---:|---:|
| Somalia | Model |3547.92 →3356.30|1.2983 →1.1906|3.6549 →3.4643|
| Somalia | Observed |4162.73 →2590.43|1.5309 →1.2045|4.2665 →2.6725|
| Sahara | Model |215.04 →221.94|2.3639 →2.4248|1.6858 →1.7278|
| Sahara | Observed |12.31 →2.42|1.9901 →2.0181|0.1411 →0.01582|
| North India | Model |547.42 →652.83|3.2063 →3.0157|0.4900 →0.4467|
| North India | Observed |748.02 →876.95|2.9523 →2.8765|0.6654 →0.6837|

Fixed observed annual rain: Somalia457.36, Sahara2.07, North India760.83mm.
SST correction alone only modestly improves Somalia. With prescribed wind its
rain falls1572mm/year and loss37.36%; with modeled wind only192mm/year and
5.22%. The wind effect changes+614.80 →−765.87mm/year between SST settings:
a−1380.67mm/year coupled interaction. Do not add standalone improvement estimates.
The joint observational response is informative, not a deployable climate law.

Somalia's observed-wind SST change reduces signed marine source1210.70mm/year
and advection547.73, while storm exchange rises283.84. With modeled winds,
SST changes convergence import+1178.36 and advection−1379.37, largely canceling.
These local concentration-equation accounts are neither tagged moisture origin
nor isolated causal shares or planetary closure. Sahara needs circulation as
well as SST: under modeled wind the sea intervention slightly worsens T/rain.
North India benefits from SST under modeled winds, but the observed-wind arms
retain mountain/spatial errors: the joint arm reaches4219.85mm/year at one
Nepal cell against519.26observed. Mean totals/curves do not replace per-cell loss.

## Water-column comparison: next mechanism is rain production

A separate read-only review validates the existing public NCEP/NCAR PW raw
archive:1991–2020,2.5degree,kg/m²(=mm),scale1,offset0,exact axes/cache values.
It performs zero integrations and changes no source/forcing. PW is already
used as Earth boundary conditioning; this is NOT independent climate validation.
Climatological periods, coarse interpolation, terrain and vertical definitions
limit quantitative comparison. Regridded cells are not independent observations.

With BOTH observed wind and SST, Somalia's mean modeled water is37.15mm versus
35.42reference (+4.90%), yet rain is2590.43 versus457.36mm/year (5.66×).
In July the model actually holds LESS water (32.90 versus36.43mm) while raining
281.93 versus25.43mm/month. The regional rain-per-mean-water proxy is5.40× the
reference, versus6.19× in the baseline. This ratio is descriptive, not a diagnosed
residence time, microphysical efficiency or proof of one coefficient's cause.
It does support inspecting conversion/stability and rainfall-component closure
instead of simply removing humidity sources until the rainfall total fits.

The PW raw field includes5993negative values(out of126144),minimum−2.307mm,
within its published numeric range. An initial read-only nonnegative assertion
caught this; the source inspection/failure assumption is documented separately.
The EXISTING builder already clips those values to zero; the normalized cache
matches exactly. No reference or climate input was repaired, rebuilt or changed.
Somalia/Sahara interpolation corners do not touch these negatives.4.55% of North
India cell-month samples involve a clipped raw corner, an additional limitation
of that mountain comparison. Archive raw/normalized PW plus full provenance and
the descriptive water-column figure/review; do not treat clipping as new physics.

## Next work and scope

Declare exact rainfall-closure endpoint captures (retained baseline versus joint
observed wind/SST, all3regions) before more integrations. Capture actual solved
W/saturation/dynamics/instability and full closure inputs, including heating-
lowered RH threshold, convective cap and subcloud evaporation. Independently
reconstruct base gated rain, exponential convective rain and supersaturation
without changing the return value. Require byte-exact parent physical/budget
fields and original numerical criteria. Identify the dominant false-summer
component before selecting a physical intervention. No such next study has
started here, and the present12-run budget is spent/closed.

The legacy optional heat_record.surface_c uses the post-addback SST under
modeled heat-only damping; it can mislabel moisture temperature as heat target.
This study avoids that recorder: it checks actual traced Teq and pre-addback
surface plus moisture SST directly. Verify/fix that separate diagnostic issue
before future sensible-heat flux audits; no current result depends on it.

Both six-panel figures were inspected. All raw12 attempts/captures/certificates,
full forcing, WOA/PW references, independent/spatial/column reviews and figures
are under output/wind_sst_diagnostic_20261127/. Worker17957 exited. Qualification
of the observed-SST diagnostic source is under output/observed_sst_fix_20261127/;
this is not a new97-region paired reference. Prior packets/qualifications stay
immutable and historical. W18c CLOSED,AAUNOPENED,r58retained,atlasr51unchanged.
