# Handoff — Earth temperature correction (30 October 2026)

Branch `claude/ecstatic-wozniak-rtrwd2`. Previous handoff (regional rainfall
benchmark, terrain research cores, detached jobs of an earlier container that
no longer exist): `reports/handoffs/BEFORE_EARTH_CORRECTION_20261030.md`.

## State

* Adopted physics is still **r39** (`calibration/local_accuracy_20261023/r39_params.json`);
  normal atlases still publish verified r38 world fields. Nothing in
  `rotclimate/model.py`, `config.py` or `joint.py` changed this session.
* Fresh-container setup: `python3 -m venv .venv && .venv/bin/pip install -r requirements.txt scikit-learn`;
  WorldClim 2.1 5′ `tavg prec elev vapr` zips into `data/cache/worldclim/`
  (geodata.ucdavis.edu); `python -I scripts/prepare_woa18.py --download`.
  The r39 dev31 run then reproduces every archived cell hash.
* New: `rotclimate/correction.py` (numpy-only application),
  `scripts/train_earth_correction.py`, `scripts/evaluate_earth_correction.py`,
  `scripts/plot_earth_correction.py`, `tests/test_earth_correction.py`.
  Model files: `calibration/earth_correction_20261030/` (final model, 12
  held-out fold models, evaluation, protocol hashes). Evidence and figures:
  `output/earth_correction_20261030/`. Report: `reports/EARTH_CORRECTION_20261030.md`.

## Measured (held out by geographic cluster)

Monthly land T MAE 1.793 → 1.540 °C over 31 regions, every policy group
better; 28 km pairs 1.896 → 1.274; 14 km pairs (atlas scale) 1.908 → 1.288; sealed Norway/SE Africa 2.621 → 2.143.
Worse: six regions (South Brazil +0.22 °C worst), seasonal range MAE +6 %,
coldest month +1 %. Köppen agreement ~unchanged (rain dominates classes).
Rain corrections were tested and **rejected** (cluster holdout made unseen
continents worse). Air-coupled SST seasonality (e53) and coupling retunes
were tested and **rejected** (S 0.999–1.023), code reverted.

Full test suite: 1605 pass; 7 fail identically on the pre-session commit
7e0b146 (harvest `settlement_cored`, Mediterranean spin-up `column_projector`,
zonefit missing `calibration/r19p_earthlike/best_params.json`).

## Rules to keep

* The correction is valid only for r39 physics (hash in its metadata);
  refit after any physics change. Keep raw output alongside corrected.
* Score honestly with whole clusters held out: neighbouring regions overlap.
* Do not tune on the sealed regions (norway, southeast_africa); they have now
  been used once for this milestone.

## Next

1. r39 world refit that scores painted zones on corrected temperatures; atlas
   layers raw + corrected.
2. Physics for the maritime lag: the land air is ~95 % sea-controlled because
   the land equilibrium is the latitude's continental column (2.3 °C mean over
   Britain). Needs a land surface layer / two-tile coast and recalibration.
3. Small: two-scale relief lapse (+~0.8 % T alone).
