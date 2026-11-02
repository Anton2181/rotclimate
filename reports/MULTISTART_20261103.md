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
