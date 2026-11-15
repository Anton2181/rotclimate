# Roman provincial capitals are about 3× larger than the size model predicts — 15 November 2026

Plan: `calibration/capital_effect_20261115/plan.json` (declared before output; A1 alias table for province names, also
before output). Development check on exposed Roman data, not blind. Capitals come from Wikidata (province P36 with
coordinates, alive at AD 150). Each is matched to the nearest AD 150 town of the size cohort within 5 km; Rome is added as
imperial capital. Wikidata entries are not hand-corrected, so some are alternative or later capitals (Camulodunum and
Eboracum for Britain, Reims and Trier for Belgica, Petra for Arabia).

| | Capitals | Size factor vs model (95% interval) | Mean area percentile | In top 14% | In top 5% |
|---|---:|---|---:|---:|---:|
| All | 28 | **3.4×** (2.3–5.2) | 0.82 | 54% | 36% |
| Without Rome | 27 | 3.1× (2.1–4.4) | 0.81 | 52% | 33% |

**What it means for the map.** Capitals are systematically much larger than their hinterlands imply, so giving the lore
capital and major cities the largest draws is supported. But the map's lore rule only reorders the existing draws. It
cannot create a city above what the size model's scatter produces, and that is what failed in southern Mesopotamia,
where the model had no city above 200 ha. A capital term in the size model is the direct fix, and it is the next
declared step.

Checks: a rerun reproduces the results file byte for byte; the matched towns are listed in `results.json`.

## Capital term in the size model: not adopted by the declared rule (narrowly)

Plan `calibration/size_capital_term_20261115/plan.json` (declared before output). M1C = M1 + c × capital, with
province-blocked folds, so each province's capitals are predicted from other provinces' capitals.

| | Held-out MAE (all 664) | Held-out MAE (28 capitals) | Mean capital residual | Gate (KS, area ratio) |
|---|---:|---:|---:|---|
| M1 (published) | 0.822 | 1.273 | +1.17 (about 3× too small) | 0.063, 0.95 pass |
| M1C | 0.808 | 0.846 | +0.03 | 0.070, 0.98 pass |

The capital coefficient is positive in all four folds (1.03–1.42, a factor of 2.8–4.1×; full fit 1.26 ≈ 3.5×). The declared
adoption rule needed the all-town MAE to fall by 2%; it fell by 1.7%, so **M1C is not adopted**. The rule judged a
28-town effect on 664 towns. Adopting it on the capital-specific evidence would be a post-hoc change of rule, which is
the owner's decision and would be declared as such.
