# Town sizes refitted with Greek wall circuits; supply at the with-Egypt share — 14 November 2026

Plan: `calibration/sizes_greek_walls_20261114/plan.json`, declared before output. Owner: "keep improving our model".
This step makes the map consistent with the Earth calibration that now passes with Egypt (GREEK_WALLS_20261114).

## Step 1: size model refit (gate passes)

Hanson areas of 40 of the 664 primary-cohort towns (Achaea, Macedonia, Epirus, wall-circuit basis) are read as inhabited
area (a half; a third at 100 ha or more; Hansen 2008). The uncorrected refit reproduces the archived release-2 size results
exactly (control).

| M1: ln area = a + b ln(hinterland people) | a | b | held-out σ | KS (≤0.10) | area ratio (0.8–1.25) |
|---|---:|---:|---:|---:|---:|
| Release 2 (published) | 2.157 | 0.127 | 1.057 | 0.058 | 0.95 |
| **Refit** | **1.915** | **0.147** | **1.048** | **0.063** | **0.95** |

M1 is still the selected model. Smaller towns come out a few percent smaller; the largest are about the same.

## Step 2: fantasy sizes rebuilt (positions unchanged, lore order strict)

| Corrected climate, sliding density | Before | After |
|---|---:|---:|
| Town residents | 13.62 M | 12.74 M |
| Largest town | 256,701 | 246,069 |
| Median town area | 31.7 ha | 30.6 ha |

Positions and the placement seat are identical; the capital is still the largest town. The existing reviewers
(`review_settlement_release3.py`, `review_settlement_release2_fantasy.py release3`) pass on the new folder.

## Step 3: grain supply at the with-Egypt Earth share 0.337

| Corrected climate | Published default (old sizes, 0.39) | New (refit sizes, 0.337) |
|---|---:|---:|
| Residents fed | 91% | 89% |
| Self-sufficient / with imports / short | 850 / 174 / 29 | 848 / 172 / 33 |

The raw climate is 87% fed with 40 short. The staffed towns of the control rule (affiliated, at least 150 fed residents)
are identical: 1,042 corrected and 1,023 raw. So the published reach, trade and administration maps stay valid. The
reviewer `review_wide_supply_release3.py` passes on the new supply.

## Step 4: published (owner permission)

The default Settlements maps (release3_central/low) now use the refitted sizes. The grain-supply option is
`release3_supply` at 34% marketed. The reach note now gives 34%, with the same staffed towns. The release-3 browser
checks pass (settlements, supply and supply-fed reach, 8 cases each), as does the Windows-style checkout check
(2,217 assets).

## Flat-density option at its own Earth share

Plan `calibration/supply_low_reading_20261114/plan.json` (declared before output). The share 0.337 was calibrated with
Earth city residents at the sliding reading. At the flat 100/ha reading Roman cities hold 4.06 M residents instead of
8.37 M. The same whole-empire setting then passes at **0.140** (270 km best, transfer 0.92 / 0.97); the sliding-reading
control reproduces the published calibration exactly. Review passed; fresh run byte-identical. The map's flat option now uses
14% (corrected climate: 1,042 of 1,053 towns fed, 99.2% of residents; raw 98.8%, 14 short). The default sliding option
keeps 34%. Browser checks and the Windows checkout check (2,217 assets) pass.
