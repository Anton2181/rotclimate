# Identify the origin of misplaced cloud rain

**Completed 16 October:** all four replays verify and reproduce the original
physical climates exactly, in 8.81 integration minutes. In Iberia-domain
reference-arid summer rain, 74.9% is boundary-labelled, 16.9% ocean evaporation
and 8.2% land recycling. See [verified source results](../output/v10_cloud_source_review/review.md)
and the [next local-boundary-humidity test](v10_spatial_humidity.md). The original
handoff below is retained. Atlas unchanged.

16 October 2026. The [completed cloud review](../output/v10_cloud_review/review.md)
verifies 52 cases / 192 saved years. Coastal winter gains repeat across four
catalogues and survive a halved permitted time step, but Iberia-domain error
barely improves. In the fixed seed67 stronger-lifting/linked comparison,
reference-Mediterranean land contributes +0.700mm/month to overall error
improvement, reference-arid land contributes -1.337mm/month, and other land
+0.738mm/month. Extra summer rain in reference-arid land offsets the useful
wetting. The interior mask includes North Africa, not just the Iberian peninsula.

The new passive replay asks where that misplaced rain last entered the
atmosphere: the open boundary, ocean evaporation, land recycling, or the
unknown initial vapor pool. It changes no physical tendency.

```sh
caffeinate -i .venv/bin/python -u scripts/replay_v10_cloud_sources.py --run
```

Four final-year replays: California/Iberia × bulk/lower-interface cloud rule,
all at the fixed seed67 stronger-lifting/linked forcing. Each starts from its
exact saved preceding-year state and must reproduce every physical field and
original ledger exactly, except elapsed time. No new spin-up, search or changed
climate. Estimated 10–25 minutes; 45-minute invocation cap, monthly checkpoints
and same-command resume. The assistant has not launched an annual replay.

## Passive attribution and limits

Transport four water labels with the same upwind fluxes, explicit boundary
humidity and dry mass as the physical model. Incoming boundary vapor receives
the boundary label; new ocean/land evaporation receives its corresponding
label. Initial atmospheric water is explicitly unknown. Land evaporation is
relabelled recycling regardless of the original origin of water in soil.
This answers **last vapor entry**, not molecular ancestry or the fraction of
rain causally removed by turning evaporation off.

The new cloud rule needs a specific treatment that the old bulk tracer lacked:
parcel condensate inherits its ascending donor's labels **before** recipient
mixing. Only the remaining bulk condensate is partitioned using the recipient's
mixed vapor. All labels sum to the physical stores/rain, with separate per-source
atmospheric budgets and bounded explicit roundoff reconciliation. They never
feed back into circulation, moisture, energy, soil or precipitation.

Save monthly source rainfall for each layer/cell, full source budgets, initial
and final pools, and the remaining unknown fraction. Report coast, interior,
scored land and reference Mediterranean/arid/other masks. Winter follows the
frozen response convention of October–March; summer is April–September.
Earlier prose describing response winter as November–April was incorrect;
the completed numerical response fields have not been changed. The separately
labelled November–April diagnostic-opportunity audit used its stated months.

If misplaced summer rain is mostly land-labelled, the next controlled test can
examine excessive recycling or its coupling to the unmixed cloud rule. If it is
mostly boundary/ocean-labelled, examine lifting placement, moisture transport
and the cloud rule before adjusting the soil bucket. Neither branch follows
causally from tags alone; a changed-physics comparison would still be required.

## Readiness and evidence

153 focused tests pass. New tests cover ascending-donor source attribution,
unchanged physical arrays, exact tiny-year replay, checkpoint/resume of both
physics and tags, source budgets and corruption/time-budget guards. Four
independent real-input probes of at most 60 simulated seconds also pass;
maximum source/store/rain/reconciliation residual is 1.78e-15mm. No real annual
replay or calibration was launched by the assistant.

Source:
`e307b56edc61e03b0313d2a9e93c924d4d9b3573e389191fc8239f00b99dd748`.
Prepared manifest: `output/v10_cloud_sources_preflight/manifest.json`.
Outputs: `output/v10_cloud_sources/{progress.json,state.json,summary.md,cases/}`.
Parent experiments and the fantasy atlas remain unchanged. Do not rerun or
edit completed parent experiments while using their frozen evidence.
