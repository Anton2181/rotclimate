# Finite surface coupling and frozen24-hour comparison

The atmosphere can now exchange heat and signed water vapor with a finite
liquid surface reservoir. Radiation heats/cools actual gas and surface enthalpy.
Rain returns its actual liquid enthalpy and mass, changing the surface heat
capacity. No source is silently clipped and no returned rain is credited twice.
Seven new coupling tests plus the twelve flux-kernel tests and existing focused
checks give **356 passes**. There are no new Earth outcomes in this declaration.

Surface enthalpy is `(C_substrate + cp_liquid M_liquid) (T_surface −273.15)`.
The explicit local step adds radiative heating and sensible/vapor enthalpy to
gas, debits the complete exchange from the surface, and transfers actual vapor
mass. Negative vapor flux is dew, handled as a real atmospheric water sink.
Liquid phase adjustment then returns rain mass/enthalpy to the surface. The
subsequent pressure dynamics/convection step returns its rain exactly once.
Total gas + kinetic + surface energy changes only through declared radiation
and lateral power; atmospheric + surface water changes only through lateral
vapor flow. This is a first-order split and makes no final-state dynamical
midpoint or balanced-initialization claim.

The frozen plan in `calibration/surface_forcing_20261029/plan.json` compares
unforced and forced24-hour runs in three regions, at900 and450 seconds:
twelve new Earth-input smoke integrations if all start. Initial atmosphere,
wind, surface reservoirs and lateral boundary conditions match within each pair.
The initial pressure-transfer rain is returned before integration and excluded
from run rainfall. Inputs remain simulated model fields; observed climate and
wind fields are not read. All failed attempts and partial states must be retained.

The declared exploratory driver uses Earth-orbit daily-mean sunlight, prescribed
outside solar reflection, pure grey longwave absorption/emission, explicit
partial-top downward radiation and neutral log-law surface exchange. Initial
liquid storage is50 kg/m² on land and10000 kg/m² over ocean, with positive
substrate heat capacity. These are declared surface assumptions, not inferred
soil moisture or fitted ocean/radiation data. The water-vapor opacity responds
to simulated water; there is no temperature restoration or rainfall-target fit.

The380 hPa top remains a partial-column boundary. An externally maintained
isothermal omitted upper slab supplies declared downward longwave; sunlight is
attenuated before entering that boundary. It is **not called the top of atmosphere**.
Grey optical depths and roughness choices are exploratory, not a spectral Earth
radiation calibration. Clouds, stability corrections, gusts, ice, runoff, deep
ocean heat supply, terrain and nonlinear momentum remain absent.

The comparison asks whether sustained physical forcing produces useful interior
rainfall after startup and whether the budgets remain robust for a day. It does
not estimate monthly climate accuracy or authorize production adoption. Before
these new runs the prototype record is54 starts /50 completions /four retained
numerical failures, separate from the unchanged legacy1934/1929 benchmark. All
normal atlas climate/biome/population datasets remain unchanged.
