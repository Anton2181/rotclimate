# Fixed marine-equilibrium target cap pilot

Six integrations only: Somalia `s_2n_43e`, Sahara `u_21n_21e` and `north_india`
at the original 56 km / 1100 km domain, three exact legacy controls first,
then the same three regions with a single Boolean source-cap law. Base is
adopted r58 in the applied marine-export diagnostic epoch. No coefficient fit,
intermediate cap strength, alternate padding, new fine or sealed-AA target,
climate adoption or atlas work is part of this pilot. W18c stays closed.

The current law targets a fraction of receiving-land saturation water. The
new law caps that target at the nearest sea's **modeled equilibrium column
water** before it is replaced by a land target. It retains the existing SST,
onshore-wind and distance gate formulas and their parameters. Realized rates
may change through the coupled climate response. An all-land domain disables
marine relaxation, including drying; all-sea equilibrium targets are unchanged.
No observation or biome label enters this new law. Existing observed Earth
boundary PW and rain-derived remote descent remain active in both arms.

This equilibrium proxy is not the actual instantaneous upstream vapor, a
back-trajectory humidity measurement, a conservative marine flux or a complete
terrain/vertical-transport model. The cap is a bounded physical hypothesis,
not an established correction. Its coupled effects on monsoon moisture must
be retained even if Somalia improves.

The unapplied patch changes only private config/model files and adds the
small pure target helper. Main model source and adopted parameters remain
unchanged. Controls must match every saved scored monthly physical field,
trace gain/sink/W/P/calendar and complete local budget in dtype, shape and
bytes. Every run must pass unchanged original numerical checks and the 0.01
local equation residual, with explicit float32 export rounding bounds.
Candidate source-target/rate traces independently reconstruct the recorded
marine term. Failure stops the study; no automatic scientific retries or
solver changes. Missing cases cannot be pooled or filled with zeros.

The prospective local screen requires at least 1% reduction in Somalia rain
loss, with neither T MAE nor rain loss worsening over 1% in any of the three
regions. Passing only permits further exposed evaluation; it is not a global
gate or deployment qualification. If it fails, do not search cap strengths or
reinterpret the protection after seeing results.

Seven pure helper tests passed before any integration: source/land bounds,
unchanged mixed-grid rates, all-land absence of source/drying, bit-exact sea
targets, invalid nearest sources/indices and nonfinite/negative input checks.
The design and scripts must be committed before preparation or execution.

```sh
.venv/bin/python -I scripts/prepare_marine_target_cap.py
OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1 \
  nice -n 10 .venv/bin/python -I scripts/run_marine_target_cap.py
```

The second command performs readiness checks only. Add `--run` for the six
fixed integrations. One low-priority worker and a singleton lock preserve the
budget. Frozen source/input/private-cache hashes and attempt receipts guard
execution. The independent reviewer automatically produces all component
accounts, declared screen results and `cap_response.png` after all six pass.
An agent must inspect that figure and publish actual findings. No program
automatically adopts the candidate, patches main, opens validation targets or
commits/pushes results.
