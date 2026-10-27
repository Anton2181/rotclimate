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

Status: declared before new Earth candidate outcomes; results pending.
