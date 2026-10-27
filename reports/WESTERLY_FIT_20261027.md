# Shared westerly-amplitude comparison — 27 October 2026

The Pacific Northwest reference audit found excessive eastward moisture winds
in four eligible native ocean footprints. This experiment tests whether a
smaller globally shared background westerly amplitude reduces that bias without
sacrificing monsoon delivery, temperature, ocean state or humidity structure.
The amplitude is not an observed column speed: it sets the peak background belt,
its fixed0.15poleward component and its fixed seasonal modulation, before terrain
drag, temperature-driven pressure winds, thermal shear and mass projection.
Coupled temperatures, sea state, circulation and water can respond.

The frozen plan `calibration/westerly_fit_20261027/plan.json` declares exactly
three amplitudes:5.0,6.25and7.5m/s versus the current8.76025m/s. These are within
the existing shared2–12m/s calibration bounds. Planet, other wind coefficients,
corrected rain/recycling law, independent no-mixing moisture, capacities, boundary
humidity, land/ocean exchanges, drying and storms remain fixed. There is no
regional coefficient, humidity reset, imposed observed wind or planetary retune.

Forty-two actual coupled Earth runs cover the same seven development regions:
21historical controls (r39, fixed-profile transport, corrected no-mix), then
21candidate cases. All archived control arrays must reproduce exactly. The new
PNW native diagnostic lives in JSON so it cannot change old NPZ fieldsets; r39
must also reproduce the independent native-vector audit exactly.

All original local rainfall/temperature, ocean, wind, humidity, branch/mass and
layer-equation safeguards remain. Added PNW guards require at least10% lower
native partial-column vector RMSE versus the corrected control and no more than
2% worse partial water or vertical-shape MAE. Footprints and areas must match.
The four ocean footprints remain a small, reused, model-assisted development
sample, not global or land circulation validation. The reference is925–300hPa
whereas modeled wind diagnoses the whole moisture column; transient covariance,
coarse geometry and different climate-normal periods limit interpretation.

This stage has no automatic promotion. Any screening qualifier requires a new
frozen full31/ocean/fine/established comparison preserving all original release
guards and repeating PNW circulation/humidity at56/28km before adoption. Fantasy
world transfer remains separate. No headline or normal atlas climate changes
on the basis of a seven-region screening score.

Status: declared before new amplitude scores; no candidate outcome yet.
