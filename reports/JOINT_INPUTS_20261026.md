# Separating shared climate laws from the fitted planet

The latest qualified Earth physics is r39. Its 31-region monthly temperature
MAE is 1.793 °C and its regional rainfall loss improves 2.30% over r38.
Across 3,667 sampled cities, monthly rain MAE is 32.84 mm and 46.47% of annual
totals are within 25% of observations. These are different aggregations, not
an overall accuracy percentage. North India remains very dry: 256 versus
761 mm/year over the scored region. See the
[r39 report](CONSTRAINED_BLEND_R39_20261025.md) for the mixed annual-city results.

The Earth atlas still publishes the verified r38 world. The later r39 world
experiments improve some scores but fail the declared regional/layout gates.
The nine-layout paired gain's bootstrap interval crosses zero. This is a
transfer problem under uncertain invented surroundings, not evidence that
physical laws must be made unrealistic to obtain any improvement.

## A concrete input boundary for future joint experiments

`rotclimate/joint.py` explicitly partitions every existing parameter into
shared physical laws, invented-world properties, or numerical settings. A new
uncategorized parameter fails closed until assigned. The same physical block
and verified numerical profile construct both models; only the world block
comes from the fantasy-world profile. Stale physics and relaxed solvers in
that profile cannot silently enter either run. Optimizer updates assigned to
the wrong block are rejected.

Earth uses fixed solar input 1, greenhouse anomaly 0, radius 1, modern tilt,
prograde rotation, orbit/calendar and Earth's land-by-latitude profile. The
regional conversion then handles actual latitude and the southern-hemisphere
mirror. These are the WorldClim-era benchmark's reference settings; greenhouse
anomaly zero is not a claim about 200 AD atmospheric composition.

Historical `earth.earth_params` and `scripts/joint_calibrate.py` are preserved
for reproduction. The former resets tilt/orbit/calendar but historically
inherits solar input, greenhouse forcing and radius. The adopted r39 profile
has Earth values for all three, so that result is unaffected. New constrained
joint work should prepare separate profiles instead:

```sh
python -I scripts/prepare_joint_fit.py \
  --physics calibration/local_accuracy_20261023/r39_params.json \
  --world atlases/earth_fit/params.json \
  --out output/my_joint_inputs
```

This saves a frozen input manifest and `earth_profile.json`/`world_profile.json`.
It **does not run an optimizer, establish physical plausibility bounds, or
approve a fit**. Freeze Earth skill/SST protections, permitted world scenarios,
the search budget and matched resolution/layout checks before evaluating new
candidates. An Earth-infeasible candidate must not become eligible through a
larger fantasy-map score. The historical soft-penalty joint runner is not this
hard-gated optimizer.

Tests perturb the fantasy star, greenhouse forcing, radius and geometry;
Earth parameters remain identical. A real coupled test produces exactly the
same seven saved fields after those changes. Shared settings still transfer
to both models, and wrong-block or unverified profiles are rejected.

## Better source diagnostics before another rainfall search

The optional moisture diagnostics now expose surface evaporation, total
column drying, the monsoon subset of drying, and convergence-driven import.
These terms already operated in the simulation. Instrumentation leaves the
ordinary climate arrays identical, including when drying and import are active.
The exporter carries their signed contributions rather than hiding them in
a net evaporation source. Monsoon drying is part of total column drying and
must not be added twice.

`calibration/moisture_sources_20261026/plan.json` declares a three-region audit
with exact historical monthly-climate controls before interpretation. It is
not a parameter search or climate adoption. Numerical, geography and source
identities remain mandatory.

The audit is now complete: all three controls reproduce exactly and all
numerical checks pass. North India's July rain is 70 versus 224 mm observed;
Iran's prescribed monsoon drying removes 52 mm/month. The
[source audit](MOISTURE_SOURCES_20261026.md) and
[browser companion](../atlases/climate_accuracy/index.html) show the maps and
signed contributions. No physical improvement or world publication is claimed.

Earth remote-monsoon descent still derives from observed global rainfall;
fantasy descent derives from its simulated domain. Fixing parameter isolation
does not make those forcings equivalent or turn regional skill into coupled
global validation. Simply removing Earth's prescribed field would omit remote
monsoon sources outside the regional grid. A future generated-forcing test
must retain their spatial coverage. The concentration-advection moisture
equation is also not a closed global water budget, even when its local
residual is small.
