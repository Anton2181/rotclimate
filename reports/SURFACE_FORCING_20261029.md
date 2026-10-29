# Day-long surface/radiation coupling — 29 October 2026

All twelve declared24-hour runs completed. Sustained forcing increases rainfall
over interior land in all three test regions and reduces the perimeter's share
of rainfall relative to the unforced controls. This is a physical response,
**not measured rainfall accuracy**. The land surface also cools substantially,
and local rainfall remains timestep-sensitive. No configuration is adopted.

The setup was committed in `2aeab87` before integration. The new conservative
[flux kernels](COLUMN_FORCING_INTERFACE_20261029.md) and
[finite-surface coupling](SURFACE_COUPLING_DECLARATION_20261029.md) have a combined
focused suite of356 passing tests. Initial atmosphere, source-model winds,
surface reservoirs and lateral conditions match within each forced/unforced pair.
No observed temperature, wind, humidity or rainfall is an input.

## Finer-step24-hour result

| Region | Forcing | Regional mean rain mm | Land mean rain mm | Interior-land mean rain mm | Rain at perimeter |
|---|---|---:|---:|---:|---:|
| North India | none | .505 | .037 | .000 | 71.6% |
| North India | surface/radiation | 1.453 | .853 | .331 | 67.8% |
| Mexico | none | .561 | .915 | .308 | 72.7% |
| Mexico | surface/radiation | 1.273 | 1.819 | .870 | 57.9% |
| Pacific Northwest | none | .087 | .006 | .000 | 94.2% |
| Pacific Northwest | surface/radiation | .729 | .395 | .030 | 64.6% |

The earlier six-hour edge-rain result describes startup, not a steady climate
pattern. Even the unforced India control reaches0.50 mm after a day with28% of
rain inside the perimeter. Future skill comparisons should separate spinup
behavior from later rainfall; the first hours alone are not a monthly climate
acceptance test. Numerical and physical-domain checks still apply at every step.

## Surface and numerical response

Forced regional net evaporation is6.07/3.42/4.84 kg/m² over the day. Land surface
temperature changes average−3.37/−1.39/−3.50 K, while ocean temperatures average
+.057/+.127/+.069 K. Maximum local surface changes are10.77/4.61/11.90 K.
Every surface remains above279 K in these cases. These differences reflect the
finite heat/water reservoir and the declared uniform initial land liquid storage;
they do not establish realistic soil moisture, surface fluxes or climate balance.

Atmospheric temperature RMS differences between900 and450 s are .0763/.0736/
.0607 K; surface-temperature RMS differences are .0213/.0365/.0105 K. Rainfall
RMS differences are .300/.397/.178 mm. Regional totals can agree more closely
than the spatial rainfall pattern, so point rainfall is not declared converged.

## Actual energy and water accounting

Surface enthalpy contains substrate heat and actual liquid heat capacity.
Evaporation/dew transfer complete vapor enthalpy and water, and sensible heat
is equal and opposite between air and surface. Local liquid phase adjustment
and pressure-dynamics/convection rain both return mass and actual liquid
enthalpy exactly once. Pending rain is cleared in the returned atmosphere;
the separate rain diagnostic remains available for maps and accumulation.

The independent publisher reconstructs saved gas + kinetic + surface energy
and atmospheric + surface water against the separately recorded net radiation
and lateral supply. This is an accounting check, not a second flux solver.
Maximum relative errors are2.69e−15 for energy and2.92e−16 for water. The separate
surface identity `change in liquid = returned rain −net evaporation` closes
to4.64e−13 kg/m². Initial pressure-transfer rain is credited before the run
and excluded from plotted run rain.

## What the driver assumes

Daily-mean Earth-orbit sunlight enters after prescribed outside reflection and
upper-air attenuation. Grey longwave depth has explicit dry and vapor terms;
vapor opacity responds to simulated water. There is no temperature restoration
or rainfall-target fit. The380 hPa top is a partial regional boundary supplied
by an externally maintained omitted upper-air emitter; it is not called TOA.
The domain is open to declared lateral mass, moisture and energy fluxes.

Surface liquid starts at50 kg/m² on land and10000 kg/m² over ocean, plus the
returned initial pressure-conversion rain. Substrate heat capacity, land/ocean
albedo and roughness are fixed declared inputs. Neutral exchange uses the actual
pressure-derived reference height, not a10 m coefficient applied to a deep cell.
Grey opacities, storage and neutral roughness are exploratory assumptions, not
measured Earth fluxes or inferred soil moisture. Clouds/spectral scattering,
stability/gust corrections, ice, runoff, deep-ocean supply, terrain and nonlinear
momentum remain absent.

## Next comparison

A short sensitivity to initial land water and a longer spinup should distinguish
the imposed wet land reservoir from a sustained rain/evaporation cycle. A wet
baseline needs a timestep comparison; a coarse dry-land branch can screen initial
condition sensitivity. Longer runs must retain all failures and report their
actual averaging window. They must not be called monthly calibration or judged
solely by greater rainfall. This is a proposed next experiment, not a completed
outcome or a claim that the initial-state uncertainty is solved.

The separate prototype record is now **66 starts /62 completions /four retained
numerical failures**. Legacy benchmark counts remain1934 attempts /1929 strict
passes /four historical failures /one interruption. Earth r39 and all normal
world, biome and population fields remain unchanged. The `.bat`-served research
atlas includes the two figures, all outcomes, raw states and the frozen plan.
