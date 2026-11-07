# Next calibrated control map (v2), with predicted settlements and population: queued plan

*7 November 2026.* This is a queue, not a test plan. Each step below gets its own frozen plan JSON before any result, and no atlas default changes unless a step passes on data it was not developed on. The ledger of spent and reserved data is `calibration/earth_components_20261105/dataset_usage.json`.

## Where things stand

**The control map.**
- **Default:** the transport-only map (legacy_0). It won the round-1 Earth test (Rome 0.820, Han 0.700).
- **Round 2 (development only):** two fixes were made on Rome / Han.
  - *Rural claim.* It now scales with the harvest (L1). With it, bare fallow staffs 84 % of Roman towns and 92 % of Han seats.
  - *Reach rule.* P2: staffed towns plus the roads within 2 year-round days of them. With it, Rome scores 0.835 against 0.820, and Han 0.682–0.692 against 0.700.
- **Blind test:** running on two never-used pools (`plan_blind.json`): Pleiades Hellenistic settlements against the land of any state in 200 BC, and Neo-Assyrian settlements against 700 BC.

**Settlements.** The atlas places candidate towns where food and transport favour them (seat counts and spacing fitted on Earth). It does not yet predict villages, sizes or where settlement stops.

**Population.** The atlas spreads a *declared* budget (60.6 M) by food support. It does not yet predict the total.

## Step 1 — control map v2 (depends on the blind result)

**If a food case passes G1 and G2 in both blind pools:**
1. **Build L1 into the atlas chain.** In `scripts/extend_settlement_fertility.py` the rural claim becomes 0.6 × the produced harvest for the fertility regimes. The labour cases keep the fixed claim, because they model short-term shocks.
2. **Build P2 into the atlas reach.** In `polity/fields.py` each polity's own sources become its *staffed* towns plus its roads within 2 year-round days of them. The year-round days, held days (2.0) and gap-fill code are unchanged.
3. **Publish as new options**, check them against the current maps, then make the passing case with the lowest census error the default. The badge becomes "Earth-tested (blind)".

**If none passes:** transport only stays the default. Report which gate failed and where, and write the next development round as its own frozen plan.

## Step 2 — predicted settlement spread (where towns and villages are)

**Question:** given the climate, food, transport and the control chain, where do settlements sit, how far apart are they, and where does settlement stop?

1. **Development (seen data).**
   - *Data.* Hanson's towns (AD 150) and the Han AD 2 county seats.
   - *Generator.* The atlas's own (`polity.settle.place_towns` on the Earth density), with no historical input.
   - *Metrics.* Three, each against the real points:
     - towns per 100 km block (rank correlation and count error);
     - the nearest-neighbour spacing distribution;
     - recall of real sites within 1 day of a generated site.
2. **Blind pool (to declare before download and scoring): the Domesday survey of England, 1086.**
   - *Why it fits.* About 13,000 vills, each with recorded households. It is a fine-grained, complete village record from a three-field, low-input farming world, which is the regime the fertility model represents.
   - *Never used here.* The Earth land/people grid covers England.
   - *What it would test.* Settlement density and spacing at the village scale, and (Step 3) population.
3. **Atlas.** Generated village-scale settlement (counts, spacing, edge of settlement), shown as a layer badged by its test.

## Step 3 — predicted population (the total, not a declared budget)

**Question:** how many people does the land feed under the AD 200 regime, and where do they live?

1. **One ledger.** Rural population = the people the regime's harvest feeds (L1), plus pastoral and foraging populations from their own models, plus the town residents the chain supports. The declared budget becomes a result, kept as an option.
2. **Development (seen).** Han AD 2 commanderies and counties, the 11 census regions, Roman provinces (A2).
3. **Blind (reserved with Step 2).** Domesday households per block (England 1086), at a declared household size, with its literature range.
4. **Atlas.** The population layer gets a "predicted total" mode next to the declared budget. Badges follow the result.

## Order and dependencies

- Step 1 first: its blind result decides the reach rule and the rural ledger that Steps 2–3 inherit.
- Steps 2 and 3 share the Domesday blind pool, so they are frozen together and scored once.
- Everything else waits: the climate work resumes after this plan is queued (P6 East Asia winter monsoon, P8 maritime lag, W3, OM2), and the reserved climate set f stays closed.
