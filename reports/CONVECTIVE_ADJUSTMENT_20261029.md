# Conservative convective adjustment and closure sensitivity

The repeated pressure-coordinate model now has an explicit local convection
closure. It redistributes heat and vapor in unstable layers instead of capping
winds or deleting buoyancy. Each adjustment preserves actual water and gas
enthalpy; subsequent phase and rain export retain their enthalpy budgets.

The closure reduces the conditional stress case's remaining parcel energy,
but strong resolved winds and substantial timescale sensitivity remain. No
timescale is selected as calibrated or validated Earth physics.

## Activation and neutral targets

An adjacent pair is adjusted if it is dry-unstable, or if the lower cell is
near saturation and a lifted saturated parcel is warmer than the upper cell.
A 0.01 K neutral tolerance controls numerical chatter. Near-saturation uses a
1e-8 relative roundoff tolerance. An unsaturated, dry-stable column is not
adjusted merely because a finite lift could release its parcel energy.

For an active pair, vapor mixing ratio becomes the dry-mass-weighted common
ratio. Heat is redistributed toward a dry-neutral or saturated-neutral parcel
lapse. The dry target uses the actual vapor heat capacity; the saturated target
uses the independently checked pseudoadiabatic temperature-dependent latent
enthalpy and liquid saturation derivative. It is integrated on the actual
pressure interval, not specified by a fitted regional stability coefficient.

With the new common q, the lower and upper temperatures satisfy

    (cp_d+cp_v*q)*(Mlower*Tlower + Mupper*Tupper)
      = initial pair sensible enthalpy

The vapor latent-reference contribution is unchanged because pair water is
unchanged. A short fixed-point solve links this exact enthalpy constraint to
the neutral parcel lapse. Actual pair water and enthalpy are retained.

The full column then undergoes enthalpy-only liquid phase/fall adjustment.
Heat released or absorbed by phase and actual exported rain enthalpy are
included. Sweeps continue until no active adjacent pair remains, or an explicit
iteration budget is exhausted. An unconverged target is not accepted by the
coupled timestep.

This is instantaneous local adjacent mixing. It does not contain entrainment,
a plume mass-flux model, convective momentum transport or explicit turbulent
kinetic energy. Its irreversible mixing is a stated closure, not an identity
or a claim that every positive parcel-energy integral must disappear.

## Finite relaxation without unbooked heat or water

The experiment declares instantaneous, one-hour and three-hour adjustment
before comparing their results. For finite relaxation time tau, the adjusted
fraction is alpha=1-exp(-dt/tau). Water, gas enthalpy and actual target rain
enthalpy are blended with this same fraction. Temperature is diagnosed from
the blended water/enthalpy; it is not interpolated independently.

Homogenizing the mixture can change saturation, so its phase adjustment is
performed explicitly and any additional rain/enthalpy is recorded. A converged
neutral target can coexist with unstable layers in the partially relaxed
actual state. Target convergence and actual remaining active interfaces are
reported separately. The infinite-timescale limit recovers the unadjusted
model, while zero timescale gives the instantaneous target.

## Coupled integration and numerical limits

The existing coupled dynamics/enthalpy/vapor/phase timestep runs first, followed
by the conservative adjustment. This is a first-order operator split. The
nested dynamical momentum certificate applies before the adjustment; the final
pressure responds at the next timestep. No false claim of a post-adjustment
Crank-Nicolson midpoint solve is made. Combined final gas enthalpy, actual
face kinetic energy, ground rain enthalpy and water/source budgets are checked.

All three closure timescales use the identical prior conditional-moist initial
state and 300/150/75-second timesteps over six hours. Nine conditional runs
make 1512 new coupled steps. A 150-second saturated-stable control adds 144,
for 1656 new steps. The original unadjusted runs are reused as exact paired
baselines rather than recomputed with a changed source or thermal profile.

The research-atlas table and raw receipts retain every closure/refinement
outcome. Instantaneous adjustment substantially reduces remaining positive
partial-column parcel energy, but does not remove all positive energy or make
resolved winds automatically realistic. Finite timescales alter both rainfall
and circulation; wind response need not be monotonic with timescale. These are
parameterization sensitivities, not evidence that the lowest wind, largest
rainfall or smallest parcel energy is the correct climate solution.

The stable control receives no pair adjustments and matches the corresponding
unadjusted state to roundoff. This is a useful selectivity check, not geographic
validation. Time refinement remains distinct from closure-timescale choice.

## Verification and remaining Earth experiment

Eleven new tests check dry neutralization, saturated conditional adjustment,
unchanged stable and unsaturated controls, independent finer parcel targets,
actual water/enthalpy/rain, the split coupled budget, explicit nonconvergence,
finite relaxation, the no-adjustment limit and invalid controls. With the prior
282 checks, the focused suite passes 293 tests.

Independent publication reconstructs final gas enthalpy, actual face kinetic
energy, exported rain enthalpy, water, saturation and relaxation fractions from
raw fields. It verifies target convergence, numerical comparisons and the
unchanged stable control. Source hashes bind the original conditional/stable
inputs and the exact code used.

Before a useful regional Earth comparison, the reduced model still needs a
declared regional forcing/boundary setup and physical acceptance criteria.
The closure-timescale cases should remain visible rather than be selected
against this manufactured wind outcome. A bounded warm-region pilot can then
test rainfall and temperature under the documented approximations; it need not
wait for proof of a global calibration optimum or unanimous regional gains.

Inherited limits remain: fixed dry pressure mass and pressure bounds, zero
depth-mean flow, omitted water loading/gas-volume/potential effects, ice,
nonlinear momentum advection, terrain, radiation and prognostic surface
pressure. Convective momentum transport and entrainment remain separate missing
processes. This closure is experimental and not adopted into Earthr39 or the
normal world/biome/population atlases. No new Earth integrations or measured
rainfall-accuracy gains are claimed. Counters remain 1934 attempts / 1929 strict
passes / four historical failures / one historical interruption.
