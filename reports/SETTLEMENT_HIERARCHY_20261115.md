# Settlement hierarchy: marked places lead their surroundings — 15 November 2026

Owner request: proposed towns should not dwarf the nearby marked (lore) place, and the model should handle this itself
rather than by swaps after the fact. A swap rule was tried and reverted at the owner's request before publication.
Plans: `calibration/settlement_hierarchy_20261115/plan.json` (amendments A1–A4, all after seeing results, disclosed) and
`calibration/settlement_hierarchy_map_20261115/plan.json`.

## Roman evidence (development data)

- **Towns near capitals:** of 95 towns within 75 km of a provincial capital, 6.3% are larger than it; the median size
  ratio is 0.11.
- **Subordinate size:** it does not follow the capital's size (coefficient −0.19).
- **No size shadow:** towns near capitals are not smaller than the size model predicts (mean held-out residual −0.12 to
  +0.03).
- **Conclusion:** the pattern is selection. The capital is the place that became the region's largest town.

## Model forms tried (province-held-out folds)

| Form | Share of subordinates larger | Median ratio | Capital factor | Verdict |
|---|---:|---:|---:|---|
| Observed | 6.3% | 0.11 | 3.22× | — |
| M1C alone (published before) | 21% | 0.37 | — | — |
| Difference model (declared) | 12.6% | 0.08 | — | fail |
| A1 conditional on centre size | 31% | 0.52 | — | fail |
| A2 selection + full capital term | 0% | 0.06 | — | fail (double count) |
| A3 selection alone | 1.3% | 0.17 | 1.99× | fail |
| **A4 partial selection + boost (fitted on training folds)** | 0.8% | 0.13 | 3.27× | narrow fail (share 0.5 points beyond the limit) |

Fitted on all the Roman data, A4 has each capital compete against half its cluster's draws, with a boost of 0.8 (×2.2).
That fit matches all three observed statistics.

## On the map (adopted; owner request, narrow miss recorded)

All 151 marked places are centres of the proposed towns within 75 km. Each takes the largest random draw among itself and
half of its cluster. The 19 provincial seats get the ×2.2 boost, which replaces the earlier capital term. Lore order and the
capital rule are kept. No post-hoc swap is used.

| Corrected climate, sliding density | Capital-term build | Hierarchy |
|---|---:|---:|
| Proposed towns larger than their marked place | 249 of 582 (43%) | 71 of 582 (12%) |
| Town residents | 11.26 M | 13.35 M |
| Largest town (imperial capital) | 208,135 | 325,665 |
| Fed at 34% marketed | 91.2% (31 short) | 84.8% (40 short) |
| Staffed towns (control rule) | 1,041 | 1,041 (same set; reach maps unchanged) |

Most of the remaining 12% sit next to imperial forts, monasteries and small fortified towns, which have small hinterlands.
They are the important place rather than the largest. The reviewers pass: the imperial capital is the largest town and lore
order holds. The browser checks (3 × 8) and the Windows checkout check (2,217 assets) pass.
