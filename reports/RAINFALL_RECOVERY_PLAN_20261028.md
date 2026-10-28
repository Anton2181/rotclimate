# Rainfall recovery plan — 28 October 2026

The adopted rainfall benchmark has not materially improved during the recent
physics/calibration sequence. The latest seven-region screen still has its
best mean rainfall error about4.5%above r39; the best new physical ocean
variant is about5.0%above it. Native humidity improvements reduce the penalized
objective but do not establish better mean rainfall/temperature. Keep r39 and
all existing published world data as the predictive reference.

Finite broader searches and separated starts do not certify a global optimum.
They do provide enough evidence to stop prioritizing broad coefficient sweeps
while the same dry-monsoon, seasonal-timing and wet-coast errors persist.
Future iteration will use small process tests with a separate rainfall scorecard.

## First diagnosis: archived seasonal water equations

Zero new Earth runs, no fit or revised acceptance rule. The new diagnostic
script checks all nine selected source JSON/NPZ hashes, full scoring masks
and monthly water closure. These are three northern regions, avoiding the
known southern crop/calendar ambiguity. Compare retained legacy4.5, best mean
rain legacy3.5, and best objective hydrostatic-half3.5.

| Region | Mode at3.5m/s | Annual model / observed mm | JJA model / observed mm | SON model / observed mm | Peak month model / observed |
|---|---|---:|---:|---:|---|
| north india | legacy | 278 / 761 | 187 / 515 | 40 / 159 | 7 / 7 |
| north india | hydrostatic half | 319 / 761 | 215 / 515 | 46 / 159 | 7 / 7 |
| mexico | legacy | 790 / 537 | 213 / 246 | 265 / 158 | 10 / 8 |
| mexico | hydrostatic half | 935 / 537 | 256 / 246 | 324 / 158 | 10 / 8 |
| pacific nw | legacy | 1050 / 897 | 94 / 110 | 267 / 242 | 12 / 12 |
| pacific nw | hydrostatic half | 1036 / 897 | 98 / 110 | 277 / 242 | 12 / 12 |

North India half-taper JJA rain is215mm against515observed. Its modeled
advection term is+211mm, storm exchange−80mm, surface evaporation+146mm
and column drying−62mm. This is a large seasonal deficit despite positive
advective supply. Mexico JJA rain is256mm against246observed, so its broad
wet bias cannot be described simply as excessive summer rainfall. PNW JJA
is98mm against110observed; inspect its wet-season excess separately.

These are signed modeled equation balances, not independent causal shares.
Observed evaporation and exact submonthly vapor-flux covariance are missing.
Native humidity and full-score rainfall have different footprints; do not form
a rain/PW efficiency ratio across them. Actual branch velocities and donor
fluxes were not saved. Monthly column means cannot reconstruct their exact
instantaneous transport. The archive therefore motivates the next diagnostic,
not a premature attribution of the deficit to a particular closure.

A matched-state definition check also compares the legacy2200m vapor-scale-
height capacity with the new hydrostatic profile at flat uniform ocean states
from0–30°C. At the retained RH0.754746, uniform/half target water remain below
the legacy effective rain capacity throughout that range; there is no gross
matched-state over-capacity failure to explain the monsoon deficit. The
capacity definitions nevertheless differ by temperature and should remain
explicit in future process tests. This calculation is not a coupled climate
result or evidence that every real column has the same thermal structure.

## Bounded next milestone

Instrument diagnostic exports of actual lower/upper winds, layer water,
dry-mass/donor exchanges, face water fluxes, storm exchange and rain components.
Rerun only three contrasting regions ×two fixed profiles (legacy3.5 and
hydrostatic-half3.5): **six diagnostic regional reruns**, each required to
reproduce every existing climate array exactly. Freeze the source transition,
inputs, profiles and instrumentation before integrations; any changed climate
output invalidates the diagnostic-only claim. Count all actual reruns.

Align rainfall, humidity and winds to the same native footprints and calendar
before relating them. Keep full-score land budgets separately. Acquire any
missing fixed native wind/humidity input explicitly; do not call reused data
independent new validation. Retain all month/season errors and approximation
limits from model-assisted reanalysis and differing reference periods.

## Choose the mechanism from evidence

1. If ocean/low-level moisture amount is wrong while circulation is credible,
   investigate boundary-layer thermal/RH structure; the current ocean change
   alone recovers only part of the monsoon deficit.
2. If lower inflow or upper return has the wrong direction, magnitude or phase,
   revise that transport/vertical-flow closure with dry-mass and water continuity
   intact. Save pressure/layer diagnostics to test the predicted change.
3. If isotropic storm exchange drains or redistributes moisture incorrectly,
   test flow/terrain-aware conservative exchange under identical inputs.
4. If moisture and circulation are credible but rain timing/efficiency is wrong,
   test the convection/orographic conversion law separately.

These are alternative diagnostic branches, not four mechanisms to add at once.
Each gets a small manufactured/paired regional test and an explicit predicted
signature. Numerical conservation and fixed Earth properties remain mandatory;
observations never reset interior humidity or specify region-specific knobs.

## Acceptance and limits on further searching

Use separate scorecards for rainfall, temperature and native atmospheric state.
Rainfall improvement is the primary claimed climate gain. Regional prediction
tradeoffs are allowed and exposed; a better humidity-weighted objective alone
is insufficient. Define the next phase's numerical success threshold before
runs (a material benchmark such as5%mean rain-error reduction is a useful
target), then test excluded-from-fit regions and finer resolution before
adoption. Current outcomes and shortlist rules remain unchanged.

Resume broader calibration only after a process test gives a credible and
useful response. After two well-tested physical hypotheses fail to produce
material rainfall gains, reassess whether the seasonal two-layer circulation/
water architecture needs replacement, rather than extending parameter boxes.

The regional Earth setup retains observation-derived cloud and remote-monsoon
backgrounds. Keep those inputs fixed for each paired test and label results
conditional; a fully predictive global background is a separate model goal.
Continue committing/pushing tested milestones and updating the .bat-served
research atlas, with plots that distinguish native-state gains from rain gains.
