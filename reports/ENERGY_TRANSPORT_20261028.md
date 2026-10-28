# Native-face prognostic vapor and moist static energy

`rotclimate/regional_energy_step.py` advances vapor and gas moist static energy
with the exact same dry donor fluxes. The isolated winds are fixed during the
step; no new Earth climate integration or circulation feedback is added.

The positive-reference transported energy per area is

    E = (cp_d Md + cp_v Wv) T + (Lv0-cp_v T0) Wv
        + g (Md+Wv) z

This differs from the prior gas enthalpy by the constant dry reference
cp_d Md T0 plus dry/vapor gravitational potential. Fixed layer dry mass makes
the reference shift immaterial to actual heat change. Including g*z is essential:
transporting temperature alone across levels would omit hydrostatic ascent
cooling. Uniform dry static energy cp*T+g*z is the dry neutral equilibrium.
For uniform vapor mixing ratio r, the preserved equilibrium is
`(cp_d+cp_v r)T + (Lv0-cp_v T0)r + g(1+r)z = constant`.

## Conservative time step

The native-face donor matrix uses removal1/dt and source old_state/dt plus
physical supply. This is backward Euler, not a tracer sink or precipitation.
Two solves advance water and energy with the same mass-flux matrix. Energy
is inverted to actual temperature using the updated vapor heat capacity.

Vapor injection carries Lv0+cp_v(Tsource-T0)+g*z per kg; the default source
vapor temperature is local air temperature. Additional heating in W/m² is
an explicitly supplied external energy rate. Incoming boundary air carries
independent temperature and vapor mixing ratio, hence consistent energy.
Outgoing air carries its actual local donor state. Every step checks actual
energy/water change against external supplies and boundary export. Closed,
unforced transport conserves total energy and vapor. Upward/downward exchange
uses the continuity-diagnosed dry flux, not a prescribed temperature reset.

All heights are fixed, lower first. Sources and timestep must keep positive
energy and temperatures150–370K; invalid states fail without clipping. The
method is implicit and donor-positive; this does not guarantee temporal accuracy
at arbitrary timesteps. Eight new tests verify independent heated boxes, vapor
injection without spurious warming, rising-air cooling/descending-air warming,
closed budgets, an exact uniform static-energy equilibrium with mass gradients
and passive boundaries, and invalid configurations. Combined with the preceding
156 tests,164 focused checks have passed this round.

## Fixed-wind transient demonstration

`scripts/demo_energy_transport.py` reuses exact saved humid-case velocities,
phase-adjusted vapor and temperature from the full-enthalpy comparison. Fixed
lower/upper representative heights are1/7km. No additional heat, vapor supply
or boundary inflow is added; the prior mode has closed walls. The same24-hour
elapsed transport is integrated with6/3/1.5/0.75-hour steps. Differences are
measured against the0.75-hour solution, not an exact climate reference. This
is time refinement of an isolated fixed-wind linear transport problem.

The experiment does not perform phase adjustment during transport. Initial
saturated air may therefore become supersaturated; no rainfall or complete
moist forecast is inferred from its final humidity. This separation tests the
energy/adiabatic transport independently before combining nonlinear operators.

## Remaining coupling work

Fixed-level moist static energy represents hydrostatic pressure/adiabatic work
approximately. It is not a complete compressible mechanical-energy equation.
No mode momentum feedback, radiation, moving levels or kinetic-energy exchange
is evolved. Rain phase coupling must account for water potential energy and
falling-water mechanical/gravitational work, which the isolated moist phase
kernel omits. Do not silently remove these terms when composing operators.

Do not also add an adiabatic c²divU temperature tendency from the dry-wave solver:
that would count ascent cooling twice. The relation between the prognostic
thermodynamic profile and pressure-mode momentum must be derived before a
coupled climate pilot. Existing Earth r39 and all normal atlas climates remain
unchanged. Counters stay1934 attempts /1929 strict passes /four historical
failures /one historical interruption. No Earth rainfall improvement or global
calibration optimum is claimed by these transport and conservation results.
