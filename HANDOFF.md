# Handoff — 2026-10-25

## Current status — 26 October 2026

**NEXT/ACTIVE:** `scripts/check_r39_world_robust.py`, plan
`calibration/map_world_r39_robust/plan.json`, outputs `output/r39_world_robust/`,
log `/tmp/r39_robust_runtime.log`. This is a new campaign: the preceding balance
attempt remains rejected. Inspected layouts17/23 are now explicitly development,
together with1/2/3. Four fixed geometries (balance001,002 and001 turned±1°)
must improve both known batches and the five-layout mean, plus predicted native
protections. At most one actual native1/2/3 check; only a native pass receives
five prospectively declared validation layouts390101,390211,390307,390401,390503.
Original native and layout thresholds remain unchanged. Cached actual member
parameters, numerical certificates and source/file hashes are checked. Nineteen
focused tests pass. The command queues `build_r39_earth_stage.py` with this new
review after the campaign exits successfully, log `/tmp/r39_earth_build.log`.
It skips a rejected review. Do not launch a duplicate builder. Browser QA and
canonical promotion still remain if the stage is built.

DO NOT edit model sources, robust/transfer helper scripts, this plan or canonical
Earth params/summary while this campaign or its queued build is running.
Current canonical Earth is still r38. The more detailed older attempt below
explains the rejected parent; its old build instructions are historical.

A final, conditional fixed-candidate audit is declared before any of its nine
new layouts in `calibration/map_world_r39_audit/plan.json`, implemented by
`scripts/audit_r39_surroundings.py`. Only if the robust campaign rejects:
audit the single already native-passing balance003, with NO parameter search,
on nine other prospective layouts490101…490907. The original17/23 rejection
remains. Require the unchanged native gate, nine-layout mean-climate gain and
a strictly positive lower2.5% paired-bootstrap bound of individual-layout score
gains (20000 draws, fixed RNG). Both estimands are reported separately; this
is uncertainty under the invented-neighbourhood generator, not real-planet
physical validation. No sample extension or second candidate. Twenty-three
focused tests pass. Run only after the robust review is complete; it skips
an eligible robust result. If it qualifies, use its review with the same stage
builder and finish actual browser checks/promotion. Otherwise retain r38.

r39 Earth physics is adopted (`calibration/local_accuracy_20261023/r39_params.json`):
dev31 S 0.987521, paired 28 km S 0.994737, established six S 0.994573. Rain loss
improves 2.30%; city monthly MAE improves but annual matches slightly worsen.
North India worsens; Iran improves strongly. Static diagnostic SST is identical.
See `reports/CONSTRAINED_BLEND_R39_20261025.md`.

All normal `.bat` atlases are available, with directed markets (3 Trade views),
continuous outlined sea routes and current HTML pages. Published Earth climate
is still r38, Whittaker outside-diagram share 1.44%, Free share 11.47%. The
actual launcher server is running locally on port 8766; browser and complete
packet checks passed. Do not claim a new world is published until verified.

The initial fixed-planet r39 world search completed 97 ds32 mean-climate cases.
Its one coarse-eligible candidate 32 passed native numerical checks but failed
publication protections: score 0.183300, strict 33.80% vs 34.99%, worse Med.
The original failed attempt is preserved in `output/r39_world_publication/`.
The world and native check processes have ended.

**COMPLETED:** `scripts/check_r39_world_transfer.py`, log `/tmp/r39_transfer_runtime.log`.
Plan: `calibration/map_world_r39_transfer/plan.json`; outputs
`output/r39_world_transfer/`. It screens at most 7 worlds at ds16, using the
measured resolution discrepancy for ranking, then at most 2 actual native ds8
checks. Each layout is checkpointed separately under `members/`. Only a native
pass takes the 17/23 layout comparison; only all passes allow publication.
Planet, r39 physics, target rules and the original native protection thresholds
are unchanged. No correction is applied to actual climate fields.

All seven ds16 screens converged. Native candidate 49 converged and improved
zonefit to 0.187963 / strict 37.04%, but tree recall 4.56% failed the unchanged
loss allowance (r38 6.79%; minimum 4.79%). Native candidate 65 also converged:
zonefit 0.187228 / strict 36.00%, tree recall 6.26%, but Mediterranean dry
7.55% exceeded the unchanged 6.91% maximum. Both are rejected, with all
native numerical checks passed; no additional-layout check was inspected.
`native_comparison.png` shows the rejected 49 result; the earlier
`world_preview.png` is ds16 only. Tree-zone mean rain falls 544→504 mm while
winter temperatures improve; see `native_target_diagnosis.json`.

**COMPLETED, REJECTED:** the conditional bounded geometry path in
`calibration/map_world_r39_balance/plan.json`, run by
`scripts/check_r39_world_balance.py`, log `/tmp/r39_balance_runtime.log`.
Its eligibility condition is now met: both endpoints failed, with successful numerics.
It was declared before any interpolated climates and before candidate 65's
native result: three geometries at fractions 1/3,1/2,2/3 between 49 and 65,
ds16 layouts1–3, at most one native check, same untouched native and layout
protections. Run `scripts/check_r39_world_balance.py` only after the parent
review is complete (it now is). It exits without work if the parent already qualifies.
Use its review path with the same staging builder if it passes. Eleven
focused interpolation, ranking and atlas-packet tests pass.

All three balance ds16 screens converged. The ranking selected `balance_003`
(2/3 toward65), which passed every actual native guard: zonefit0.187353,
strict36.35%, tree5.73%, Med dry6.88%, Cs80.90%. Its additional-layout score
on17/23 was0.187013 vs r38's0.187191, so it failed the unchanged gate despite
better strict agreement33.60% vs32.39%. The attempt stopped, with no second
candidate chosen after this result. The queued staging builder exited without
work, correctly preserving canonical r38. No balance/build process remains.
`native_balance.png` shows native gains but explicitly says ineligible.

Preserve the completed transfer/balance plans, scripts and evidence. The original
map/data source audit is in `input_audit.json`. A new robustness campaign must
explicitly treat inspected layouts17/23 as development data and reserve other
layouts for prospective validation; do not relabel this failed attempt a pass.

If `output/r39_world_balance/review.json` says `eligible_for_publication=true`,
run `python -I scripts/build_r39_earth_stage.py --review output/r39_world_balance/review.json`.
It reuses the verified native checkpoint, writes `atlases/earth_fit_r39_next`,
and checks assets/food/population. Browser-check that staging folder through
port 8766, then promote only after its checks pass. Preserve canonical Earth
as a backup, copy the new polity cache to `output/polity_map/earth_fit.npz`,
update Earth note in `atlases/pages.json` and the hub description to r39,
refresh pages/hub, render both political plates, check all canonical browsers,
commit and push. Hosted external artifacts still lack a publishing tool.
If the supplemental attempt fails, retain the canonical atlas and record why.

Normal pushes: `git push origin HEAD:claude/friendly-turing-43ygeu` from local
branch `work`. User requests autonomous continuous development, frequent updates,
and every generated substantive map/plot shown inline. No agents unless the
user explicitly requests agent delegation. Older status below is historical.

## Repository publication follow-up

Earth r38 is built and promoted to `atlases/earth_fit`, with all three layout
numerical certificates passing. See `reports/ATLAS_R38_20261025.md` and
`output/atlas_r38/earth_publication.json` for map comparisons and browser QA.
The hub and atlas pages are refreshed. Free-fit and Whittaker political exports
are now promoted and browser-checked; all three have political plates at fills
0 and 1 day and claimed/held population figures. Map tables and figures are in
`reports/POLITY_V3_20261025.md`; publication checks are in
`output/atlas_r38/political_publication.json` and `food_population_checks.json`.
Hosted artifacts remain unchanged because no tool for those URLs is available.

The r38 rainfall-structure search completed all 120 evaluations (control plus
119 candidates). The final input guard matches the initial identity. None
passes all regional protections; retain r38 and do not run finer-grid or
established-six selection on these rejected candidates. See
`reports/RAIN_STRUCTURE_20261025.md` and
`output/rain_structure_20261025/final_review/`. `search/best_params.json` is a
rejected research candidate. No climate search remains active.

All three repository atlases now use inbound-directed trade with three Trade
views (routes, market hinterlands, people served) and continuous outlined sea
lanes. See `reports/DIRECTED_TRADE_20261025.md` and
`output/directed_trade_20261025/publication/publication.json`. Full population
and political tables are unchanged. Render-only changes have separate records.

A geography-only pilot completed from `calibration/earthlike_geography_20261025/plan.json`
via `scripts/check_earthlike_geography.py`; all 18 runs converged, none of the
five alternative geographies beat the ds16 control, and no finalist advances.
See `output/earthlike_geography_20261025/review.json` and
`reports/JOINT_EARTH_FIT_20261025.md` for the negative result and target-factor
diagnosis from the published ds8 climate.
It holds r38 physics and the current planet fixed, compares six exterior
scenarios across three layouts at ds16, and requires matched ds8 plus new-layout
checks before adoption. Its experiment script and source manifest are frozen historical evidence.
The fixed-footprint terrain audit confirms resolution dependence of the existing
uplift proxy; it is a diagnostic, not a coupled rainfall improvement.
The original list below describes the state before this follow-up.

The next two controlled physics pilots are complete and rejected: common-DEM
terrain quadrature (16/16 numerical passes, 4 exact r38 controls) and faster
column-water transport (all coarse candidates rejected, no fine selection).
The terrain closure is opt-in; production remains legacy/r38. Ninety-eight
focused tests pass. See `reports/TERRAIN_QUADRATURE_20261025.md` and the matching
plans/results. No model integration is active for these completed pilots.

**r39 is now adopted for Earth physics.** The constrained-combination campaign
passes dev31 S=0.987521 (all groups better), paired 28 km S=0.994737 and the
established six S=0.994573. Full records and mixed city results are in
`reports/CONSTRAINED_BLEND_R39_20261025.md`. North India worsens; do not call it
a Himalayan fix. Static diagnostic SST remains exactly unchanged.

A **world refit is active** via `scripts/refit_r39_world.py`, log
`/tmp/r39_world_runtime.log`, plan `calibration/map_world_r39/plan.json`.
It holds r39 physics, tilt/spin and other planetary properties fixed, fits
97 mean-climate world candidates at ds32/layouts1–3, and still needs native and
layout-transfer checks plus a staged Earth-atlas rebuild. Do not edit model
sources, its scripts/plan or canonical Earth params while it runs. Local HTML
atlases stay available on verified r38 data with current economic maps.

## Historical handoff before this follow-up

The current status above supersedes the old status and task list below. Do not
repeat completed builds or the completed rainfall search from these instructions.

Branch: `claude/friendly-turing-43ygeu`. Everything below is committed and pushed. Background jobs
that were running when the session ended did NOT save; rerun them as listed.

## Done this session

- **Polity v3: de facto vs de jure** (`polity/defacto.py`, `polity/render.py`): held land
  (within 2 days of a polity's own roads and towns) against the painted claims; categories held /
  claimed-unheld / held-by-another / held-unclaimed / contested; a gap fill (closing in travel time)
  with atlas variants 0, ½, 1, 2 days. Earth test (`scripts/polity_fill_check.py`,
  `calibration/polity_20261025/plan_fill.json`, `fill.json`): fills up to 2 days change the match to
  historians' maps by < 0.01, so the default is 0 and the fill is a cartographic choice.
- **People and control per polity**: `polity/defacto.py: polity_table`, written to
  `atlases/<atlas>/data/polities.csv` and `atlas.json` → `reach.defacto` (claimed, held, unheld,
  held by others, beyond claim, contested, mean control, within-a-day share).
  `scripts/polity_tables.py` recomputes them without redrawing.
- **Trade** (`polity/trade.py`, `polity/routes.py`): Price Edict costs (sea : river : road =
  1 : 5 : 28), catchments and market access over claimed land only, gravity flows routed per season,
  sea lanes bundled (blur + thinning). Earth test (`scripts/polity_trade_check.py`,
  `plan_trade.json`, `trade.json`): market access does NOT explain Roman town size, so towns are not
  sized; COST_SCALE = 270 road-km is set from Duncan-Jones, not fitted.
- **Vector map data** (`polity/vectors.py`, `polity/mapdata.py`): `data/vectors/*.geojson` +
  `political.svg` (Inkscape layers) in source-map pixels. **Plate**:
  `scripts/render_political_plate.py <atlas> [--fill 0]` (needs `output/polity_map/<atlas>.npz`,
  written by the export).
- **Atlas page**: generic layer-variant selector in `atlas/index.html` (copy into atlases with
  `scripts/refresh_atlas_pages.py`). Atlas build now writes `winds12.npz` itself before the political
  layers (`scripts/build_atlas_variant.py`, `scripts/export_winds12.py: write`).
- **Climate r38 adopted** (`reports/STABLE_LAND_20261025.md`,
  `calibration/local_accuracy_20261023/r38_params.json`): gate S 0.9834 (T 1.841 → 1.796 °C, every
  group better), 28 km 0.9849, sealed six 0.9752; cities within 25 % 43.1 → 46.7 %; sea vs WOA18
  2.79 → 2.87 °C (reported).
- Earth-fit world refit on r38 done: `calibration/map_world_r38/world/best_params.json` (0.189 at
  ds32; r37 world on r37 was 0.194).

## State of the atlases

- `atlases/whittaker_fit`: political layers exported (de facto variants, trade, vectors) but BEFORE
  the last fix (trade catchments = claimed land only). Re-export.
- `atlases/free_fit`: political v3 layers NOT yet exported.
- `atlases/earth_fit`: still the r37 build. r38 rebuild NOT done.
- Hosted artifacts and hub NOT republished (URLs below).

## To do, in order

1. **Earth-fit atlas on r38** (~1 h):
   ```
   mkdir -p output/atlas_r38 && OMP_NUM_THREADS=1 python3 -I scripts/build_atlas_variant.py \
     --params calibration/map_world_r38/world/best_params.json --name earth_fit_next \
     --title "Rotclimate Earth-Fit Atlas" --eyebrow "Climate, farming and settlement · three layouts · c.200 AD" \
     --note "Only world parameters fitted; Earth r38 physics held fixed. Climate averages surroundings layouts 1–3, with recorded linear, temperature and moisture convergence checks. Farming and population layers use low-input c.200 AD technology; population values are declared settlement scenarios." \
     --downsample 8 --image-scale 2 --seeds 1,2,3 --workers 2 --fit-objective zonefit --require-verified \
     --checkpoint output/atlas_r38/earth_publication.pkl > output/atlas_r38/earth_build.log 2>&1
   ```
   Compare `atlases/earth_fit_next/summary.json` with `atlases/earth_fit/summary.json` (zonefit
   0.1756, strict 25.9 %), then `git rm -r atlases/earth_fit && mv atlases/earth_fit_next atlases/earth_fit`,
   change "r37" → "r38" for earth_fit in `scripts/build_fit_hub.py`, run it.
2. **Political exports** for the other two (≈20 min each; export into a staging copy so the tree
   stays clean): `python3 -I scripts/export_reach.py atlases/whittaker_fit atlases/free_fit`.
3. **Plates and figures**: `scripts/render_political_plate.py <atlas> --fill 0` (and `--fill 1`),
   `scripts/plot_polity_people.py <atlas>`.
4. Fill in "Map results" in `reports/POLITY_V3_20261025.md` (per-polity table, figures).
5. **Republish** (load the artifact-design skill first; package with
   `scratchpad pack.sh` logic = `scripts/package_atlas_artifact.py`, list files, publish with
   `files`; give `.geojson` an explicit contentType `application/geo+json`):
   earth_fit https://claude.ai/artifact/ABFAoyPzTuMNVWmByPxctF ·
   free_fit https://claude.ai/artifact/Ko7QGWnekU4RLhcMzVwZBY ·
   whittaker_fit https://claude.ai/artifact/XipEjxEomSAqXS4KhAy3RD ·
   hub https://claude.ai/artifact/GPxfbcEiUkiWUr9ubYdMaw.
   Browser check: scratchpad `polity/browser_check_v3.py` (variant selector, trade layer).
6. **Climate next**: rain-structure search from r38, plan frozen in
   `calibration/rain_structure_20261025/plan.json`:
   `python3 -I scripts/gate_calibrate.py --plan calibration/rain_structure_20261025/plan.json --out calibration/rain_structure_20261025/search --workers 3 --hours 1.85 [--resume]`
   then the gate per the plan's "afterwards" (`scripts/gate_stable_land.sh` is the template; 28 km
   check on up to three candidates). Target: north India's monsoon (July 76 mm vs 224 on r38; the
   model rains on the Tibetan plateau instead of the Himalayan front:
   `output/diag_rain/north_india_r38/rain.png`).

## Rules kept throughout

Plans are frozen before results; tests run once; deviations reported. Don't edit `rotclimate/`
while a search, gate or build is running. No model names in commits. Commit trailers as in the
existing history. Never use `pkill -f` patterns that match your own shell (kill by PID).
