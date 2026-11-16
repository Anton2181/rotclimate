# Fixed-site settlement hierarchy candidate — 16 November 2026

The refreshed Earth fit now has an actual fantasy map comparison. Open the
[offline interactive viewer](../output/urban_hierarchy_candidate_20261116/index.html),
[corrected comparison](../output/urban_hierarchy_candidate_20261116/comparison_corrected.png)
or [raw comparison](../output/urban_hierarchy_candidate_20261116/comparison_raw.png).
The viewer supports both climate scenarios and density readings, synchronized
pan/zoom and town selection, name/actor search, change colours and CSV downloads.
It embeds its map and data and needs no external service. The terrain includes
only shared painted roads, so the corrected view does not inherit raw-only tracks.

This is a **development preview**, with `adopt=False` and `gate.passed=False`.
The published atlas and its defaults are unchanged. Climate remains parked at
fantasy r44. The modest held-out improvement reported in
[the preceding joint trial](URBAN_HIERARCHY_REFRESH_20261116.md) is the development
evidence; fitting all source records here produces no new validation evidence.

## Exact published-map controls, with one disclosed metadata exception

The governing [candidate declaration](../calibration/urban_diagnosis_20261116/hierarchy_candidate_build.json)
was committed in `dc57b1c5c` before this fit. Both published controls were rebuilt
first on the same 1,034 raw / 1,053 corrected sites. All six town CSV, site JSON
and complete fields NPZ files reproduce their release hashes exactly. Unrounded
area, population and annual-ledger summaries also reproduce. Fixed population,
occupation, land, collection ownership, tracks, prior and marked cells match.
Missing collection/track caches were reconstructed from published packets;
the placement replay recovered track ordering and asserted the identical site
set. No new climate fit or alternative placement was used.

The first raw control stopped after its three output files matched: its input
receipt contained the newer `atlas.json` hash. The released metadata was
recovered from commit `d05e7092b139919eed6d5af1f4275274110cae7d`. The sole
difference is the later `land_forest` display-layer descriptor in the raw and
corrected layer lists. The failure, log, producer snapshot and old metadata are
preserved under `failed_metadata_control/`. A narrowly scoped
[A1 amendment](../calibration/urban_diagnosis_20261116/hierarchy_candidate_metadata_a1.json)
was committed in `9e0c7859d` before retry or candidate fitting. It requires both
metadata hashes and exact equality after removing only that layer descriptor;
all other metadata, inputs, numerical results and binary controls stay exact.
The independent review checks this exception. **Full historical input-receipt
byte identity is not claimed.**

## Final source fit and fixed application

All 664 existing source records are training at this stage. The same refreshed
population recipe, four province folds, 28 capital centres, 95 source pairs,
70 bounded hierarchy choices and five selection seeds are retained. Four-fold
OOF mean errors supply RMS scatter and selection means; the final mean is fit
to all 664 records. No new source pool or exponent search was opened.

| Parameter | Published | Candidate |
| --- | ---: | ---: |
| Intercept | 1.9151803604 | 1.5549387677 |
| ln H coefficient | 0.1470388831 | 0.1826427224 |
| Scatter | 1.0479729291 | 1.0364605311 |
| Hierarchy selection phi | 0.50 | 0.25 |
| Capital log shift | 0.80 | 1.00 |

The candidate uses the published residual selection, lore ranking and three
global top lore slots on unchanged sites. All 151 marked places remain eligible
for residual selection, while only the existing 19 capital seats receive the
capital shift; 121 places participate in lore ranking. This all-marked
application differs from the 28 source capital centres and remains an explicit
transfer assumption.

The canonical builder refuses an unadopted fit. As declared beforehand, an
isolated runtime adapter bypasses **only** that output guard, retaining the
false gate in the actual candidate metadata. The literal substitution, original
source hash and exact adapted source are retained. No canonical builder was
edited and the old historical owner adoption was not reused for the new fit.

## Area, population and annual local cereal results

| Map / density | Total area ha, old → new | Town residents, old → new | Change | Local cereal supported towns, old → new |
| --- | ---: | ---: | ---: | ---: |
| Raw / central | 54,415.65 → 54,582.29 | 13,272,677 → 13,170,501 | −0.770% | 245 → 242 |
| Raw / low | 54,415.65 → 54,582.29 | 5,441,565 → 5,458,229 | +0.306% | 236 → 239 |
| Corrected / central | 55,165.90 → 55,197.28 | 13,465,015 → 13,314,620 | −1.117% | 264 → 262 |
| Corrected / low | 55,165.90 → 55,197.28 | 5,516,590 → 5,519,728 | +0.057% | 247 → 249 |

World population is fixed at 53,119,878.8724 raw / 53,428,650.0883 corrected.
Rural population changes by the opposite of the town change. All requested
residents are allocated to floating precision: maximum unmet total is
2.92e−11 people, and maximum population residual is 7.46e−9 people. This uses
actual finite own/wider source movement, rather than merely reporting desired
town populations. Complete precision and per-town movements are in
`comparison.csv`, `town_changes.csv` and the compact `town_model.npz`.

The legacy annual local collection check leaves 792/795 raw and 791/804 corrected
towns dependent on imports under the central/low readings. It also records 68
raw / 6 corrected source cells below rural annual need. These deficits remain
visible. Import dependence is not a result from a new wider-supply calculation
and does not mean final famine or full support. This stage neither reruns wider
grain trade nor qualifies seasonal origin food, field work, civilian/staff
competition or continuous delivery. Population conservation alone cannot do so.

### Individual town changes need a seed check

The median candidate/published area ratio is 1.0157 raw / 1.0151 corrected;
838/1,034 and 865/1,053 towns lie within ±10%. However, 39 raw / 34 corrected
towns more than double, while 22 raw / 13 corrected towns fall below half.
The most extreme ratios are 0.0839–24.30 raw and 0.0591–50.47 corrected.

These are **one paired scenario draw (seed 1)**. Changing the hierarchy selection
changes which places receive residuals, and the later lore permutations can
move large areas between fixed places. A 50-fold change at one node is not
evidence that this particular town should grow 50-fold. Before interpreting
such changes, compare paired seeds and report persistent changes and interval
widths. The next declaration fixes that comparison before its results exist.

## Independent verification and reproduction

The [scientific review](../output/urban_hierarchy_candidate_20261116/review.json)
passes six exact released controls, independent QR full/OOF fits and all 70
selection losses, independent full-distance ownership and residual/lore replay,
4,174 site-case rows and eight annual population/cereal cases. Maximum area
difference is 1.14e−13 ha and maximum rural difference is 2.28e−13 people.
All scientific exports, including candidate full fields, reproduce byte for byte
in a fresh directory. Source/protected main-asset hashes match.

The presentation review independently checks all 2,087 towns and 37,566 values,
the exact embedded payload and shared terrain. Chromium checks passed at
1440×1100 and 390×844, including every SVG coordinate, both modes/readings,
search, synchronized selection, colours, zoom/pan/reset, CSV download and mobile
overflow. No browser exceptions occurred. Review receipts and desktop/mobile
screenshots are stored beside the viewer.

From the repository root, with the existing source packets and Python environment:

```sh
.venv/bin/python scripts/prepare_urban_candidate_control.py
.venv/bin/python scripts/build_urban_hierarchy_candidate.py
.venv/bin/python scripts/build_urban_hierarchy_candidate.py --out output/urban_hierarchy_candidate_20261116/fresh
.venv/bin/python scripts/review_urban_hierarchy_candidate.py
.venv/bin/python scripts/render_urban_hierarchy_candidate.py
.venv/bin/python scripts/review_urban_candidate_presentation.py
```

Serve the repository locally, then run
`node scripts/check_urban_candidate_browser.cjs <local-viewer-URL>`.
Large prepared/full-field caches and the fresh duplicate are ignored; the
compact model, exact output receipts, CSV/site JSON, maps and viewer are tracked.

## Next bounded stage

[candidate_supply_robustness.json](../calibration/urban_diagnosis_20261116/candidate_supply_robustness.json)
declares a five-seed fixed-site comparison and annual work-limited wider-supply
controls. The seed component has since completed and is independently reviewed;
see [URBAN_CANDIDATE_SEEDS_20261116.md](URBAN_CANDIDATE_SEEDS_20261116.md).
Wider supply remains next. The declaration does not authorize adoption from annual results. The existing
`settlement_residents.allocate_residents` / `audit_origin_food` seasonal joint
accounting, affected supply/staff/reach/trade chain and appropriate transfer
evidence still precede adoption or main-site publication. Do not reopen climate,
Buringh sizes or climate `l`, or redo the completed source-fit audits.
