# Wind and rain-setting interactions — 28 October 2026

Prospectively declared after the completed broad rainfall search, whose
research validation shortlist is empty. No adopted climate is replaced.

The declaration calibration/wind_interaction_20261028/plan.json selects
three separated, admissible parent settings using the parent's objective and
normalized distance rule: local1_05, local2_05 and local3_05. Each receives
background westerly amplitudes 4.5, 6.0 and 8.5 m/s, compared with its archived
7.5 m/s parent. This parameter is the shared background peak amplitude, not
an observed atmospheric column velocity. The coupled temperature, sea state,
humidity and wind fields respond. All planetary and remaining actual model
parameters equal the environmental control.

Four exact controls and nine candidate profiles each run the same seven
regions: at most 91 new regional integrations. The common search runner has
an empty local proposal list, so no local polishing is performed. Archived
parent anchors add no runs. The parent's thermal reference, hard numerical,
conservation, branch, source and parameter checks remain mandatory. Prediction
weights, normalization floors and research shortlist criteria are identical
to the parent; no accuracy gate is changed after results.

The test asks whether a more realistic native circulation can also improve
rainfall under the different retained storm/rain settings. It is a small
conditional interaction bracket, not a global four-dimensional optimization
or independent validation. Any shortlist needs separately declared broader
Earth, ocean, resolution and world assessment before adoption. All outcomes,
including failures and regional damage, will be retained.

Status: complete; source `9c1e789`. All 91 actual regional integrations pass strict numerics; all 28 archived main controls and four native companions reproduce exactly. No candidate reaches the research shortlist; no adopted climate changes.

## Completed measurements

| Trial | Parent rain setting | Wind amplitude m/s | Objective | Mean rain / r39 | Mean T / r39 | Worst combined / r39 |
|---|---|---:|---:|---:|---:|---:|
| global01 | local1_05 | 4.5 | 1.12568 | 1.06867 | 1.03585 | 1.27665 |
| global02 | local1_05 | 6 | 1.15529 | 1.12280 | 1.02709 | 1.37937 |
| global03 | local1_05 | 8.5 | 1.22528 | 1.23453 | 1.01795 | 1.71350 |
| global04 | local2_05 | 4.5 | 1.13676 | 1.09416 | 1.04344 | 1.33848 |
| global05 | local2_05 | 6 | 1.16689 | 1.14835 | 1.03496 | 1.40030 |
| global06 | local2_05 | 8.5 | 1.23686 | 1.25841 | 1.02648 | 1.73150 |
| global07 | local3_05 | 4.5 | 1.12657 | 1.08807 | 1.05389 | 1.35898 |
| global08 | local3_05 | 6 | 1.16543 | 1.15752 | 1.04611 | 1.52540 |
| global09 | local3_05 | 8.5 | 1.24980 | 1.29062 | 1.03775 | 1.88861 |

The 4.5 m/s end improves the objective and mean rainfall error at each of the
three retained rain settings, compared with its 7.5 m/s parent. The best
objective and best mean combined climate ratio both select global01:
F1.12568, meanS1.05226, meanR1.06867, meanT1.03585, worstS1.27665.
Its mean rainfall-error ratio is 10.0% below the same rain setting's parent
1.18798. It still exceeds r39, and fails every aggregate shortlist threshold.

Pacific Northwest rainfall falls from 1,623 to 1,191 mm/year (897 observed).
Native ocean wind-vector RMSE falls to 2.048 m/s. North India remains at
278 mm/year against 761 observed. Different mechanisms dominate these errors;
reducing wind alone is not a monsoon correction. Temperature worsens under
the weaker wind, and native humidity-shape errors remain substantial.

Global07 has the smallest native squared regret but a worse mean climate
ratio than global01. Sixteen post-search weight/region-omission diagnostics
select either global01 or global07; they reuse existing records and are not
independent validation. The Pareto front is global01/global04/global07.

All three best sampled wind amplitudes lie at the lower bracket boundary.
This is evidence against treating the old neighborhood as an optimum, not a
proof that further reductions remain physically credible or improve global
skill. Only nine fixed four-parameter combinations were run; no local polish,
full-region/finer-grid/established/world stage or adoption occurred.

Independent verification rechecks 336 frozen sources, all raw rows and array
hashes, actual per-case parameters, native footprints, each step's water and
branch certificates, exact controls, paired anchor selection and the scalar
objective. The series now contains **1,487 actual attempts / 1,483 passes /
four preserved historical failures**. This round adds no numerical failures.

Five figures and complete compact measurements are published in the climate
accuracy companion served by start_atlases.bat: paired wind curves, all
regional errors, ranking sensitivity, signed water equations and full-score
seasonal rainfall. The broad-search section also now includes the seasonal
comparison. Normal world climate, agricultural, population and foraging data
remain unchanged. The older inherited plan control-description string refers
to the preceding 84-run factorial; the literal grid and actual count here are
91, as declared before this experiment.

Next conditional mechanism test: remove the retained empirical subsidence and
monsoon column sinks separately and jointly at two separated wind/rain
settings. Conservative donor vertical exchange stays active. This tests a
possible overlap; it does not presume that drying removal repairs the model.
A fresh declaration must precede those integrations and retain these outcomes.

## Seasonal display and native humidity appendix

The later diagnostic appendix reorders the recorded six-month southern shift
to show actual January–December labels, including East Australia. Earlier
plots displayed model-calendar months. Source arrays, paired errors, weights,
annual totals and selection outcomes are unchanged. Full-score rainfall
series remain separate from the historical cropped water-equation diagrams.

The native humidity curves use the exact objective footprints: North India
land (11 cells), Iberian ocean (20), East Australian land (7), and PNW ocean
(4). They compare partial-column water and upper700–300/lower925–700 mean
specific humidity, without substituting a mean curve for local MAE. Native
controls are transport_control for the first three and column_control for
PNW; the original r39 record has no saved humidity certificate. All underlying
area/day-weighted metrics stay downloadable. These are development-region
diagnostics, not another independent observational validation.
