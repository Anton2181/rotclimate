# Resume the r38 rainfall-structure campaign

The handoff's frozen plan is unchanged at
`calibration/rain_structure_20261025/plan.json`. It searches ten existing
physical settings against the 31-region gate objective, then allows at most
three eligible candidates through the paired 28 km screen. The selected
candidate takes the established six-region check once. No candidate is an
adopted r39 merely because its search score improves.

## Input recovery before candidate search

The first invocation stopped before scoring any candidate because the newer
Earth-grid preparation required WorldClim vapor pressure, absent in this
workspace. That empty setup is preserved under `setup_missing_inputs/`.
WorldClim's 5-minute vapor-pressure archive was restored and checked, along
with January WOA18 temperature profiles used to derive ocean shelf depth.
Shared global forcing caches were prepared before parallel region workers.

All **31 r38 reference regions** were rerun. Their temperature monthly MAE
and rainfall loss reproduce the earlier adopted r38 run **exactly in every
region**. Mean monthly temperature error is 1.796 °C and rainfall loss about
0.4528. The restarted search's first control also scores **S = 1.0000**.
These remain reused development regions, not independent validation.

New benchmark identities include the actual polar-fetch, ocean-connection,
cloud-reference, monsoon-descent and sea-depth fields. Previously those newer
inputs were omitted from the per-case hash. Vapor-pressure archives are now
included in the source manifest. Existing frozen results remain intact;
current campaigns use fresh output directories. This changes provenance,
not the physics or the measured r38 climate.

`scripts/guarded_gate_search.py` verifies actual regional forcing, source
hashes, starting parameters, reference certificates and exact reproduction of
the planned objective before starting/resuming a search. A snapshot was
recorded for the restarted invocation after its control reproduced r38.
The snapshot includes the search and wrapper sources and package versions.
Future resumes should use this guard rather than the unguarded historical
entry point:

```sh
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 .venv/bin/python -I scripts/guarded_gate_search.py \
  --plan calibration/rain_structure_20261025/plan.json \
  --input-reference output/rain_structure_20261025/reference_recovery \
  --out calibration/rain_structure_20261025/search --workers 2 --hours 1.85 --resume
```

The model sources and frozen plan remain fixed while the search runs.
The worker count is two for this workspace's two-core quota; political
exports temporarily share those cores. The time budget is the handoff's
1.85-hour resumable invocation budget, not an estimate of when all 120
candidates will finish.

![Rainfall before the search](../output/rain_structure_20261025/reference_rainfall.png)

The recovered maps show the problem the plan targets: a missing wet Himalayan
front with excessive rain farther north, and deficient rain on Japan's south
coast. Brown in the ratio panels means too dry, blue-green too wet; ratios
include a +50 mm stabilizer. No post-hoc rainfall-map correction is applied.
