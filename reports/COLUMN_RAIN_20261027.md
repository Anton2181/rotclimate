# Whole-column convection with independent layer water — 27 October 2026

The independent moisture reservoirs exposed a closure inconsistency. The
Bretherton-style empirical convection relation is a function of whole-column
humidity. Applying its convex exponential separately to two differently humid
layers can amplify rain without additional column water. The prior implementation
also evaporates upper-layer rain according to upper-layer humidity, although
that rain falls through the lower air.

The new opt-in `moisture_reservoir_rain_scheme='column-convection'` keeps the
local dynamical rain gate and supersaturation overflow in each layer, while
computing the empirical convective coefficient once from total column water.
The common coefficient multiplies actual layer water, so the convective total
recovers the original column relation, including its dry numerical floor.
Both layers' non-overflow rain share the original evaporation factor evaluated
on actual lower-layer humidity. Upper vapor loses its gross rain; the evaporated
fraction becomes a source of actual lower vapor. The equal and opposite internal
precipitation-transfer terms cancel in the column ledger. Lower local rain retains
its effective attenuation. Ground rain is the attenuated dynamic/convective
amount plus unattenuated local overflow. At the old
proportional humidity profile the original total ground-rain law is recovered
to roundoff. Individual layer losses change because evaporated upper rain now
enters lower air rather than remaining aloft.

No coefficient is fitted, and no water profile is reset. Winds, dry-air
continuity, donor vertical exchange, actual lower-air evaporation, calibrated
absolute capacity, normalized moist-profile capacity fractions, boundaries,
drying and conservative storms remain unchanged. This does not add explicit
parcel ascent, cloud entrainment, ice, latent-heat feedback or vertical energy.
The previously verified parcel calculation remains isolated.

The predeclared plan `calibration/column_rain_20261027/plan.json` runs42actual
Earth integrations over the same7development regions:28historical controls,
then14candidate cases (no extra mixing or the previous5day mixing). All historical
NPZ fields must reproduce exactly. Existing regional rainfall, temperature,
ocean, native-wind, dry-mass, branch-speed and humidity safeguards are retained.
Each layer and the summed-column equation must pass the unchanged residual
limits, including primer steps. The corrected closure must be certified at every
step and in all later full31/ocean/fine/established gates. Earth planetary
parameters remain locked, and fantasy-world qualification remains separate.

Status: complete; neither candidate qualifies.

## Completed Earth comparison

Source `69d2f8b`;42/42actual runs passed strict numerical checks, with28exact historical controls. Neither eligible candidate qualified, so no full31/ocean/fine/established stages ran and no adopted climate or headline changed.

| Closure | Combined error / r39 | Rain loss / r39 | Temperature MAE / r39 |
|---|---:|---:|---:|
|reservoir_control|1.17546|1.35486|0.99607|
|column_no_mix|1.13100|1.27291|0.98909|
|mixing_control|1.28217|1.52319|1.04114|
|column_mix5|1.19409|1.36480|1.02339|

The corrected no-mixing closure reduces aggregate rain loss by6.05% relative to its previous independent-water control; the mixed closure reduces it by10.40%. These are improvements over failed experimental profiles, not gains over adopted r39. The best corrected closure still has27.29% higher rain loss than r39 and fails protected Iberia, Japan, Mexico, Pacific Northwest and native vertical humidity.

| Region | Observed annual mm | Previous no mixing | Corrected no mixing | Previous5day mixing | Corrected5day mixing |
|---|---:|---:|---:|---:|---:|
|north_india|760.83|280.63|272.46|316.19|295.89|
|iran_plateau|232.39|225.71|212.69|316.50|293.42|
|iberia|391.83|821.67|737.34|1041.12|908.23|
|pacific_nw|897.46|2543.19|2394.06|2780.49|2590.60|

Each corrected candidate passes231primer/scored seasonal steps across7regions. Every layer and summed-column equation satisfies the unchanged0.01scaled tolerance; the signed internal precipitation transfer cancels exactly at every step.

| Corrected closure | Maximum internal re-evaporation mm/day | Maximum layer scaled residual | Maximum column scaled residual |
|---|---:|---:|---:|
|column_no_mix|3.35263|0.00999342|0.00999338|
|column_mix5|3.42099|0.00999516|0.00999619|

The largest recycled amount is a local seasonal-step extreme, not annual regional rainfall or newly created water. It is removed from upper vapor and added to lower vapor.

The ocean humidity guard remains useful: the no-mixing correction passes partial-water protection but still fails vertical-shape protection; the5day correction fails both. Ground-rain improvement therefore does not establish a realistic atmospheric profile. Explicit parcel cooling, entrainment, ice and vertical energy remain unresolved.

The next separately declared PNW audit compares native external winds and humidity, because excessive advective supply predates the reservoir changes. That audit reruns existing climates exactly; it does not tune them. The series after this42case experiment contains854actual Earth attempts,850passes and4preserved earlier failures.
