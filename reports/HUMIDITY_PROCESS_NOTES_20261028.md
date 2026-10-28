# Vertical humidity process notes — 28 October 2026

This is a research note, not an implemented atmospheric correction or a new
calibration result. Current native curves show high upper/lower humidity
ratios alongside a column-water deficit over North India. A ratio alone
cannot distinguish too little lower-layer water from too much upper-layer
water; reconstructing layer amounts from separate spatial mean ratios and
mean water would also introduce a nonlinear averaging error.

One physical boundary hypothesis merits a separately declared reference test:
current ocean targets partition total water using a saturation profile, which
corresponds to a vertically uniform relative-humidity shape before the
independent interior transport responds. Real marine relative humidity can
vary with pressure. This does not justify resetting solved interior humidity.

Manabe and Wetherald (1967), Thermal Equilibrium of the Atmosphere with a Given
Distribution of Relative Humidity, Journal of the Atmospheric Sciences24,
241–259, supplies a classical pressure-dependent tropospheric RH profile in
Eq.(2), printed page243. It decreases linearly with normalized pressure,
using surface RH0.77 and a zero crossing at p/ps0.02. The original paper
also specifies a stratospheric minimum mixing ratio, so a clipped tropospheric
shape alone would not reproduce that full radiative-convective model.

Primary paper, downloaded and title/method checked from its scanned pages:
https://www.gfdl.noaa.gov/bibliography/related_files/sm6701.pdf
PDF SHA256: 169b6b1907b42fdc13f66018dca9a567a358aa12ea4b561f16d6c5a9ea384dfe

A useful next step would compare uniform and pressure-tapered RH shapes on
the same cached native ocean thermal profiles, with observed humidity withheld
from construction. Keep temperature assumptions and footprint weights fixed;
report all regional and seasonal errors rather than requiring universal
improvement or selecting only favorable coasts. This is a reference/process
comparison, not independent new observations or a solved climate response.

A later coupled test must explicitly choose whether surface RH or total ocean
water is held fixed. Normalizing a tapered profile to preserve total water
can require excessive lower-layer RH; applying a fixed surface RH changes
column water. Those are different experiments, and must not be conflated.
Any mechanism must leave actual interior water independently solved and retain
numerical conservation, native errors and unchanged planetary settings.
