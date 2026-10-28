# Shared buoyancy, hydrostatic pressure and vertical-mode state

A manufactured audit finds that the earlier two well-mixed donor boxes cannot
be coupled directly to the smooth first vertical mode while retaining its
independent wave-speed/adiabatic law. `audit_box_mode_coupling.py` advances a dry
stable two-box background with exactly mass-balanced opposing flow and projects
its actual temperature tendency onto that mode. At1/0.1/0.01-second timesteps,
the response converges to0.512312 of the smooth expected ascent tendency and
0.263697 of the descent tendency. Independent one-sided donor limits reproduce
these numbers. Donor exchange adjusts receiving air over a discontinuous
background; it is not the smooth reversible buoyancy equation.

This does not invalidate the old fixed-wind water/static-energy budgets or show
that this mismatch uniquely causes existing Earth rainfall errors. It does
block treating those boxes and the continuous mode as one consistent feedback
model. Adding a second adiabatic tendency or fitting a new wave speed to one
direction would hide the inconsistency rather than resolve it. No Earth run or
calibration count is added by the audit.

## An energy-paired vertical grid

`rotclimate/vertical_state.py` stores reduced pressure/horizontal velocity at
vertical cell centers and buoyancy/vertical mass flux at internal interfaces.
Rigid top and bottom lids supply zero vertical mass flux. Positive cell reference
density and interface stability N² define the kinetic/available-energy weights.
Unstable or neutral stability is rejected, never clipped to force a dry mode.

For cell masses Mk=rho_k*dz_k, centered gradient D, and interface weight
W=rho_face*distance/N², hydrostatic balance is D*phi=b. Pressure is reconstructed
by integrating b over center distances; its dry-mass mean is set to zero.
Continuity gives rho*w=-cumsum(Mk*div(Uk)) at internal interfaces. It explicitly
checks the zero total dry-column divergence required by the rigid lid.

Summation by parts then gives

    sum(Mk phi_k div(Uk)) = sum(rho_face distance b w)

The right side is the negative available-energy tendency from
`db/dt=-N²w`. Thus pressure work and buoyancy work cancel using actual discrete
operators, including variable density, stability and vertical spacing.

Normal modes solve

    D^T W D F = lambda M F; c=1/sqrt(lambda)

The zero barotropic mode is excluded. All n-1 internal modes are retained and
normalized by mass: mean(M F_i F_j)=delta_ij. Their buoyancy structures are D F.
Mode pressure amplitudes reconstruct both pressure and buoyancy; heating is
projected with the same W weight. Independent tests verify physical buoyancy
work equals projected modal work. A pressure gauge offset changes no buoyancy.
This is a linear anelastic hydrostatic column, not a complete compressible,
terrain-following or moist prognostic atmosphere.

## Stable reference and physical thermodynamic input

The prescribed dry reference has theta(z)=theta_surface*exp(N²z/g). Hydrostatic
Exner is integrated analytically, then T, p and ideal-gas density are recovered.
Standard potential temperature uses reference pressure1000hPa; surface pressure
is101325Pa. No reference temperature floor or stability adjustment is applied.
For theta_surface300K,N0.01/s,H15km, top T is192.6K and pressure124.3hPa.
The reference is stable and Earth-like by construction; these scales are fixed
demonstration priors, not fits to regional rainfall.

Actual thermodynamic inputs can produce virtual-potential-temperature buoyancy:
Tv=T*(1+r/epsilon)/(1+r), theta_v=Tv*(pref/p)^(Rd/cp), b=g*(theta_v/theta_ref-1).
r is vapor/dry mixing ratio, not specific humidity. The exponent is dry Rd/cp;
this diagnostic does not redefine the separate finite-capacity moist enthalpy.

With constant density and N, discrete mode speeds match independent cosine
eigenvalues and converge quadratically to NH/(k*pi). With density from the
hydrostatic reference, the first speed is45.6995/45.5496/45.5122/45.5029m/s at
8/16/32/64 levels. The earlier uniform-density continuous first mode was47.7465m/s;
these are different specified vertical models, not measured accuracy gains.

Fourteen new tests verify analytic hydrostatic reference, dry/mixing-ratio
buoyancy, discrete cosine spectrum, refinement, actual pressure reconstruction,
variable-coefficient work/continuity, modal adiabatics and source projection,
and invalid backgrounds/column mass flux. Earlier174 tests and kernels are
unchanged. Next: a transient wind/pressure/buoyancy state using these same
operators before any moist-column feedback or bounded Earth pilot.

Earth counters remain1934 attempts /1929 strict passes /four historical failures
/one historical interruption. Earthr39 and normal atlas climates remain
unchanged. Neither the structural audit nor unique linear modes establish a
global optimum of the nonlinear Earth calibration or improved rainfall skill.
