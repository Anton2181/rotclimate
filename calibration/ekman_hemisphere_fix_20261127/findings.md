# Coastal Ekman direction now follows signed Coriolis

Main upwelling now turns wind right for positive Coriolis and left for negative,
using both actual modeled latitude and planetary spin. Exact-equator directional
cooling is zero; no empirical magnitude/coastal weights/smoothing/coefficient
changes elsewhere. This corrects a generic direction error, not a fitted climate
candidate or full dimensional Ekman/equatorial circulation model.

Ten production SST snapshots exercise both hemispheres/spins and reversed winds
on a known west coast, stopping at the existing diagnostic tap before heat or
moisture solves. Previously6failed/4passed; all10pass after correction. Another
check proves exact legacyNH bytes (including signed zeros) and commutation with
a proper map rotation. Combined56 moisture/transport/marine/coordinate/forcing
regressions pass with no failures/errors/skips. Raw pre-fix failures are retained,
including their original whitespace; patch context is also preserved exactly.
Code/document whitespace checks pass independently of those raw artifacts.

## Six prospectively declared changed-source comparisons

All six integrations pass their original numerical certificates,0.01 signed
local equation criterion, source/input/library provenance and actual case IDs.
Parameters, observations, coordinates and calendar are exactly matched to the
parent wind study. The four Sahara/NIndia cases (modeled and observed wind)
reproduce every shared monthly/raw/budget field byte-exact as required; their
entire grids lie north of the equator. No retry or numerical adjustment occurred.

Somalia's padded grid spans−8.67 to+13.49degrees with138 southern coastal
source cells. Their corrected cooling can affect northern scored cells through
coupled circulation and moisture. Changes are small relative to the bias:

| Somalia wind | Rain mm/year before → after | T MAE C before → after | Rain loss before → after |
|---|---:|---:|---:|
| Model |3556.41 →3547.92|1.298150 →1.298340|3.663438 →3.654915|
| Observed |4097.36 →4162.73|1.514907 →1.530892|4.202165 →4.266507|

Modeled-wind rain drops8.49mm/year and loss improves0.233%; T MAE worsens
0.000190C. Observed-wind rain rises65.36mm/year and loss worsens1.531%; T MAE
worsens0.01599C. The maximum scored monthly T changes are0.00392/0.05695C.
Retain the mechanically correct direction without claiming a global skill win.
The primary Somali over-rain, false summer seasonality and source compensation
remain. Source changes need not improve a climate whose fitted components have
compensating errors. No coefficient was selected or adjusted using these results.

All observed actual heat/moisture wind samples remain exactly prescribed and
match the parent samples. All six raw attempts/captures/certificates, independently
reviewed changes and inspected source_changes.png are retained under
output/ekman_hemisphere_fix_20261127/. Worker17445 exited; no active scientific
workers. This turn completed24 predeclared regional integrations across three
separate packets (6wind,12source ablation,6changed-source), with no retries.

## Source epoch and next issue

qualification.json records the89 current source hashes, test logs and six-case
review. It is an engineering source qualification, NOT a new97-region paired
reference, planetary skill validation or atlas adoption. Historical source-pinned
qualifications and completed diagnostic packets remain immutable. Their earlier
source is not silently current after this correction.

Before an observed-SST diagnostic, correct/verify the separate existing
sst_damping_heat_only interaction: its modeled undamped seasonal anomaly is
currently added after the observed sea has set heat exchange, so moisture,
convection and e91 receive observed SST plus a modeled anomaly. This is not a
literal observed-SST intervention when the flag is active. A diagnostic-mode
source fix should first prove actual prescribed sea for both uses, preserve
model-SST arithmetic, and precede any wind×SST comparison. No such fix or new
experiment has been made/declared here. Do not just run the old attribution
script and label its sea fully observed.

Remaining main physical leads: Somali coastal SST/boundary supply/precipitation
conversion and coupling; Sahara's wrongly directed thermal-pressure flow;
North India's terrain/spatial rain errors. Marine deletion/global turning and
prior target-cap shortcuts remain unsupported. W18c permanently CLOSED, AA
UNOPENED, r58 retained, atlasr51 unchanged. Establish a current-source paired
reference before future calibration or map use.
