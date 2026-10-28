# Stable separation of surface and atmospheric thermal patterns

This is the second bounded thermal-structure mechanism test, following the
failed single-pattern profile. It does not fit regional parameters or alter
Earth constants. The previous India comparison suggested that a single thermal
pattern misses a reversal in the meridional gradient aloft; that development
sample motivates the hypothesis and is not new independent validation.

At fixed absolute pressure sigma=p/101325Pa, prescribe

    T(p) = max([B + (A−B)*sigma^a]*sigma^k, 200K)
    k = Rd*Gamma/g, nominal a = 1/[-ln(0.75)]

A is the modeled common-height Tsl interpreted at101325Pa. B is the existing
modeled zonal EBM temperature reference, interpreted at the same pressure.
Both fields are smoothed at500km. The nominal e-folding pressure depth derives
from the existing25% lower dry-air mass layer; it is not searched or tuned.
The environmental Gamma stays6K/km. The background is a zonal proxy for the
free atmosphere, not a separately solved vertical energy field or observed
forcing. Height-dependent local anomaly decay allows gradients to change
direction with height. This is an opt-in diagnostic law for wind shear;
saturation, rainfall, surface energy and water reservoirs retain their laws.

For a warm anomaly Delta=A−B>0, limit a to

    a <= (Rd/cp−k)*A/Delta

This guarantees dlnT/dlnp<=Rd/cp at all pressures up to the reference level;
the corresponding lapse never exceeds g/cp (about9.77K/km). Cold anomalies
are stable without this upper bound. The floor is isothermal and stable.
This is a prescribed stable profile, NOT an energy-conserving convective
adjustment or a claim that actual radiative/latent energy was solved. The
state-dependent exponent follows the same physical law everywhere; it is
never fitted by region. The fixed default-off flag is
`moisture_thermal_anomaly_decay=False` and requires thermal layer winds.

Take pressure-coordinate partial derivatives of the two references (including
the derivative of the stability bound) before integrating between local dry
mass centroids. Resolve the floor interval, including cold inversions with
two crossings, then use16-point Gaussian quadrature. The same conservative
wind projection and actual water donor exchange remain. Both earlier toy
climate modes are bit-exact with the new flag off.71 focused tests pass:
static stability/extreme anomalies, independent finite derivatives and pressure
quadrature, hypsometric lapse, gradient reversal, floor crossings, terrain
invariance, shared parameter validation, default equivalence and strict coupled
water/dry ledgers. Toy checks add no Earth benchmark integrations.

## Literal experiment before outcomes

18 actual regional runs: three regions (India, Mexico, PNW) ×two fixed ocean
settings (legacy, hydrostatic half) ×three wind modes (original, single-pattern,
stable separated). Run12 exact historical controls first, then6 new cases.
The controls reproduce every prior climate field and extra PNW native array;
actual parameters/case hashes are bound to each archive with only the new
flag made explicit. Freeze the three existing changed core files and all new
profile/runner/test/reference sources before any integrations. Record all
failures. No new forcing or observations are fetched for this experiment.

Success remains mean paired regional rainfall-loss ratio<=0.95 against the
ORIGINAL wind controls, plus mean monthly temperature MAE increase<=0.25C.
The failed single-pattern cases are explicit context, not an easier baseline.
Expose all regional tradeoffs without individual rain-score vetoes. Require
strict water and dry continuity, dry static stability, every primer/scored
certificate and branch speeds<=80m/s without velocity clipping. A wind score
improvement is not a substitute for rainfall improvement. No automatic atlas
adoption, independent validation claim or broad optimizer restart follows.

Before:1898 actual attempts,1893 strict passes,4 historical failures and1 old
interruption. This experiment permits18 new attempts (maximum1916 cumulative).
If this second well-tested hypothesis fails to give material rainfall gains,
stop adjusting these temperature/shear forms and reassess the circulation/
energy architecture. Any later adoption requires excluded-region, resolution
and world-transfer checks. Keep observed cloud/remote-monsoon backgrounds and
all approximations explicit. Normal atlases remain on the adopted climates.
