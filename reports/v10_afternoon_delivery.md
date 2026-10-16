# Three-to-four-hour delivery and weather-repeatability batch

15 October 2026. The user requested a bounded unattended batch after completing
the twelve-case event-forcing experiment. No real annual integration is run by
the assistant. Use cached reference inputs; NOAA access remains paused.

```sh
caffeinate -i .venv/bin/python -u scripts/afternoon_v10_delivery.py --run --hours 3.75
```

The invocation has a 3-hour-45-minute budget. It may finish earlier; it stops
near the budget if cases remain. Time checks occur during integration, with
monthly checkpoints. An interrupted month is repeated on resume. Run the same
command again to continue, with another invocation budget. It verifies completed
evidence before skipping it. Do not edit experiment sources while it runs.

## Fixed work order

1. Four passive diagnostic replays of the completed seed-41 final years, using
   their exact preceding-year states. Require identical physical arrays,
   monthly rainfall and annual ledgers, excluding elapsed time.
2. Eight fixed synthetic catalogues: 67, 103, 149, 211, 307, 401, 503, 607.
   For each catalogue and each California/Iberia region, run four conditions:
   original lifting with steady humidity; sixteenfold convergence fluctuations
   with steady, event-linked or half-month-shifted humidity. Each case runs
   three to six repeating annual cycles, retaining the settling assessment.
3. After each region/catalogue's four climates, replay the final year of the
   original/steady and stronger-lifting/event-linked cases with passive
   diagnostics. Again require exact physical reproduction.

Total: four reference replays, 64 climates and 32 new-weather diagnostic
replays, or 100 jobs. The old 12-case experiment took 31 minutes; this larger
batch is estimated at roughly 3–4 hours, with runtime depending on weather,
settling and diagnostic overhead. The budget controls the duration even if
not all 100 jobs finish. Regions/catalogues form complete comparison groups
in sequence, so partial completion retains usable paired evidence.

## What this resolves

The completed experiment increased coastal winter rainfall from 26.0 to
70.2 mm in California and 16.3 to 35.5 mm in Iberia, versus 534.8 and 439.2 mm
in the reference. It did not solve Mediterranean drought. Timing accounted
for only a small, nonuniform part of the improvement in one catalogue.

The diagnostic replays measure coastal/interior vapor input and export,
recipient humidity during upward exchange, layer rainfall, and instantaneous
condensation opportunities before and after prescribed thermal relaxation.
They distinguish possible delivery and saturation bottlenecks without
changing the physical trajectory. Opportunity sums can recount the same
vapor; they are not the rainfall of an alternative climate. Regional gross
transfers are not source tags or causal rainfall fractions.

The paired catalogues check whether the lifting effect and small timing
effect repeat across different synthetic storms. Sixteenfold amplification
is a fixed forcing contrast inherited from the prior forcing-only audit,
not an observed storm strength. It is not retuned for each catalogue. Monthly
mean dry circulation is retained and monthly gross incoming boundary water
is matched across conditions **within** each catalogue/region. Means and
water doses need not match **between** different catalogues.

No best catalogue or parameter set is selected. Some catalogues were used
in prior studies; this is paired sensitivity, not untouched validation or
an observational confidence interval. Keep all outcomes, including labelled
unsettled cases. The reference temperature, prescribed circulation, dry
upper boundary and instantaneous liquid rainout limitations remain.

## Evidence and safeguards

New adapters are confined to `experiments/v10_weather_panel.py` and the new
runner. They reuse the frozen physical engine, and change the weather seed
through instance-local events. The original seed-41 algorithm must reproduce
exactly. Sources, inputs, forcing arrays, completed summaries and annual
checkpoint files are pinned and checked on resume. Changed evidence stops
the batch for diagnosis. Outputs are separate from all parent evidence.

113 focused tests pass, covering paired ordering, explicit seeding, exact
original forcing/physics on tiny manufactured inputs, passive diagnostics,
binary restart, time limits, corrupted evidence and read-only default use.
The preflight passed: two seed-67 forcing calendars, an exactly reproduced
California seed-41 calendar, and 24 independent regional operator probes of
at most 60 simulated seconds. Seed-41 flow/boundary adapters are identical in
both regions; the passive collector leaves all tested physical arrays intact.
No real annual climate was integrated. Frozen event and diagnostic sources
still match their prepared identities. The new batch source is
`9446abd0630b812322925a76e41e62ea891ca1bb0d9b690c9d0213342004f306`.

Progress, logs and the accumulating paired summary are in
`output/v10_afternoon_delivery/`. Full passive diagnostics are in each case's
`summary.json` and checkpoint arrays. The fantasy atlas stays unchanged.

See the [completed event review](../output/v10_event_review/review.md),
[four-reference-replay protocol](v10_delivery_replay.md) and
[research strategy](research_strategy_20261015.md).
