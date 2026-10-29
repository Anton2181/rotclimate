# Fourteen-day wet/dry initialization experiment

The three-day experiment still shows large differences in rainfall, surface
water and land temperature between wet and dry starts. Wet surfaces are losing
water; dry surfaces are gaining some. Neither run yet establishes a settled
climate. Selecting the wetter initialization because it rains more would risk
fitting startup water rather than improving physics.

Two literal plans in `calibration/extended_surface_spinup_20261029` extend the
same forcing and physics to fourteen days, starting again from the same initial
atmosphere and surface temperatures. Wet land starts with 50 kg/m² water and dry
land with zero, before the common conversion rain is returned. Water changes
both available evaporation and heat capacity; these are not equal-energy states.
Each plan has three regions and one 900-second timestep: six new integrations.
The qualified fast phase solver and exact transport factor reuse reduce cost
without retuning parameters. All six preflight preparations pass.

Daily arrays and cumulative water/energy supplies are saved. The first three
days must match the earlier coarse wet/dry archives within the fixed tolerances
in the plans. Analysis will compare day 3, 7 and 14 gaps, spatial differences,
days 8–14 rainfall means and soil-water trends. Every daily saved energy/water
budget will be reconstructed independently. Evaporation follows from rainfall
minus change in surface water; whole-column net horizontal water import follows
from change in atmospheric plus surface water. These identities do not identify
the geographical origin of rainfall water.

The experiments always attempt their full declared duration. Domain violations,
failed iterations and partial results are retained without replacement, clipping
or altered parameters. No initialization is selected by a rainfall score. There
is no claim that fourteen days is sufficient: solar forcing advances seasonally,
lateral initial-state reservoirs stay fixed, and the upper boundary remains an
externally supplied partial column at 380 hPa. Other unresolved approximations
include flat terrain, neutral exchange using a deep first air cell, liquid-only
thermodynamics and omitted nonlinear momentum.

No outcome from these longer integrations is known in this declaration. Six new
starts would move the separate prototype record from 87 starts /83 completions /
four retained earlier failures to 93 /89 /four if all finish. Legacy 1934/1929,
Earth r39 and normal atlas fields remain unchanged. No monthly rainfall accuracy,
recalibration, global optimum or physical-model adoption is claimed.
