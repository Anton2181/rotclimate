# Broader rainfall search with explicit tradeoffs — 28 October 2026

This is a new prospective research policy, following the user's request to
allow regional accuracy tradeoffs and investigate other parameter basins.
Previous campaigns and their failed acceptance decisions remain unchanged.
No adopted Earth or fantasy climate is replaced by this experiment.

The search retains the conservative, independently solved water layers,
corrected column convection and falling-rain recycling, fixed 6.0 K/km
environmental capacity profile and 7.5 m/s westerlies. The existing external
thermal/capacity reference must still qualify. No regional parameter, observed
humidity reset or planetary change is introduced.

Hard requirements cover numerical convergence, water/mass/branch equations,
conservative internal transfers, finite outputs, unchanged geography and native
footprints, declared actual parameters, and branch/column speed bounds.
Rainfall, temperature, native humidity/wind and modeled SST prediction errors
are separately reported objectives. A 2% prediction regression no longer
invalidates an otherwise admissible research candidate.

## Frozen design

`calibration/global_rain_20261028/plan.json` contains all 32 initial points,
objective weights, normalization scales, bounds, local-start selection and
adaptive proposal rules. Source, plan and tests are committed before new
Earth integrations. The original four controls rerun on each of seven regions,
with every archived main NPZ field and array reproduced exactly.

The 32 scrambled Sobol points use seed 20261028 and cover three shared axes:

| Coefficient | Range | Sampling |
|---|---:|---|
| Storm exchange rate | 0.4–3.5 per day, before the storm envelope | Logarithmic |
| Dynamic rain timescale | 3–35 days | Logarithmic |
| Convective activation RH | 0.50–0.85 | Linear |

These are empirical sensitivity ranges, not physical confidence intervals.
Storm exchange affects heat as well as water; temperature, sea state and
circulation respond. Every other actual per-case parameter must equal the
fresh environmental control.

After the global stage, select up to three physically admissible starting
points ordered by objective, separated by at least 0.35 in normalized
parameter space. Each receives six sequential coordinate proposals at a
normalized step of 0.12. The center moves only when the objective improves;
exact duplicate proposals reuse records and add no Earth integrations.
This is bounded local refinement, not a converged optimizer. At most 18 new
local profiles follow the 32 global profiles, for a maximum of 378 actual
Earth integrations including 28 controls. A two-hour campaign ceiling and
per-profile/completion source checks apply. Failures remain preserved.

## Objective and candidate advancement

Let each regional combined ratio be `S_i = 0.5*(TMAE/Tref + rainloss/rainref)`.
The main objective is the equal-region mean of these ratios, plus:

- `0.25 * mean(max(S_i - 1.05, 0)^2)` for regional damage;
- `0.05 * mean(max(native normalized error regression, 0)^2)`;
- `0.05 * mean(max(ocean normalized error regression, 0)^2)`.

Native errors compare the same wind, partial-water and humidity-shape metrics
on the same native footprints. Fixed denominator floors prevent near-zero
reference errors from dominating: 0.5 m/s, 1 mm and 0.02 for the dimensionless
shape error. Ocean-error normalization has a 0.1°C floor. These are objective
scales, not estimated observational uncertainties. Every raw component and
regional result remains available; none is hidden by the aggregate.

The Pareto front retains non-dominated combinations of mean combined error,
worst regional error and native regression. A research shortlist additionally
requires mean combined ratio ≤0.995, mean rain ratio ≤0.99, temperature ratio
≤1.02 and worst regional combined ratio ≤1.15. These new limits are fixed
before outcomes. A shortlist permits a separately planned broader validation;
it does not authorize adoption. No single-region veto is used to prune the
optimization path before that stage.

Any finalist still needs prospective full-region, ocean, finer-grid and
established-region checks, and a matched world assessment before replacement
of a normal atlas climate. The other 24 dev31 regions and sealed six are not
optimization inputs in this campaign; their historical use prevents calling
them wholly new independent observations.

## What the experiment can establish

Broader coverage and separated starting points reduce dependence on the old
parameter neighborhood. They cannot prove a global optimum. Report boundary
hits, different basin outcomes, invalid cases and all regional/native skill
tradeoffs. If systematic wet-coast/dry-monsoon errors persist throughout the
box, that motivates another transport or closure hypothesis; it does not by
itself establish that every possible parameterization must fail.

Status: predeclared; new integrations not yet started.
