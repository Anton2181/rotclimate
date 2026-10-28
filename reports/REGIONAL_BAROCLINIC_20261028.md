# Regional dry circulation: mass weights, walls and passive boundaries

The new `rotclimate/regional_baroclinic.py` extends the isolated circulation
foundation to a rectangular regional domain. It does not change the coupled
Earth model, its parameters, rainfall scores, atlas climates or calibration
counter. The previous periodic operator remains untouched so its published
verification can still be reproduced.

## Equations and mass weights

For positive cell dry-column mass M, constant mode speed c, positive momentum
and thermal damping r and rT, the model solves

    r U + Coriolis(U) + grad(phi) = 0
    c² div(M U)/M + rT phi = Q

Rows increase southward. U occupies internal east/south faces; phi and Q are
cell-centered geopotential anomaly and modal heating (m²/s² and m²/s³). M may
be relative column mass or kg/m²; changing its units leaves the solution and
per-mass budgets unchanged. Internal face mass is the arithmetic mean of the
two neighboring cells. Exterior face mass is the adjacent cell value.

Let G be the cell-to-internal-face difference gradient, W the diagonal face
mass, and M the diagonal cell mass. Conservative divergence is
`-M^-1 G^T W U` plus explicit exterior fluxes. The solved unknowns are
`sqrt(W) U` and `sqrt(M) phi/c`. Thus the pressure and transport blocks are
`A=c sqrt(W) G M^-1/2` and `-A^T`. This adjoint relation prevents spurious
pressure work over a column-mass gradient.

Each cell contributes `M*f/4` to every pair of incident internal east and south
faces. Square-root face mass scaling makes this rotation block skew by using
its negative transpose in the other momentum equation. Coriolis therefore
does no discrete mass-weighted work even when both mass and rotation vary.
Missing exterior velocities are zero in the rotation interpolation. At passive
edges their diagnosed normal velocities are not included in this interpolation;
that is an explicit boundary approximation, not an exact rotating wave closure.

## Boundaries and energy

Each edge can be a wall (zero normal velocity, the default) or a passive
impedance. The latter imposes outward normal velocity `Un=phi/c`, using the
adjacent cell pressure. It corresponds to a zero incoming normal characteristic
in the nonrotating, locally one-dimensional wave limit. It is first order at
the edge and not transparent for arbitrary oblique or rotating waves. It has
no imposed incoming circulation, so it is not yet a substitute for the actual
regional Earth's lateral state. Exterior velocity has no momentum degree of
freedom or kinetic storage in this reduced operator.

The impedance adds a positive thermal damping diagonal `c/dx` per open edge.
At corners both face contributions are counted. Every solve verifies

    sum(M phi Q/c²) = r sum_internal(W U²)
                      + rT sum(M phi²/c²)
                      + sum_passive_faces(M phi²/(c dx))

Rates are reported divided by total cell mass. Boundary export is nonnegative;
a wall exports zero. Integrated thermal forcing balances relaxation plus
boundary mass flux. This is the dry *modal* energy budget, not a full atmospheric
radiative/latent budget. Positive drags and passive boundaries give a positive
definite symmetric part and hence a unique steady linear solution. This removes
an optimizer/local-minimum issue for this particular linear circulation solve;
it says nothing about global uniqueness of the nonlinear climate calibration.

## Two-layer continuity

For constant lower/upper mass fractions a and 1-a, the helper embeds the mode
as `Ulower=-(1-a)U`, `Uupper=aU`. Dry column flux cancels at every interior and
exterior face. Required upward exchange per local total-column mass is
`a(1-a) div(M U)/M`; it cancels each layer's horizontal mass convergence.
Positive values take dry air upward from the lower layer. This is a diagnosis
only: no water is moved, and heating is never treated as external air injection.
Varying layer fractions, a barotropic background and transport of actual donor
water require separate conservative coupling.

## Validation

Seventeen regional tests cover both axes' analytic closed-box eigenmodes,
an independently manufactured variable-mass pressure/flux solution, a resting
state over a large mass gradient, independent mass and energy budgets with
three boundary combinations, invariance to column-mass units, local/two-layer
and exterior dry continuity, first-order convergence to the continuous Robin
Helmholtz solution at 12/24/48 cells, and invalid inputs. Together with the
existing periodic operator these are 26 tests. They use known equations and
independent face budgets rather than rainfall-fitting targets.

The manufactured comparison script `scripts/demo_regional_baroclinic.py`
compares flat/wall, variable-mass/wall and variable-mass/passive configurations
under identical prescribed forcing. Its resolution check changes the mesh,
not the physical domain or forcing. This is an operator check, not an Earth
benchmark integration or evidence of improved rainfall.

The fixed 200/100/50 km comparison reduces RMS geopotential difference against
the 50 km solution from 1.114 to 0.379 m²/s² (relative RMS 11.46% to 3.88%).
The independent modal energy residual stays below 5.3e-15 relative across all
three configurations, with zero diagnosed total-column face velocity residual.
These are numerical consistency results, not climate accuracy percentages.
The focused suite including earlier thermal and moisture components passes
104 tests. Zero additional Earth integrations were run; cumulative counts stay
1934 attempts / 1929 strict passes / four historical failures / one historical
interruption.

## Remaining physical work

Variable mass is only one aspect of topography. This model has no terrain
metric, terrain-dependent vertical eigenmode, mountain blocking, spherical
geometry, background-flow advection, time-dependent moist thermodynamics or
convection. Its mode speed and damping are fixed demonstration scales, not
calibrated atmospheric constants. Physical modal heating must be projected
from an explicit atmospheric energy budget; a surface temperature contrast is
not itself a heating rate. Treating the current surface energy-balance output
as atmospheric heating without that accounting would invent energy.

Next: donor-conservative moisture exchange and physical forcing accounting,
then a bounded and separately declared coupled Earth experiment. Any acceptance
must still use location/month rainfall loss with regional tradeoffs allowed,
temperature and physical constraints, excluded regions and resolution checks.
No search result or numerical conservation certificate establishes a global
climate optimum. Earth r39 and all normal world/biome/population climates stay
unchanged until a coupled result passes those checks.
