# Parcel cooling and condensation — 26 October 2026

The independent seasonal humidity experiment improved some rainfall errors but
left too much moisture aloft and failed regional and humidity protections.
This follow-up tests a missing process in isolation: cooling and condensation
while air rises, before it enters a broad upper reservoir. It changes no
seasonal climate, atmospheric forcing or atlas climate packet.

Source `fc91ae4`; plan `calibration/parcel_ascent_20261026/plan.json` was frozen
before the manufactured outcomes. Exactly18initial/endpoint combinations use
285/300K, actual vapor-pressure RH30/60/90%,1000hPa starting pressure and
750/500/300hPa endpoints. Each runs64/128/256steps; all54numerical paths passed.
The18cases are manufactured parcels, not54Earth climate integrations.

## Consistent approximate thermodynamics

Dry gas uses Rd287.05J/(kg K), cp1004J/(kg K), constant Lv2.5MJ/kg, and the same
Bolton liquid saturation law as the column implementation. Below cloud base,
T=T0(p/p0)^(Rd/cp), with unchanged vapor mixing ratio. A root locates where
this dry path first reaches saturation, avoiding numerical condensation before
the lifting condensation level (LCL).

Above the LCL, write x=ln(p0/p), r=epsilon*es/(p-es), and
C=r*(1+r/epsilon). The actual Bolton derivative D=dln(es)/dT gives

    dT/dx = -(Rd*T + Lv*C)/(cp + Lv*C*D)
    dwork/dx = Rd*T
    dr/dx = C*(1 + D*dT/dx)

This directly satisfies cp*dT+Rd*T*dx+Lv*dr=0 in the declared dry-gas,
constant-cp/Lv approximation. Using an unrelated saturation derivative with
Bolton humidity would leave an avoidable first-law discrepancy. RK4 integrates
both temperature and pressure work; the saved residual uses the actual endpoint
saturated mixing ratio. There is no artificial200K isothermal heating floor.

Vapor and immediate condensate are expressed per kilogram of conserved dry air:
r_initial=r_vapor+r_condensed. Specific humidity q=r/(1+r) is per kilogram of
changing moist air. Subtracting initial/final q values would give an incorrect
parcel condensation ledger. Initial RH is es_actual/es_saturation, rather than
q/q_sat. These convention differences are explicitly tested.

## Results

Every path has nonnegative monotone condensation and passes the unchanged
predeclared checks. Maximum water residual is3.47e-18kg/kg dry air. Maximum
first-law residual is4.17e-5J/kg dry air versus the declared0.01limit. Maximum
64/128versus256step endpoint temperature difference is3.30e-8K, below1e-5K.
Ten unit checks separately cover analytic dry cooling/work, no condensation
before LCL, the exact dry/dewpoint intersection, mass conventions, saturated
starts, null displacement and rejected unsupported states.

For the fixed300K warm-parcel examples:

| Initial RH | LCL hPa | Condensed at750hPa | At500hPa | At300hPa |
|---|---:|---:|---:|---:|
|30%|756.0|1.69%|68.22%|97.21%|
|60%|884.4|21.73%|65.83%|94.71%|
|90%|974.5|25.68%|60.29%|89.82%|

Percentages are fractions of initial vapor per conserved dry-air mass; warmer
moister parcels also release more absolute water and cool more slowly after
saturation. The plot always shows the declared300K paths and all18endpoint
sensitivities, rather than selecting by a rainfall score. The download retains
every285/300K result and every numerical resolution.

## Coupling limits

Endpoint pressure changes condensation enormously. The proof does not choose
a detrainment pressure, add a fitted upper-humidity ratio or reset actual layer
water. A future conservative transfer must derive its parcel starting state
and detrainment from the represented layers, book both surviving vapor and rain,
and account explicitly for latent heat and the fate of condensate. Recomputing
a saturated temperature path is not environmental heating feedback.

The parcel is liquid-only, has constant dry heat capacity/latent heat and omits
entrainment, ice, re-evaporation and environmental heat exchange. Some colder
cases reach207K, where ice and variable thermodynamics matter. Passing the
budget checks verifies this approximation; it does not demonstrate realistic
clouds, observed atmospheric profiles or improved rainfall.

All earlier812Earth attempts remain unchanged (808passes,4preserved failures).
Science Earthr39 and fantasy Earthr38 remain adopted. The figure and endpoint
checks are folded into the existing independent-water atlas study, keeping
older results collapsible. No separate map topic or new climate headline.
