# New physics avenues: move beyond the current rainfall representation

14 October 2026. Requested research pivot toward larger ideas. This review uses
the current source, saved strict-convergence runs and primary research. The
assistant ran a saved-field audit and small operator tests only. No climate
simulation, calibration, download of gridded climate data or atlas export was
launched. The production model and its source/input fingerprint are unchanged.

## Recommendation

The strongest proposed development is an isolated **v10 atmospheric water and
storm prototype**, supported by a small Earth benchmark. The repeated regional
trade-offs suggest that improving the representation of water delivery is more
promising than continuing to adjust the same rain-efficiency and mixing knobs.
This is a hypothesis about model structure, not proof that the painting is
physically achievable or that one replacement will raise its fit.

The current storm continuation remains available as a frozen v9 comparison.
The user's newly selected rule remains in force: already-good Mediterranean
worlds may stay within 5% dry land, the worst-world result must improve, and
cold-dry/hot-dry/overall/Cs protections remain unchanged. A new physics engine
does not automatically inherit a validated fit or permission to ignore those
evaluation priorities.

## 1. Replace diffuse storm mixing with budgeted water transport and weather

### What the source and saved fields show

`rotclimate/solver.py` transports a scalar using `u.grad(W)`. Here `W` is
precipitable water, a column water amount, but that operator is a concentration
advection form rather than the divergence of a column moisture flux. The two
differ when winds diverge. The model's prescribed plus thermally driven winds
are not established moisture-weighted column winds, and there is no solved
upper-level return flow or atmospheric mass-continuity constraint.

The storm approximation is also spatially broad and isotropic: roughly 423 km
Gaussian mixing in the current fit, multiplied by a rate depending on location,
season, coastal side and elevation. In the saved world-1 Mediterranean region,
the winter local equation terms, averaged per painted cell, are:

| Term | Winter total, mm |
|---|---:|
| Rain | 451.56 |
| Evaporation | +108.54 |
| Mean-wind concentration transport | -69.83 |
| Diffusion | +47.35 |
| Regional storm exchange | +365.48 |

These are terms in the existing local equation, not independent causal sources
or a conservative global budget. They nevertheless establish that the storm
exchange approximation has a large role in this fit. Increasing winter mixing
also acts on nearby dry zones; a route-specific storm representation could
provide different spatial freedom without referencing the painted labels.

### An exact structural conservation issue

For a normalized symmetric mixing operator `G`, the existing exchange is
`rate_i * (G(W)_i - W_i)`. A spatially variable rate does not generally give
equal water gain and loss across a closed system. In a manufactured two-box
example, water amounts [0,10] mm, rates [2,0] per day and an equal-average mixing
operator produce sources [10,0] mm/day: a net gain despite a closed system.
This is not a measured leak rate for the open, padded production domain.

A prototype with symmetric pairwise conductances
`C_ij = G_ij*(rate_i+rate_j)/2` produces [5,-5] for that example and conserves
the total. With a constant rate it reduces to the original exchange. It is a
tested building block, not yet an open-boundary atmospheric closure.

The frozen-field audit also compares the current advection term with an upwind
finite-volume flux divergence on the same saved water and winds. Across the
Mediterranean, the median annual difference is about +2,355 mm-equivalent,
versus current mean annual rain of about 805 mm. This is **not extra rainfall**:
no alternative atmosphere was solved. It includes divergent-wind physics and
different face placement. Its magnitude is a reason to reformulate winds and
water consistently, not to drop a flux stencil into the existing solver.
Boundary-face accounting cancels to numerical precision in the audit.

### Research basis and proposed replacement

Tootoonchi, Bordoni and D'Agostino (2025) find that transient storms sustain
Mediterranean land wetting, while regional stationary circulation helps produce
summer drying. Their budget separates mean and transient moisture fluxes and
uses mass-consistent winds. This motivates separating weather transport from
the mean circulation rather than treating all exchange as one smoothing field.
[Primary paper](https://wcd.copernicus.org/articles/6/245/2025/).

Copernicus specifically provides mass-consistent ERA5 budgets whose winds are
adjusted to satisfy mass constraints; its unadjusted flux diagnostics can have
numerical contamination. The analogous requirement for our model is a wind/
water system with explicit and testable mass accounting.
[Official dataset documentation](https://cds.climate.copernicus.eu/datasets/derived-reanalysis-energy-moisture-budget?tab=overview).

Proposed v10 prototype:

- A moist lower layer and a drier upper return layer, with atmospheric mass
  exchange derived consistently from horizontal convergence/divergence.
- Conservative horizontal and vertical water fluxes, explicit evaporation,
  condensation/rain and storage, with boundary imports/exports recorded.
- A small ensemble of idealized passing winter disturbances. Transport and
  rain-out happen for each disturbance before seasonal averaging. Tracks and
  forcing depend on circulation and geography, never target-zone masks.
- Conservative pairwise exchange only for unresolved mixing, distinguished
  from the directed storm transport.

This remains an approximate regional atmosphere, not a claim to have built a
general-circulation model. Vertical structure, disturbance forcing and runtime
must be tested. A transient ensemble may cost more than the current mean-flow
model; no speed improvement is claimed before a measured prototype.

## 2. Require success on real Mediterranean and dry-interior climates

The existing model has Earth-derived zonal temperature and reference-city
comparisons, but the files do not establish a held-out regional validation of
its rainfall machinery. A successful fantasy fit alone cannot show that the
rain transport is physically transferable.

Build two small Northern Hemisphere test regions: California–Sierra Nevada–
Nevada, and Iberia–western Mediterranean–North Africa. Fix their latitude,
rotation, coastline and terrain. Evaluate monthly rain/temperature, winter
moisture delivery, annual water balance and the wet-coast/dry-interior contrast.
Use one region for physics choices and the other for transfer testing; do not
tune each independently to get a good headline.

Seager et al. (2019) identify winter storm tracks and summer anticyclones as
central to the geography of Mediterranean-type climates. Those are useful
mechanistic targets for a benchmark, beyond matching a Köppen label.
[Author-hosted primary paper](https://ocp.ldeo.columbia.edu/res/div/ocp/pub/seager/SeagerEtAlTypes2019.pdf).

WorldClim 2.1 supplies monthly temperature/precipitation climatology for
1970–2000 and elevation, suitable for broad climate-pattern comparison.
[Official data page](https://www.worldclim.org/data/worldclim21.html).
The checkout contains derived city normals, but **not** the raw WorldClim
grids (`data/cache/` is absent). Terrain/coast grids and atmospheric forcing
would need to be obtained before an actual regional benchmark can run. The
city data can define initial seasonal targets, not substitute for a gridded
moisture-budget reference. No such data download was performed here.

## 3. Treat the larger continent/ocean layout as a physical hypothesis

In the same broad-anchor physics, coarse world-1 Mediterranean dry area is
11.59%, versus 3.67%, 1.54%, 2.27% and 3.11% on the other checked surroundings.
These five cases are development/validation evidence, not a statistical climate
distribution. Still, that range is much larger than the recent fine-grid drift
or local parameter gains, so the uncertain area outside the painting matters.

Replace generic procedural-seed robustness alone with a few explicitly drawn,
physically coherent larger-scale hypotheses: winter upwind ocean fetch,
continental interior, mountain barriers and enclosed seas. Diagnose where the
painted Mediterranean's winter vapour actually comes from under each. Prefer
independently plausible geography to arbitrary water sources chosen to match
the painting. Keep the drawn map itself unchanged.

This could also support a better large-scale circulation boundary condition.
Retrograde Earth research finds substantial reorganizations of circulation,
precipitation and ocean transport, so a reversed zonal wind sign cannot by
itself validate all regional responses.
[Mikolajewicz et al. (2018), primary study](https://esd.copernicus.org/articles/9/1191/2018/).
The previous T21 ExoPlaSim run already provides a broad independent check; the
painted region spans only a few cells there, so it cannot adjudicate our local
dry strip. A much heavier full GCM is not the first proposed development step.

## 4. Later: actual land-water storage, with limited expectations

The current `soilP` is a smoothed recent-rainfall rate, not a soil-water store.
Land evaporation is a fraction of that rate. Snow is calculated after the
climate solve; runoff/drainage analysis is also downstream of the climate.
A finite soil/snow water store with energy-limited evaporation could improve
summer heat, drought persistence and wetland water availability.

This is lower priority for fixing missing Mediterranean winter rain. Earlier
project experiments found drainage indices weak on the map's coarse height
tiers. Adding a river-wetness label alone does not resolve that limitation or
create the missing atmospheric water supply. Similarly, delayed orographic
rain is physically motivated, but earlier short cloud-spillover trials were
unproductive; it needs a new specific diagnosis before becoming the main bet.
Smith–Barstad's theory explicitly treats condensed-water advection, conversion,
fallout and downslope evaporation, providing a later upgrade path.
[Primary paper](https://journals.ametsoc.org/doi/abs/10.1175/1520-0469%282004%29061%3C1377%3AALTOOP%3E2.0.CO%3B2).

## Development sequence and decision points

1. **Done:** saved-field and manufactured conservation audit. Isolated operator
   building blocks in `scripts/audit_moisture_structure.py`; eight tests pass.
   Reproducible audit: `output/moisture_structure_audit/audit.json`.
2. Construct small closed/open two-layer test problems. Require water and dry-air
   mass accounting, nonnegative stores and explicitly accounted boundary fluxes
   before coupling to the atlas. Prove convergence on those manufactured cases.
3. Build the Earth test inputs and evaluate rain seasonality across a coast and
   a mountain/interior transition. Benchmark continuous fields and budgets.
4. Have the user run a bounded v9/v10 comparison on the fantasy main world and
   a cold-dry stress world. Reuse old v9 results. Freeze geometry and classifier,
   report rain supply, seasonal contrasts and every protected-zone score.
5. Expand calibration only if the new mechanism passes its physical tests and
   the regional comparison gives evidence that it addresses the observed
   limitation. Retain the current atlas until a new result is reviewable.

Implementation follow-up: the user authorized this direction. A first isolated
two-layer water/storm engine and a bounded Earth rainfall pilot are now built;
see [prototype scope, fast tests and user-run protocol](v10_prototype.md).
Temperature is observed forcing in that first stage and is not evaluated as a
prediction. Regional Earth runs and the fantasy comparison remain unrun. The
production model is unchanged; the next experiment tests this mechanism before
expanding to a coupled climate engine or another parameter search.
