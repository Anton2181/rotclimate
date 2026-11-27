# Four unchanged circulation-component captures

The public NCEP/NCAR 1991-2020 sigma0.995 surface reference reverses the sign
of July's eastward wind at the scored Somali cells: +2.50 m/s observed versus
-6.81 in r58; the larger domain gives -4.02. This motivates a component audit,
not another humidity fit or adoption of observed winds on a fictional world.

Four fixed diagnostic replays only: Somalia at1100/4012km, Sahara1100 and
NorthIndia1100, all56km with the same r58/Earth parameters and scored cells.
Instance wrappers return the original zonal/pressure wind outputs unchanged.
They capture the pressure actually supplied to the prior-step turning gate,
current thermal-pressure anomaly and returned wind components. Original
strict certificates and exact dtype/shape/bytes of saved monthly physical
states, gain/sink/W/P traces/calendar and complete budgets are mandatory.
No source/parameter/tolerance change, numerical retry or new physical variant.

All four use Earth normalization (prograde, north bearing0), pressure winds,
no wind cap, no friction split, no added subtropical/latent-heating wind and
no moisture shear. The independent reviewer reconstructs momentum from Pa/m,
signed Coriolis and actual friction, then reconstructs total wind from returned
belt/turning plus pressure contributions and drag. It checks surface/moisture
wind equality at every saved scored sample. Pressure-gate clipping and crossing
masks are calculated per step before monthly averaging.

The NCEP fields never enter g.obs_wind, model SST, boundary water or a solver.
The independent reviewer uses them only after the four physical runs finish.
Surface sigma0.995 is not850hPa. Its 2.5-degree resolution cannot validate a
coastal jet's fine placement. Full observed SLP and its global-zonal anomaly
are both retained as distinct diagnostic slopes; neither is equated to the
model's temperature-derived pressure anomaly or copied into its turning gate.
SLP's source millibars are explicitly converted to Pa. The period, grids,
missing values, scales and units were verified from the raw public files.

Prepare and run after committing the design:

```sh
OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1 \
  nice -n 10 .venv/bin/python -I scripts/trace_circulation_components.py
```

Add `--run` for the fixed four captures. Fresh225 regular private files and
immutable source/input hashes preserve isolation. A singleton lock/attempt
receipts prevent duplication; failure stops execution without retry. Status
has per-step timestamps. The independent review/figure runs automatically
after all four pass; inspect it and publish actual findings. Five reference/
momentum-unit tests passed before any integration.

The public reference came from NOAA PSL's THREDDS fileServer after its download
hostname timed out. One429 was recovered with a delayed data request. Those
were data acquisitions, not regional integrations. Raw files, exact URLs/hashes,
verified metadata and normalized data are in output/circulation_reference_20261127/.
No fine/AA target use, W18c revival, coefficient search, climate adoption or
atlas rebuild is part of this diagnostic.
