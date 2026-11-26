# Saved-field marine-access audit

The audit gives little support for false marine access as the explanation of
Somalia's excess rain. Keep the current marine gate unchanged. The baseline's
288 scored cell-months all reach real sea in both backward-flow proxies.
This closes one bounded diagnostic, not the outstanding climate problem.

The committed plan fixed three existing cases, two arc-length steps (14 and
7 km) and a 1,700.925 km horizon before analysis. It required **zero new
climate integrations**. The exact current e91 geometry was reconstructed and
checked against the actual pure geometry block in `model.py`. All three
domains contain sea, and all scored nearest-sea indices denote real sea.
The generic all-land EDT exterior-background risk is covered by a synthetic
test; it is not the cause in these cases.

## What the proxies show

| Case | Scored cell-months | Sea reached, 14 / 7 km | Domain exit, 14 / 7 km | Land through horizon, 14 / 7 km |
|---|---:|---:|---:|---:|
| Somalia r58 | 288 | 288 / 288 | 0 / 0 | 0 / 0 |
| Somalia minimum turning | 288 | 266 / 265 | 0 / 0 | 22 / 23 |
| Sahara r58 | 300 | 100 / 101 | 186 / 185 | 14 / 14 |

There are no calm paths. Step-size status agreement is 100%, 99.65% and
99.67%, respectively. In turning Somalia, every positive monthly local gate
has a sea-reaching proxy. The 22/23 land-through-horizon rows have zero gate
when evaluated on monthly mean wind, but carry 0.528 mm/year of positive
captured marine exchange averaged over all scored cells. This is consistent
with submonthly variability; the two quantities sample different times.

Sahara has 85/86 positive-gate rows whose paths leave the saved domain. Those
paths are **unknown**, not evidence of false marine access. Fourteen
positive-gate rows remain over land through the finite horizon. Nevertheless,
captured marine exchange is exactly zero in this case. A positive directional
gate alone does not establish active moisture supply: it excludes other
coefficient factors and the actual signed humidity difference.

The mean absolute difference between the gate of monthly mean wind and the
monthly mean instantaneous gate is 0.01510, 0.00438 and 0.00466, with maxima
0.19562, 0.05691 and 0.09414. Consequently, a monthly wind map is not an exact
reconstruction of instantaneous marine forcing. These differences do not
constitute model error: production applies its gate at individual time steps.

## Captured exchange, with seasonal cancellation retained

| Case | Positive exchange | Negative exchange | Net exchange |
|---|---:|---:|---:|
| Somalia r58 | +230.832 | -243.515 | -12.683 |
| Somalia minimum turning | +451.036 | -26.549 | +424.487 |
| Sahara r58 | 0 | 0 | 0 |

Units are mm/year averaged over scored land cells. Positive and negative
instantaneous terms were separated **before** monthly averaging. The baseline
has substantial opposing seasonal exchange despite its small annual net.
These terms are not removable rainfall or observational causal shares.

## Verification and limits

Eight synthetic tests cover flow direction, alongshore flow, calm paths,
domain exits, a bent flow, invalid inputs and all-land geometry. An independent
scalar implementation with manual bilinear interpolation checks all **1,752
paths**, including status, length and reached sea index. Another **4,380
independent scalar checks** cover sea distance against brute-force real sea
coordinates, both gate evaluations and signed monthly exchange. All 876
cell-month records are present exactly once, source hashes remain unchanged,
and the scientific figure was inspected.

The paths follow frozen monthly **surface** flow, not actual time-dependent
air parcels. Surface and transport winds matched at all traced scored cells
in these three cases; this does not prove full-domain or general equality.
Finite-horizon land paths are not assertions of infinite continentality.
This audit establishes neither conservative boundary fluxes nor a new climate
parameter setting. Adopted r58, the atlas, W18c and its gates are unchanged.

## Next direction

Prioritize the existing positive-only convergence-import term and its relation
to advection and column drying. Somali baseline diagnostics already show
roughly +1,592 mm/year of convergence import alongside +1,585 mm/year of
advection. First audit the algebra, signs and spatial/seasonal overlap in
saved traces; do not infer double counting from these magnitudes alone.
Any new integrations need a separate bounded declaration. Physical changes,
including the already identified exported-budget correction, wait until
W18c closes so its source inventory remains frozen. A future physical
candidate still requires the full development, fine and sealed validation
sequence. Do not use the current negative proxy result to justify tuning
marine geometry against rainfall.

Artifacts: `output/marine_gate_audit_20261126/` contains the full table,
provenance, independent review, qualification and `marine_access.png`.
