# Settlement map release 4: plan, foundations and requirements — 15 November 2026

Owner request: "build a plan for the next version of the settlement map and its foundations/requirements/auxiliaries;
start working on it." This plan builds on the working rules and the S1–S5 programme of
`SETTLEMENT_CONTROL_ROADMAP_20261110.md`, and replaces nothing in them. Every work package below is declared before scoring,
reviewed independently and replayed fresh, and changes the map only on a passed gate or an explicit owner decision.

## 1. Where release 3 stands

| Layer | Status | Evidence | Known weakness |
|---|---|---|---|
| Town count | Earth-fitted | Han + Rome, 1.6–2.3% total error | development pools only |
| Town positions | Earth-fitted (heartland prior, L 800 km) | 8/8 cross-pool quadrants; Vidarbha: no harm | **first blind test failed** (southern Mesopotamia, percentile 0.48) |
| Town sizes | Earth-fitted + capital term (owner) | Hanson areas with Greek walls; KS 0.063 | blind test failed (no city above 200 ha); size barely depends on people |
| Residents | Literature density | Hanson sliding 100–500/ha | density is a reading, not a fit |
| Grain supply | Earth-calibrated, Egypt included (development) | 0.337 sliding / 0.140 flat, 270 km | each fix (floodplain, Frier, Greek walls) followed a failure |
| Political reach | Blind-tested rule (v2.1) | CHGIS 1080, Pleiades 550 | staffing from supply-fed residents |
| Population pattern | Blind-tested pattern | Domesday rank 0.63 | level supplied, not predicted |
| Trade, administration | Rebuilt, untested | — | no Earth test of their own |
| Rural settlement | Not represented | — | towns only; villages absent |

## 2. Goals of release 4

1. **Roles, not just towns.** Distinguish provincial seats, ports, market towns, garrisons and villages (roadmap S2). The capital
   term showed that role explains size better than hinterland people. Ports and road hubs are the next candidates, and each role
   needs its own Earth evidence.
2. **Better positions, tested blind.** Find what the environment score misses (the Mesopotamia failure: channels and route
   nodes), add only Earth-tested site factors, and score once on a reserved blind pool.
3. **Earth tests for administration and trade.** The model chooses provincial seats and market links. Test the seat choice against
   Roman provincial capitals and Han commandery seats, and market access against town size, as declared development tests.
4. **Ensembles.** Publish recurring centres and size ranges over draws instead of one draw, so that a proposed town reads as a
   likelihood, not a prediction.
5. **Rural settlement layer.** Villages from the same people ledger (roadmap S2), checked against rural survey densities.

## 3. Foundations (needed before or alongside the goals)

| Foundation | Why | State |
|---|---|---|
| F1 Maize in the crop model | New World analogues; unlocks the reserved Valley of Mexico pool | owner to-do; needs Earth maize yield/phenology sources |
| F2 New World heartland cores | heartland prior is Old World only | with F1 |
| F3 Role data on Earth | ports (Hanson has no port flag), road hubs (Itiner-e), seats (Wikidata capitals, CHGIS levels) | capitals done; ports/hubs to source |
| F4 Blind pool register | remaining unseen pools: Valley of Mexico (reserved, headers only) | others spent; keep searching |
| F5 Earth people level | Frier level used for supply; the map still uses the committed pattern | decide one level for both |

## 4. Auxiliaries (tooling that makes each step safe)

| Auxiliary | Why | Deliverable |
|---|---|---|
| **A1 One-command chain runner** | a republication now needs about 15 manual commands with text substitutions; this session hit path, shadowing and key bugs | `scripts/settlement_chain.py` + a declared chain spec; verify mode rebuilds into staging and compares bytes with the published outputs |
| A2 Generic reviewer harness | each step re-adapts old reviewers by string substitution | reviewers parameterised by model spec (coefficients, flags, amendments) |
| A3 Release checklist | browser, checkout, hub, evidence page, dataset register | encoded as the chain runner's final stage |
| A4 Evidence page per release | the calibration page is hand-maintained | generated from the chain spec and results |

## 5. Work packages and order

| WP | Content | Gate / output | Depends on |
|---|---|---|---|
| **WP0** | A1 chain runner reproducing release 3 + capital term byte for byte | verify mode: identical sizes, supply and reach outputs | — |
| WP1 | Administration Earth test: model seat choice vs Roman provincial capitals (Wikidata) and Han commandery seats | declared development test; report | WP0 |
| **WP1b** | **Settlement hierarchy size model (owner request): centres first, subordinate towns sized relative to their centre from Roman evidence (6% of towns near a capital exceed it; median ratio 0.11). Replaces post-hoc swaps** | province-fold gate (see calibration/settlement_hierarchy_20261115) | WP0 |
| WP2 | Port and road-hub size terms (Hanson + Itiner-e + coast/river) with province-blocked folds | same rule as the capital term; owner decides adoption | F3 |
| WP3 | Position factors: route nodes, confluences, coast; development on Han/Rome | quadrant gate as release 3 | F3 |
| WP4 | Ensembles of positions and sizes (≥20 seeds) → recurring-centre and size-range layers | browser checks; no change to the default draw | WP0 |
| WP5 | Rural settlement layer from the people ledger | rural-survey density check | WP4 |
| WP6 | Maize and New World cores (F1, F2), then the Valley of Mexico blind test | blind score once | F1, F2 |
| WP7 | Release 4 publication through the chain runner | all checks | WP1–WP5 as passed |

## 6. Started now

WP0, the chain runner: `scripts/settlement_chain.py` with the spec `calibration/settlement_chain/release3_capital.json`. The
first milestone is a verify run that rebuilds the published sizes and supply into a staging folder and confirms they are
identical to the published outputs.

## 7. Progress log

- 15 Nov: WP0 verify **passed**: the chain runner rebuilt the published sizes, supply and staffing packets byte for byte in staging.
- 15 Nov: owner flagged proposed towns dwarfing nearby marked places. A post-hoc swap rule was tried and **reverted at the
  owner's request** (not published). Replaced by WP1b, declared in `calibration/settlement_hierarchy_20261115/plan.json`, with
  Roman evidence that subordinate towns sit well below their regional centre.
- 15 Nov: WP1b **published**: settlement hierarchy (marked places lead their 75 km clusters), proposed towns larger than their marked place 43% → 12%; see SETTLEMENT_HIERARCHY_20261115.md.
- 15 Nov: WP4 **published**: 40-draw ensemble (`scripts/settlement_ensemble.py`; replica reproduces the published draw exactly);
  new Settlements option "where proposed towns recur" (345 positions hold a town in at least half the draws, corrected) and
  marked-place resident ranges (download). Viewer badges updated (34%/14% shares, hierarchy, failed first blind test).
- 15 Nov: WP0 spec updated to the published hierarchy build (`calibration/settlement_chain/release3_hierarchy.json`); verify **passed**.
- WP2 (port/road-hub size terms): the release-2 calibration already tested coast, river and road terms (M2): held-out MAE 0.834 vs
  M1 0.831, i.e. no gain. No new Earth role data (a port list) is available, so WP2 is parked until such data exist.
- 15 Nov: WP5 (village layer) **blocked on evidence, not code**: the Roman rural Britain tables were re-downloaded (snapshot hashes
  match), but they are excavated sites whose density follows development-led archaeology, not village density; Domesday, the only
  village-scale census, is spent. A village layer would be untestable. Parked until an unspent rural census-like pool exists.
  Work switched to the climate model (owner instruction).
