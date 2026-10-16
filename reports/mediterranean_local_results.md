# Local calibration: modest survivor, then check seasonal settling

14 October 2026. User-run results; assistant analysis uses saved fields. The
production atlas remains unchanged. No further parameter search is prepared.

## Completed bounded batch

Seven new runs completed, including the world 1 anchor, in about 61 minutes
total. Every run matches the expected parameters and current model-source
fingerprint, with all enabled temperature, moisture-equation and linear-solver
convergence checks passing.

- Exchange rate -10%: rejected on world 1. Mediterranean dry land rose
  12.02% → 17.37%, and Cs area fell 37.24% → 32.30%.
- Seasonal contrast 0.8: passed world 1, rejected on world 302. Cold-dry recall
  fell by 2.88 percentage points, exceeding the declared 2-point limit.
- Storm width -5%: passed all three worlds. Retain it as a local shortlist;
  it does not meet the goal of <=5% dry Mediterranean land on every world.

| World | Mediterranean dry, anchor → shortlist | Cold-dry recall | Hot-dry recall | Overall strict agreement |
|---|---:|---:|---:|---:|
| 1 | 12.02% → 11.29% | 68.30% → 67.69% | 57.16% → 60.88% | 48.90% → 49.24% |
| 302 | 1.67% → 1.47% | 54.04% → 54.15% | 34.61% → 38.24% | 50.43% → 50.73% |
| 301 | 3.97% → 3.37% | 69.62% → 68.40% | 64.61% → 64.41% | 54.20% → 54.13% |

The surviving width is 5.779318°; exchange and seasonal contrast stay at
0.998329/day and 0.7. Its exact world 1 configuration is frozen in
`calibration/round20_retrograde_local_shortlist.json`, separate from production
profiles. All three saved runs were rechecked against the declared per-world
guards before exporting this file. This is a small improvement, not a repaired
Mediterranean or a final model selection.

## Why the surrounding world changes the dry fraction so sharply

The remaining 338 dry Mediterranean cells on shortlist world 1 are all steppe
(283 BSh, 55 BSk). Their median annual precipitation is 463.3 mm and median
shortfall below the current Köppen non-arid threshold is 46.7 mm. The width
adjustment increased annual rain on the original dry patch by a median of only
1.16 mm. That explains its limited physical benefit.

Compare those **same 338 locations** under other surrounding worlds:

| Measure on world 1's dry locations | World 1 → 301 | World 1 → 302 |
|---|---:|---:|
| Cells changing from dry to non-arid | 257 | 304 |
| Median paired annual-rain change | +7.44 mm | +81.20 mm |
| Median winter share before → after | 65.64% → 75.46% | 65.64% → 78.37% |
| Median paired dryness-threshold change | -137.02 mm | -139.92 mm |
| Changed cells crossing the winter 70% boundary | 214 | 284 |

The standard Köppen rule changes its annual dryness threshold from
20 × mean annual temperature + 140 mm to 20 × temperature when at least 70%
of annual precipitation falls in winter. Thus crossing this seasonal boundary
lowers the threshold by 140 mm at unchanged temperature. The implementation
matches the rule in [Peel et al. (2007), Table 1, discussion manuscript](https://hess.copernicus.org/preprints/4/439/2007/hessd-4-439-2007-print.pdf).
This is a legitimate classification boundary; do not remove it to improve fit.

Offline counterfactual decomposition holds either annual rain or the dryness
threshold at its world 1 value. Of the 257 cells becoming non-arid in world 301,
205 would do so from the changed threshold alone, 40 from the changed annual
rain alone, 11 from either change independently, and one needs both changes.
Threshold changes include both temperature and the discrete seasonality term;
the separate 70% crossing count identifies the latter. These mixed-field
counterfactuals are attribution tools, not simulated climates.

Rain moving from summer to winter is a real physical improvement for the user's
Mediterranean goal. The classifier amplifies it; a large change in the dry-area
percentage need not imply a similarly large change in total water supply.
Use continuous monthly rainfall, winter/summer totals and temperatures alongside
class counts. Data: `output/mediterranean_tuning/threshold_attribution.json`.

## Next check: has the seasonal cycle settled?

All local solves converge, but the model currently warms up for eight steps
(116.8 days at 25 steps/year), with soil rain memory of 50.8 days and feedback
through evaporation and summer cooling. Local equation convergence alone does
not establish independence from the initial soil/water/temperature state. We
have not established that insufficient warm-up caused the remaining dry area.

`scripts/check_mediterranean_spinup.py` checks the unchanged shortlist on world 1
after one and two full warm-up years. Only the final year is scored. It reuses
the verified eight-step baseline, adds two sequential runs (50 and 75 total
seasonal steps), and saves:

- All existing convergence histories and exact rule fields.
- Monthly rain, temperature, moisture and transport diagnostics.
- Changes in annual/seasonal indices, climate labels and winter-70% crossings.
- Direct monthly differences between one-year and two-year warm-ups, so equal
  annual totals cannot conceal a changed seasonal cycle.

```sh
.venv/bin/python scripts/check_mediterranean_spinup.py --run
```

Allow about 30–40 minutes at recent world 1 speeds; difficult retries can add
time. The default without `--run` only reads files and prints the plan. Each
completed run resumes only with matching parameters, model and diagnostic
source fingerprints, requested/observed warm-up length, and field metadata.
Numerical failures stop the batch with details saved. No automatic extra runs,
parameter tuning, acceptance decision or atlas update occurs.

The model's existing run logic is unchanged, preserving the fingerprints of
the completed comparisons. The diagnostic wrapper now exposes its existing
warm-up argument and records the actual warm-up length. Calendar tests with
fake solves confirm both schedules repeat complete years and score only the
last year, without running a real climate simulation.

After these checks, compare continuous monthly/seasonal changes before choosing
a sufficient warm-up. Then check independent surroundings and grid/seasonal
resolution on the frozen shortlist. If the cycle is already settled, investigate
winter supply/summer transport sensitivity rather than extending this local
search. Thirty-two focused tests pass. The assistant ran only offline analysis,
read-only plans and fast tests.
