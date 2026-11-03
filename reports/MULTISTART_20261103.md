# Three-start calibration on the recovered r42 references

All three declared 13-evaluation starts completed: **39 evaluations**, including
three r42 reproduction controls and 36 proposals. Every run covers all 49
development regions. This is a bounded nine-parameter search using existing
physics strengths, gates, wet-sun response and precipitation timescale. The
Earth transform keeps its planet/orbit fixed; no regional correction coefficients
or observed wind/SST resets are introduced.

| Start | Best development S49 | Evaluation |
| --- | ---: | ---: |
| r42-centred | 0.9913780 | 7 |
| Independent Sobol centre 1 | 1.0000000 | 0, reproduced r42 control |
| Independent Sobol centre 2 | 0.9983071 | 11 |

The unchanged prospectively declared selection rule chose start 1, evaluation 7
after every start finished. Its equal-region temperature MAE falls from
**1.883929 to 1.878921 C** and rainfall loss from **0.500448 to 0.493148**:
combined error -0.8622%, temperature -0.2658%, rain loss -1.4586%. Rain loss is a
dimensionless composite metric, not an accuracy percentage or an amount of rain.

The gain is small and uneven. Twenty-four of 49 individual regional combined
ratios improve; 25 worsen. Historical groups are reported, not used as vetoes:
holdout +3.75%, midlatitude +2.34%, dev12 +1.73%, retired b -7.68%, retired c
-3.15%. The overall score follows equal-region mean errors, not a requirement
that every region improve or the count of regions that improve.

## What this says about local minima

Independent starts test dependence on the chosen centre and seed. Here the
current basin produced the best qualifying proposal. Two generations per start
in nine dimensions are sparse: this does not prove global optimality, establish
that the parameter bounds contain the best physical model, or exclude missing
mechanisms. Separate conservative-transport tests explicitly probe a different
model family; those failures are retained in TRANSPORT_FACTORS_20261102.md.

Resampling the same 49 development regions 10,000 times gives a descriptive
95% S interval of **0.9633 to 1.0158**. This illustrates sensitivity to the mix
of regions. It is **not** uncertainty corrected for candidate selection or
spatial dependence, and its fraction below one is not a probability of improved
unseen-Earth performance.

## Validation and publication

The selected parameters, all 39 scalar records, original history hashes and
source identities were committed before any fresh validation. The driver in
`scripts/validate_r42_multistart.py` reproduces both full 49-region error vectors
to 1e-10 and checks actual reference footprints, then applies the unchanged
policy-v3 development gate. A passing candidate gets a fresh paired 28 km check;
only if that also passes does the driver commit qualification and evaluate
the previously declared unseen set e once, paired with r42.

Validation output and its final outcome are recorded in
`output/r42_multistart_validation_20261102`. The validation driver does not
adopt physics or overwrite atlas data. The served Earth atlas remains r42 until
a qualified release is explicitly adopted and fully rebuilt. The current
launcher prints its verified atlas snapshot rather than inferring a data update
from newer simulation code.


## Retrospective search-coverage audit — 3 November 2026

The39 records comprise three exact r42 reproduction controls and36 unique
proposals. Normalize the proposals to the declared bounds and subtract the r42
anchor: the design has rank9, condition number6.53. All nine parameter directions
are represented, but this does not densely cover their joint space or certify
convergence to a local/global minimum. The per-parameter scatter plots mix
changes in every other parameter and are not isolated causal effects.

A fixed anchored linear ridge model (alpha0.01, no hyperparameter selection)
trained on two complete search starts predicts the omitted start with combined
score MAE0.57%,1.34%,0.65%. Identical reproduction controls are excluded from that
error evaluation. Prediction errors are comparable to the winning0.86% gain;
this retrospective emulator is not reliable evidence of unseen improvement.
No new candidate or global optimum is selected by the audit.

R43's marine-land heating threshold lies1.2% of its declared range above the
old lower bound0.3; dry-branch strength is near the upper bound0.3/day. A separate
prospective reused-region screen tests thresholds0.15/0.05 and drying0.4/day,
including one fixed combination. The threshold stays strictly positive because
zero disables the marine gate rather than giving its continuous limiting form.
All planet/orbit settings, other strengths, imposed-forcing choices and strict
numerical criteria remain fixed. No reserved observations, adoption or atlas
promotion follow from that screen. Plans: calibration/parameter_bounds_20261103.

Audit code, source hashes, plot and fold predictions: scripts/audit_search_geometry.py
and output/search_geometry_20261103. The normal research companion includes the
same coverage plot and explicitly retrospective interpretation.
