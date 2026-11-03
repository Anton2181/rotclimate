# Conservative fitted-flux screen

Declared before any fitted regional climate integration. Eight reused development regions only. Fresh unchanged-r43 control must match original raw r43 fields within .01 C/.05 mm monthly with identical observed/forcing footprint. Both fixed conservative vapor/storm profiles finish; only the vapor face stencil differs between them. Physical diffusivity, planet/orbit, modeled winds/SST and closures fixed. No tuning, reserved F, model adoption or normal atlas changes. Incomplete profiles stay unscored.

Source pinned to `c20f99bdee079fbb34221964799693bfdbc2ca25`. Waits for complete r43 atlas
publication to prioritize the map export. One worker; private derived-cache writes.

Run: `.venv/bin/python -u -I scripts/screen_fitted_flux.py --plan calibration/fitted_flux_20261103/plan.json`

All outcomes and raw cell packets are retained and pushed to both branches.
The combined error uses equal-region means of T MAE and rain loss, normalized
to the fresh control. Compare fitted flux directly with conservative upwind
flux as well as the production control; a relative gain need not beat production.
