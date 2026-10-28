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

Status: declared; no new integrations at declaration commit.
