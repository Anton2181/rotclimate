# Fixed-planet r39 world transfer

The qualified r39 Earth physics is held fixed while fitting the fantasy world's
latitude, orientation, elevation tiers and unknown surroundings. The existing
retrograde rotation, 33.50° tilt, Earth-sized planet, orbit and stellar input
are unchanged. Target rules and publication protections are unchanged.

The first 97-case ds32 search did not yield a publishable world: its native
candidate 32 converged but lost strict agreement and Mediterranean skill.
The complete failed review remains in `output/r39_world_publication/`.

A declared supplemental screen uses that measured resolution discrepancy to
rank archived candidates, computes seven actual ds16 mean climates and chooses
at most two actual ds8 checks. Corrections rank proposals only; integrated
climate fields and the final metrics are never corrected. Each numerically
verified surroundings layout is saved separately with an input identity.

All seven intermediate worlds converged. The selected native order is 49,65.
Candidate 49's complete native result is:

| Measure | Published r38 | Native r39 candidate 49 |
|---|---:|---:|
| Zone-fit objective | 0.182806 | 0.187963 |
| Exact target-zone agreement | 34.99% | 37.04% |
| Mediterranean classified dry | 6.41% | 6.08% |
| Mediterranean classified Cs | 74.55% | 80.46% |
| Tree-zone recall | 6.79% | 4.56% |

**Candidate 49 is rejected.** The tree recall must remain at least 4.79% under
the previously declared allowance. All its numerical checks passed, but a
better aggregate cannot cancel this regional failure. The canonical atlas
therefore stays on r38. Candidate 65 also converged but is rejected:
zonefit 0.187228, strict agreement 36.00%, tree recall 6.26%, Mediterranean
dry share 7.55% versus the unchanged 6.91% maximum. No additional-layout
result was inspected for either rejected endpoint. The full final review is
`output/r39_world_transfer/review.json`.

The tree-zone climate diagnosis is descriptive: mean annual rainfall falls
from 543.7 to 504.4 mm, mean coldest-month temperature rises 6.24→6.42°C,
and the humidity factor falls 0.369→0.334. Insufficient moisture is the
larger weakness; this is not a causal sensitivity measurement. Existing
classification rules remain fixed.

`output/r39_world_transfer/native_comparison.png` compares the actual native
climates. `world_preview.png` is the earlier ds16 preview. Input and picture
hashes accompany both. No new model run is required to make these figures.

A conditional three-case geometry path was declared in
`calibration/map_world_r39_balance/plan.json`, before candidate 65's native
result and before any interpolated climate integrations. Both endpoints are
now rejected with successful numerics, so this path is running. It keeps all original protections and
allows only one further actual native candidate. Eleven focused tests cover
locked physical parameters, interpolation/ranking and complete atlas assets.

All three actual ds16 balance screens converged:

| Fraction from 49 toward 65 | Zone objective | Exact agreement | Tree recall | Mediterranean dry |
|---|---:|---:|---:|---:|
| 1/3 | 0.186653 | 36.90% | 5.56% | 5.05% |
| 1/2 | 0.186477 | 36.87% | 5.56% | 5.05% |
| 2/3 | 0.186510 | 36.67% | 5.98% | 5.45% |

The declared ranking, using measured endpoint resolution discrepancies only
to predict test order, chooses the 2/3 case (`balance_003`). Its one actual
native test is running; these coarse results do not establish a native pass.
The five existing world-publication guard tests also pass.

Publication requires a native pass followed by the layouts17/23 comparison,
a full staged export, food and population accounting, complete asset checks,
and Chromium checks through the actual `.bat` server. All normal atlases remain
available meanwhile, with current directed markets and three Trade views.
