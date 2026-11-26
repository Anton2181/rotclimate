# W18c development snapshot: 13 completed records

At this fixed snapshot, w1_005 is the provisional leader under the existing
penalized development objective. S97 is 0.9842206: temperature MAE improves
1.936%, rain loss improves 1.220%, and their combined normalized mean improves
1.578%. Its worst regime S is 1.0179688, inside the existing 1.02 point limit.
This is **not a finalist, full development pass or adoption**. The full
development bootstrap, fine28 and single sealed-AA stages remain outstanding.

The improvement is uneven: 52 of 97 regions improve in combined contribution
and 45 worsen. Nigeria box s2_5n_7e and Somalia s_2n_43e contribute -0.5214 and
-0.4216 percentage points to the global score change, together about 59.8%
of its net improvement. This is an exact score decomposition, not causal
attribution or evidence of general planetary skill.

| Exposed development region | T MAE, r58 → candidate (C) | Rain loss, r58 → candidate | Contribution to S97 change, percentage points |
|---|---:|---:|---:|
| Somalia | 1.298 → 1.645 | 3.663 → 3.188 | -0.4216 |
| Western Europe | 1.252 → 1.409 | 0.322 → 0.373 | +0.1071 |
| North India | 3.206 → 3.319 | 0.490 → 0.474 | +0.0178 |
| Namibia/Kalahari | 1.511 → 1.551 | 1.080 → 1.074 | +0.0067 |
| NW Australia box u_24s_124e | 0.751 → 0.747 | 1.043 → 1.033 | -0.0117 |

Negative contributions improve the score. They use the **global reference
mean losses**, not an average of individual region ratios:
`0.5/97 * ((candidate_T-reference_T)/mean_reference_T
+ (candidate_P-reference_P)/mean_reference_P)`.
Summing all 97 contributions exactly recovers S97−1. Rain loss is the existing
dimensionless loss, not a rainfall percentage or annual rainfall amount.

Tropical-dry and tropical-wet regime scores improve to 0.94518 and 0.95204.
Several other groups are close to or above parity: temperate S=1.00374,
highland 1.00469 and Mediterranean 1.01797. Their component losses can trade
off: arid temperature MAE worsens 3.51% while rain loss improves 3.79%; temperate
rain loss worsens 3.90% while temperature MAE improves 3.15%. Those are group
averages and do not establish local protections that the policy does not have.

Western Europe is already an exposed development region and its current
coarse result worsens in both components. That is a concrete reason the
declared fine-resolution check remains necessary; it does not predict its
unopened result. Somalia's rain loss improves but its temperature MAE rises.
The dry-interior and North Indian issues are not resolved by the aggregate
headline gain.

The existing search, objective, candidate budget, proposal sequence and all
gates remain unchanged. No candidate is rejected or rescued from this readout,
and no confidence interval, fine target or sealed-AA target is evaluated here.
Do not add a retrospective regional veto or change selection based on this
report. Finish the declared campaign, freeze the leader by the original
objective, and apply the existing validation sequence. The prepared padding
diagnostic and unapplied budget correction remain separate follow-up work.

The snapshot checks all candidate reference scores for a single common epoch,
verifies the score decomposition independently, and preserves every completed
record. The inspected figure, all 97 regional contributions and seven regime
summaries are under `output/ppe_20261127/W18c_progress_0013/`. Regions carry
equal weight within this development policy; these are not global-area or
independent validation estimates. No new climate integrations or adoption.
