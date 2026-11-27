# Scope of Earth calibration and transfer to the atlas

r58 is a regional Earth model with prescribed Earth information. Its existing
accuracy gates support that configuration; they do not by themselves validate
the corresponding simulation on a fictional world. This audit clarifies an
already documented distinction, not a new invalidation of r58 or W18c.
No integrations, parameter changes, gate changes or atlas rebuild were made.

## Active and inactive observed inputs

- **Land-edge humidity is conditioned on NCEP column water.** r58 sets
  `edge_obs_pw=0.5785060503520072`. In `model.py`, the monthly observed column
  water is interpolated and capped at saturation before blending with the
  modeled land boundary value. This is an input to the moisture solve, not
  just a score. A grid without `obs_pw` raises an explicit error when this
  parameter is positive.
- **Monsoon descent uses an observed-rain-derived global field on Earth.**
  `earth.py` supplies `g.descent` from the WorldClim rainfall-driven global
  kernel. r58's `monsoon_descent=0.06087777091190219` makes it active in the
  drying/convection calculation. Where a grid has no supplied descent,
  `model.py` instead constructs descent from its own previous modeled rain
  over the available domain. Those have different forcing and spatial scope.
  WorldClim rainfall is also the Earth precipitation evaluation source; this
  prescribed forcing must be disclosed when describing predictive independence.
- **Observed SST and global observed cloud reference are inactive switches
  in r58:** `sst_source="model"`, `cloud_reference="domain"`. Loading their
  optional arrays on an Earth grid does not make those branches active.
- **Zone labels are distinct from these prescribed forcings.** A static AST
  scan of model, geography, temperature, EBM and solver files finds only one
  `g.target`/`grid.target` occurrence, used for a diagnostic array's shape.
  Earth construction and downstream scoring/export do use observed labels.
  This limited source scan is not a complete dynamic proof of all dependencies.

The r58 adoption already states that observed edge humidity is an Earth
calibration boundary and the fictional atlas keeps `land_edge_rh`. The current
atlas r51 parameter file omits `edge_obs_pw`; its config default is zero.
Simply copying r58 parameters to a grid with no observed water would therefore
fail explicitly. Removing that setting would define a changed configuration
whose performance needs its own evidence. The atlas remains r51.

## Meaning for the running padding study

Moving the domain edge changes the geographic locations of its prescribed
humidity as well as the extent of the simulated terrain, winds, filters and
other operators. Identical scored cells and observations make the comparison
useful, but do not isolate the convergence smoother's boundary treatment.
Earth's externally supplied global descent also differs from the modeled
local-domain descent available on a fictional grid. A rainfall improvement
with larger padding is neither a standalone-world validation nor evidence
that one particular operator caused it.

## Work after the frozen campaigns

First finish the fixed padding review and W18c's existing selection/gates.
Apply and retest the already prepared marine-budget export correction in a
new source epoch so coupled source attribution includes that actual term.
Before transferring a later climate profile to the atlas, explicitly record
which Earth-only forcings are replaced and validate the resulting configuration
on exposed Earth geometry with those same replacements. Preserve the
Earth-conditioned benchmark as a separate comparison. Any new experiment
needs its own declared design and budget before execution; this note launches
none and changes no current campaign or validation set.

## Reproduction

Run `.venv/bin/python calibration/earth_conditioning_20261127/audit_source.py`.
`source_audit.json` records source hashes, selected parameters including omitted
defaults, the scanned target occurrence and the pre-existing adoption note.
It performs no climate integration and preserves the recorded source epoch.
