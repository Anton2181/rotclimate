# Earth-calibrated unmarked settlement model — 7 November 2026

Plan, frozen before results: `calibration/settlement_model_20261107/plan.json` (amendments 1–2 made before any blind
outcome). Harness: `scripts/settlement_model_earth.py` (prepare / grid / grid2 / fit3 / blind). Figure:
`scripts/plot_settlement_model.py` → `reports/figures/settlement_model_sui610.png`.

## Question

The atlas places towns that the map does not mark: county seats, market and administrative centres. It uses
`polity.settle.place_towns`. The rule fills the land greedily, taking the best site first. Each town blocks a
catchment of radius 1.6 R, where R comes from the E1 count rule (one seat per about 40,000 people, β 0.7), and
dry land needs water nearby. The site score is

`density^a × (1 + w_r·exp(−river_km/3)) × (1 + w_c·[coast ≤ 6 km]) × (1 + w_d·[road ≤ 4 km]) / (1 + k_f·slope)`

The current weights are assumptions: a 1, w_r 1, w_c 0.5, w_d 0.5, k_f 20. The question is whether Earth data can
fit them, and how well the rule predicts where real towns sit, how many there are and how they are spaced.

## Data

| Pool | Use | Towns |
|---|---|---|
| Rome AD 150: Hanson towns inside Cliopatria's Roman Empire, Itiner-e roads | development (seen) | 1,085 |
| Han AD 2: county seats inside the Han commanderies | development (seen) | 1,264 |
| Hellenistic: Pleiades settlements in the B1 window | development (the spent control-blind pool) | 2,053 |
| **S1** Sui AD 610: CHGIS V6 county seats inside Cliopatria "Sui Dynasty" | **blind**, scored once | 1,033 inside |
| **S2** Cities of 1300 (Bosker, Buringh & van Zanden 2013) north of 45° N, west of 30° E, beyond the Roman frontier | **blind**, scored once | large cities only |

S1 shares its window, and many seat places, with Han AD 2; this dependence was declared in the plan. S2 is a new
region and a new era. Both pools are now recorded as spent in `calibration/earth_components_20261105/dataset_usage.json`.

How each metric is scored:

* **M1:** rank correlation of town counts per 100 km block.
* **M2:** F1 at 25 km, with the model placing exactly as many towns as the pool has.
* **M3:** KS distance between the nearest-neighbour spacing distributions.
* **M4:** count error |log10(model / real)|.
* **M5:** site-rank AUC (S2).

## Development

1. **Weight grid** (243 settings; `grid.json`). The current weights score mean F1 0.453 and M1 0.274. The best
   setting (a 1.5, w_r 3, w_c 0, w_d 1.5, k_f 60) scores F1 0.463 and M1 0.288. The gain is small.

   Diagnosis: the placed towns form a regular lattice, with a median nearest neighbour of 45 km (10–90 %: 37–57).
   Real towns cluster, with a median of 20 km (9–64). M3 is 0.68–0.93. The count itself is right: Han 1,303 placed
   against 1,264 real.
2. **Count-limited spacing** (amendment 1; `grid2.json`). This keeps the E1 count and shrinks the blocking radius.
   It repairs the spacing distribution (M3 0.80 → 0.38–0.42 at s 0.4–0.6), but F1 falls to 0.23–0.31. The crowded
   towns follow the density field, and that field correlates only weakly with the real towns per block (Rome 0.28,
   Han 0.15). The candidate stays at spacing 1.6.
3. **Fitted suitability** (amendment 2; `fit3.json`). A case-control logistic regression on fields the map can
   supply:
   * food density, river at 3 and 15 km, coast at 6 and 30 km;
   * elevation, slope, relative elevation, aridity, road at 4 km.

   With leave-one-pool-out, mean F1 is 0.428 (Rome 0.38, Han 0.42, Hellenistic 0.48). That is below the stage-1
   candidate's in-sample 0.463, so this fit was not sent to the blind test. The strongest terms are road within
   4 km (+0.67), food density (+0.46), lower elevation (−0.49) and coast within 30 km (+0.40).

## Blind result (`blind.json`)

| | current weights | stage-1 candidate |
|---|---|---|
| S1 F1 at 25 km | 0.477 | 0.484 |
| S1 M1 block rank correlation | 0.286 | 0.318 |
| S1 M3 spacing KS | 0.758 | 0.758 |
| S1 M4 count error | 0.045 (+11 %) | 0.047 |
| S2 site AUC | **0.629** | 0.626 |

The candidate passes G1, G3 and G4 but fails G2 by 0.003, so **it is not adopted**. The atlas keeps its current
weights, and `polity/settle.py` is unchanged; the configurable copy lives in `polity/settle_experiments.py`.

## What this means for the atlas

* **Count: Earth-tested.** The number of unmarked seats is within about 11 % on an unseen state (Sui, 1,146 placed
  against 1,033 real) and within 3 % on Han.
* **Placement: partly tested.** About half the towns fall within a day's walk (25 km) of a real seat, and the land
  rank AUC is 0.63 for large medieval cities. That is better than chance, but weak.
* **Pattern: not reproduced.** The model spreads towns almost evenly, while real networks cluster: on the North
  China Plain, in the Sichuan basin and around Guangzhou in AD 610 (see the figure). The atlas's evidence text for
  Settlements already says "count Earth-fitted, sites assumed".

## Round 2: towns on the old-heartlands density (`plan_round2.json`, frozen before results)

Earlier work (`reports/POPULATION_20261023.md`) had already found the missing history: capacity multiplied by
exp(−D / 800 km), where D is the travel cost to the nearest old core (the four river cradles, plus Rome). That
model is Earth-tested: Han AD 2 census rank 0.29 → 0.84, Roman towns 0.19 → 0.62 (blind). The map already computes
this density (`settlement_cored`), but its unmarked towns still use the bare base.

Candidate C1 places the towns on the cored density, with the same total people inside the polity and nothing
tuned. Here, as on the fantasy map, 75 % of the Han AD 2 seats lie north of 33° N, against 33 % of the bare density.

| Development (`dev2.json`) | F1 | block rank M1 | spacing KS M3 |
|---|---|---|---|
| current, mean of 3 pools | 0.453 | 0.274 | 0.798 |
| **C1 (L 800 km)** | **0.533** | **0.512** | **0.727** |
| Han AD 2 alone | 0.424 → 0.578 | 0.107 → 0.614 | 0.782 → 0.720 |

| Blind (`blind2.json`, scored once) | current | C1 | gate |
|---|---|---|---|
| T1 Tang AD 742 seats (1,334 inside Tang): F1 | 0.538 | 0.551 | G1 pass |
| T1 block rank M1 | 0.400 | 0.504 | G2 pass |
| T1 spacing KS M3 | 0.795 | 0.739 | G3 pass |
| T1 count error M4 (towns placed) | 0.070 (1,135) | 0.099 (1,062) | **G4 fail** (> 0.08) |
| T2 cities of 1300 inside the Roman frontier: site AUC | 0.771 | 0.754 | **G5 fail** |

**Not adopted.** The cored density gives a better Chinese pattern on unseen data. But it places too few towns
(−20 %), and it ranks medieval European city sites worse; the Rome-centred core does not match the urban map of
1300 (Flanders, Iberia, southern France). Under the frozen gates, the atlas keeps the bare density.

Two things a round 3 could test, both of which need a new blind pool declared first:

* **Count.** Keep the E1 count from the bare density, and use the cored density only to rank and space the sites.
  This would fix G4.
* **Site ranking.** Score the cored density against an AD ≈ 200 target, not a medieval one. No unspent AD ≈ 200
  site pool exists yet.

## Why, and what could fix it

The clustering is mostly population history, not site quality. In AD 610 the Chinese population was still
concentrated in the north and in Sichuan. The model's density is a static carrying-capacity field, and it rates the
rice south nearly as high as the north.

A static site score cannot recover that history, whatever its weights. All three development approaches hit the same
wall: they cannot beat block correlations of about 0.3.

The next useful step is to drive the placement from a time-dependent population instead:

1. Make the predicted population ledger the density input (task 83: rural L1, pastoral, foraging and towns).
2. Make that population depend on distance from the farming hearth and on the polity's age, using the language and
   farming-spread model (F15b).

Then re-test the clustering, with M1 and M3, on a fresh blind pool. CHGIS at other dates, which share the window,
must be declared before use.
