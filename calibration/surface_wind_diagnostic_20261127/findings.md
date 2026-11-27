# Correcting surface winds does not by itself correct the climate

All six predeclared runs finished, without retries or numerical changes. The
three model-wind controls reproduce archived monthly T/P/E/W/u/v, raw solver
winds/gain/sink/W/P/calendar and all local budget fields byte-exact. All six
original numerical certificates pass, including the strict0.01 moisture
criterion. Max exported scaled residuals are below0.01 in every case; North
India observed-wind is close at0.009974, which does not justify relaxing it.

The verified1991–2020 NCEP sigma0.995 surface reference was sampled on each
full padded grid, projected with the existing equidistant Jacobian including
metric factors, stored/read-only and checked before/after integration. Actual
scored heat and moisture wind samples match the prescribed calendar
interpolation in shape, dtype and bytes. Independent review rechecks source/
input/forcing hashes, projection inverse, each attempt's parameter dictionary
and raw solver samples. Only wind_source differs between paired arms. Original
Earth boundary PW/descent, SST configuration and every other coefficient remain.

| Region | Annual rain mm, model → observed wind | Observed mm | T MAE C, model → observed wind | Rain loss, model → observed wind |
|---|---:|---:|---:|---:|
| Somalia |3556.41 →4097.36|457.36|1.298 →1.515|3.6634 →4.2022|
| Sahara |215.04 →12.31|2.07|2.364 →1.990|1.6858 →0.1411|
| North India |547.42 →748.02|760.83|3.206 →2.952|0.4900 →0.6654|

Sahara's rainfall loss falls91.63% and its temperature improves. This supports
circulation as a major part of its present false summer monsoon. It remains
wetter than the extremely dry reference. A generic stronger summer turning
would not reproduce this northward-flow correction.

Somalia worsens: rain loss +14.71%, annual rain +540.95mm and T MAE +0.217C.
Its model already rains throughout May–October instead of the observed dry
summer separating two rainy seasons. Prescribed surface winds do not recover
that seasonal structure. Circulation mismatch alone therefore cannot explain
or fix the rainfall error under the retained moisture/source configuration.

North India's near-correct annual mean and improved regional seasonal curve
hide spatial redistribution. The existing loss is computed per cell, not from
the regional mean. Its annual per-cell log RMSE rises0.5616 →0.7635 and
normalized cell-month absolute error0.4184 →0.5672. Several Nepal cells
receive~3246–3889mm/year against~366–772observed. Both loss components worsen;
this is not a metric contradiction or reason to replace the metric with a
mean-total score. The supplemental spatial review retains coordinates and
worst-cell values. Coarse reanalysis and the existing free-wind terrain uplift
are limitations; this diagnostic does not establish either as an isolated cause.

## Coupled local source changes

Signed annual term changes (mm/year), prescribed minus model wind:

| Region | E | Marine relaxation | Column drying | Convergence import | Advection | Diffusion | Storm exchange | Rain |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Somalia |+19.01|+1675.24|−5.12|−1332.36|+198.76|−30.39|+16.28|+540.95|
| Sahara |−200.34|+347.92|+261.91|−476.17|−431.23|+9.67|+285.50|−202.72|
| North India |+40.40|−77.26|−78.03|+165.37|+322.47|−14.47|−157.86|+200.60|

Somalia's convergence import falls from1592 to259mm/year, yet its marine
relaxation changes from a small net sink(−12.68) to a1662.56mm/year source.
This source compensation more than offsets the convergence decrease. Advection
also grows. Actual equations close with saved residual/rounding; these terms
are local concentration accounts, not planetary mass closure, tagged moisture
provenance or independent causal shares. The marine term's response is a strong
next mechanism lead; the rejected fixed receiving-target cap under modeled
winds is not reopened or tuned by this result.

## Scope and next step

This experiment replaces both heat and moisture velocities with coarse surface
winds; it does not prescribe an observed3D atmospheric state. It changes related
advection, convergence, fetch, uplift and thermal feedbacks together. Modeled
pressure-dependent drying and belt subsidence remain, responding to the coupled
state. The2.5degree reference cannot resolve a coastal jet or Himalayan terrain;
regridded cells are not independent observations. No global accuracy claim or
fictional-world forcing/adoption follows from the Sahara improvement.

Next, prospectively declare a fixed wind×marine-relaxation ablation on the same
three regions. Preserve these six completed packets and add exact replays as
controls before disabling inflow_gain in the diagnostic arms. This measures
whether e91 source compensation persists and what the monsoon/desert costs
are; turning it off is an ablation, not an accepted final moisture law. No
new experiment is authorized by an already-spent integration budget: give it
its own plan and immutable records before execution.

The six-panel wind_response.png was visually inspected. It shows all regional
T/P monthly curves and fixed observations clearly; use the spatial review
alongside North India's misleading mean improvement.15 combined forcing and
reference tests pass. All raw forcing and six capture/certificate/attempt
packets, independent review, spatial review and figure are retained under
output/surface_wind_diagnostic_20261127/. Worker16724 has exited.
W18c stays CLOSED, AA UNOPENED, r58 retained, atlas r51 unchanged. Future
calibration still requires a current-source paired reference.
