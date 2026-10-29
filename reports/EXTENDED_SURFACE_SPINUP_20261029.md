# Fourteen-day land-water initialization results

All six fixed integrations complete. Large rainfall, soil-water and land
temperature differences persist between wet and dry starts after fourteen days.
The first three days reproduce the six earlier coarse cases within the declared
tolerances. Every one of 84 daily saved water/energy budgets independently closes.

| Region | Start | Days 8–14 rain mm/day | Evap mm/day | Soil trend mm/day | Day 14 soil kg/m² | Day 14 surface K |
|---|---|---:|---:|---:|---:|---:|
| north india | wet | 1.993 | 2.050 | -0.064 | 38.55 | 302.41 |
| north india | dry | 0.450 | 0.146 | 0.326 | 3.29 | 307.05 |
| mexico | wet | 1.599 | 1.844 | -0.252 | 44.67 | 297.47 |
| mexico | dry | 0.388 | 0.186 | 0.216 | 5.09 | 301.18 |
| pacific nw | wet | 1.096 | 1.591 | -0.491 | 35.62 | 290.71 |
| pacific nw | dry | 0.004 | 0.014 | -0.009 | 0.23 | 294.15 |

Soil trends are linear slopes over the fixed seven-day window, not an assumed
steady flux balance. Dry India and Mexico are still gaining water; wet cases
still lose some. Pacific Northwest dry land has very little available liquid.
This establishes persistent initialization sensitivity, not multiple equilibria.
Solar forcing advances seasonally and lateral initial-state reservoirs remain
fixed. Fourteen days does not establish a stationary climate.

The wet state was inherited from the original 50 kg/m² baseline; the dry state
starts at zero, before common initial conversion rain is returned. The water
changes both evaporation and heat capacity. Initial atmospheric fields and
temperatures are common, but total initial energy is not. No state was selected
because of its rainfall, and no climate parameter was optimized.

The plans were committed in `e133bb19` before integration. All daily fields,
scalar histories, raw source hashes and both literal plans are retained in
`output/extended_surface_spinup_{wet,dry}_20261029`. Downloads include days 3/7/14
gaps, spatial rain RMS differences and all initial/daily arrays. The qualified
fast phase and exact-factor backend preserves the same physical equations.

Maximum reconstructed daily total energy relative error is 2.258e-14;
water relative error is 5.047e-16. These checks independently
reconstruct saved gas + kinetic + surface energy and atmospheric + surface water
against the recorded external supplies. They do not independently validate the
flux laws. Daily surface evaporation is rain minus change in surface liquid.
Net horizontal column water input is change in atmospheric plus surface water.
Neither identity attributes water to a geographical source.

For calibration, these results rule out treating a three-day or fourteen-day
spinup as sufficient to erase guessed soil water in this setup. Future scores
need a declared initialization ensemble or substantially longer spinup and a
fixed evaluation window. A mean objective may allow regional tradeoffs, but it
cannot resolve this uncertainty by selecting whichever starting state rains more.

The next declared experiment tests lower-cell grid resolution and timesteps.
The original exchange reference height was about 750 m; conservative static
refinement prepares heights near 175 m and 43 m without changing pressure mass
or supplying energy/water. Nine 24-hour dynamic controls are frozen separately.
Their outcome will diagnose flux geometry and numerical sensitivity, not measure
monthly rainfall skill. Flat terrain, partial upper atmosphere, neutral exchange,
liquid-only thermodynamics and omitted nonlinear momentum remain limitations.

The six completed cases bring the separate prototype record to 93 starts /
89 completions /four retained earlier numerical failures. Legacy 1934/1929 and
Earth r39 remain unchanged. There is no new rainfall accuracy score, physical
adoption or recalibration. All normal world/biome/population fields are unchanged.
