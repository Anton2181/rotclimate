# Settlement and de facto control development roadmap

Owner approved 10 November 2026. This is the durable queue for the whole programme,
not just its first experiment. Read this alongside the current entry in HANDOFF.md
at every continuation. Physics development has its own queue; neither queue
silently replaces the other.

## Working rules

* Every milestone records code, Earth data exposure, results, limitations, adoption
  decision, atlas consequences, and the next unfinished task. Commit and push
  milestones to both maintained branches. A failed experiment does not complete
  its parent stage or cancel later stages.
* Follow the dependency chain: environment → occupancy and land use → settlements
  → shared people/food allocation → institutions and transport → differentiated
  control. New utility layers must have an explicit consumer in this chain.
* Include all actors, unaffiliated communities and mobile populations. Missing
  markers are missing evidence, not proof of empty or ungoverned land.
* Keep recorded sites, game-era administrative scenarios and generated hypotheses
  distinguishable. A generated town is not independent evidence for its owner.
* Keep one population, land and seasonal food ledger. Do not add overlapping
  farming, pastoral or foraging capacities or invent institutional staff.
* Separate development, spent evaluation and genuinely prospective tests. Han,
  Rome, Hellenistic sites, Sui 610, Tang 742, the inspected medieval city pools and
  Domesday are already exposed. New dates sharing sites are not independent by
  default. Never rerun an old test and call it blind.
* Publish qualified changes through the normal Windows launcher atlas; preserve
  previous defaults when evidence is insufficient. Expose experimental results
  as research, with their status, rather than silently replacing the main map.

## Successive stages

### S1 — Count-separated, clustered settlement placement [IN PROGRESS]

- [x] S1a: Preserve the current Earth-tested count as a separate budget; implement
  candidate placement with explicit eligibility, marked anchors, reproducible
  seeds and reported shortfalls. Count must not change with the history prior.
- [x] S1b: Compare clustering and locations on declared development Earth pools;
  isolate count separation, spacing and history-prior effects. Report seed spread,
  counts, 25 km matching, 100 km block rank and nearest-neighbour spacing.
- [ ] S1c: Resolve historical occupancy assumptions. Do not equate food capacity
  with actual population or use Rome as a timeless medieval urban attractor.
- [ ] S1d: Freeze a finalist and identify a defensible prospective transfer pool
  before evaluating it. Record coverage, site roles, shared geography and dates.
- [ ] S1e: If qualified, rebuild settlements, tracks, food-supported institutions
  and control together; show actual before/after atlas maps. Otherwise record
  rejection and the next S1 experiment. Parent S1 remains unfinished.

Done means: count and placement are genuinely independent, clustering improves
without an unacceptable aggregate location loss, transfer has been assessed, and
the downstream consumer chain has been reviewed. A passing unit test is not an
Earth qualification.

### S2 — Rural settlements, market hierarchy and institutional roles [PENDING]

- [ ] Separate villages, markets, ports, administrative seats and garrisons;
  roles may overlap. Preserve known anchors; do not classify from icon size alone.
- [ ] Allocate resident populations and service catchments from the same rural
  population and food ledger. Fit sizes/roles using appropriate Earth evidence.
- [ ] Model settlement interactions and demand for routes, checking that demand
  does not create cost-free transport or double-count generated infrastructure.
- [ ] Validate counts, clustering, rank/size and role-specific performance;
  distinguish administrative-seat datasets from village surveys and urban lists.
- [ ] Rebuild available administrative/military sources and atlas outputs.

Literature starting point: Bevan & Wilson (2013), doi:10.1016/j.jas.2012.12.025.
Done means: role-specific settlements feed the actual authority model, not merely
another descriptive overlay.

### S3 — Local administration, central connection and military reach [PENDING]

- [ ] Connect existing administrative-link diagnostics to local institutional
  persistence and central coordination; include non-imperial actor structures.
- [ ] Distinguish local administration, fiscal collection, military access and
  nominal claims. Losing a capital link must not erase local institutions.
- [ ] Retain identifiable enclosure assumptions and unknown/unscored areas.
- [ ] Validate each relationship against relevant Earth evidence, reporting the
  limits of historical extent polygons as proxies for local obedience.
- [ ] Integrate differentiated control into the main atlas without selector clutter.

Literature starting point: Smith (2005), doi:10.1111/j.1467-8306.2005.00489.x.

### S4 — Collectible surplus and sustained institutions [PENDING]

- [ ] Audit existing production → household needs → storage → collection → freight
  → civilian/staff allocation as one seasonal ledger; reuse current machinery.
- [ ] Constrain staff, collection and transport by resources, capacity and explicit
  access/permission scenarios. Fed residents do not automatically become soldiers.
- [ ] Feed viable institutions into local administration and central coordination;
  roads improve travel but are not independent authority sources.
- [ ] Test seasonal failures, shortages and source-inventory sensitivity on Earth;
  distinguish annual effective access from reliable seasonal presence.
- [ ] Publish the resulting settlement and control changes together.

Literature starting point: Mayshar, Moav & Pascali (2022), doi:10.1086/718372.
Appropriability motivates a hypothesis to test, not a cereal-to-state shortcut.

### S5 — Mobile and nonstate communities [PENDING]

- [ ] Connect existing grazing/foraging and seasonal-circuit experiments to actual
  occupancy, with water, feed, camp locations and non-overlapping resource use.
- [ ] Represent local communities, negotiated passage and overlapping seasonal
  rights without forcing permanent towns or a single tribal state everywhere.
- [ ] Feed mobile occupancy and institutions into settlements/control while
  distinguishing land use from exclusive political sovereignty.
- [ ] Validate mobility/resource use with suitable Earth analogues; expose missing
  evidence and avoid inferring social organisation from biome alone.
- [ ] Publish integrated results for imperial, other-state and nonstate areas.

## Cross-cutting work, required at every stage [ONGOING]

- [ ] Ensembles over site draws, historical occupancy and uncertain affiliations;
  report recurring centres/control and scenario sensitivity, not uncalibrated
  probabilities presented as confidence.
- [ ] Maintain data/source identities, Earth exposure register, population/food
  conservation checks and separate component versus end-to-end validation.
- [ ] Keep normal launcher atlases, explanatory text and exports consistent;
  post useful generated maps during development.

## Current resumption point

S1a/b initial milestone completed on10November: count-separated allocator,
72 prespecified evaluations across two exposed Earth pools, five-seed comparisons,
unique matching, retained prepared NPZs and research-page publication. Details:
[SETTLEMENT_LOCATIONS_20261110.md](SETTLEMENT_LOCATIONS_20261110.md).

The original November7 inputs were not recovered exactly. Reconstructed current
slope/HAND inputs have newly computed paired baselines; historical JSON scores
were not reused as controls. All variants preserve1202 Han/1292 Roman proposals.
The development lead improves clustering strongly and Han unique matching, while
Roman unique F1 slips0.367→0.358. **Not adopted.** S1 as a parent remains unfinished.

Next: S1c, resolve historical occupancy and evaluation resolution/roles. Preserve
the distinction between known historical inputs and generated priors; examine the
Roman unique-match loss rather than optimizing proximity scores alone. Compare
the frozen grid's deterministic18km history alternative: it improves uniqueF1 in
both pools (Han0.591, Rome0.422), but has worse spacingKS than the selected9km
stochastic lead. Preserve both; do not silently replace the frozen winner or
claim this inspected tradeoff is fresh validation. The9km
raster/exclusion has an explicit spacing-error floor and is not a village test.
Then S1d needs a frozen defensible prospective transfer protocol; exposed Han,
Rome, Sui, Tang, Hellenistic, medieval-city and Domesday pools cannot qualify as
new unseen tests. Hellenistic source recovery/extra development comparison also
remains available; it was not a recovered pool in this two-pool protocol.

After qualification, S1e rebuilds the shared settlement/food/staffing/control chain.
Then continue S2–S5 above. No parent stage is complete; no later stage is dropped.

## Milestone log

|Date|Milestone|Evidence/decision|Next|
|---|---|---|---|
|2026-11-10|Full programme persisted and pushed; commit67f68aad|Five stages, completion criteria, cross-cutting requirements|S1a/b|
|2026-11-10|Development protocol frozen; commit17c73556|Twelve variants, fixed counts, exposed data only, no adoption|Recover inputs and run|
|2026-11-10|S1a/b initial comparison complete|See settlement-locations report; no production adoption|S1c/d, then S1e; retain S2–S5|
