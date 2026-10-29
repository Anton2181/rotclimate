# Conservative radiation and surface flux interfaces

`rotclimate/column_forcing.py` adds two standalone flux kernels. They have twelve
analytic tests and have not yet been coupled to an Earth integration. They do
not change the adopted climate model, calibrations or atlas datasets.

## Radiation

The pure absorption/emission grey two-stream kernel follows the same general
energy-budget approach documented by [climlab GreyGas](https://climlab.readthedocs.io/en/stable/api/climlab.radiation.greygas.html).
This is an independent small implementation, tested against analytic limits;
it is not a spectral radiation package or an Earth-calibrated opacity model.

Cell zero is nearest the surface. Longwave transmission is `exp(−tau)` and
absorptivity/emissivity is `1 − exp(−tau)`. Each layer emits its absorptivity
times `sigma T⁴` into each stream. The surface emits with its declared
emissivity and reflects the remaining downward longwave. Shortwave radiation
is absorbed on both its downward path and its surface-reflected upward path;
there is no shortwave thermal emission or atmospheric scattering.

Atmospheric heating is actual net-flux convergence. At every column,

`sum(atmospheric heating) + surface heating = net radiation entering the top`.

Optical depths, incoming solar/longwave, surface albedo and emissivity are explicit
caller inputs. No opacity, humidity feedback or surface state is fitted here.
The top boundary is **not automatically the top of atmosphere**. In particular,
the present 380 hPa regional prototype omits upper air that can emit downward
longwave; treating that boundary as empty space would be an additional assumption.
Spectral windows, clouds, scattering, ice and aerosol effects are absent.

Tests cover a transparent atmosphere, an opaque one-layer solution, an isothermal
radiative cavity with a reflecting surface, exact isothermal-layer subdivision,
random-column energy closure and invalid optical inputs.

## Surface exchange

The neutral transfer coefficient is

`kappa² / [log(z_ref/z0_momentum) log(z_ref/z0_scalar)]`.

Reference height and both roughness lengths are explicit. This avoids silently
applying a coefficient for 10 m wind to a pressure cell centered hundreds of
metres above ground. Air temperature is dry-adiabatically referred to surface
pressure before evaluating the neutral potential-temperature difference.
Dry partial-pressure density and water mixing ratio match the dry-mass vapor
convention. The moist air heat capacity includes vapor heat capacity.

Vapor flux is signed: positive evaporation, negative dew. Surface water
availability suppresses evaporation, while dew can still fall on a dry surface.
Evaporated vapor uses surface donor temperature; condensing vapor uses the
surface-referred air donor temperature. Actual vapor enthalpy is separately
resolved into phase heat plus transported liquid enthalpy, using the existing
temperature-dependent vapor/liquid heat-capacity convention. Using latent heat
alone would omit a real reference-temperature-dependent water energy term.

Tests cover neutral equilibrium, zero wind, evaporation stress and dew signs,
reference-pressure/height behavior, actual vapor energy accounting and invalid
surface inputs. No Monin–Obukhov stability correction, gust parameterization,
ice or surface-state integration is included. These are neutral transfer
approximations and do not establish accurate surface fluxes on the deep grid.

## Coupling required next

A finite surface heat/water reservoir must debit the complete vapor enthalpy
and sensible flux supplied to air, credit actual returned rainfall enthalpy,
and change heat capacity when liquid mass changes. The atmospheric forcing
must preserve gas enthalpy and water through phase adjustment. Signed dew
requires an actual vapor sink; the existing nonnegative evaporation argument
cannot simply be given a negative value. A first-order forcing split must be
described as such, with its own total energy/water tests before longer runs.

There are no new Earth integrations or calibration scores in this milestone.
The separate prototype smoke count remains54 starts /50 completions /four
retained numerical failures; legacy benchmark counts and normal atlases remain
unchanged. These interfaces are groundwork for sustained forcing, not a claimed
rainfall-accuracy improvement.
