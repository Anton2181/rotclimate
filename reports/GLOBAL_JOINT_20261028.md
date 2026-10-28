# Joint global wind, rain and drying search — 28 October 2026

Prospectively declared after committed, independently verified wind and drying
experiments, both with empty validation shortlists. Previous outcomes and the
preserved drying-generator metadata issue remain unchanged. This experiment
uses a new fixed literal grid; it does not revise earlier acceptance decisions.

## Design

Thirty-two fixed scrambled Sobol points, seed2026102803, jointly sample six
shared coefficients. Each normalized dimension has16points in each half;
all32points are distinct. No local proposals or adaptive extension follows.
The common runner's single best-start record is bookkeeping, not refinement.

| Coefficient | Range | Scale |
|---|---:|---|
| Storm exchange rate |0.4–3.5/day before the storm envelope|log|
| Dynamic rain timescale |3–35days|log|
| Convective activation RH |0.50–0.85|linear|
| Background westerly amplitude |2.5–8.5m/s|linear|
| Legacy subsidence drying |0–0.019548865912820436|linear|
| Legacy monsoon descent |0–0.015443602894513648|linear|

Wind's lower endpoint is newly declared because the paired wind bracket's
best points remained at4.5m/s. A shared background wind coefficient is not a
planetary rotation change or a directly observed column speed; native errors
and solved branch-speed bounds remain reported/checked. These are empirical
sensitivity ranges, not measured physical confidence intervals.

Endpoint drying deletions worsened both parent settings. Continuous strengths
are still tested jointly with rain/wind, because fixed-anchor endpoint tests
cannot exclude another interaction basin. This does not assume sink removal
is a correction or attribute any future gain to one physical mechanism.

Four exact controls and32candidates each run the same seven development
regions: **252maximum new regional integrations**. Old parent anchors are
not extra runs. The two-hour ceiling, per-profile source checks and preserved
numerical failures remain. All candidate parameters are explicit in
calibration/global_joint_20261028/plan.json, committed before integrations.

## Physics and advancement

Keep independently solved lower/upper water, conservative horizontal flux and
donor vertical exchange, corrected column convection/falling-rain recycling,
no added symmetric vertical mixing, and the environmental6K/km capacity
profile. Every other actual parameter, geography, native footprint and Earth
planetary property equals the fresh environmental control. Actual coupled
land/sea temperatures, humidity and winds respond.

The inherited objective and shortlist are unchanged: equal-region normalized
combined climate error plus explicit regional/native/ocean squared regret.
Numerical convergence, conservation, branch bounds, thermal reference, source,
case and parameter identities stay hard. Prediction regressions are costs,
not individual-region pruning vetoes. The research shortlist still requires
meanS≤0.995, meanR≤0.99, meanT≤1.02 and worstS≤1.15. It permits separately
frozen broader validation, never automatic adoption.

Source/archive verification must reproduce the literal Sobol sequence and all
raw controls, actual parameter blocks and objective values. Publish every
point, failed case and native/regional tradeoff. The other24dev31regions and
sealed six are not optimization inputs here; prior historical use prevents
calling them wholly new independent observations in a later evaluation.

This is finite six-dimensional coverage, not a converged local optimizer,
a global-optimum certificate or a fully validated atmospheric energy model.
The environmental profile does not solve radiation or latent-energy feedback.
Any finalist still needs broader Earth, ocean, resolution, established-region
and matched world assessment before replacing a normal atlas climate.

Status: complete; source `c91e7b8`. All252actual regional integrations pass strict numerics, all32candidate settings meet the declared structural checks, and no candidate reaches the research shortlist.

## Completed results

The best new point is global11: F1.15523, meancombined1.05922,
meanrain1.07241, meanT1.04602, worstcombined1.28663. This is worse than
the preceding wind-study best global01 (F1.12568, meancombined1.05226,
meanrain1.06867). The new experiment therefore produces no accuracy gain
or replacement, despite broader joint coverage. All32fixed outcomes are
retained, including regional and native errors.

| Comparison | Objective | Mean rain / r39 | Mean combined / r39 |
|---|---:|---:|---:|
| Previous wind-study global01 |1.12568|1.06867|1.05226|
| New joint-global global11 |1.15523|1.07241|1.05922|

The finite32point six-dimensional design can miss a narrow or boundary basin.
It is neither a global-optimum certificate nor evidence that every possible
parameterization fails. The earlier controlled wind result and explicit
regional tradeoffs remain valid; the new data reduce confidence that tuning
these six coefficients alone is an adequate cure for the remaining bias.

All28main archived control fields and4native companions reproduce exactly.
Independent verification replays the Sobol points and conditional parent,
checks actual parameters/source/input identities, every raw row/array hash,
step water/branch certificates and the scalar objective. Cumulative series:
**1809actual attempts /1805passes /four preserved historical failures**.
This round adds252passes and no numerical failure. No full/fine/established/
world stage or adoption ran.

Six figures and compact complete metrics are published in the companion:
six-axis coverage and progress, all regional errors, weight/region sensitivity,
signed water equations, full-score rainfall seasons and native humidity seasons.
The normal climate, agricultural, population and foraging packets and measured
city-accuracy headlines remain unchanged.

The separate pressure-dependent marine RH process comparison supplies a
physical lead, not a climate gain. Any coupled implementation must explicitly
separate a physical uniform-profile ocean column from its RH taper, preserve
default controls, leave actual interior water independently solved and retain
all climate/native tradeoffs. Passing that small reference test alone cannot
authorize an atlas climate replacement.
