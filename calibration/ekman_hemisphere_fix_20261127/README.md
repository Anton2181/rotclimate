# Signed-hemisphere coastal Ekman correction

The production upwelling direction formerly turned all prograde winds right,
even where the actual modeled latitude is southern. This contradicts the
signed-Coriolis balance: right inNH/left inSH, reversing for retrograde spin.
New ekman_turn supplies only that directional quarter-turn, preserving the
existing magnitude/cooling/weights/smoothing elsewhere. At exactly f0 the
hemisphere direction is undefined, so the empirical contribution is zero;
this is not a resolved equatorial upwelling or wind-stress transport model.

Ten known-answer production SST snapshots stop at the existing sst tap before
any heat/moisture solve: both hemispheres, both spins, wind reversal and exact
equator. Before the fix6fail/4pass; after all10pass. A further known-vector
check verifies exact legacyNH bytes (including signed zero) and commutation
with a proper map rotation. Combined56 relevant tests pass with no skips or
failures. Pre-fix failures and final regression XML/logs are retained. All prior
scientific workers exited before source changes; completed packets immutable.

Prospectively commit this plan/source before six regional integrations. Same
three exposed cases, both modeled and prescribed surface wind. Same params,
56km cells,1100km pad, actual inputs, scored cells and original numerical
criteria. Four Sahara/NIndia domains entirely north of equator MUST reproduce
all shared physical/raw/budget fields byte-exact. Somalia domains cross the
equator: report actual changes, no fit or accuracy/adoption gate. All6 original
certificates and0.01 local equations must pass; verify prescribed raw winds.
One worker nice10, all4thread variables1; literal venv Python path. Prepare
with scripts/run_ekman_hemisphere_regression.py, execute once with --run. Fixed
6-run limit, preserve/stop on any failure or interruption, no automatic retry.

New225 regular private files use current89 model source files and frozen134
caches/2helpers. Record the new source epoch separately; prior qualifications
are historical, not silently current after this fix. No atlas rebuild or
calibration adoption: r58 retained, atlasr51 unchanged, W18c closed,AAunopened.
A current-source97-region paired reference is still required before fitting.
