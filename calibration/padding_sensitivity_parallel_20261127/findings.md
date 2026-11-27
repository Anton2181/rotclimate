# Completed aligned-domain padding study

All nine declared integrations completed with their original numerical checks.
All three 1100 km controls reproduced the archived r58 temperature/rain fields
exactly at float32; Somalia/Sahara also reproduced E/W/u/v. The independent
review verified source/input/field hashes, scored footprints, coordinates,
unchanged observations/calendar, monthly reconstruction from actual traces,
scores and all nine pairwise comparisons. No failed or missing cases remain.
The original waiting study remains retired: these are the single nine-case
budget prospectively moved to private low-priority execution, not extra cases.

## Results at identical scored locations

Annual rain is the scored-cell mean, in mm/model year. Observations are fixed
across padding sizes, not resampled to the larger domains.

| Region | Observed | 1100 km | 2220 km | 4012 km |
|---|---:|---:|---:|---:|
| Somalia | 457.36 | 3556.41 | 3831.87 | 3589.19 |
| Sahara | 2.07 | 215.04 | 13.33 | 7.22 |
| North India | 760.83 | 547.42 | 429.39 | 469.64 |

| Region | Temperature MAE C, 1100 / 2220 / 4012 | Rain loss, 1100 / 2220 / 4012 |
|---|---|---|
| Somalia | 1.298 / 1.281 / 1.364 | 3.6634 / 3.9374 / 3.6946 |
| Sahara | 2.364 / 1.898 / 2.089 | 1.6858 / 0.1497 / 0.0761 |
| North India | 3.206 / 3.321 / 3.029 | 0.4900 / 0.5808 / 0.5386 |

Sahara's extreme excess rain falls sharply, but 7.22 mm/year still exceeds
2.07 observed. Somalia stays about 7.8 times observed; the middle domain is
wetter than either endpoint. North India becomes drier than the already dry
control at both expanded sizes. Its largest-domain temperature MAE improves
while rain loss worsens. There is no general rainfall improvement from expanding
all domains, and no aggregate score or best padding is selected.

## Coupled moisture response

These are actual instantaneous rate-times-water integrals, averaged over the
same scored cells and model calendar, not products of monthly averaged fields.
Drying is the signed total traced linear sink term; it is not all atmospheric
moisture loss. Surface evaporation is not a tagged recycling fraction.

| Region | Convergence import mm/year, 1100 / 2220 / 4012 | Linear drying mm/year, 1100 / 2220 / 4012 |
|---|---|---|
| Somalia | 1591.65 / 1386.39 / 925.86 | -194.16 / -192.61 / -193.75 |
| Sahara | 787.72 / 215.27 / 325.38 | -1378.40 / -954.97 / -1118.34 |
| North India | 484.38 / 266.76 / 319.39 | -566.27 / -549.02 / -569.34 |

In Somalia, 1100 to 4012 km cuts import by 665.79 mm/year while rain rises
32.78. Surface E changes -2.52 and drying +0.41. The unpartitioned equation
remainder rises 700.67 mm/year. At 2220 km the corresponding remainder rise
is 493.01. Thus the earlier fixed-wind boundary proxy cannot be translated
directly into a rain correction.

The remainder is **defined** as P minus surface E, import and drying. It
combines unrecorded advection, diffusion, storm/marine exchange and equation
residual. This identity is not a measured boundary flux, a separated mechanism
or a budget closure certificate. Current saved packets cannot partition it.
Sahara's 4012 km rain/E changes are -207.82/-205.37 mm/year; neither that
covariation nor the import response identifies which coupled process caused
the change.

## Domain stability and interpretation

Between 2220 and 4012 km, monthly temperature RMS differences are 0.383 C
(Somalia), 0.289 C (Sahara), 0.534 C (North India). Monthly rain RMS differences
are 27.11, 1.17 and 8.07 mm/model month, respectively. North India's maximum
cell-month temperature difference is 1.85 C, and its maximum rain difference
is 78.04 mm. Similar annual means would not establish field convergence.
No convergence-to-truth claim is made from three domain sizes.

Expanded domains change terrain, winds, numerical operators and the locations
of the prescribed observed humidity boundary. Earth's supplied global
rain-derived monsoon descent remains a different forcing from fictional-grid
modeled local descent. See ../earth_conditioning_20261127/findings.md. Regional
projection distortion also remains at the enlarged periphery. These findings
do not isolate Gaussian reflection, justify a world-boundary replacement,
invalidate historical r52/r53 failures or supply independent planetary skill.

## Next work

Keep W18c's original search, selection and development/fine/sealed gates
unchanged. Do not deploy larger padding as the climate fix. The prepared
marine-exchange diagnostic correction remains unapplied to the active main
source while that campaign runs. A separately declared, bounded diagnostic
capture using that correction can split the compensating source terms while
requiring exact physical reproduction of these completed cases. Such captures
would be additional diagnostic integrations, not retries, qualification of a
new climate or permission to tune against validation targets.

The atlas remains r51 and adopted Earth climate r58. No physical candidate,
parameter change, padding selection, climate adoption or map rebuild results
from this study.

## Evidence and checks

`output/padding_sensitivity_parallel_20261127/review.json` retains all nine
statistics, all nine paired field comparisons and hashes of 36 raw files.
The 2x3 `padding_changes.png` figure was visually inspected: labels and legends
are readable, fixed observations and both signed sources are visible, all
nine cases are plotted, and no missing result is hidden by aggregation.
`completed_accounting.json` independently reconstructs monthly instantaneous
source amounts and records the nine annual partial accounts and six control
differences. Its explicit interpretation prevents treating the remainder as
an observed process or closure test.

Reproduce the supplementary analysis with
`.venv/bin/python calibration/padding_sensitivity_parallel_20261127/analyze_completed.py`.
It verifies the independent review's raw field/receipt/footprint hashes,
checks annual sources against the review, preserves the completed packet and
performs no integrations. The existing reviewer tests passed before execution;
all original numerical criteria remained unchanged during the study.
