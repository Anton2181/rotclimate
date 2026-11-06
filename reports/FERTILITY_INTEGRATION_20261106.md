# Fertility integration: computed, not yet published (decision needed on the default)

**AD 200 nitrogen input:** 27.5 kg N/ha/yr, the middle of the 20–35 band, as you chose.

## What was built

- **`harvest/fertility_regimes.py`** is a vectorised, per-cell equilibrium version of the qualified round-2 model.
  - **Validation:** it is checked against the full model on Rothamsted climatology (`scripts/validate_fertility_emulator.py`). It is within 4 % for continuous cereal, clover and manure, and 19 % low for bare fallow.
  - **Simplifications:**
    - monthly water bucket, with kc 1.3 under crop and 0.8 bare, which reproduces the daily ledger's drainage;
    - Rothamsted soil everywhere;
    - Hargreaves PET × 0.625;
    - season length of 9 bins for wheat and 5 for barley, ending at the cell's harvest boundary.
- **Factor per wheat/barley cell:** F = Y_land(regime) / (0.68 × A0). This is the regime's absolute equilibrium grain per field hectare against the previous chain's A0 × sown share.
  - A first pass divided by the model's own unmanured reference instead. That ratio explodes where the reference approaches zero (Earth-fit came out at 1.96× cereal), so it was replaced before anything was published.
- **New cases in the same Settlements / Supply-supported reach chain:** fert_transfer, fert_bare and fert_legume (`scripts/extend_settlement_fertility.py`). All nine earlier cases are kept exactly, and rural food claims stay fixed.

## Earth census anchor (`output/fertility_integration_20261106/earth_census.json`)

**No transfer is needed at the Han North China Plain.** It is water-limited, so bare three-field farming keeps its AD 2 fit (F 1.01) and the calibrated transfer m* is 0. The NCP therefore cannot identify the nutrient transfer that matters in wet climates, and fert_transfer and fert_bare are currently identical.

**Across the 11 census regions** (development: already seen in task A2), mean |log10(historical / capacity)| is:

| case | mean \|log10 ratio\| |
|---|---:|
| previous chain | 0.538 |
| bare three-field | **0.407** |
| clover third | 0.682 |

**Where the gain comes from:** wet regions where nitrogen, not water, limits yield.

| region | historical / capacity, previous | historical / capacity, bare |
|---|---|---|
| Gaul | 0.10–0.22 | 0.55–1.24 |
| Sichuan | 0.09 | 0.59 |

- **Italy** now sits above capacity (1.08–2.03). That is consistent with Rome's grain imports.
- **Dry regions** (Wei valley, Syria, Mesopotamia) get F above 1, because water limits there before nitrogen does.

## The map (`map_factors.json`, `settlement_fertility_20261106/*/review.json`)

The map's wheat/barley cells are well watered (A0 at its 1 t/ha cap), so nitrogen binds:

| atlas | median F, bare | cereal vs previous | staffed sources, bare | staffed sources, clover | cereal, clover |
|---|---:|---:|---:|---:|---:|
| free_fit raw | 0.15 | 0.54× | 201 (was 1,191) | 613 | 1.22× |
| earth_fit raw | 0.22 | 0.44× | 276 (was 1,023) | 975 | 1.52× |
| earth_fit corrected | 0.20 | 0.42× | 272 | 1,010 | 1.50× |
| whittaker_fit raw | 0.59 | 0.77× | 332 | 717 | 1.48× |

The bare 10th percentile is 0: there the model gives **zero grain** where uptake falls below the 26 kg N that the residue relation sends to stubble and roots first. That is an artifact at very low nitrogen. Real crops still set some grain, so the bare collapse is overstated.

## Open decision

Which regime should be the default on the map? The census favours low-transfer (bare) farming in the Roman world, but on the wet map it removes about three-quarters of staffed sources. The current default is unchanged (joint365), and the fertility cases are computed but not published.
