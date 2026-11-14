# Would fixing Egypt's harvest be enough? No — 14 November 2026

Plan: `calibration/egypt_sufficiency_20261114/plan.json`, committed (45f3d8de) before any output.

**Question.** The whole-empire Roman grain-supply calibration fails and passes only with Egypt removed
(SETTLEMENT_SUPPLY_CALIBRATION_20261113.md). The harvest model gives Egypt about half its historical output.
If Egyptian harvests were raised to the historical level, would the unchanged declared rules pass?

**Answer: no.** Every variant fails. Egyptian yield ×1.94 or ×2.16 (historical/model capacity), with or without
also scaling Egypt's farmers, lets eastern cities reach 95% fed, but only at a marketed share of 0.61–0.67 against
0.38 in the west. That is a factor 1.6–1.75, outside the declared ×1.25, and transfer west→east is 87–89% (<90%).
So harvest is necessary but not sufficient: a second blocker remains in getting grain to eastern cities.

![figure](figures/egypt_sufficiency_20261114.png)

| Variant (270 km) | e95 west | e95 east | West→east transfer | Passes |
|---|---:|---:|---:|---|
| Control (= archived whole empire, exact) | 0.38 | never | 0.53 at 540 km | no |
| Yield ×1.94 | 0.38 | 0.64 | 0.88 (at 200 km) | no |
| Yield ×2.16 | 0.38 | 0.61 | 0.89 | no |
| Yield and farmers ×1.94 | 0.38 | 0.67 | 0.87 | no |
| Yield and farmers ×2.16 | 0.38 | 0.65 | 0.88 | no |
| Egypt removed (archived) | 0.37 | 0.42 | 0.92 | yes |

## Where the grain gets stuck (post-hoc, exploratory)

`scripts/egypt_sufficiency_diagnostic.py` (not declared) on yield and farmers ×2.16 at 270 km and share 0.5:
the cities inside the Egypt mask hold 1.42 M person-years of excess after their own hinterlands, against
a 1.05 M deficit among the others; 1.29 M is shipped between them, yet only 0.97 M of 1.36 M residents are fed.
Alexandria is fully fed. Arsinoe in the Fayum (126,000 residents) gets nothing: it owns no surplus land and
receives no shipment. Memphis is 19% fed and several Middle Egypt towns 15–39%. The surplus sits in the delta
while the hungry cities are up the valley and in the Fayum. Two things the model lacks are candidates: the Fayum
basin as cropland (the Bahr Yusuf irrigated it), and Nile boat freight up the valley, which the network may price
as road. Neither is tested here.

Caveat: the declared Egypt mask (lon ≥ 29° E, lat ≤ 32° N, inherited from the without-Egypt variant) also
contains the southern Levant (for example Jerusalem), so "Egyptian" flows include some Levantine cities.

## Checks

The control reproduces the archived whole-empire surface and decision exactly. The reviewer
(`scripts/review_egypt_sufficiency.py`) rebuilds every e95, the west/east ratio, the haul-limit choice and the
transfer from the stored surfaces with separate code (85 checks) and confirms Egyptian surplus rises with k. A fresh
run is byte-identical. Nothing on the fantasy map changes; the adopted share 0.3923 still rests on the
without-Egypt calibration.

## Next

Fix the intra-Egypt geometry before the floodplain crop rule is worth fitting: check that the Fayum and Nile
valley cells are crop land with water in the Earth harvest grid, and that the freight network carries Nile boats
in the trade months. Then rerun this sensitivity unchanged.
