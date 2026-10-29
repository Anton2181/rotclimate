# Conservative transfer for lower-atmosphere resolution checks

The current lowest atmospheric cell spans approximately 1013–855 hPa. Its
surface-exchange reference height in the India archive is 730–773 metres.
Applying neutral exchange at the actual cell height avoids a false 10-metre
coefficient, but the cell remains too coarse to resolve a surface layer. A
controlled vertical-resolution experiment is a useful next physical check.

The new pressure-overlap operator transfers cell-integrated vapor and gas
enthalpy conservatively between grids sharing the same top and bottom pressure.
It reconstructs the source as piecewise constant, then performs target-pressure
phase adjustment. The caller must return conversion rain and its actual liquid
enthalpy to the surface. This conversion is distinct from rainfall during a run.

Mass-weighted velocity transfer conserves vertically integrated momentum.
Coarsening loses resolved kinetic variance, exposed as a separate signed energy
quantity without assuming conversion to heat. Piecewise-constant refinement
preserves kinetic energy up to roundoff. The eight new tests cover arbitrary
overlaps, reversible refinement, constant concentration, pressure lids, momentum,
kinetic variance, rain enthalpy and fast/reference phase equivalence. A focused
86-test suite passes. Existing frozen physics sources remain unchanged.

The literal static protocol in `calibration/pressure_grid_remap_20261029` declares
four-way and sixteen-way subdivisions of only the first old cell in each of
three saved initial Earth-input arrays. Six static transfers start **zero new
climate integrations**. The transfer checks pressure mass, water plus returned
rain, gas/surface/kinetic energy, face momentum and refinement kinetic energy.
Tolerances and inputs are fixed before outcomes; failures must be retained.

No outcome from these six static cases is known in this declaration. No new
subcell lapse is invented: a constant source cell becomes constant subcells
before target phase. The resulting atmosphere is not promised to be balanced.
Neither hydrostatic force changes nor rainfall skill can be assessed from this
static audit. Subsequent dynamic grid comparisons will require a separate frozen
protocol and spin-up treatment. Earth r39 and normal atlas fields stay unchanged.
The ongoing fourteen-day wet/dry experiment is independent of this new module.
