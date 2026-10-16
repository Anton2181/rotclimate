# Round 19: diagnose the render collapse before recalibrating

Latest status, 14 October 2026: the bounded local calibration is complete. A 5%
narrower storm width is the only candidate passing all declared world/zone limits,
but still leaves 11.29% dry Mediterranean land on world 1. Offline analysis finds
strong amplification by Köppen's winter-70% dryness threshold. The next check
tests one and two full warm-up years on unchanged shortlist world 1, with no
new tuning or atlas update. See [the latest results](mediterranean_local_results.md)
and [current roadmap](near_term_plan.md); sections below preserve earlier history.

Research update, 13 October 2026. No simulations or calibrations were run for this
investigation. Findings below use saved round-19 results, rendered outputs, code
inspection, and the cited research. The next experiments are prepared for the user.

## Fresh world 301: temperature/wind cap reached; bounded retry prepared

The first user-run validation job completed in 672.6 seconds (11.2 minutes), then
was correctly rejected. All 2,832 internal linear solves converge and all 33
moisture equation checks pass. Three coupled temperature/wind steps (19–21)
reach the 192-iteration cap without reaching the unchanged 0.05°C full-update
tolerance. Final maxima are 0.495, 0.196 and 0.130°C globally, and 0.101, 0.095
and 0.054°C inside the map. This is a local temperature fixed-point issue, not
a recurrence of the moisture imbalance. The rejected 54.21% accuracy is not a
valid candidate selection result.

Preserved the original diagnostic JSON and fields under
`output/mediterranean_validation/*_pre_temperature_retry.*`. No other validation
jobs completed and no atlas change occurred.

Added optional `t_adaptive_retries` (default 0) and `t_require_convergence`
(default false). The first temperature stage retains the exact old iteration
arithmetic. If enabled and a stage fails, continue from its damped state with
half relaxation and twice the iteration cap. Validation uses at most two retries:
0.25/192, then 0.125/384, then 0.0625/768. This is a bounded solver strategy,
not a changed physical forcing or relaxed accuracy threshold. The full update,
not the small damped step, must still be below 0.05°C. A persistent failure now
stops at the failing seasonal step rather than completing the rest of the world.

Each stage records its error history, damping, cap and stopping reason. Retry
progress is printed during user-run diagnostics. If strict convergence fails,
the validation failure JSON includes full stage traces. Both finalists and all
screening seeds use the same retry policy, and model-source fingerprinting
prevents reuse of the old failed result.

Run only the first failed job initially:

```sh
.venv/bin/python scripts/validate_mediterranean.py --cases strong_seasonal --seeds 301 --run
```

After success, the default validation command can resume and reuse this result.
Runtime may exceed the original 11-minute attempt; the real-world retry is not
verified yet. No new physical parameter test is requested. Sixty-nine focused
tests pass, including exact first-stage arithmetic, a stiff oscillatory fixed
point stabilised by stronger damping, and a no-fixed-point case that exhausts
the exact bounded budget without falsely converging. Affected tests were also
rechecked after adding retry progress reporting. Assistant ran no seasonal model.

## Interaction completed: stop single-world nudges and screen two finalists

The user completed focused + strong seasonal exchange in 491.6 seconds. All
enabled convergence checks pass. Relative to strong seasonal alone:

| Metric | Strong seasonal | Focused + strong seasonal |
|---|---:|---:|
| Overall strict agreement | 48.90% | 48.79% |
| Mediterranean dry B area | 12.02% | 1.57% |
| Mediterranean Cs area | 37.24% | 50.37% |
| Mediterranean strict recall | 34.27% | 43.29% |
| Cold-dry strict recall | 68.30% | 48.38% |
| Hot-dry strict recall | 57.16% | 63.73% |

The interaction keeps the Mediterranean benefit and improves hot-dry agreement,
but does not adequately preserve cold-dry land. Two near-identical overall scores
hide a substantial regional tradeoff. The user previously chose to protect
cold-dry land, so neither the latest combined fit nor a changed atlas is silently
selected. Exact combined parameters are preserved in
`calibration/round20_retrograde_focused_seasonal_verified.json`.

The next phase is fresh-surroundings screening of the two finalists on seeds
301/302, not another hand-picked parameter nudge. Prepared
`scripts/validate_mediterranean.py`: four sequential simulations, read-only plan
by default, exact parameter/model-source matching for resume, paired comparisons,
strict convergence checks and exact saved rule fields. Only observed complete
pairs produce a paired candidate gap. Two worlds do not establish statistical
robustness; they screen whether the tradeoff is stable outside world 1.

```sh
.venv/bin/python scripts/validate_mediterranean.py --run
```

At the recent eight-minute cost this is roughly a 32-minute user-run batch, with
variation possible. The atlas remains unchanged. After screening, prepare one
small bounded exchange/width/seasonality calibration with explicit dry-zone
limits, then independent shortlist checks and atlas review. The detailed roadmap
is in `reports/near_term_plan.md`. Sixty-six focused tests pass. The assistant
prepared and tested the plan without launching climate runs or calibration.

## Stronger seasonality helps; complete the focused/seasonal interaction test

The user completed contrast 0.7 in 482.9 seconds. All enabled numerical checks
pass. Compared with contrast 0.4:

| Metric | Seasonal 0.4 | Strong seasonal 0.7 |
|---|---:|---:|
| Overall strict agreement | 46.91% | 48.90% |
| Mediterranean Cs climate area | 30.26% | 37.24% |
| Mediterranean dry B area | 15.10% | 12.02% |
| Mediterranean strict recall | 28.29% | 34.27% |
| Cold-dry strict recall | 67.04% | 68.30% |
| Hot-dry strict recall | 60.78% | 57.16% |

The hot-dry cost continues, so stronger seasonality is not a universal gain.
Exact verified parameters are preserved in
`calibration/round20_retrograde_strong_seasonal_verified.json`. Atlas unchanged.

Mean Mediterranean winter rain increases 419.3→449.8 mm and summer decreases
363.8→352.7 mm. Cold-dry summer rain falls 226.6→204.3 mm, while winter rises
176.1→187.5 mm. The dose response reinforces seasonality as a useful control,
but about 42.4% of the Mediterranean target still has humid Cfa climate.

Next complete the interaction between two measured mechanisms, with no new
free parameter: use the already-tested focused storm width/rate and contrast
0.7 together. Focused storms increased mean Mediterranean winter rain by 66.2 mm
relative to the verified current fit, but raised cold-dry summer rain by 54.3 mm.
Strong seasonality reduced cold-dry summer rain by 54.6 mm relative to that same
baseline. These comparable measured responses motivate testing whether the
seasonal reduction mitigates focused storms' summer damage. They are not assumed
additive; winter effects and nonlinear transport could still make the combined
case unsuitable.

```sh
.venv/bin/python scripts/diagnose_moisture.py --converged --cases focused_seasonal --run
```

This is one simulation, on the same world and verified numerical settings. It
retains the original belt geometry, not the rejected poleward shift. Existing
comparisons are retained. Judge Mediterranean Cs/dry area and both dry zones
together before selecting a fit; current atlas stays unchanged. Sixty-four
focused tests pass, including verification that the combined controls match
their previously tested values. Assistant ran no seasonal simulation or search.

## Poleward circulation rejected; preserve the successful seasonal candidate

The user completed the poleward case in 444.1 seconds. All local numerical
convergence checks pass, but the physical response is strongly unfavorable:

| Metric | Seasonal fit | Poleward belts |
|---|---:|---:|
| Overall strict agreement | 46.91% | 32.94% |
| Mediterranean dry B area | 15.10% | 56.01% |
| Mediterranean Cs area | 30.26% | 13.79% |
| Mediterranean strict recall | 28.29% | 9.85% |
| Cold-dry recall | 67.04% | 73.86% |
| Hot-dry recall | 60.78% | 44.90% |
| Swamp recall | 12.49% | 0.00% |

Mediterranean mean winter rain falls 419.3→316.5 mm and summer 363.8→206.3 mm.
Drying both seasons does not produce the desired wet-winter climate. Hot-dry
summer rain instead jumps 294.6→525.5 mm, demonstrating a large circulation
reorganization rather than a selective Mediterranean summer correction. Reject
this case; retain the exact seasonal candidate and the current atlas.

The next controlled test stays on the successful seasonal fit's geometry and
increases the existing exchange contrast from 0.4 to 0.7. At seasonal extrema,
exchange factors change from 1.4/0.6 (winter/summer) to 1.7/0.3. That halves the
summer coefficient relative to the seasonal candidate, with a 21.4% increase
in its winter coefficient. These are coefficients, not a prediction that rain
will scale proportionally. The previous 0.4 response improved Mediterranean and
cold-dry agreement but slightly hurt hot-dry; that tradeoff must remain visible.
No new parameter, latitude change or target-based physical forcing is introduced.

```sh
.venv/bin/python scripts/diagnose_moisture.py --converged --cases strong_seasonal --run
```

One case runs and all prior exact matching comparisons are retained. The atlas
remains unchanged. This is a dose-response check on the only new physical control
that has helped the verified baseline, rather than another circulation relocation.

### Prevent future research commands from undoing numerical verification

Code inspection found calibration and sensitivity entry points still forcibly
replacing the saved moisture cap with two iterations. Added shared
`config.apply_numerics`: positive moisture tolerance automatically preserves
saved grid/time/moisture settings; explicit overrides still win. Legacy files
retain each command's original defaults. Render uses the same helper, so a verified
moisture profile cannot silently be shortened to three iterations either.

Calibration and sensitivity now support `--saved-numerics`, explicit `--picard`,
and a read-only `--plan`; sensitivity uses spawn workers rather than fork, matching
the existing calibration workflow. No calibration/sensitivity job was launched.
Sixty-three focused tests pass, including actual CLI-plan parameter checks and
legacy/explicit-override behavior. Assistant work used saved results, read-only
plans and small tests only.

## Seasonal exchange succeeds, but summer circulation remains a limitation

The user completed the seasonal case in 477.6 seconds. All temperature, linear
and moisture checks pass. It improves the verified current baseline without
the focused case's cold-dry collapse:

| Metric | Verified current | Seasonal exchange |
|---|---:|---:|
| Overall strict agreement | 43.31% | 46.91% |
| Mediterranean Cs climate area | 20.67% | 30.26% |
| Mediterranean dry B climate area | 23.75% | 15.10% |
| Mediterranean strict recall | 18.54% | 28.29% |
| Cold-dry strict recall | 66.18% | 67.04% |
| Hot-dry strict recall | 65.10% | 60.78% |

The hot-dry decline remains a real tradeoff. Seasonal exchange is the best
verified candidate so far by overall agreement, but it still does not meet the
Mediterranean objective sufficiently. Preserved exact parameters as
`calibration/round20_retrograde_seasonal_verified.json`; atlas unchanged.

### Why reducing summer exchange has only a modest rainfall effect

Mediterranean mean winter rain rises 374.8→419.3 mm, but summer falls only
376.3→363.8 mm. The summer storm-exchange source falls 244.3→198.5 mm; this is
partly offset by wind advection becoming less negative (−67.3→−41.5 mm), plus
small increases in diffusion and evaporation. These are observed local equation
terms, not a conservative global water budget. About 46.3% of the Mediterranean
target remains Cfa: its seasonal pattern is still too humid in summer.

The next controlled probe changes one existing physical parameter relative to
the seasonal candidate: `hadley_edge` increases 4°, from 24.386 to 28.386°.
The model's summer high-pressure-belt centre therefore moves 27.82→31.82°N,
closer to the Mediterranean target. Its summer storm centre moves 40.82→44.82°N.
The winter storm centre also moves 33.95→37.95°N, so northern winter rain may
increase and must be checked. The test changes winds, subsidence and storm
positions together; it is not a hand-painted summer rainfall correction.

The hypothesis is that the current circulation keeps the Mediterranean region
too far outside summer subsidence and too close to summer storms. Geography
supports testing a poleward belt shift, but the coupled rain response is not
known until simulated. No added parameter or classifier change is required.

```sh
.venv/bin/python scripts/diagnose_moisture.py --converged --cases poleward --run
```

This runs one case, reuses prior comparisons, retains verified moisture settings
and leaves the atlas unchanged. Assess Mediterranean dry area and Cs coverage,
both intended dry zones and convergence together. Fifty focused tests pass,
including verification that the poleward case differs from seasonal exchange
only in belt position. Assistant work was saved-field analysis and small tests,
not a climate simulation.

## Focused-storm comparison with settled moisture completed

The user completed the focused case in 479.2 seconds. Temperature, linear and
moisture checks all pass, so this comparison no longer rests on unfinished
moisture updates:

| Metric | Verified current baseline | Verified focused storms |
|---|---:|---:|
| Mediterranean Cs climate area | 20.67% | 37.37% |
| Mediterranean dry B climate area | 23.75% | 9.12% |
| Mediterranean Cfa area | 46.93% | 45.22% |
| Mediterranean strict recall | 18.54% | 34.50% |
| Cold-dry strict recall | 66.18% | 43.07% |
| Overall strict agreement | 43.31% | 44.63% |

The winter improvement is real, but summer rain remains the main untreated
Mediterranean issue. Mean winter rain per painted Mediterranean cell increases
374.8→441.0 mm, while summer barely changes, 376.3→372.0 mm. In cold-dry land,
summer rain increases 259.0→313.2 mm. Thus stronger/narrower exchange alone
still spends cold-dry agreement without restoring the desired seasonal contrast.
The current atlas is retained per the user's preference.

### Next physical development: independent seasonal exchange contrast

Added opt-in `eddy_seasonality` (default 0 preserves existing arithmetic). The
model already moves the storm belt seasonally and applies a winter/summer factor
to the storm envelope. The new parameter adds an independent multiplier to the
whole eddy exchange rate, including its background floor:

`exchange = existing_exchange * (1 - eddy_seasonality * season)`

Here `season` is the model's regional index, +1 at lagged summer and −1 at
lagged winter. The fixed probe uses 0.4, giving 1.4× winter and 0.6× summer
exchange at the seasonal extrema. These are exchange coefficients, not promised
rainfall changes. The coefficient multiplier has mean one over a sinusoidal
year, but full annual exchange/rain is not conserved because the storm envelope,
water gradient and winds also vary. Both heat and moisture exchange use the
same coefficient. No target paint or zone label enters the physics.

The motivation is observed model source seasonality: in cold-dry land, current
storm exchange supplies 137.5 mm in winter and 224.2 mm in summer; Mediterranean
values are 288.9 and 244.3 mm. Reducing summer supply directly addresses the
unwanted humid summer, while retaining stronger winter supply. On Earth, the
[Met Office](https://weather.metoffice.gov.uk/learn-about/weather/types-of-weather/storms/winter-storms)
describes stronger autumn/winter thermal contrasts as a mechanism for stronger
jets and sometimes stronger storms. This supports testing a seasonal contrast;
it does not establish a universal amplitude or prescribe a retrograde planet's
circulation. The fixed value 0.4 is a hypothesis, not a calibrated result.

Run **one** new physical probe on the verified current baseline:

```sh
.venv/bin/python scripts/diagnose_moisture.py --converged --cases seasonal --run
```

The test retains current width, mean eddy-rate parameter, world seed and verified
numerical settings. It does not stack the rejected focused-storm changes. The
completed baseline and focused case remain in the comparison file; only the new
case runs. Output remains `output/moisture_converged/`. Seasonal trials require
converged numerics, and the atlas remains unchanged. Both previous verified
cases took about eight minutes; the new case may differ.

Forty-nine focused tests pass, including default exchange arithmetic, winter/
summer direction, positivity, invalid-setting checks and verification that the
new probe changes exactly one physical parameter. The assistant researched and
prepared this test, but launched no seasonal simulation or calibration.

## Equation-converged moisture baseline completed

The user completed the strict moisture check in 475.8 seconds (7.9 minutes).
Every seasonal step including spin-up passes temperature, linear and moisture
convergence checks. Moisture iterations range 28–46 (median 36), below the 256
cap. Maximum scaled local residual is 0.009981, below the requested 0.01.
All 1,970 linear solves converge, maximum 212 sweeps.

Mean absolute moisture-equation residual / mean rain falls from 82.4% to
0.0437% in cold-dry land, 37.4% to 0.0193% in Mediterranean land, and 21.0% to
0.0125% in hot-dry land. This validates local equation closure for this run;
it does not independently establish periodic soil spin-up, resolution convergence
or physical realism of the simplified climate model.

The corrected climate exposes the old fit's seasonal numerical dependence:

| Mediterranean metric | Two moisture updates | Equation-converged |
|---|---:|---:|
| Cs climate area | 68.27% | 20.67% |
| Dry B climate area | 6.18% | 23.75% |
| Cfa humid subtropical area | 15.56% | 46.93% |
| Strict Mediterranean recall | 65.73% | 18.54% |
| Median winter-half rainfall | 419.6 mm | 320.3 mm |
| Median summer-half rainfall | 245.8 mm | 300.0 mm |

Whole-map strict agreement is now 43.31%, versus 54.58% with two unfinished
moisture updates. Cold-dry recall improves 61.07→66.18%, hot-dry 59.02→65.10%.
The main Mediterranean problem is now both inadequate winter rain in some cells
and excess summer rain in others; a uniform annual rainfall increase cannot
resolve both. Median annual temperature barely changes (18.74→18.63°C over
the Mediterranean target). No rule thresholds or physical parameters were changed
for this numerical verification.

Saved exact verified numerical settings and physical fit as
`calibration/round20_retrograde_moisture_verified.json`. The atlas remains on the
current user-selected render, as explicitly requested. Previous physical-probe
comparisons are provisional until rerun with equation-converged moisture.

Next run only the already-prepared focused-storm alternative with identical
verified numerics. This is a controlled comparison, not a new parameter search:

```sh
.venv/bin/python scripts/diagnose_moisture.py --converged --cases focused --run
```

The script now preserves the completed current baseline in `comparison.json`
when the focused case is run separately, and adds Mediterranean climate shares
and per-zone strict recall to that comparison. Cases with different numerical
settings are not silently mixed. Output remains `output/moisture_converged/`;
the completed baseline is reused. The last run took about eight minutes, so
the old two-minute estimate is no longer appropriate for converged moisture.
Forty-three focused tests pass. Assistant work used saved results and small tests
only; no seasonal simulation or atlas rebuild was launched.

## Moisture transport diagnosis completed: unfinished nonlinear moisture solve

The user completed exact current/focused transport reruns. They reproduce the
previous accuracy values, confirming that diagnostic recording did not alter
the outputs. Both temperature and internal linear solves converge, but the
final **moisture equation does not balance** after two partial Picard updates.

| Zone | Current mean absolute residual / mean rain | Focused |
|---|---:|---:|
| Cold-dry | 82.4% | 87.6% |
| Mediterranean | 37.4% | 41.2% |
| Hot-dry | 21.0% | 22.4% |
| Swamp | 18.6% | 21.4% |

These ratios compare equation rates, not absolute rainfall bias or a conservative
global water budget. Mean absolute instantaneous residuals are aggregated before
division, so opposing seasonal errors cannot cancel. In the current cold-dry
zone, the signed winter residual totals −89.5 mm per average cell and summer
+152.9 mm, while the annual signed sum is only +63.4 mm. Looking only at annual
signed closure would understate the failure.

The observed focused-minus-current cold-dry annual mean term changes are:
rain +71.1 mm, storm exchange +78.2 mm, evaporation +17.6 mm, wind advection
+0.1 mm, diffusion −9.8 mm, and residual +15.0 mm. Most added storm exchange
is in summer (+67.2 mm versus +11.0 mm in winter). Storm exchange is a clear
changed source, but the large unsettled residual prevents treating this as a
reliable settled physical attribution. Summary: `output/moisture_transport/analysis.json`.

### Added opt-in equation-based moisture convergence

Extracted moisture iteration into `rotclimate/moisture.py`. Existing profiles keep
the same fixed-count half-updates by default. The new opt-in mode evaluates the
actual discrete moisture residual after each update, with freshly recomputed
rain rate and storm mixing. It stops when the maximum full-interior
`abs(residual) / max(rain + abs(evaporation), 0.1 mm/day)` meets the requested
tolerance. This checks the equation, not an artificially small damped update.
Adaptive runs also enforce the current Dirichlet boundary after damping; legacy
boundary/update arithmetic is preserved when convergence checking is disabled.
The zero-water rainout expression now safely evaluates to zero instead of 0/0.

New settings: `moisture_relaxation` (default 0.5), `moisture_residual_tol` (default
0, disabled), and `moisture_require_convergence` (default false). They are
included in numerical provenance. Diagnostic comparisons now reject explicitly
checked moisture convergence failures as well as linear/temperature failures.

Next user-run verification is **one current physical fit**, with quarter moisture
updates, a 256-iteration maximum, 1% scaled equation tolerance, and tighter linear
rtol 1e-7 so linear update error is less likely to limit moisture closure:

```sh
.venv/bin/python scripts/diagnose_moisture.py --converged --cases current --run
```

Output goes to `output/moisture_converged/`. It may take longer than the previous
two-pass runs. Strict mode stops at the first seasonal moisture failure and saves
`current_failure.json` with parameters and the reported residual rather than
continuing an invalid full run. A successful run saves the usual rule fields,
transport arrays and convergence traces. If successful, inspect actual closure
and climate changes before comparing the focused case again. Do not presume a
better numerical solve will improve target accuracy: physical calibration must
be judged on the settled result. The current atlas remains unchanged as requested.

Forty-two focused tests pass: the observed transport matches the actual solver
operator; legacy two-pass water arithmetic matches with/without exchange; a small
nonlinear moisture problem reaches its equation tolerance; tiny damping cannot
fake convergence; and absolute residual aggregation detects cancellation. The
assistant ran only these small tests, read-only plans and saved-output analysis,
not a seasonal simulation or calibration.

## Focused storms completed: Mediterranean cured, cold-dry damage rejected

The user completed the focused-storm case in 118.0 seconds. Temperature and
linear solves converge. Mediterranean dry area falls 6.18→0.37% (185→11 cells):
174 original dry cells recover and zero new dry cells appear. On the same
original cells, median winter-rain change is +87.6 mm, summer −5.6 mm, annual
+84.6 mm. The improvement is physical in the model and does not merely move
the dry patch elsewhere in the Mediterranean target.

However, cold-dry strict agreement falls 61.07→32.56%, overall agreement
54.58→51.49%, and balanced recall 54.22→50.70%. Hot-dry agreement modestly
improves 59.02→60.29%. Cold-dry annual temperature is almost unchanged, but
annual rainfall has a median same-cell increase of 67.0 mm; median winter and
summer increments are +36.2 and +29.9 mm separately. This contradicts the
simplified zonal winter-exchange inference: coupled transport and moisture supply
matter, not just local storm-envelope amplitudes.

The user explicitly chose to **keep the current atlas and investigate the
cold-dry damage**, rather than previewing the focused fit. The rejected fit is
preserved for reproducible diagnosis as
`calibration/round20_retrograde_focused.json`. The current selected atlas profile
is unchanged. Spatial comparison: `output/mediterranean_focus/tradeoff.png`.

### Observe moisture transport before further tuning

Added opt-in recording of the local discrete moisture equation: upwind advection,
central diffusion, storm exchange, surface evaporation and rain. Positive
transport terms supply water. Residual equals evaporation plus transport sources
minus precipitation. Terms are evaluated from the final water field and current
nonlinear rain rate, including a fresh evaluation of the mixing field. Therefore
a large residual can expose the unfinished moisture iteration (currently only
two Picard iterations), even if each internal linear solve converges.

The model uses nonconservative concentration advection `u.grad(W)`; these terms
are **not** a conservative global water budget. Outer-ring terms are excluded
and the cropped in-map fields are saved. Absolute instantaneous residuals are
averaged separately so cancellation cannot hide errors. Diagnostic observation
does not change solver iteration, forcing or climate parameters.

`scripts/diagnose_moisture.py` prepares two reruns of the exact current and
rejected fits to obtain fields that were not previously archived:

```sh
.venv/bin/python scripts/diagnose_moisture.py --run
```

Default without `--run` is a read-only plan. The script reuses exact matching
completed diagnostics and prints progress. Each case saves a diagnostic JSON,
usual rule fields, and monthly transport/water/wind fields under
`output/moisture_transport/`. No calibration or atlas overwrite occurs. Next
analysis should distinguish additional direct storm exchange, wind supply and
moisture-equation residuals in the cold-dry zone. Large closure errors take
priority over further physical parameter tuning. The recent simulation cost
was about two minutes per world; diagnostic overhead may differ.

Thirty-six focused tests pass, including manufactured upwind/diffusion/exchange
balances and a cancellation test for absolute residual aggregation. Only fast
tests, read-only plans and saved-field analysis ran in the assistant session.

## Continuing the remaining dry-strip investigation

Saved-field analysis places the remaining 185 dry Mediterranean cells around
35.49°N (median), with median elevation 46.8 m and distance to cropped-grid water
191.9 km. The cold-dry target's median latitude is 39.19°N and hot-dry's 27.81°N.
These are lowland moisture-delivery problems, rather than high-altitude cells
simply receiving a mountain classification. Low local elevation does not rule
out an upstream rain shadow. Distance includes lakes and is limited by the
cropped grid, so it is not an exact open-ocean moisture-path length.

Prepared a fixed `focused_storms` probe relative to the current combined atlas
profile: narrow storm width 20% (6.083→4.867°) and increase eddy exchange 25%
(0.998→1.248/day). This tests focusing exchange in the winter storm belt rather
than spreading an increase across latitudes. The width×rate product remains
constant, but this does **not** conserve rainfall or the full moisture budget;
the background exchange floor also increases, and storm width changes direct
rain efficiency and heat exchange as well.

For the simplified solstitial zonal profile at each group's median latitude,
the proposed winter exchange ratio is 1.21 in the remaining Mediterranean strip,
0.91 in cold-dry land and 0.84 in hot-dry land. Mediterranean summer ratio is
0.95, but summer ratios in the two dry zones are about 1.21 and 1.20. Thus
summer effects could offset winter benefits. This calculation ignores basin
asymmetry, shifted storm reach, actual winds, moisture supply and terrain; it
is a test-design rationale, not a predicted rainfall result. Exact figures and
assumptions are saved in `output/mediterranean_focus_design.json`.

The user can run **one** simulation:

```sh
.venv/bin/python scripts/mediterranean_pilot.py \
  --params calibration/round20_retrograde_mediterranean.json \
  --baseline-fields output/mediterranean_stable/combined_fields.npz \
  --baseline-diagnostics output/mediterranean_stable/combined_diagnostics.json \
  --out output/mediterranean_focus --cases focused_storms --run
```

No calibration, new physics parameter or atlas overwrite is involved. The pilot
retains convergence checks and per-zone agreement, and now tracks original dry
cell locations: cured, persistent and newly dry Mediterranean cells. It also
compares winter/summer rainfall changes on the same original dry cells. This
prevents a similar total dry area from hiding a dry patch that merely moved.
The same-grid requirement is checked before spatial comparison. Thirty-three
focused tests pass. Assistant activity was saved-field analysis, a read-only
plan and lightweight tests only; no climate simulation.

## Mediterranean atlas rebuild completed and verified

The user completed the combined-profile atlas render. Verified that the exact
saved rule-field parameters match `round20_retrograde_mediterranean.json` and
atlas metadata records 8/25/2, 192 coupled iterations and quarter relaxation.
The rebuilt summary reproduces pilot strict accuracy 54.5821% exactly. Display
accuracy on the same model fields is 56.3057%; mean rule coverage is 49.0994%.

The Mediterranean target now contains 68.27% Cs climate and 6.18% dry B climate
(185 of 2,994 model-grid cells). The remaining dry cells are steppe, not BW
desert on this grid. Dayan and Ayah now have Csa at their model-grid locations;
Yezi and Šepaš remain BSh. Other remaining dry town locations include Ferasa,
Aēnaha and Alektruôn. Full-resolution interpolation can differ at boundaries.
Median annual rain in remaining dry cells is 455.3 mm, with a median fixed
non-arid threshold gap of 46.0 mm; do not extrapolate this to a uniform rain
addition over the map.

The atlas is now updated, rather than awaiting the render. No further run is
requested immediately: review this map before choosing another physical change.
The forest display issue and single-world robustness limits remain as described
below. This verification used saved outputs only.

## Combined stable fit: best tested Mediterranean compromise on this world

The user completed the combined case in 119.3 seconds. All linear and coupled
temperature solves converge; temperature iteration uses at most 48 iterations.
The 25% stronger storm exchange plus 2° larger seasonal belt migration keeps
the Mediterranean benefit while recovering most lost cold-dry agreement.

| Metric | Stable baseline | Storm mixing | Combined |
|---|---:|---:|---:|
| Dry area inside Mediterranean target | 24.15% | 6.15% | 6.18% |
| Mediterranean target with Cs climate | 44.09% | 66.03% | 68.27% |
| Mediterranean strict recall | 41.85% | 64.16% | 65.73% |
| Cold-dry strict recall | 64.51% | 39.64% | 61.07% |
| Hot-dry strict recall | 68.33% | 67.25% | 59.02% |
| Forest strict recall | 59.13% | 59.45% | 51.38% |
| Overall strict agreement | 48.70% | 51.61% | 54.58% |
| Mean zone recall | 51.81% | 52.98% | 54.22% |

The result is the best compromise among these fixed probes for the user's
Mediterranean priority. Hot-dry and forest agreement still decline versus the
stable baseline; this is not an across-the-board improvement. The atlas's
existing forest display multiplier remains a separate unresolved issue.
Single-world success does not establish robustness to procedural surroundings.
No spin verdict or large calibration claim is made.

Preserved exact diagnostic parameters as
`calibration/round20_retrograde_mediterranean.json`, after verifying that only
the two intended physical controls changed from the stable baseline and both
convergence checks passed. The next useful action is an atlas preview, rather
than another speculative parameter test:

```sh
.venv/bin/python -m rotclimate render \
  --params calibration/round20_retrograde_mediterranean.json \
  --saved-numerics --out output --atlas
```

This user-run render replaces atlas data and refreshes the usual rule diagnostics
and exact fields. The current atlas remains unchanged until that command runs.
Stable baseline and all pilot archives are retained in their separate folders.
After reviewing the map, any further selection or calibration should use the
stable coupled solver and test multiple surroundings. No further search is
prepared now. The assistant saved the profile and analysed existing results;
no climate simulation or render was launched.

## Stable storm mixing completed: Mediterranean improvement survives convergence

The user completed the stronger-exchange case with damped temperature iteration
in 117.9 seconds. Both linear and coupled temperature solves converge; the
temperature iteration uses at most 48 iterations. Relative to the stable baseline:

| Metric | Stable baseline | Stable storm mixing |
|---|---:|---:|
| Mediterranean target with dry B climate | 24.15% | 6.15% |
| Mediterranean target with Cs climate | 44.09% | 66.03% |
| Mediterranean strict recall | 41.85% | 64.16% |
| Cold-dry strict recall | 64.51% | 39.64% |
| Hot-dry strict recall | 68.33% | 67.25% |
| Overall strict agreement | 48.70% | 51.61% |
| Mean zone recall | 51.81% | 52.98% |

This is a real improvement within the settled temperature/wind model on this
world. Unlike the unstable trial, hot-dry agreement is largely retained; cold-dry
rain contrast is the remaining major tradeoff. The exact candidate is preserved
as `calibration/round20_retrograde_stable_mixing.json`; it has not replaced the
atlas. These are single-world results and do not establish robustness to the
procedural surroundings or convergence of all other nonlinear processes.

Prepared one combined probe: retain the 25% stronger storm exchange and add the
2° seasonal belt migration. The earlier unstable belt-only trial helped cold-dry
recall; that is motivation to test the interaction, not evidence that it will
work with the stable solver. No further free parameters or paint-dependent
physical forcing are introduced.

```sh
.venv/bin/python scripts/mediterranean_pilot.py \
  --params calibration/round20_retrograde_stable.json \
  --baseline-fields output/temperature_stability/coarse_damped_seed1_fields.npz \
  --baseline-diagnostics output/temperature_stability/coarse_damped_seed1.json \
  --out output/mediterranean_stable --cases combined --run
```

The combined case runs one simulation and retains the completed storm-mixing
row in the same comparison file. Only exact matching experiment parameters are
retained when resuming. Success would preserve most Mediterranean gains while
recovering cold-dry agreement without other large losses. If it does not, avoid
repeated unguided combinations and inspect season-specific moisture transport
and spatial rain contrasts. Thirty-two focused tests pass; no assistant-run
climate simulation or atlas update.

## Damped temperature baseline completed: converged, but drier Mediterranean

The user completed `coarse_damped` with quarter temperature updates and 192
maximum iterations. Runtime was 129.3 seconds. All 33 seasonal steps including
spin-up satisfy the original full-update 0.05°C convergence test. Coupled
iterations range 16–51, median 24; no iteration cap hits. All 947 linear solves
converge, maximum 182 sweeps. Largest final in-map temperature update is 0.04990°C.
This verifies the temperature/wind iteration on this one world, not every
nonlinear process or every possible world.

Physical parameters are unchanged, but model-grid strict accuracy changes
54.19→48.70%, and dry area inside the Mediterranean target increases
12.99→24.15%. Mediterranean strict recall falls 57.41→41.85%; cold-dry rises
56.32→64.51%; hot-dry is 68.33%. Median winter rainfall over all Mediterranean
target cells falls 388.7→344.1 mm. The old fit's apparent quality is numerically
sensitive; keeping the unstable iteration to retain a higher score is not a
physical solution. Prior pilot gains must be rechecked with the settled solver.

Saved exact verified parameters as `calibration/round20_retrograde_stable.json`.
The atlas still uses the user's previous selected render; it has not been
replaced with this lower-fit numerical baseline.

Next is only the storm-mixing probe on the stable baseline (no belt-shift repeat
or broad search). The comparison verifies the saved baseline's convergence
history and records convergence for the candidate. If either linear or coupled
temperature convergence fails, the script saves diagnostic results and stops.

```sh
.venv/bin/python scripts/mediterranean_pilot.py \
  --params calibration/round20_retrograde_stable.json \
  --baseline-fields output/temperature_stability/coarse_damped_seed1_fields.npz \
  --baseline-diagnostics output/temperature_stability/coarse_damped_seed1.json \
  --out output/mediterranean_stable --cases storm_mixing --run
```

This is one user-run simulation. Compare reduction in Mediterranean dry area
with loss of intended dry-zone agreement before selecting a physical change.
The assistant checked the read-only plan and 31 focused tests; no simulation
was run by the assistant.

## Mediterranean pilot results: moisture delivery helps, coupled solve is unstable

The user completed both cases. Neither is selected for the atlas.

| Metric | Saved baseline | Seasonal belt shift | Stronger storm mixing |
|---|---:|---:|---:|
| Dry climate inside Mediterranean target | 12.99% | 12.12% | 2.81% |
| Mediterranean Cs climate inside target | 61.19% | 60.05% | 69.04% |
| Mediterranean strict recall | 57.41% | 52.91% | 62.76% |
| Cold-dry strict recall | 56.32% | 66.08% | 30.64% |
| Hot-dry strict recall | 69.22% | 62.55% | 41.37% |
| Swamp strict recall | 23.15% | 12.81% | 15.04% |
| Overall strict accuracy | 54.19% | 53.96% | 48.90% |

Stronger storm mixing supplies the missing rain, but does not preserve regional
contrasts. On the *same original 389 dry Mediterranean cells*, median winter
rain increases 284.6→378.1 mm and annual rain 472.7→573.2 mm. Cold/hot-dry
targets also become wetter. The belt shift barely reduces dry Mediterranean
area and worsens its label recall. Do not promote either change or launch a
large search around them yet.

### Newly detected temperature/wind fixed-point failure

All linear solves converge, but the separate nonlinear temperature/wind
iteration does not: the belt case fails its 0.05°C test on 21 seasonal steps
including spin-up; storm mixing fails on 20. Worst final temperature updates
*inside the map* are 16.75°C and 15.30°C, respectively. Median per-step maximum
updates inside the map are 4.40°C and 2.61°C. These are spatial maxima, not mean
temperature errors or estimates of absolute bias. Nevertheless, they clearly
show the coupled fields have not settled. The existing strict setting applies
to the linear solver only. Relative climate comparisons are provisional until
this is addressed; the saved baseline archive does not contain convergence
history, so it cannot establish baseline fixed-point convergence either.

Prepared opt-in `Params.t_relaxation` (default 1.0 retains existing arithmetic).
With damping enabled, successive temperature states take a fraction of the full
update. Crucially, convergence is still measured using the full undamped update,
so an artificially tiny step cannot falsely count as convergence. This standard
fixed-point stabilisation is not yet verified on the real climate model.

Next user-run test is one unchanged physical world with quarter updates and
192 maximum coupled iterations; the original linear solver settings remain:

```sh
.venv/bin/python scripts/diagnose_numerics.py \
  --params calibration/round20_retrograde_selected.json \
  --cases coarse_damped --out output/temperature_stability --save-fields
```

The script reports seasonal progress and saves exact fields. Check
`temperature_convergence.unconverged_steps` and the final full update before
interpreting climate scores. If quarter updates still fail, investigate that
failure rather than proceeding to calibration. If stable, establish a stable
baseline and revisit seasonally/spatially appropriate moisture delivery. The
atlas and selected physical profile remain unchanged. Thirty focused tests pass,
including a known oscillatory fixed point and a safeguard against false
convergence from small damping. Only plans and lightweight tests were run by
the assistant; no climate simulations.

## Next priority: Mediterranean rain, not forest labels

The user's priority is the dry patch replacing the intended Mediterranean
region. On the saved model grid, 389 of 2,994 Mediterranean-target cells
(12.99%) have dry B climates: 11.79% of the target is hot steppe BSh and 1.20%
cold steppe BSk. None is a true BW desert on this grid. The atlas combines
steppe/desert under dry labels, so this distinction does not remove the visual
or design problem. The main patch runs through Yezi, Šepaš, Dayan and Ayah.

The dry cells have median annual rainfall 472.7 mm, winter-half rainfall
284.6 mm and annual temperature 19.18°C. Their median shortfall relative to
the *current* non-arid Köppen threshold is 45.2 mm/year (10th–90th percentile
8.3–122.3 mm). Almost all (99.74%) already satisfy the dry-summer precipitation
test. Their winter rainfall fraction is typically 63%; increasing winter rain
can also change the Köppen threshold at the 70% winter-rain boundary. Thus
45 mm is a diagnostic gap at fixed temperature/seasonal threshold, not a
guaranteed physical rainfall prescription or a reason to edit the classifier.

The most direct next aim is greater cool-season moisture delivery while
preserving dry summers and the genuinely intended dry zones. This is consistent
with the [Met Office's Mediterranean climate description](https://weather.metoffice.gov.uk/climate/climate-explained/climate-zones).
The link between winter rain and cyclone tracks is also supported by
[Reale & Lionello (2013)](https://nhess.copernicus.org/articles/13/1707/2013/).
Those Earth studies motivate the process to inspect; they do not determine a
fictional retrograde planet's parameter values.

Prepared `scripts/mediterranean_pilot.py`, using only two existing physical
controls. The plan reuses the exact saved baseline and never overwrites the
atlas. Each probe retains the same world seed and strict numerical settings:

1. `seasonal_belts`: increase seasonal Hadley/storm-belt migration by 2°
   (1.434→3.434°). In the code this shifts the winter storm belt equatorward
   and summer belt poleward. It also changes winds and subsidence; any rain
   improvement is a hypothesis, not a guaranteed consequence.
2. `storm_mixing`: increase storm-related moisture/heat exchange by 25%
   (eddy rate 0.799→0.998/day). This tests moisture supply, rather than simply
   making available water rain out faster. It affects other zones and seasons.

Default invocation prints a read-only plan. The user can run both with:

```sh
.venv/bin/python scripts/mediterranean_pilot.py --run
```

Or run only the first with `--cases seasonal_belts --run`. Completed cases are
reused when exact parameters match; each saves diagnostics and exact rule fields
under `output/mediterranean_pilot/`, plus `comparison.json`. Seasonal progress
includes spin-up. Selection should first consider Mediterranean dry area and
Cs climate area, then collateral loss in cold/hot-dry recall and other zones.
The first pass is one world, not a robust selection verdict. Only a promising
physical change should proceed to a small multiworld check. No broad calibration
is requested. The assistant ran the plan and fast tests only.

## Completed retrograde rebuild and offline diagnosis

The user completed the selected retrograde render on 13 October. Atlas metadata
confirms reversed spin and the selected 8/25/2 strict numerical settings. On
this world, model-grid strict accuracy is **54.19%**, display accuracy **56.51%**,
and mean fuzzy rule coverage **49.41%**. These measure different things. The
pilot's 49.33% strict accuracy was the mean over 12 fresh worlds, not this map's
expected exact score. Full-resolution display interpolation can also differ
from these same-field model-grid audits.

Saved diagnostics divide all painted model-grid cells into:

| Outcome | Share |
|---|---:|
| Correct strict label | 54.19% |
| Intended zone incompatible with simulated Köppen class | 28.90% |
| Köppen-compatible, own membership below 0.3 | 7.89% |
| Köppen-compatible, other label wins | 9.03% |

Classification is a real issue, but cannot account for most misses. In particular,
43.68% of cold-dry land and 30.78% of hot-dry land fail their Köppen gate;
changing label precedence cannot repair those climates. For cold-dry, the annual
temperature factor is above 0.5 everywhere, while the aridity factor is below
0.5 on 43.68%. Excess rain relative to the dry threshold is the main measured
limitation there, rather than lack of cold. Mediterranean gate failures cover
38.81%; these include excessively dry, humid and cold climates, so a uniform
rainfall shift would not fix them all.

### Forest versus warm-wet is a display tradeoff

The current atlas multiplies forest membership by 0.75 before assigning labels.
On identical saved fields it raises warm-wet recall from 47.24% to 69.98%, but
reduces forest recall from 58.07% to 12.74%. Mountains and fallback display types
also affect these comparisons. Thus a higher overall display score hides a
severe loss for the smaller forest zone.

`scripts/audit_saved_rules.py` now probes fixed alternatives without running a
climate simulation or modifying the atlas. Its JSON output is
`output/rule_policy_probes.json`. Exclusive-label precision here is calculated
on painted land; it differs from the fuzzy hierarchical precision used by
calibration. Results from the selected world:

| Policy probe | Accuracy | Mean zone recall | Warm-wet recall | Forest recall |
|---|---:|---:|---:|---:|
| Current strict rules | 54.19% | 56.52% | 47.24% | 58.07% |
| Current atlas display | 56.51% | 53.56% | 69.98% | 12.74% |
| Forest weight 0.9, no display overrides | 57.48% | 56.49% | 66.88% | 37.26% |
| Warm-wet priority only when membership ≥0.9 | 57.32% | 58.10% | 61.39% | 54.99% |

The priority probe retains existing Köppen gates and swamp priority, and otherwise
uses strict labels. It is a promising *candidate for evaluation*, not a validated
replacement. Its threshold was one of three fixed probes, not a fitted optimum.
Do not compare its result with a full-resolution atlas as if the grids and
policies were identical. Production classification remains unchanged.

### Swamp attribution needs false-positive checks

Swamp strict recall is 23.15%. Its smallest factor is annual heat on 49.88% of
painted swamp, flat ground on 27.61%, and humidity on 22.51%. Median annual
temperature is 21.31°C, close to the rule's 21°C transition. These are measured
limitations, not proof that any condition should be removed.

Removing annual heat everywhere raises swamp recall to 42.56%, but lowers its
exclusive precision from 79.29% to 41.71% and overall accuracy from 54.19% to
52.89%. Removing humidity raises recall to 38.19%, reduces precision to 69.16%,
and raises overall accuracy to 55.57%. The latter still does not justify calling
drier land swamp. These counterfactuals demonstrate why recall-only factor
attribution cannot choose physical or rule changes.

Next development should separate forest/vegetation from thermal-moisture climate
labels, or validate selective hierarchy against the existing blanket forest
weight. Physical improvements should target dry-zone rain contrasts and swamp
heat/wetness together, rather than globally warming or drying the world. Before
another search, compare any proposed label policy on saved fields from multiple
worlds; the current pilot summaries alone cannot recompute alternative labels.
No additional long run is requested now. This investigation ran only the offline
archive probes (under a second) and 17 focused tests; no climate simulation.

## Selected atlas: retrograde pilot fit; original preparation

The user selected the saved reversed-spin fit for the atlas. The unchanged
parameter file is saved as `calibration/round20_retrograde_selected.json`, with
the tested 14.7 km grid, 25 seasonal steps, two moisture iterations, original
upwind transport, strict rtol=1e-6 and a 2,000-sweep cap. Its physical parameters
are exactly the pilot winner, which was also the reversed-spin starting fit.

The atlas update is a user-run render:

```sh
.venv/bin/python -m rotclimate render \
  --params calibration/round20_retrograde_selected.json \
  --saved-numerics --out output --atlas
```

The assistant prepared the update; the user subsequently completed the rebuild
as recorded above. The assistant did not launch the simulation.
This command uses the tested model grid, not an unverified fine-grid/73-step
configuration. Rendered terrain detail is still drawn from the source map.

### Confirmed structural label issue

`BROADER` in score.py explicitly recognizes forest as broader than warm-wet
and swamp, and warm-wet as broader than swamp, for spill/F1 scoring. However,
`best_zone` mostly takes the largest fuzzy membership among allowed classes,
with only swamp receiving a special priority. Rules containing more conditions
therefore compete against shorter, broader rules on their raw product values.

A concrete compatible Cfa example has coldest month 10 °C, warmest 27 °C,
annual mean 18 °C, aridity ratio 3, driest summer month 80 mm, and wettest winter
month 160 mm. Its warm-wet membership is 0.9254, but forest is 0.9530. It is
labelled forest despite strongly meeting the warm-wet rule. This calculation
uses the existing rules, not an altered climate simulation. It establishes a
real mechanism for missed labels, not its spatial prevalence in the selected run.

The [hierarchical classification literature](https://www.jmlr.org/papers/v12/wang11c.html)
explicitly represents parent/child relationships rather than ignoring them in a
flat classifier. The relevant design question here is whether forest should
remain an exclusive peer of a narrower climate zone, or be treated hierarchically
or as an additional vegetation tag. A different classifier can improve literal
map agreement without improving temperatures or rain; both effects must remain
separately reported. No label policy has been changed in this update.

### Swamp: compound thresholds versus actual waterlogging

Swamp combines five factors: hot summer, mild winter, humidity, flat ground and
a hot annual mean. Their product must usually pass the 0.5 priority threshold
to displace broader high-membership labels. If every factor were 0.8, their
product would be only 0.32768. Equally strong factors would each need to reach
about 0.87055 to give a product of 0.5. This is a mathematical property of the
rule, not an observation that the retrograde swamp has five 0.8-valued factors.

The selected fit also has substantial wet cooling (0.566) and sea offset −2 °C.
Those settings suggest heat requirements deserve inspection, but do not establish
that heat causes the swamp failure. Rainfall, slope and Koppen eligibility must
be checked before proposing a change.

[Stacke & Hagemann (2012)](https://hess.copernicus.org/articles/16/2915/2012/hess-16-2915-2012.html)
model wetland extent through water balance and slope distributions. This supports
separating waterlogging from thermal climate requirements; it does not justify
removing the legend's “hot” condition or introducing a complex wetland model
without evidence. Earlier project tests found poor discrimination from HAND,
wetness index and drainage on these broad height tiers, so those methods should
not be reinstated blindly.

### Diagnosis included in the same rebuild

The existing rule formulas are now expressed as named factors, retaining their
thresholds, multiplication order and label behavior. The render saves:

* `output/rule_diagnostics.json`: per-zone Koppen eligibility, rule strengths,
  strict/display label confusion, and mutually exclusive reasons for misses.
* `output/rule_fields.npz`: exact cropped indices, rule memberships and factors,
  Koppen classes, terrain, land/target masks and parameter provenance for later
  analysis without a new climate run.

Misses are separated into incompatible Koppen class, eligible but below the
membership cutoff, or eligible but losing to another label. Each factor's
statistics include an attribution probe that sets just that factor to one and
reclassifies the unchanged climate. Such a probe is an upper-bound diagnostic,
not a physical improvement or recommendation to loosen a criterion.

These outputs will let us quantify the warm-wet/forest competition and identify
whether annual heat, summer heat, water supply, terrain or eligibility limits
swamp classification in the *actual selected world*. Subsequent label-policy
experiments can run against the saved fields cheaply. No extra calibration is
needed to obtain this diagnosis.

Seventeen focused tests pass, covering the confirmed overlap example, failure
partition, rule factors, unchanged Koppen constraints, exact selected profile,
and an archive round-trip with no pickled data. No seasonal simulation or
calibration was launched by the assistant.

## Round-20 pilot completed: limited classification gain, continued trade-offs

The user stopped the reversed-spin search after its first population, then ran
the comparison of saved fits. There were 65 Earth-like candidates and 17
reversed-spin candidates. The reversed winner is its unchanged starting fit;
three unique configurations were evaluated on twelve fresh worlds (201–212),
requiring 36 simulations. This is an unequal-budget pilot, not a definitive spin
selection experiment.

| Held-out metric | Reversed | Earth-like winner | Earth-like start |
|---|---:|---:|---:|
| zonefit objective | 0.4142 | 0.3991 | 0.3694 |
| strict painted-land accuracy | 49.33% | 43.36% | 42.44% |
| display-policy accuracy | 51.60% | 50.77% | 46.24% |
| mean per-zone strict recall | 50.57% | 44.60% | 44.87% |
| fuzzy F1 objective | 0.4330 | 0.4655 | 0.4717 |
| wet-summer lowland above 30 °C | 7.39% | 5.13% | 9.89% |

Reversed leads strict accuracy on all twelve paired worlds. The objective gap
is +0.0150 with a paired bootstrap 95% interval −0.0111 to +0.0426; it is
undecided under the declared comparison. Its display-policy advantage is only
0.83 percentage points. Earth-like retains the stronger fuzzy-rule objective.
These are trade-offs, not a single clear winner across all metrics.

### What Earth-like's score gain actually means

Relative to its unchanged starting world, the Earth-like winner gains 0.02973
in zonefit, 0.915 points in strict land accuracy, and 4.525 points in display
accuracy, while mean per-zone recall declines 0.269 points. Its fuzzy F1
objective also declines by 0.00614.

Recomputing the *same saved held-out metrics* with only the hot-wet-summer
penalty set to zero gives 0.40373 for its start and 0.39913 for the winner.
The 0.03432 reduction in that realism penalty more than explains its 0.02973
net score gain. This is a useful realism improvement, but not evidence that
the added classification term substantially solved zone matching. No extra
simulations were needed for this attribution.

| Per-zone strict recall | Reversed | Earth-like winner | Earth-like start |
|---|---:|---:|---:|
| cold wet | 77.44% | 70.61% | 50.92% |
| cold dry | 40.68% | 56.25% | 59.85% |
| warm wet | 46.72% | 7.76% | 7.16% |
| Mediterranean | 57.73% | 67.51% | 57.51% |
| swamp | 19.72% | 37.54% | 47.14% |
| forest | 60.92% | 22.63% | 32.79% |
| hot dry | 50.79% | 49.89% | 58.70% |

The Earth-like search mainly reallocates successful labels toward cold-wet and
Mediterranean regions while losing swamp, forest and hot-dry recall. Its primary
warm-wet weakness barely improves. Reversed fits warm-wet and forest much better,
but loses swamp and cold-dry coverage/recall. Neither outcome justifies expanding
this expensive search unchanged.

### Development decision

Retain both worlds and the corrected current atlas. Do not silently promote a
spin based on one chosen metric or publish the pilot as an equal-budget verdict.
The next research priority is to explain the overlapping warm-wet/forest labels
and the swamp-versus-humid-coast requirements, with separate accounting for
Köppen eligibility, fuzzy thresholds, and competition between allowed labels.
That diagnosis should precede another objective blend or large calibration.
The existing tight-solver result remains valid; no new numerical failure was
identified by this comparison.

The assistant read the saved results and recomputed scoring components only;
no calibration or climate simulation was launched.

## Regenerated atlas checked; classification-aware pilot prepared

The user regenerated the atlas from the strict profile. `output/summary.json`
and `atlas/data/atlas.json` agree exactly on the tested settings and metrics:
mean fuzzy coverage 0.548106, strict accuracy 43.7783%, and display-policy accuracy
46.0979% on the model grid. The atlas is now based on the corrected numerics.

The label audit exposes a trade-off rather than a missing global weight:

| Zone | Strict recall | Display-policy recall |
|---|---:|---:|
| Cold wet | 47.36% | 43.63% |
| Cold dry | 54.89% | 54.89% |
| Warm wet | 5.44% | 21.82% |
| Mediterranean | 64.63% | 65.32% |
| Swamp | 55.67% | 55.67% |
| Forest | 30.35% | 11.25% |
| Hot dry | 62.63% | 62.63% |

The display policy discounts forest and replaces certain high/cold labels with
mountain. Its extra 2.32 accuracy points are a change in classification policy,
not a physical climate improvement. Neither policy is changed by this update.

### Optional objective: zonefit

The old optimized F1r objective rewards fuzzy rule membership and spill control,
but does not directly reward the exclusive, Köppen-gated zone classification.
Added an opt-in objective to test that mismatch:

    balanced(v) = 0.5 mean(v) + 0.5 softmin(v), softmin temperature = 0.08
    zonefit = 0.5 balanced(fuzzy F1) + 0.5 balanced(strict zone recall)
              - existing rainfall and wet-summer-heat penalties

Each zone has equal weight regardless of its area. The soft minimum discourages
sacrificing one zone; the fuzzy half supplies smoother search feedback and
continues penalizing geographic spill. Realism penalties retain their existing
strength. This blend is an experimental design choice, not a literature-derived
physical law. It could trade a little physical F1 for better labels; report both.
Historical F1r, strict labels, and atlas labels are preserved for comparison.

Calibration now logs per-zone strict recall and display accuracy across its
surroundings ensemble. Held-out comparisons support the new objective and
report both classification measures and mean per-zone recall. When starting
parameter files are supplied, they are also re-evaluated on the same fresh worlds
so improvement is compared against a numerical-consistent baseline.

### Run the small round-20 pilot

```sh
.venv/bin/python scripts/round20_pilot.py
```

Use `--plan` to preview commands with no writes or simulations. The run:

1. Takes each spin's retained round-19 polished physical parameters and applies
   identical strict numerics (14.7 km grid, 25 steps, 2 moisture iterations,
   48 temperature iterations, solver rtol 1e-6, 2,000 sweep cap, strict failures).
2. Gives each spin 65 candidate evaluations (the starting candidate plus four
   populations of 16) on surroundings 1–3, without first-world racing.
3. Keeps physical search bounds equal, with sea/land offsets within ±2 °C.
4. Compares each winner and its unchanged starting fit on worlds 201–212.
   Finalists are selected by calibration score, before looking at held-out results.

Outputs are under `calibration/r20_pilot`, with starts, experiment specification,
per-candidate logs and `rematch.json`. The runner refuses an existing output
directory to avoid silently mixing experiments. Set `--out` to a fresh directory
for another run. It never renders or changes the published atlas.

This is a pilot with only four search generations and twelve held-out worlds,
not a definitive spin verdict or thorough optimization. It should establish
whether the objective change is promising before a larger search. The new
coarse strict solves took about a minute per world in the diagnostic; with
three worlds per candidate, two spins and four workers, expect hours rather
than minutes. Parameter-dependent solve costs and CPU contention make a precise
ETA unreliable.

Success should include better held-out mean zone recall, inspectable per-zone
changes (especially warm-wet and forest), and retained acceptable F1/realism.
A higher new scalar score by itself is insufficient. No gains are claimed before
the experiment runs.

Thirty-two focused tests passed, including the new objective's response to
classification, protection of a collapsed zone, unchanged realism penalties,
ensemble recall aggregation, and pilot settings. Only the plan was executed;
no assistant-run climate simulation or calibration.

## Verification complete; regenerate the atlas with saved settings

The user completed `fine_verified`. Every one of the 243 linear solves met its
update tolerance; the maximum was 602 sweeps, below the 2,000 limit. Every
coupled temperature/wind step also converged. The objective is 0.4659994 and
strict painted-zone accuracy is 43.7783%, differing from `fine_tight` by only
0.0021 percentage points. Cold-dry median precipitation remains 275.1 mm/year.
This resolves the observed numerical discrepancy for this one-world, 25-step
configuration to the tested tolerances.

Saved the exact tested parameters as
`calibration/round19_earthlike_strict.json`. This retains round 19's physical
world; it is not a newly optimized calibration. Historical calibration files
and default numerical settings remain available for reproducibility.

Both render entry points now accept `--saved-numerics`, which preserves the
parameter file's grid, seasonal step count and moisture iteration count, with
explicit command-line overrides taking precedence. The previous default render
path silently changed all three; its legacy defaults remain unless this new
flag is selected. Numerical settings are exported in `summary.json` and
`atlas.json` for provenance.

Run this to replace the stale atlas and maps with the verified configuration:

```sh
.venv/bin/python -m rotclimate render \
  --params calibration/round19_earthlike_strict.json \
  --saved-numerics --out output --atlas
```

It simulates the fine grid at 25 seasonal steps, exactly as verified, then
regenerates maps, climographs and the seasonal GIFs generated by `render`.
It does not perform a calibration. Expect at least the verified simulation's
roughly eleven minutes, plus rendering time. A 73-step atlas still requires
its own consistency check; the command deliberately reproduces the tested case.

The next development question is how to improve actual painted-zone fit.
Rendering now exports `label_policy_audit`, comparing strict unweighted labels
with the atlas's existing forest discount and mountain/display fallback policy
on the same model fields. Atlas display classification was moved into a shared
function without changing either policy or the historical benchmark. This audit
will quantify semantic mismatch separately from climate mismatch, without a
second simulation. Full-resolution interpolation can still alter boundaries.

Nineteen focused tests passed, including saved-settings preservation, explicit
render overrides, legacy defaults, display-policy behavior, numerical kernels,
and diagnostic experiment design. CLI help was checked. No seasonal simulations
or calibrations were launched by the assistant.

## Follow-up: tight linear solves close the grid gap

The user completed the tighter-solver comparison:

| Case | Objective | Accuracy | Cold-dry median rain | Hot-dry median rain |
|---|---:|---:|---:|---:|
| Coarse, original stopping tolerance | 0.4804 | 44.22% | 255 mm/year | 361 mm/year |
| Fine, original stopping tolerance, temperature converged | 0.2932 | 32.55% | 485 mm/year | 682 mm/year |
| Coarse, rtol=1e-6 | 0.4668 | 43.65% | 277 mm/year | 338 mm/year |
| Fine, rtol=1e-6 | 0.4660 | 43.78% | 275 mm/year | 346 mm/year |

The same-seed grid gap shrinks from about 11.67 accuracy points to 0.12 points,
and the objective gap to 0.00076. Per-zone rainfall and coverage agree closely.
This strongly identifies loose embedded linear solves as the principal cause of
the apparent resolution sensitivity for this world and configuration. It does
not establish convergence across other worlds, spin directions, or 73 steps/year.

The result also shows why waiting for temperature/wind fixed-point convergence
was insufficient: that outer iteration was converging around inaccurate inner
linear solutions. The original coarse fit had modest optimistic numerical bias,
so tighter solves need not improve its optimized score.

There is one remaining verification issue: the fine run took 600.5 seconds and
32 of its 243 linear solves reached the 400-sweep cap. The coarse run took 57.5
seconds and needed at most 191 sweeps. The old status only recorded counts,
which cannot distinguish convergence on the last allowed sweep from an
unfinished solve.

The solver now records the actual stopping decision and final sweep update.
`solver_max_iter` and `solver_require_convergence` are saved numerical parameters.
Historical defaults remain 400 and false; incomplete legacy-mode solves emit one
warning per solver instance. Strict profiles reject unfinished solves rather
than feeding them silently into scoring. The update criterion remains the
existing one; it is not a residual error bound.

A final fine-grid verification raises the allowed cap to 2,000 while retaining
rtol=1e-6, original upwind transport, and the same physical world. It exits early
when tolerance is reached, and fails explicitly if a solve remains unfinished:

```sh
.venv/bin/python scripts/diagnose_numerics.py --cases fine_verified
```

This writes `output/r19_diagnostics/fine_verified_seed1.json`. Expect a run of
roughly the same order as the previous fine-grid check (about ten minutes),
possibly longer. The 2,000 cap is a limit, not a requested fixed sweep count.
Verify zero unfinished linear solves, temperature convergence, and stable
rainfall/accuracy relative to `fine_tight` before adopting settings for new
calibration or a full atlas render.

Sixteen focused tests passed, including rejection of an unfinished solve and
correct recognition of convergence exactly on the final allowed sweep. No
seasonal simulations were run by the assistant.

After the numerical verification, the remaining ~56% mislabelled land needs
physical/objective work: warm-wet hard recall is still only 5.4%, despite rule
coverage 35.6%; forest recall is 30.3% despite coverage 76.7%. Aligning the atlas
and evaluation label policies and evaluating per-zone classification trade-offs
remains the next development priority. No inference of a new preferred spin
should be made from these one-world diagnostics.

## Follow-up: fitted transport improves little

The user completed both fitted-transport runs. Both satisfy the temperature
iteration criterion, and neither linear solver reaches its 400-sweep limit.

| Case | Objective | Accuracy | Cold-dry median rain | Hot-dry median rain |
|---|---:|---:|---:|---:|
| Original coarse grid | 0.4804 | 44.22% | 255 mm/year | 361 mm/year |
| Original fine grid, temperature converged | 0.2932 | 32.55% | 485 mm/year | 682 mm/year |
| Fitted coarse grid | 0.4798 | 43.59% | 259 mm/year | 357 mm/year |
| Fitted fine grid | 0.3086 | 33.40% | 472 mm/year | 664 mm/year |

The fitted scheme improves the fine-grid result by just 0.85 percentage points.
Its coarse/fine gap remains 10.18 points. It is therefore not a demonstrated
solution to this calibration's grid sensitivity. The existing default remains
upwind; do not recalibrate around fitted transport based on these results.

A cheap inspection of static geography fields (no seasonal simulation) found
mean differences at aligned coarse-cell centers of approximately 1.1 percentage
points in terrain drag, 0.27 points in basin-side weighting, 0.14 points in sea
enclosure, and 0.43 points in lake coupling. Some local coastline and terrain
changes are much larger, so these averages do not rule out a geographic cause.

### Next controlled test: linear solver accuracy

`AdvectionSolver.solve` currently stops on a per-sweep update threshold equal
to `rtol × max(abs(boundary))`, with default rtol=0.001. That is not a residual
criterion or a bound on the error in the solution. On a finer mesh, the diagonal
coefficients grow and each sweep's update can become small while the accumulated
error remains significant. Scaling every moisture cell against the wettest
boundary can also be loose for dry inland cells. Successful temperature/wind
fixed-point convergence does not establish that each embedded linear solve is
accurate. These are reasons to test the tolerance, not a confirmed diagnosis.

`solver_rtol` is now explicit in the parameter file, retaining its historical
0.001 default. Two new cases use the original upwind transport, 48 temperature
iterations, and a sweep tolerance 1,000 times tighter on each grid:

```sh
.venv/bin/python scripts/diagnose_numerics.py --cases coarse_tight,fine_tight
```

They write `coarse_tight_seed1.json` and `fine_tight_seed1.json` into the existing
diagnostic directory. Compare against `baseline` and `grid4_t48`, particularly
rainfall in dry zones and the coarse/fine gap. Check the recorded sweep caps:
if tighter solves hit 400 iterations, those outputs cannot establish linear
convergence and the solver needs a residual-based stopping rule and larger cap
or direct-solver check. The 48-iteration temperature cap must be checked too.

If tightening changes little, the next priority is a common-geography refinement
test to isolate coastline/topography sampling from the numerical mesh. Do not
spend another full calibration on any of these unconfirmed explanations.

Thirteen focused tests passed after preparing the tolerance cases; settings were
previewed only. No seasonal simulations were run by the assistant.

## Follow-up: temperature convergence and transport experiment

The user completed `grid4_t48` and `grid4_t96`. Both have exactly the same
objective (0.29318846) and accuracy (32.5503%), every temperature/wind step
satisfies the existing 0.05 °C update criterion, and neither needs more than
28 iterations. Thus the 12-iteration limit was too low for this grid, but solving
to the existing tolerance does not restore the coarse-grid fit. It slightly
reduces accuracy further. Tighter tolerance has not been tested.

### Matrix warnings: reproduced independently of climate

A tiny test of positive random values (`180×180` matrix, entries 0.001–0.01,
multiplied by a vector of values 1–50) reproduces all three warnings on this
machine's NumPy 2.2.6 / Apple Accelerate backend. The output is finite and agrees
with explicit sums to about 1.4e-14. This matches the documented
[NumPy issue #28687](https://github.com/numpy/numpy/issues/28687).

The EBM and monthly aggregation now use `matrix_product`, an explicit NumPy
contraction with BLAS dispatch disabled. This bypasses the warning path rather
than suppressing warnings. Actual nonfinite temperature/rainfall causes the
diagnostic to stop before scoring. Floating-point reduction order changes, so
bitwise agreement with old runs is not promised.

### Next hypothesis: grid-dependent transport diffusion

The original advection scheme is first-order upwind. At leading order it adds
approximately |u| dx/2 of diffusion along x and |v| dx/2 along y. For an example
2 m/s wind, that is about 14,700 m²/s on the calibration grid versus 7,400 m²/s
on the render grid. The explicit heat and moisture diffusivities are 40,000 and
60,000 m²/s. This gives a concrete grid-dependent perturbation, whose nonlinear
climate impact remains to be tested. Geography sampling and terrain-drag changes
are other possible contributors; the transport test does not eliminate them.

[NIST FiPy's numerical-scheme guidance](https://pages.nist.gov/fipy/en/master/numerical/scheme.html)
describes upwind false diffusion and exponentially fitted alternatives.
An optional `transport_scheme="exponential"` now implements a local fitted
stencil with nonpositive neighbor coefficients, the zero-wind diffusion limit,
and the pure-upwind limit at zero physical diffusion. It exactly balances the
constant-flow exponential boundary-layer test at both tested spacings. For
spatially variable winds it approximates the existing nonconservative equation;
it does not establish a conservative moisture budget. This is experimental.

The default is still `upwind`; existing parameter files keep their transport
scheme. The next user-run comparison tests fitted transport on both grids with
a temperature-iteration cap of 48:

```sh
.venv/bin/python scripts/diagnose_numerics.py --cases coarse_fitted,fine_fitted
```

The new files are `output/r19_diagnostics/coarse_fitted_seed1.json` and
`fine_fitted_seed1.json`. Compare their objective, per-zone rainfall, accuracy,
and convergence decisions with each other, and with `baseline` and `grid4_t48`.
A smaller resolution gap with successful convergence would support transport
error as a contributor. It would not validate the fitted world's climate or
remove the need for a later calibration under consistent numerical settings.
A poor fit on both grids can still be a useful outcome: the existing coarse-grid
calibration may have relied on numerical diffusion.

Validation: 13 focused tests passed, including analytic boundary layers under
both wind signs and grid spacings, fitted sweep/direct agreement, coefficient
signs and limits, monthly constant-field preservation, matrix contractions, the
existing upwind solver regression, and experiment-design checks. No seasonal
climate simulations were run by the assistant.

## Follow-up: controlled results supplied by the user

The user ran the five diagnostics. These comparisons all use the same physical
parameters and surroundings seed (1), isolating the numerical settings:

| Case | F1r objective | Zone accuracy | Cold-dry coverage | Hot-dry coverage |
|---|---:|---:|---:|---:|
| Calibration settings | 0.4804 | 44.22% | 0.495 | 0.627 |
| Moisture iterations 2→3 only | 0.4793 | 43.87% | 0.484 | 0.623 |
| Seasonal steps 25→73 only | 0.4609 | 43.28% | 0.368 | 0.594 |
| Grid ~14.7→7.4 km only | 0.3003 | 32.96% | 0.094 | 0.173 |
| All render changes | 0.2384 | 32.41% | 0.017 | 0.147 |

**The leading moisture-iteration hypothesis below is not supported as the main
cause. Grid refinement dominates this test.** It accounts for an 11.25-point
accuracy drop versus 11.81 points for all render changes; this is a comparison,
not an additive attribution because interactions are possible. Time resolution
still matters, particularly for cold-dry coverage.

The cold-dry region's median annual precipitation rises from 255 to 475 mm with
grid refinement alone (658 mm in the full render), while its median annual
temperature barely changes: 14.15→14.09 °C. Hot-dry precipitation rises from
361 to 685 mm. Warm-wet annual rain is still plentiful, but its median driest
summer month drops from 41 to 1.6 mm. Thus the rendered classes reflect altered
rainfall and seasonality, not just different labels or a temperature shift.
These are per-zone distributions; a common-cell comparison remains useful.

A new lead is the coupled temperature/wind fixed-point iteration. It reaches
its 12-iteration cap on 29/33 steps on the finer grid, versus 0/33 on the coarse
grid; the full render reaches it on 65/96 steps. The linear advection solver
never reaches its 400-sweep cap. Cap hits are not proof of nonconvergence (the
last iteration might meet tolerance), so the diagnostic now records the actual
stopping decision and final temperature update, both globally and inside the
map. These are fixed-point updates, not full PDE residuals.

Next, run two fine-grid cases with higher temperature iteration caps. Nothing
else changes relative to the existing `grid4` case:

```sh
.venv/bin/python scripts/diagnose_numerics.py --cases grid4_t48,grid4_t96
```

This writes two new files under `output/r19_diagnostics` without overwriting the
original five. No new calibration is needed. If both converge to similar fields
and recover the coarse-grid climate, insufficient iteration was important. If
both converge but remain wet, spatial discretization/geography effects remain.
If iteration fails to settle, test damped temperature/wind coupling rather than
blindly increasing the cap again. There is no guarantee that a more converged
climate will better match the painting: the coarse fit may exploit numerical
error. Rainfall budgets and resolution-consistent tuning would then be needed.

Only the three quick experiment-design tests and settings preview were run by
the assistant; the two climate runs are left to the user.

## What the saved results establish

The screenshot matches `output/summary.json`: mean rule coverage 0.4497 and hard
zone accuracy 32.41%. The bars measure fuzzy rule coverage, not the percentage
of each zone correctly labelled. The 0.45 headline is also not the calibration
objective: the rendered F1 objective is only 0.2384.

`output/params.json` matches `calibration/r19p_earthlike/best_params.json` except
for three numerical settings:

| Setting | Calibration | Render |
|---|---:|---:|
| downsample | 8 (~14.7 km) | 4 (~7.4 km) |
| steps/year | 25 | 73 |
| moisture Picard iterations/step | 2 | 3 |

The geography seed in both files is 1. Calibration scores average worlds 1–3;
the screenshot is one world, so the table below is evidence of a discrepancy,
not yet a controlled estimate of numerical error.

| Rule coverage | Calibration winner (3 worlds) | Render (world 1) |
|---|---:|---:|
| cold wet | 0.595 | 0.524 |
| cold dry | 0.606 | 0.017 |
| warm wet | 0.356 | 0.170 |
| Mediterranean | 0.558 | 0.887 |
| swamp | 0.433 | 0.523 |
| forest | 0.794 | 0.879 |
| hot dry | 0.581 | 0.147 |

The rendered full-resolution land is about 74% Cs (Mediterranean) and only 1.2%
B (arid) classes. This strongly points to rainfall amount/seasonality and aridity
threshold crossings as the proximate classification problem; it does not yet
identify which numerical change caused it.

The held-out comparison also establishes a real scoring trade-off:

| Round 19, 60 surrounding worlds | Earth-like | Reversed |
|---|---:|---:|
| optimized F1-realism objective | 0.4749 | 0.4276 |
| painted land correctly labelled | 43.34% | 49.04% |
| cold-dry F1 | 0.634 | 0.481 |
| warm-wet F1 | 0.471 | 0.597 |

Reversed spin wins hard accuracy on 55/60 worlds. Earth-like wins the optimized
objective by 0.0473 (paired bootstrap interval 0.0365–0.0554). The rematch's
“Earth-like ahead” verdict applies to its objective, not all definitions of fit.
Earlier round-18 accuracy is not directly comparable across changed zone rules.

## Priority 1: numerical consistency

The strongest code-level suspect is the moisture solve in `rotclimate/model.py`.
Rain-out is nonlinear in relative humidity. Each Picard update solves a linear
system with coefficients from the current humidity, then blends old and new
moisture 50:50. The loop stops after a fixed two or three iterations with no
nonlinear convergence test. Rain is recomputed from the resulting moisture and
fed back into soil recycling. Changing iteration count can therefore change the
climate being optimized. Changing steps/year also changes how often this
incomplete nonlinear solve runs. This is a hypothesis, not a confirmed cause.

Grid refinement independently changes numerical diffusion in the first-order
upwind transport, coastline/terrain sampling, and gradients. The linear solver
also returns at its iteration cap without reporting a residual failure. A small
change in its last iterate alone is not proof that the full coupled system has
converged.

NASA's [verification guidance](https://www.grc.nasa.gov/www/wind/valid/tutorial/verassess.html)
separates iterative convergence, conservation, spatial convergence, and temporal
convergence. That ordering is appropriate here. Increasing resolution is not by
itself evidence of a more trustworthy calibrated answer.

Prepared `scripts/diagnose_numerics.py` compares a same-seed baseline with changes
in Picard count, steps, grid, and the combined render settings. It saves objective,
coverage, hard accuracy, per-zone confusion and Köppen shares, and 10/50/90th
percentiles of temperature, rainfall, aridity and seasonal rain. Iteration-cap
counts are included as warning indicators, not residual convergence proofs.

Recommended first run (five simulations, no optimization or map rendering):

```sh
cd <PROJECT_ROOT>
.venv/bin/python scripts/diagnose_numerics.py
```

Results go to `output/r19_diagnostics/*_seed1.json`. For an inexpensive settings
preview, add `--plan`. To run only the first two cases:

```sh
.venv/bin/python scripts/diagnose_numerics.py --cases baseline,picard3
```

If the extra moisture iteration causes most of the change, next run:

```sh
.venv/bin/python scripts/diagnose_numerics.py --cases picard6,picard12
```

Six or twelve iterations are diagnostic probes, not assumed converged settings.
The remedy would be residual-based damped nonlinear iteration, moisture-budget
checks and a convergence cap with an explicit failure signal. Then use identical
numerical tolerances in calibration and rendering. If time resolution dominates,
check periodic spin-up and soil-memory coupling. If grid resolution dominates,
compare fields on a common land mask and physical sampling locations, then audit
upwind diffusion and terrain/coast representation. The first five runs detect
sensitivity; they are not a complete grid-convergence study.

## Priority 2: make the fitting target match the map's purpose

The current objective optimizes overlapping fuzzy F1 scores. Hard accuracy uses
an exclusive, Köppen-gated winner. The forest and warm-wet rules overlap by design;
a climate can improve a zone's fuzzy score while receiving a different label.
Moreover, `atlas.zone_labels` discounts forest by 0.75 while `score.evaluate`
uses full weight: the displayed map and hard-accuracy number need not agree.

First unify the label policy and report both literal map accuracy and physical
rule coverage. Then retain a Pareto shortlist across balanced per-zone hard recall,
fuzzy F1, and realism, rather than silently declaring one scalar winner. Do not
simply maximize overall accuracy: a large painted zone could drown out small ones.
Keep the existing physical rules fixed during that experiment so improvement is
not achieved by moving the definition of success.

[QuadTune (2025)](https://gmd.copernicus.org/articles/18/9767/2025/)
provides regional response diagnostics for identifying stubborn biases and
trade-offs. The useful idea here is to examine each zone's response before deciding
which parameters to tune; adopting the entire framework is unnecessary.

## Priority 3: diagnose precipitation before adding more physics

After numerical convergence is established, compare monthly temperatures and
rainfall separately in the failed zones. A useful attribution experiment replaces
one field at a time between two runs on a common grid, then recomputes classes.
This is diagnostic only; the hybrid fields are not physical climate solutions.

A [2026 nextGEMS preprint](https://arxiv.org/abs/2604.25447) uses observed/model
field substitutions and finds that precipitation errors dominate Köppen
misclassification in the models it studied. It supports the diagnostic method;
it does not establish the cause in this fictional-world simulator.

If cold-dry remains too wet on converged runs, investigate upstream moisture,
windward/lee budgets, and cold-season precipitation. If warm-wet remains too dry
in summer, diagnose the storm belt, subsidence and moisture source separately.
Uniformly reducing rainfall would help the dry zones while risking the wet ones.

Only then consider transporting condensed water and allowing lee-side evaporation.
[Smith & Barstad (2004)](https://journals.ametsoc.org/view/journals/atsc/61/12/1520-0469_2004_061_1377_altoop_2.0.co_2.xml)
explicitly model airflow, condensate advection and downslope evaporation.
[LFPM (2022)](https://gmd.copernicus.org/articles/15/2063/2022/)
is another inexpensive orographic framework worth comparing. Neither is a
justified drop-in fix for the observed render collapse.

## Priority 4: spend future search runs more efficiently

Once numerical settings and the objective are settled, re-screen sensitivities:
the ten genes frozen from round 17 may no longer be inert under new orientation,
zone rules and converged moisture physics. Use small local response experiments
and validate promising combinations with the full simulator.
[LiMMo (2025)](https://gmd.copernicus.org/articles/18/6177/2025/)
demonstrates monthly, spatially resolved linear emulation for regional climate
calibration. An emulator can save evaluations, but cannot repair an inconsistent
underlying simulator; the existing search logs also mix configurations and are
not automatically a valid training set.

Do not launch round 20 yet. The immediate deliverable is a controlled diagnosis
of why the saved fit changes during rendering, followed by a consistent definition
of displayed and optimized zone agreement.
