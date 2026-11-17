# Provisional settlement atlas r5 — 17 November 2026

The atlas now offers the frozen refreshed hierarchy and its own rebuilt annual grain supply. Provisional central settlements become the Settlements default. Release-4 settlements and their derived layers remain explicitly labelled reference cohorts. The owner authorized this bounded publication; the historical candidate adoption/validation gates remain false.

Open `atlases/earth_fit/provisional/index.html` through the normal local atlas server for synchronized before/after maps, town search, zoom/pan, raw/corrected climate and both density readings. New publication figures are `comparison_corrected.png` and `comparison_raw.png` in the same folder. Hosted URL and deployment receipt are recorded separately after deployment.

## Fixed scope

No climate refit, new training pool, relocation or total-population change. Climate r44, town locations, lore ranks, residual algorithm and seed 1 remain fixed. The already reviewed exposed-source final fit has coefficients [1.554938767713789, 0.1826427224092563, 1.0], residual sigma 1.0364605311460373 and hierarchy phi 0.25. The central density spans 100–500 people/ha; the low reading is 100 people/ha. These are scenarios, not censuses.

Annual wide supply is rebuilt from each cohort’s own remaining rural population, with 600 field hours/worker/year and extraction 0.3371937035110408 (central) or 0.14049021985082757 (low). Alternate extraction and 300-hour cases remain in the downloadable scenario comparison. Freight geometry was rederived during the fresh replay; all released controls matched exactly. Grain support is an annual ration equivalent and never replaces allocated residents.

| Climate / density | R4 residents | Provisional residents | R4 annual grain need met | Provisional need met | Short towns R4 → provisional |
|---|---:|---:|---:|---:|---:|
| raw / central | 13,272,677 | 13,170,501 | 81.14% | 80.99% | 47 → 52 |
| raw / low | 5,441,565 | 5,458,229 | 96.70% | 96.79% | 21 → 21 |
| corrected / central | 13,465,015 | 13,314,620 | 84.24% | 86.61% | 43 → 42 |
| corrected / low | 5,516,590 | 5,519,728 | 98.20% | 98.99% | 12 → 9 |

## Qualification and limits

The refreshed Earth fit was checked on exposed development sources, not a new untouched holdout. All-664 log-area CRPS improves about 1.08%; the strict-153 sensitivity improves about 3.21%. Size KS is slightly worse and the strict Egyptian subset remains underpredicted. The earlier pipeline failed its southern Mesopotamia blind placement/size test; this provisional release does not resolve independent transfer validation.

Annual people and grain conservation and listed field-work limits pass. Seasonal continuous food/work, complete diets, warehouse capacity/access, handling staff and actual crop calendars remain unresolved. Recent warehouse evidence work did not supply adopted empirical rates. Five application seeds (1, 7, 19, 43, 97) describe scenario sensitivity; their quantiles are not calibrated confidence or posterior intervals. Individual town changes can be large.

Only the new settlement and annual-grain options use the provisional populations. Reach, trade, administration and recurrence use their R4 or older explicitly named inputs. The new options suppress older integrated ledgers. The atlas banner, option notes and reference labels disclose this boundary. No seasonal or authority claim follows from the new maps.

## Verification and preservation

Independent reviews were rerun before changing live publication files: eight isolated Earth hierarchy fits and 560 losses; candidate final fit and 70 losses, six exact controls, 4,174 site-case rows and eight annual population cases; 20 five-seed size draws and 40 annual people cases; 32 annual grain scenarios and 33,392 town-scenario rows. A timing-only change in the Earth reviewer’s captured pytest output was saved as a separate r5 receipt; the original archived receipt was restored exactly.

The fresh candidate run matches all 13 scientific files. The fresh supply run independently rebuilds the network, matches four released control files plus the complete unrounded control receipt, and matches all ten compact candidate/supply scientific files. Its top source inventory additionally enumerates later, unused modules; no model equations were changed. Fresh raw/large arrays are local/ignored under the release output; compact replay hashes are tracked.

`scripts/review_settlement_provisional.py` verifies all preserved viewer values, all 8,348 added per-town grain values, scenario totals, maps and downloads against the reviewed source cohorts. It also verifies 1,178 frozen identities, using the exact archived originals for the authorized live publication whitelist. Browser checks exercise both climates, both densities, all four new atlas options, old-reference retention, downloads, search, synchronized selection/zoom, and mobile layout.

Live publication changes intentionally invalidate historical checks that demand old live atlas bytes. Those historical receipts remain unchanged. `baseline.json` and `baseline/` retain the precise pre-release files; the new reviewer checks those snapshots and every other frozen input. Replaying the historical producers requires their original publication baseline (commit 4a1525635/10e08d1b9) plus the pinned local scientific inputs; do not overwrite the new live atlas merely to make an old guard pass.

Publication recipe: `scripts/publish_settlement_provisional.py`. Independent publication reviewer: `scripts/review_settlement_provisional.py`. Browser check: `scripts/check_provisional_atlas_browser.cjs`. Declaration: `calibration/settlement_provisional_release5_20261117.json`. Receipts: `output/settlement_provisional_release5_20261117/`.

## Next work

The bounded map release is complete when deployment and browser receipts pass. Further science proceeds separately: resolve seasonal food/work and credible handling/staff inputs before claiming annual-to-seasonal feasibility or rebuilding control layers for the candidate; independent transfer qualification remains outstanding. Climate and the abandoned northern-steppe experiment remain deferred.
