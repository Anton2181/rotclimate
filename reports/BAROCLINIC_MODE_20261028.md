# Forced dry baroclinic mode — isolated architecture prototype

The rainfall mechanism sequence motivates moving beyond prescribed thermal
shear and kinematic projections. The new isolated operator solves coupled
steady momentum and thermal-thickness adjustment on a periodic staggered grid:

    r*u + F*v + grad_x(phi) = 0
    r*v − F_transpose*u + grad_s(phi) = 0
    c²*div(U) + rT*phi = Q

Rows point south; v here is southward, opposite the existing model's map-up
v. U lives on cell faces and phi is a cell geopotential anomaly. Q is modal
heating in m²/s³, not external dry mass injection. c is a dry mode gravity-wave
speed, r momentum damping and rT thermal relaxation. This is a linear dry
shallow-water/baroclinic mode; it is not yet a coupled planetary atmosphere.

The Coriolis operator is skew and the discrete gradient/divergence are negative
adjoints. With positive damping, the symmetric matrix part is positive and
the steady solution is unique. The actual discrete modal energy identity is

    mean[r*(u²+v²) + rT*(phi/c)²] = mean[phi*Q/c²]

This is energy input/dissipation per reference modal mass, not a whole-atmosphere
radiative or latent-energy budget. Constant-depth flat periodic geometry is an
isolated mathematical limit. Variable rotation is supported with skew paired
interpolation, but periodic north/south wrap is not an Earth boundary treatment.
The implementation deliberately does not select an Earth climate or tuning set.

Nine tests verify independent discrete Fourier solutions with zero/positive/
negative Coriolis, uniform heating, variable-rotation energy and integral thermal
balance, heating-driven lower convergence, mass-balanced opposing layer winds,
and invalid input rejection. The heating example has c=50m/s (equivalent depth
about255m), Earth rotation at30°N, momentum damping5days and thermal relaxation
20days. These are fixed manufactured-example scales, not fitted climate results.
Its modal energy identity closes to1.5e-15relative and thermal equations to about
1.8e-16m²/s³. It generates a convergent lower response and opposing upper return.

Embedding shear mode U as lower=−0.75U, upper=+0.25U cancels the total dry-column
velocity pointwise. A later implementation must still couple actual layer dry
mass, donor water exchange and any barotropic background conservatively. The
heating/cooling term in the thermal mode must not be mistaken for a source of
planetary air mass. No regional ClimateModel.run or Earth benchmark integration
is added by this prototype.

Before a coupled pilot: define physical heating and mode projection in consistent
energy units; supply regional open/terrain boundary conditions and conservation
checks; choose fixed Earth-like mode/damping priors; verify known flow limits
and numerical resolution; then predeclare a bounded climate comparison. Do not
use observed winds or rainfall as interior forcing or choose these constants
by looking at regional gains. Existing atlas climates remain unchanged.
