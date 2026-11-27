# Fixed wind × marine-relaxation ablation

Declare and commit before any preparation or integration. Twelve fixed runs on
Somalia/Sahara/North India at56km,1100km pad and identical scored cells. First
six are exact controls, replicating BOTH model- and observed-wind arms of the
completed surface_wind_diagnostic_20261127 study. Next six disable only
inflow_gain (set0), repeating the same wind arms. The source removes both
marine moistening and drying, not evaporation or ordinary resolved advection.
The fixed complete2×2 design is diagnostic; no score screen or selection.

Same current89 physical source files,134 frozen caches,2 helpers as parent,
all225 regular private copies. Same existing solver settings and strict0.01
criterion. One worker nice10, all4 BLAS/OMP thread variables1. Literal venv
Python path, never resolve its symlink. Exactly12 integration limit; preserve
and STOP on any numerical/physical replay/verification failure or interrupted
attempt, without automatic retry, budget extension or tolerance adjustment.

Run scripts/run_wind_marine_ablation.py to prepare only, then --run to execute.
The new private model and full projected forcing packets are separate from
immutable completed studies. Full-source/input/library/plan hashes checked.
Read-only observed surface wind uses the same verified reference, projection
metrics/rotation and calendar. Actual heat and moisture wind samples must be
exactly prescribed. All6 controls must match every saved shared physical/raw/
budget field byte-exact; disabled arms must have identically zero marine term.
Independent scripts/review_wind_marine_ablation.py checks raw fields/attempts,
source/forcing/parameter provenance, certificates, equations and comparisons.
Report all four arms/region, both within-wind source ablation responses, and
change in observed-minus-modeled wind rainfall response under ablation.

The prior6-run study found Somali convergence import fell by1332mm/year but
marine source increased1675mm/year, offsetting circulation correction. This
ablation measures coupled compensation and monsoon/desert costs. A beneficial
result would not establish a general source law: removing e91 also changes
W, heat, advection, recycling, and drying. Do not infer tagged fractions or
conservative planetary closure. Do not reopen/tune the rejected target-cap
law, W18c finalist or spent validation. AA UNOPENED; r58 retained; atlasr51
unchanged. Fresh current-source paired reference required before calibration.
