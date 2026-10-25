# Handoff — 2026-10-25

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

The r38 rainfall-structure search is active, with its restored 31-region
reference reproducing adopted r38 exactly. See `reports/RAIN_STRUCTURE_20261025.md`
and use `scripts/guarded_gate_search.py` for future resumes; inspect the live
process before starting another. No physical model source may change during
that search. All three repository atlases now use inbound-directed trade with three Trade
views (routes, market hinterlands, people served) and continuous outlined sea
lanes. See `reports/DIRECTED_TRADE_20261025.md` and
`output/directed_trade_20261025/publication/publication.json`. Full population
and political tables are unchanged. Render-only changes have separate records.

A geography-only pilot is running from `calibration/earthlike_geography_20261025/plan.json`
via `scripts/check_earthlike_geography.py` (log `/tmp/earthlike_geography_runtime.log`).
It holds r38 physics and the current planet fixed, compares six exterior
scenarios across three layouts at ds16, and requires matched ds8 plus new-layout
checks before adoption. Do not modify its script or climate sources while active.
The fixed-footprint terrain audit confirms resolution dependence of the existing
uplift proxy; it is a diagnostic, not a coupled rainfall improvement.
The original list below describes the state before this follow-up.

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
