# Environmental temperature profile in independent moisture — 27 October 2026

A saturated rising parcel is not necessarily the environmental air profile.
The cached PNW audit found the moist profile too cold aloft, even though its
saturation-humidity ratio looked closer to actual humidity. This experiment
separates the vertical environmental lapse from the fitted surface-elevation
lapse. It tests two fixed, globally shared environmental lapse rates, 6.0 and
6.5 K/km, without fitting a local humidity multiplier or changing the planet.

The new opt-in reservoir temperature profile integrates hydrostatic liquid
saturation with the prescribed lapse. It partitions the existing calibrated
total saturation and ocean boundary water between layers. At a matched state
it preserves their totals and does not overwrite the independently solved
layer water; subsequent coupled states may respond. The original moist profile
remains the default and an exact numerical control. Diagnostic vertical
temperatures are not new prognostic energy states or a solution of radiation,
latent heating, ice or convection.

Both candidate lapses use 7.5 m/s shared background westerlies, the prior
setting that passed the PNW circulation/humidity guard. Every other
coefficient remains fixed, including the surface-elevation lapse of
4.4142078309475306 K/km. Actual smoothed surface temperature and pressure
anchor the coupled capacity profile. Observed pressure-level temperature
never enters the climate integration.

The predeclared 42-case plan includes 28 historical controls then 14 candidate
runs over the same seven development regions. It preserves every temperature,
rainfall, ocean, wind, humidity, mass, branch and layer-equation safeguard.
The declared three-region cached reference audit separately checks anchored
temperature and saturation-capacity shape in California, Iberia and PNW; it
adds no Earth runs and does not select or fit either profile. Physical
reference qualification is mandatory in addition to rainfall skill.
All outcomes and failures are retained.

Status: complete; neither coupled candidate qualifies.

## Completed reference and coupled comparison

Scientific source `9746d51`; all 42 actual coupled Earth runs passed strict
numerics, 28 historical controls reproduced exactly, and runtime was 480.6
seconds. Neither environmental profile passed all screening guards. No full
31-region, ocean, fine-grid, established-region or world checks followed.
No candidate was adopted.

The cached three-region reference is frozen separately in
`output/environmental_reference_20261027_verified/`. Environmental 6.0 passes
the declared thermal/capacity guards: mean withheld-temperature MAE is 3.004 K
versus 4.055 K for moist, and mean observed-temperature saturation-shape MAE
is 0.03028 versus 0.05905. Environmental 6.5 fails several regional and
aggregate guards and is blocked regardless of rainfall. Both declared coupled
outcomes remain reported. One earlier reference-reader compatibility failure
occurred before metrics; it is preserved separately and adds no Earth
integration.

| Profile | Combined error / r39 | Rain loss / r39 | Temperature MAE / r39 | Reference guard |
|---|---:|---:|---:|---|
| Moist, 7.5 m/s | 1.10496 | 1.21977 | 0.99015 | Moist control |
| Environmental 6.0 | 1.12593 | 1.23797 | 1.01389 | Pass |
| Environmental 6.5 | 1.17289 | 1.32367 | 1.02212 | Fail |

At the same temperature/sea state the total capacity and ocean-water formulas
are identical; only normalized layer fractions change. Coupled states may
then respond and change the numerical capacity values later. The
environmental profile does not reset actual humidity or add an atmospheric
energy model.

| Region | Observed annual mm | Moist, 7.5 m/s | Environmental 6.0 | Environmental 6.5 |
|---|---:|---:|---:|---:|
| North India | 760.83 | 271.84 | 340.59 | 362.05 |
| Iran Plateau | 232.39 | 197.78 | 204.23 | 217.84 |
| Iberia | 391.83 | 690.72 | 673.20 | 745.27 |
| Japan | 1601.36 | 1066.25 | 1160.50 | 1256.20 |
| Mexico | 536.71 | 874.34 | 1095.69 | 1193.60 |
| East Australia | 640.69 | 604.58 | 882.37 | 985.27 |
| Pacific Northwest | 897.46 | 2167.17 | 2001.99 | 2172.29 |

Environmental 6.0 raises North India rainfall from 272 to 341 mm/year and
improves rain loss from 0.79745 to 0.72478; its native land q ratio moves from
0.48684 to 0.43123 toward the observed 0.25111, but remains too high. Japan
and PNW rain losses also improve. Mexico rain loss worsens from 0.87644 to
1.06837 and eastern Australia from 0.40933 to 0.55282, reversing the overall
gain. The aggregate temperature ratio of 1.01389 also exceeds the fixed 1.01
limit. Annual rainfall alone is not the metric.

The PNW native ocean q-shape MAE improves from 0.06285 to 0.04451 with
6.0 K/km, but partial-water MAE worsens from 1.14837 to 1.26510 mm. Its mean
partial water moves closer to observations, from 11.356 to 11.444 versus
11.989 mm, illustrating why a closer annual mean cannot replace local
monthly error safeguards. Native wind vector error remains improved versus
the original-wind control. Iberia still fails the stronger fixed-profile
humidity benchmark.

Every primer/scored environmental profile and lapse is certified alongside
both layer and summed-column equations; each candidate regional run certifies
33 primer/scored steps (231 across its seven regions) and
preserves exact cancellation of internal precipitation recycling. Calibrated
absolute capacity/source laws, all other coefficients and planetary settings
remain fixed. No reference field enters the climate integration.

The reference figure distinguishes saturation capacity from actual humidity,
while the coupled maps show actual rain. The declared 6.5 K/km map is retained
even though its physical-reference check fails. It is not a selected fit.
These are small reused coastal samples and development regions, not a new
global validation set.

The series now contains 941 actual Earth attempts, 937 passes and four
preserved original failures. Reference calculations and their
schema-compatibility failure add zero Earth runs. All normal
climate/economy/settlement packets and headline measurements remain unchanged;
science Earth r39 and fantasy Earth r38 remain adopted.
