# Current convergence-import audit

The current Somali baseline receives positive convergence import at **every
saved cell and seasonal step**, not only during its rainy season. This is a
large empirical closure worth investigating, but the audit finds no algebraic
double counting in its addition to concentration-form advection. Keep the
model unchanged while W18c runs.

This is explicitly exploratory: source reading and simple rate/annual summaries
preceded the committed scope declaration. No physical hypothesis was fitted
or independently validated. The audit reuses three fixed exposed cases, with
zero climate integrations and no fine or sealed target access.

## Actual source accounting

| Annual local term, mm/year | Somalia r58 | Somalia minimum turning | Sahara r58 |
|---|---:|---:|---:|
| Positive-only convergence import | +1591.645 | +605.435 | +787.724 |
| Positive concentration advection | +1643.649 | +799.331 | +583.600 |
| Negative concentration advection | -58.306 | -74.794 | -116.280 |
| Independent column drying | -194.164 | -192.074 | -1378.396 |
| Rain sink | -3556.410 | -2439.564 | -215.038 |
| Simultaneous min(import, drying magnitude) | 111.402 | 79.486 | 349.916 |

These selected terms are not the complete local equation: evaporation, eddy
exchange, diffusion and signed marine exchange also contribute. Positive and
negative advection were separated at individual cells/steps before averaging.
The min-overlap row measures co-occurring terms, not their physical redundancy
or an amount of removable rainfall.

The baseline Somali gain coefficient spans 0.0512–0.1765/day, with mean
0.0974/day. It is positive in 100% of samples and coexists with positive
concentration advection in 84.5%. Minimum turning reduces the mean coefficient
to 0.0400/day and import to 605.4 mm/year; its previously documented marine
exchange rises, so this is not an isolated import-removal experiment. The
Saharan gain is positive in 56% of samples, while much stronger independent
drying removes water. Separate import and drying can be simultaneous without
being an algebraic contradiction.

## What the source actually computes

The continuum product rule distinguishes `-u·grad(W)` from `-div(u W)`:
the latter also contains `-W div(u)`. Production uses the former concentration
form. Thus equal-sign advection and import at one cell do **not** prove the
same transport has been counted twice. The discrete concentration and shared
face flux stencils also differ beyond the continuum compression term.

Production adds `gain * W` with
`gain = flux_convergence * clip(-Gaussian(div), 0, 1e-5/s)
* clip((T_col - 15 C)/10 C, 0, 1)`. r58 has flux_convergence=1 and Gaussian
scale 2,000 km. The export half is explicitly omitted in the historical
closure. Independent drying is built from subsidence/branch/descent terms;
`divergence_drying` separately damps rain ascent rather than supplying a
signed, conservative vapor-export term.

The divergence code can subtract a diagnosed monsoon-heating velocity before
smoothing. That branch is **inactive here**: r58 has monsoon_heating=0. It
must not be invoked as the explanation for these cases. Other optional
column-shear branches are inactive too; traced surface and transport winds
match at all scored cells in these cases. Saved monthly wind and water fields
still cannot reconstruct the instantaneous gain, because clipping,
temperature gating and gain-times-water products do not commute with monthly
averaging. This audit uses the actual instantaneous rates instead.

One concrete follow-up is regional boundary dependence: the 2,000 km Gaussian
scale is larger than these runs' 1,100 km padding, and SciPy's default
four-sigma kernel reaches 8,000 km. The saved grids are only 45×45 cells at
56 km. This establishes a support mismatch, **not** a measured rainfall bias.
Quantify how much kernel weight uses reflected continuation before attempting
any larger-domain or changed-closure climate experiment.

## Earlier alternatives and their limits

These are historical experiments against their own r39/r43 controls. Their
scores are not pooled with r58 or fresh W18c results.

| Historical experiment | Recorded outcome |
|---|---|
| r39 vapor flux | No-import comparison S=1.0390, mean rain-loss ratio=1.0885; conservative-storm no-import S=1.0003, rain ratio=1.0236. Both flux profiles failed numerical checks; no finalist. |
| r39 flux with column wind | All step checks passed after separately declared damping/work changes, but flux variants had S=1.679–1.765 and mean rain ratios=2.367–2.548. No finalist. |
| r39 column mass closure | Balanced variants had S=0.9889–0.9981, but rain ratios=1.0119–1.0287 and protected-region/circulation failures. No finalist. |
| r43 fitted flux | Eight-region screen completed: upwind S=2.1113, fitted S=2.1861 against fresh control. Fitted versus upwind S=1.0227; no sealed run or adoption. |

The fitted-flux record's `T` and `P` fields are fractional changes, not raw
normalized ratios; the reported S values above are its recorded combined
scores. Original convergence failures and protected-region failures remain
failures. Conservative accounting alone has not produced acceptable climate
accuracy. Restarting a wholesale flux switch is not the next justified step.

## Verification and next action

All **3,650** import/drying exports exactly match float32 reconstructions from
actual rate×water. An independent scalar reviewer checks all **1,825 unique
cell/steps**, **16,425 scalar values** and **396 monthly integrals/fractions**;
all 36 case-months are complete. Four historical result records are copied
faithfully and kept in separate epochs. Source hashes are unchanged and the
seasonal figure was inspected. The previously failed marine-budget export
checks remain preserved; this audit does not reclassify them.

Next, measure Gaussian support and boundary-extension sensitivity on the same
saved fields without interpreting it as a climate rerun. If appreciable,
declare a bounded padding/convergence experiment with a wet-monsoon protection
case before any integration; do not change the scale to match Somali rain.
Any physical source change and the already identified core diagnostic export
fix wait for W18c closure. Adoption still requires all current gates. r58 and
the atlas remain unchanged; the sealed AA set is unopened by this work.

Artifacts: `output/convergence_import_audit_20261126/` contains complete
instantaneous/monthly tables, provenance, review, qualification and
`seasonal_terms.png`.
