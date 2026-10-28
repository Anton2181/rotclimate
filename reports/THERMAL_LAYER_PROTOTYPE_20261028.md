# Thermal shear with conservative layer winds — prototype history

Continuation: the common-pressure construction and default-off coupled path are
now implemented. The initial isolated milestone below is retained as history;
see THERMAL_WIND_PILOT_20261028.md for the new paired experiment declaration.

The completed six-case transport diagnosis found large errors in the vertical
wind structure. In particular, PNW eastward wind weakens between the modeled
lower and upper branches while the reference increases substantially with
height; India's modeled summer lower eastward flow is missing and upper
meridional flow has the wrong sign. Changing ocean humidity scarcely changes
those winds. See [the diagnosis](TRANSPORT_DIAGNOSIS_20261028.md).

The new `rotclimate/thermal_layer_winds.py` is an isolated physical operator,
not yet selected by the coupled model. It does not constitute a calibrated
rainfall improvement, introduce an atlas climate or add Earth integrations.
No existing physical source or default pathway changes.

## Two constraints rather than an algebraic upper return alone

The current dry layers contain25% and75% of column mass. Their pressure
centroids are0.875ps and0.375ps; their ratio is7/3, fixed by that geometry.
With a supplied common-pressure layer-mean temperature, hydrostatic/geostrophic
thermal wind gives the upper-minus-lower wind difference:

    Delta U = Rd ln(7/3) [f/(f²+f10²)] k cross grad_p(Tbar)

Rd is287.05J/(kg K). The existing smooth10-degree equatorial regularization
is retained explicitly; it also damps midlatitude shear and does not solve
equatorial momentum. The temperature gradient is assumed approximately
constant over the pressure interval. This remains a two-box representation,
not a vertically resolved atmosphere.

The desired upper flow equals the desired lower flow plus this shear. Project
their dry-mass-weighted mean using the existing stationary column-mass
projection, then apply the same velocity correction to both layers. A common
correction preserves the prescribed wind difference while making the total
dry divergence vanish on the exact arithmetic faces. It minimizes the total
dry-mass-weighted squared velocity correction under those two constraints.
Open-border velocities may change. Actual humidity and an imposed upper/lower
q ratio never enter this construction. Layer convergence and donor water
exchange remain necessary even when column dry divergence is zero.

## What is verified

Nine isolated tests cover analytic linear-temperature thermal-wind signs and
spin reversal; exact uniform-temperature/equatorial limits; dry continuity
and shear preservation over tilted terrain; steady transport of uniform
specific humidity with nonzero layer exchange/diffusion; the minimum-correction
property against alternative admissible divergence-free flows; and invalid
input rejection. These are manufactured operator tests, not Earth climate runs.

## Required before coupling

Construct the temperature gradient on common pressure surfaces from the model's
thermal state. Differentiating a raw terrain-cooled surface temperature or a
sigma-surface temperature would introduce a spurious terrain term. This input
construction needs its own hydrostatic/terrain invariance checks. The common
projection may materially alter lower winds and does not separately solve
frictional momentum or energy; examine its size, boundary changes and feedback
when a coupled pilot is declared. A better isolated shear does not prove that
rainfall, temperature or native humidity will improve.

Keep Earth orbit, gravity, rotation, dry-air constants and the fixed pressure
geometry unchanged. No observed wind forcing, region-specific multiplier,
independent regional calibration or broad parameter sweep belongs in that
first test. Freeze a new source transition, common-pressure temperature law,
small paired climate cases and success criteria before any integrations.
Rainfall remains primary; report all temperature, atmospheric-state and
regional tradeoffs, including failures. Existing r39/adopted atlas data remain.
