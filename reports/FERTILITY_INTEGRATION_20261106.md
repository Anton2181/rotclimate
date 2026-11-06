# Fertility integration: published, bare three-field at the AD 200 N input is the default

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

**No transfer is needed at the Han North China Plain.** It is water-limited, so bare three-field farming keeps its AD 2 fit (F 1.05) and the calibrated transfer m* is 0. The NCP therefore cannot identify the nutrient transfer that matters in wet climates, and fert_transfer and fert_bare are currently identical.

**Across the 11 census regions** (development: already seen in task A2), mean |log10(historical / capacity)| is:

| case | mean \|log10 ratio\| |
|---|---:|
| previous chain | 0.538 |
| bare three-field | **0.459** |
| clover third | 0.685 |

*Corrected 6 November 2026:* this table and the region rows below first quoted the run before the stand-scaled-residue fix (bare 0.407, clover 0.682; Gaul 0.55–1.24, Sichuan 0.59, Italy 1.08–2.03). The values here are those of the published `earth_census.json` (commit 9decd991; error at the geometric midpoint of each historical range). The ranking is unchanged.

**Where the gain comes from:** wet regions where nitrogen, not water, limits yield.

| region | historical / capacity, previous | historical / capacity, bare |
|---|---|---|
| Gaul | 0.10–0.22 | 0.31–0.69 |
| Sichuan | 0.09 | 0.29 |

- **Italy** now brackets capacity (0.88–1.66), with the upper end above it. That is consistent with Rome's grain imports.
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

## Decision and final run (user: fix the artifact, then bare three-field as default)

**Artifact fix.**
- **The change:** root and stubble residues now scale with the stand below 0.5 t grain (Bolinder et al. 2007). This is `harvest/soil_fertility.STAND_T`, behind an option that is off by default for rounds 1–2.
- **Recheck on spent data** with the frozen round-2 parameters (`scripts/recheck_stand_residues.py`):
  - development loss 0.1711 → 0.1705;
  - Broadbalk 1926–67 scores unchanged (still qualifies).

**Census (Earth, with the fix).**
- **North China Plain:** no transfer needed (F 1.05, ratio 0.96).
- **Italy:** 0.88–1.66.
- **Gaul:** 0.31–0.69.

**Map, final:**

| atlas | factor median (10th pct), bare | cereal vs previous, bare | staffed sources, bare | access months, bare | staffed sources, clover third | cereal vs previous, clover third |
|---|---:|---:|---:|---:|---:|---:|
| free_fit raw | 0.31 (0.05) | 0.61× | 201 (joint365 1,207) | 1.95 (7.31) | 614 | 1.27× |
| earth_fit raw | 0.35 (0.18) | 0.54× | 278 (1,044) | 2.46 (7.24) | 975 | 1.53× |
| earth_fit corrected | 0.35 (0.19) | 0.53× | 273 (1,064) | 2.40 (7.36) | 1,010 | 1.51× |
| whittaker_fit raw | 0.60 (0.08) | 0.84× | 333 (1,053) | 3.06 (7.07) | 717 | 1.52× |

**Published.**
- `fert_bare` (default) and `fert_legume` are in the same Settlements / Supply-supported reach selector as the earlier cases, in all three atlases.
- The hosted artifacts were republished, including the features added since the last hosted version: coverage, administration, presence, pasture and farm work.

**Hosting fixes in `scripts/package_atlas_artifact.py`:**
- feature packets keep raw bytes (their scripts hash what they fetch);
- references in feature manifests follow the `.wasm` rename;
- gzip packets are sent as `application/wasm`.

The hosted Earth-fit atlas leaves out the optional tiered-colour twins (89 files), to stay under the host's 511-file limit; that toggle is absent there. All three packages pass `scripts/check_atlas_smoke.js` with no failed requests.
