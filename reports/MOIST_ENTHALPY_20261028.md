# Phase change with water heat capacities and precipitation enthalpy

`rotclimate/moist_enthalpy.py` extends the prior dilute phase model without
changing its reproducible kernel. The new liquid-only fixed-pressure boxes
include cp_d=1004, cp_v=1850 and cp_l=4186 J/(kg K), with Lv0=2.5e6 J/kg at
T0=273.15K. Their gas/liquid enthalpies per area are

    Hg = (cp_d Md + cp_v Wv)(T-T0) + Lv0 Wv
    Hl = cp_l Wl(T-T0)

The heat-capacity difference implies Lv(T)=Lv0+(cp_v-cp_l)(T-T0). Liquid can
enter at a different temperature from the air. Given total initial enthalpy
H0 and vapor change x, the equilibrium temperature is obtained directly:

    Tnew = T0 + [H0 - Lv0(Wv+x)] /
                [cp_d Md + cp_v(Wv+x) + cp_l(Wl-x)]

A bracketed monotone saturation root chooses x; if all liquid evaporates
without saturation, x=Wl. Bounds preserve nonnegative water and150–370K
supported equilibrium temperatures. Incoming liquid can be150–370K, initial
air180–330K, pressure10–110kPa and vapor/dry mass ratio≤0.2. The Bolton
liquid saturation formula is unchanged; no ice physics is added.

Upper condensate falls at the **adjusted upper temperature**. Its actual
liquid enthalpy enters the lower box. Surviving ground rain leaves at the
adjusted lower temperature and exports cp_l P(Tlower-T0). Therefore

    initial gas enthalpy = final gas enthalpy + ground rain enthalpy

Water also balances: initial vapor equals final vapor plus ground rain.
The gas sensible change plus rain's exported sensible energy equals Lv0
 times the vapor loss. Ground-rain enthalpy is relative to liquid at0°C and
can be negative for supercooled liquid; no freezing is modeled. Mechanical
and gravitational energy of falling water remain omitted.

## Temperature forcing versus the heat ledger

To compare the earlier specified Boussinesq mode under the same temperature
change, CPdry*Md*(Tnew-Told)/dt is stored as **dry-equivalent temperature
forcing**, not as net thermodynamic heating. This quantity divided by
CPdry*Md recovers the actual Tdot used in buoyancy projection. It must not be
summed and interpreted as a full moist-energy source. Water's changing heat
capacity and incoming/outgoing enthalpy mean these are different quantities.
The full gas/rain enthalpy ledger is stored independently and conserved.

The fixed comparison reuses the exact initial temperatures, vapor, layer mass
and representative pressures from the preceding dry/humid lower-air pulse.
It adds two phase-column cases and two isolated steady regional responses,
not Earth integrations or a time-dependent coupled moist climate. Old and new
ground rain, phase temperature, projected forcing and mode work are compared;
no parameter is adjusted to favor a location. Constants N=0.01/s,H=15km,Tref=275K,
c=NH/pi and five/twenty-day drags are unchanged.

## Checks and limits

Ten new tests compare against an independent enthalpy/Brent root, cold versus
warm rain, actual column water and enthalpy budgets including precipitation,
complete reevaporation and invalid inputs. In the cold/warm full-evaporation
limit the gas enthalpy difference exactly equals the incoming liquid's sensible
heat difference. Omitting exported precipitation enthalpy creates a material
energy residual, so the test checks that this term is necessary.

No Earth rainfall improvement or climate adoption is claimed. The old dilute
kernel, regional solver and saved climates remain unchanged. The new method
still omits ice, water mechanical/gravitational energy, finite cloud/fall times,
convection, prognostic atmospheric heat advection and radiation. The vertical
mode is a maintained constant-N Boussinesq approximation. A fully closed Earth
atmosphere and nonlinear moist-circulation feedback remain future work.

Earth benchmark counters remain1934 attempts /1929 strict passes /four
historical failures /one historical interruption. Manufactured phase and
linear response checks are not benchmark climate runs or global-optimizer
searches. Mean rainfall gains with regional tradeoffs remain the eventual
acceptance criterion, with temperature/physics and held-out checks.
