# Conservative moisture replay on r42

Prospective eight-region development screen. This starts **after** the r42
atlas has passed its final publication checks and its commit has been pushed.
It cannot change the adopted model or an atlas.

The first profile changes numerical damping/work limits only. It must preserve
all reference forcing and observations, pass strict convergence checks, and
stay within 0.01 C / 0.05 mm per month of the retained r42 fields. Otherwise the
screen stops without attempting the physical profiles.

Four physical profiles then revisit conservative vapor/storm transport,
mass-balanced counterflow, independently stored layer moisture, and removal of
empirical drying terms when resolved transport is enabled. These existing
opt-in mechanisms previously struggled on older circulation. The experiment
asks whether r42's changed circulation provides a better basis; it does not
assume that conservation alone produces realistic weather.

All eight cases are reused development regions, not unseen validation. Every
outcome is retained; incomplete profiles receive no aggregate score. No
observed wind, humidity, or SST fields are imposed, and the Earth transform
keeps the same planet. A useful result would still need tuning and full 49-region,
fine-grid, wind/SST and prospective unseen evaluation before adoption.

Run from the repository root after committing the declaration:

```sh
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 nice -n 10 .venv/bin/python -u -I \
  scripts/run_r42_conservative_replay.py \
  --plan calibration/r42_conservative_replay_20261102/plan.json \
  --out output/r42_conservative_replay_20261102 --workers 1
```

The driver records status and all profile logs in the output folder. It checks
frozen sources before and after each profile, commits only its own results,
and pushes the result commit. A failed atlas publication leaves this queue
unstarted. The declared maximum is 40 new regional integrations, including
the eight numerical controls.
