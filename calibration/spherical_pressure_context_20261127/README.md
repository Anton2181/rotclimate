# Whole-planet pressure-filter reference prototype

This is a next-direction prototype, not a climate candidate, parent climate
prediction, adopted operator, or demonstrated solution to the Somali jet.

The zero-exterior pressure experiment failed its coupled guards. The new
direction explicitly supplies a whole-planet thermal-anomaly field rather than
inventing its unknown exterior from a regional crop. Its small-grid reference
operator uses great-circle Gaussian lengths, exact spherical cell areas and
periodic longitudes, retaining the existing two-scale pressure algebra and
hPa/K to Pa conversion. All coefficients are explicit inputs; none are fitted.

Five known-answer geometry/operator tests pass: spherical area4*pi and constant
pressure; longitude rotation/hemisphere reflection; broad-limit area-weighted
mean (not unweighted pixel mean); and a remote heat low whose anomaly is zero
inside a regional crop but whose pressure gradients reach that crop. A smooth first spherical harmonic
also converges toward its independently integrated continuum-kernel eigenvalue:
maximum absolute errors0.0075592,0.0021335,0.0005463 on8x16,16x32,32x64
grids (2500km Gaussian). This one-mode result is not an all-scale convergence
certificate.

Source experiments/spherical_pressure_context.py deliberately limits dense
quadrature to2048 cells. It is a reference for later scalable implementation,
not an efficient production globe. Finite latitude-longitude quadrature has
resolution/orientation error: longitude shifts and hemisphere reflection tests
do not establish invariance under arbitrary3D rotations or all-field continuum convergence.
Row normalization preserves constants, not a certified conservative transport.

No real global anomaly field has been constructed. No parent temperature or
momentum is solved, regional forcing replaced, climate integrations performed,
wind/rain skill scored, candidate selected or model source changed.
The solar-bound97-region experiment remains separate and immutable.

Before a coupled candidate: specify how the parent thermal field is predicted
without regional observations; demonstrate resolution convergence and sampling
across nested domains; establish scalable/reference agreement; then declare
fixed coupled evaluations and controls. Passing this toy prototype is not that
evidence. In particular, a static EBM+landmask estimate is only a possible parent
hypothesis, not the missing actual atmosphere. W18/W18c closed; AA unopened.
