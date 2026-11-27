# Six exact rain-closure captures

Prospective6-run budget, commit before preparation or integration. Replay three
baseline cases then three jointly observed wind/SST endpoints from the finished
wind_sst_diagnostic_20261127 packet. Same source/params/inputs/grid/observations,
56km/1100km and original strict numerical criteria; all parent shared fields,
raw winds/SST/sea targets and budgets must reproduce byte-exact. No tuning.

A private-module wrapper calls original solve_moisture with unchanged arguments,
returns its original object, and copies actual solved W plus actual saturation,
dynamics, instability and all closure values. No condensate or humidity spread
in this fixed legacy branch; assert these declared conditions. Restore wrapper
after run even on failure. Save complete scored trace and verify independent
base humidity/dynamics rain, exponential/capped/subcloud-attenuated convection,
and supersaturation sum to actual rain. Four pure known-answer tests pass.

Run scripts/trace_rain_closure.py to prepare225 regular private files, then
--run; one worker nice10/all4thread vars1/literalvenvPython. Preserve and stop
on any failure/interruption; no automatic retry or tolerance change. Independent
scripts/review_rain_closure.py checks actual parent params/arrays/certificates,
reconstructs components separately, reports annual and interval-weighted July
means and draws stacked monthly rain versus fixed observations. Component sizes
are identities, not effects of removing terms. No adoption or new profile.
W18c CLOSED,AAUNOPENED,r58retained,atlasr51unchanged; current97reference absent.
