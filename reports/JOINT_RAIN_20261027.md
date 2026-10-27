# Joint storm and rain calibration — 27 October 2026

The empirical rainfall coefficients were calibrated with older water
transport equations. This experiment tests their interactions on the current
conservative, independently solved lower/upper water states. The fixed
6.0 K/km environmental profile already passes the separate thermal/capacity
reference audit, while its coupled rainfall and humidity still fail regional
protections. A physically plausible capacity shape alone does not establish
an accurate climate.

The predeclared plan is `calibration/joint_rain_20261027/plan.json`. The
comparison is complete: all 84 integrations passed strict numerical checks,
but none of the eight candidate combinations qualifies. No candidate replaces
the adopted fit.

## Fixed factorial design

Three shared empirical coefficients vary in a full two-level factorial.
Their environmental-control values are storm rate 1.434152674408984 per day,
dynamic-rain timescale 11.078614585004903 days, and convective RH threshold
0.6829148729649469.

| Trial | Storm rate day⁻¹ | Dynamic-rain timescale days | Convective RH threshold |
|---|---:|---:|---:|
| rain01 | 1.0 | 8 | 0.65 |
| rain02 | 1.0 | 8 | 0.72 |
| rain03 | 1.0 | 15 | 0.65 |
| rain04 | 1.0 | 15 | 0.72 |
| rain05 | 1.8 | 8 | 0.65 |
| rain06 | 1.8 | 8 | 0.72 |
| rain07 | 1.8 | 15 | 0.65 |
| rain08 | 1.8 | 15 | 0.72 |

Storm rate scales conservative exchange before the existing storm envelope;
it changes heat exchange as well as vapor redistribution. Temperature,
modeled sea state and winds respond through the coupled model and face their
unchanged safeguards. The dynamic-rain timescale appears in the local
rain-removal coefficient; it is not a measured atmospheric residence time.
The convective threshold belongs to the empirical whole-column exponential
relation and uses the model's approximate saturation capacity.

All eight combinations retain independent water without additional vertical
mixing, corrected column convection and falling-rain recycling, the fixed
6.0 K/km environmental capacity partition and 7.5 m/s background westerlies.
Calibrated total capacity/source formulas, surface-elevation lapse and all
other shared coefficients stay fixed. Earth orbital, radiative, rotation and
radius settings remain locked. Actual humidity remains solved; no observed
thermal profile enters the integration, and no local rain multiplier or
imposed upper/lower humidity ratio is fitted.

The parameters are empirical closure sensitivities. This small design does
not establish an optimum, a measured storm frequency or a solved vertical
energy profile. Environmental radiation, latent-energy feedback, entrainment,
ice and cloud dynamics remain unresolved.

## Controls and unchanged qualification

Four controls run first on each of the seven reused development regions:
original r39, common-mass fixed-profile transport, corrected moist partition
with original winds, and the archived environmental 6.0 profile. Every main
NPZ fieldset and array must reproduce exactly before candidates. This gives
28 control integrations followed by 56 candidate integrations. Separate PNW
native companions retain their hash checks and original footprints.

The original accuracy protections remain mandatory: combined error must
improve by at least 0.5% and rainfall loss by at least 1% versus r39; aggregate
temperature may worsen by at most 1%. North India rainfall must improve by
at least 5%; Iran rainfall and every other regional combined error retain
their existing 2% protections. Modeled SST, native outside-region winds,
column and separate-branch speeds, dry mass, conservative storm transport,
layer equations and summed water equations retain their existing limits.
Every primer/scored step must certify the chosen environmental profile,
lapse and rain scheme, including cancellation of falling-rain recycling.

Iberian ocean partial-water and vertical-q-shape errors remain limited to
102% of the fresh fixed-profile transport control. PNW wind vector error
must remain at most 90% of the fresh corrected moist original-wind control;
PNW partial-water and q-shape errors remain at most 102% of that same control.
The failed environmental research control never replaces these denominators.
Masks, true native areas, pressure ranges and observational fields stay fixed.
The separate frozen three-region thermal/capacity reference remains an
additional guard for every candidate; capacity and actual humidity are
assessed separately.

`maximum_finalists=0` prevents automatic promotion from this exploratory
screen. Any candidate that passes every safeguard still requires a separately
frozen full 31-region, ocean, paired fine-grid and established-region
comparison, including PNW native wind and humidity at 56 and 28 km. Fantasy
world transfer and normal atlas adoption require their own qualification.
No threshold or candidate value may change after outcomes.

## Completed comparison and preserved failures

Scientific source `e207736`; results are in
`output/joint_rain_20261027/`. All 84 actual Earth integrations passed strict
numerics. All 28 historical main NPZ controls reproduce their complete field
sets and arrays exactly. No candidate passes every accuracy, regional and
humidity safeguard, so no full 31-region, finer-grid, established-region or
world-transfer stages follow.

The entries below are ratios against the original r39 control. Rain loss
includes local monthly errors; a closer regional annual total does not
necessarily improve it.

| Profile | Rain loss / r39 | Temperature MAE / r39 | Combined error / r39 | Qualifies |
|---|---:|---:|---:|---|
| Environmental control | 1.23797 | 1.01389 | 1.12593 | No |
| rain01 | 1.32545 | 1.03196 | 1.17871 | No |
| rain02 | 1.31645 | 1.02961 | 1.17303 | No |
| rain03 | 1.27548 | 1.01251 | 1.14400 | No |
| rain04 | 1.26466 | 1.00981 | 1.13724 | No |
| rain05 | 1.25178 | 1.02782 | 1.13980 | No |
| rain06 | 1.24286 | 1.02529 | 1.13408 | No |
| rain07 | 1.19427 | 1.00639 | 1.10033 | No |
| rain08 | 1.18431 | 1.00376 | 1.09404 | No |

The best experimental aggregate rainfall result is **rain08**: storm rate
1.8/day, dynamic-rain timescale 15 days and convective threshold 0.72. Its
rainfall loss is **4.33% lower than the environmental control**,
but remains **18.43% above r39**. Its aggregate temperature ratio of 1.00376
passes the fixed 1.01 protection, while combined error 1.09404 remains above
the required 0.995. An improvement within the experimental family is not an
improvement over the adopted climate.

All eight candidates fail regional combined-error protections in Iberia,
Japan, Mexico and the Pacific Northwest, the aggregate combined-error and
rainfall targets, Iberian ocean humidity shape, and PNW partial-water error.
The shorter 8-day rain timescale also fails Iberian partial-water protection.
Five combinations fail aggregate temperature protection; rain04, rain07 and
rain08 pass it. No failed guard is relaxed to make the best aggregate trial
qualify.

For rain08, Iberian partial-water MAE is 0.95277 of the fixed-profile control,
but vertical-q-shape MAE is **3.27126 times** that control. PNW vector RMSE is
0.76818 of its original-wind moist control and q-shape MAE is 0.62447, while
partial-water MAE is **1.06560**, exceeding the unchanged 1.02 protection.
Those controls remain the declared denominators. Better winds or one humidity
metric cannot compensate for another failed observation.

All selected thermal-profile, dry-column, conservative transport, independent
layer-water and precipitation-recycling certificates remain required at every
primer/scored step. The three-region reference qualification remains an
additional condition, rather than evidence of global thermal accuracy.

The supervisor's status was stale after a user pause. Independent verification
reconciles the completed run files, frozen sources, identities, numerical
certificates and control arrays; it does not claim a certified successful
supervisor completion. Preserve that distinction in the verification record.
This milestone adds 84 real integrations to the previous 941: the series now
contains **1,025 actual attempts, 1,021 passes and four preserved earlier
failures**. No failure is removed from that history.

## What this says about local minima

This design tests three-way parameter interactions that single-coefficient
experiments could miss. It does **not** establish a global optimum or rule out
other local minima. The best rainfall result is at a corner of the tested
box, so there is no evidence that this box encloses the best value. Extending
the box may also worsen native humidity or regional errors: the best aggregate
trial still fails both kinds of guard.

A defensible next search can use bounded, reproducible multistart or
space-filling sampling of shared coefficients, retain every physical and
observational safeguard, and evaluate any finalist on the untouched full,
finer-grid and established-region checks. Additional development-region
improvements alone cannot establish generalization. If no combination can
meet the independent humidity constraints, another closure or transport
change may be required rather than a different optimizer. Earth-like orbital,
radiative and rotation settings stay fixed throughout.

Normal climate fields, existing economy/settlement estimates and headline
measurements remain unchanged by this experiment. Science Earth r39 and fantasy Earth r38 remain
adopted; this experiment adds research evidence only.

## Publication choices fixed before outcomes

The figures retain all 12 profiles in the regional rainfall-error matrix.
North India's monthly plot includes r39, the environmental control and all
eight candidates. Iberia separately shows the fixed-profile humidity control,
environmental control and all eight candidates. PNW monthly diagnostics show
the environmental control and all candidates, while error bars retain the
original-wind moist denominator. Each trial label carries the three
coefficients or refers to the complete fixed coefficient table.

The spatial example is **rain05**, index four in the declared Cartesian
order. It is a fixed middle-index example; a two-level factorial has no
central parameter corner. Its map was fixed before the scores were available.
All outcomes and failed safeguards remain in the downloadable results.
The existing thermal reference is linked and retained in metadata without
adding another standalone atlas topic.

These seven regions and the small coastal reference samples have been reused
during development. They provide conditional regional checks rather than
new independent validation or a global/city accuracy headline. Earlier joint
rain searches on r35/r38 used older concentration-form transport; later
conservative experiments tested a humidity threshold, shared winds or storm
hop geometry. This new factorial addresses interactions on the current
independent-water equations and does not reinterpret those earlier failures.
