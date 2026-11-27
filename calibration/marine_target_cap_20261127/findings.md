# Marine-equilibrium cap fails the fixed local screen

All six integrations and the independent review passed their original
numerical/equation checks. All three legacy controls reproduced the archived
scored physical fields, traces and complete budgets in dtype, shape and bytes.
There were no failures, retries, solver changes or fitted coefficients.
The candidate nevertheless **fails the prospectively declared local screen**
and remains unapplied to main. Retain the existing r58 law and atlas r51.

| Region | Annual rain mm/year, legacy → cap | T MAE C, legacy → cap | Rain loss, legacy → cap |
|---|---|---|---|
| Somalia | 3556.41 → 3556.91 | 1.29815 → 1.29811 | 3.66344 → 3.66394 |
| Sahara | 215.04 → 210.34 | 2.36390 → 2.35408 | 1.68577 → 1.65813 |
| North India | 547.42 → 538.96 | 3.20627 → 3.19591 | 0.48996 → 0.49716 |

Somalia's rain loss worsens 0.0137%, rather than improving the required 1%.
North India's rain loss worsens 1.4691%, exceeding the fixed 1% protection.
Sahara's loss improves 1.6395%, but its rain still exceeds the fixed observed
2.07 mm/year by roughly two orders of magnitude. This is insufficient to
justify a broad search, another cap strength or a new deployed climate.

## Where the target actually binds

Candidate rate and target traces were captured from the actual helper calls,
not reconstructed from monthly means. The reviewer verifies the capped
target is exactly the minimum of land-relative and upstream-equilibrium
targets and that rate × (target − actual water) reproduces the signed recorded
marine term within explicit float32 export rounding bounds.

| Scored region | Samples with bound target | Samples with positive marine rate | Bound among positive-rate samples |
|---|---:|---:|---:|
| Somalia | 0.0% | 90.0% | 0.0% |
| Sahara | 100.0% | 0.0% | Not applicable |
| North India | 24.19% | 29.94% | 31.94% |

The hypothesized excessive land-relative target does **not** occur at the
scored Somali cells under this r58 configuration. At the Saharan scored
cells the lower target is inactive because the marine rate is zero. Their
small coupled state changes therefore must not be described as a direct
local cap effect. Saved scored traces do not locate all changed cells outside
the footprint or isolate the domain-wide feedback pathways.

North India supplies a genuine active test of the cap. Its mean signed
marine exchange falls by 32.49 mm/year, but rain falls only 8.45. Advection
changes +16.05 and storm exchange +10.27 mm/year; the other source changes
and small equation residual account for the remainder. This is a coupled
local equation, not a tagged causal share of rain or a conservative marine
boundary flux. Less humidity supply worsens this already dry region's rain
loss despite its small temperature improvement.

Maximum scaled local residuals of the capped runs are 0.001696 (Somalia),
0.005990 (Sahara) and 0.009974 (North India), all within the unchanged 0.01
criterion. Each entire original numerical certificate also passes. The
failed screen is a response/accuracy result, not a numerical failure.

## Decision and next work

Do not apply the private cap patch, fit intermediate strengths, change the
protection or reopen W18c. The tested target ceiling does not solve Somalia's
wet bias. The actual Somali source budget and prior turning ablation instead
support investigating circulation and coupled transport, keeping Sahara and
monsoon controls. Correcting a marine reservoir target alone is not supported
as the next Somali fix.

The helper's all-land test separately exposes a generic correctness issue in
the legacy model: an all-land EDT has no valid sea index, while the original
warm-sea branch assumes one. This did not cause the errors in these three
real mixed land/sea domains. A narrow no-sea guard can be addressed separately
with genuine coupled toy regression checks, without adopting this rejected
physical cap or claiming to fix the Earth rainfall biases.

This pilot uses exposed Earth cases with the existing observed boundary PW
and remote rain-derived descent. It establishes neither standalone-world
skill nor global climate qualification. Fine outcomes and unopened sealed AA
were not used; W18c remains permanently closed, adopted r58 unchanged.

`output/marine_target_cap_20261127/review.json` retains all six metrics,
component accounts, three comparisons, target/rate fractions, the failed
declared screen and hashes of 18 raw files. `cap_response.png` was visually
inspected: all three regions, legacy/cap/observed monthly rain and temperature,
units and interpretation are readable. Overlapping curves reflect the small
actual changes, not missing runs. Seven pure helper tests passed before the
six declared integrations, and the committed design preceded all attempts.
