# Earth height profiles and physically derived reference stability

A fixed 6 K/km lapse-rate reference with an explicit 200 K isothermal cap
improves the inferred first internal-mode speed in three sampled groups and
worsens the fourth. The equal mean of four group absolute relative speed errors
falls from 17.22% with constant N=0.01/s to 8.92%. These are conditional,
height-derived linear-mode diagnostics, not measured wave speeds, rainfall
accuracy, held-out validation or an adopted climate improvement.

## Physical reference

`rotclimate/lapse_reference.py` derives hydrostatic pressure, ideal-gas density,
potential temperature, stability and pressure-column depth from one temperature
structure. Below the declared cap, T=Ts-Gamma*z and

    p = ps * (T/Ts)^(g/(Rd*Gamma))
    N² = g/T * (g/cp - Gamma)

Above zt=(Ts-Tcap)/Gamma, temperature is Tcap, pressure decays exponentially,
and N²=g²/(cp*Tcap). Temperature and pressure are continuous at the cap;
stability changes there explicitly. Gamma=0 has its exact isothermal limit.
An analytic pressure-to-height inverse also covers the cap. Neutral/unstable
reference lapses are rejected, not clipped into a positive stability floor.
The cap is a stated reference structure, not predicted convection, radiation
or a diagnosed tropopause. No separate density, wave-speed or column-depth
parameter is fitted.

The audit fixes Gamma=0.006 K/m, already the environmental lapse used in prior
experiments, and Tcap=200 K for every region/month. Its basal temperature is
conditioned on the lowest observed 925–850 hPa layer thickness under that lapse:

    Ts = Gamma*dz / [1 - (850/925)^(Rd*Gamma/g)]

This uses an Earth thermal anchor and is not an independent prediction of it.
It does not insert observed temperatures, winds or humidity into the simulator.
The 925 hPa base is a partial-column reference lid, not the physical surface.

## Cached height diagnostic

The only reanalysis variable used is NCEP 1981–2010 monthly geopotential height.
All input subsets are cached and provenance checked; no download or Earth
integration is needed. The pressure edges are 925,850,700,600,500,400,300,250,
200,150,100 hPa. Layer virtual temperature and the dry-exponent virtual potential
temperature proxy are

    Tv_layer = g*dz / [Rd*log(p_bottom/p_top)]
    theta_v_layer = Tv_layer * [100000/sqrt(p_bottom*p_top)]^(Rd/cp)
    N²_interface = g*diff(log(theta_v_layer))/diff(z_layer_center)

Hypsometry yields a pressure-layer mean; assigning that mean to a height
midpoint and geometric-mean pressure is a coarse diagnostic approximation.
Reference N² uses the same secant log-theta operator on analytic reference
potential temperature at those height centers. It is not a saturated moist
stability diagnosis or a direct measurement of propagating mode speed.

Density is pressure-layer mass dp/g divided by observed thickness. All three
mode solves use identical observed height cells and density, with rigid lids
at 925 and 100 hPa. Only the supplied stability differs. This controls geometry
and mass rather than comparing a partial observed column with an unrelated
15 km full reference. The pressure-depth inverse is recorded as a secondary
conditional diagnostic, not used to change the mode geometry.

Exact native land/ocean masks, overlap areas and month order come from the
previous divergent-thermal control archives. These are reused development
footprints, with limited coverage. Surface pressure is unavailable, so the
audit cannot independently certify that 925 hPa is above ground in every land
cell; reanalysis pressure-level extrapolation can affect such profiles.

| Footprint | Native cells | Valid monthly cell profiles | Constant N error | Lapse/cap error |
| --- | ---: | ---: | ---: | ---: |
| North India land | 11 | 129/132 | 14.92% | 5.13% |
| Mexico land | 1 | 12/12 | 14.61% | 6.82% |
| Mexico ocean | 1 | 12/12 | 8.34% | 12.03% |
| Pacific Northwest ocean | 3 | 36/36 | 31.01% | 11.71% |

Errors are mean absolute relative first-mode speed differences. Within each
group, native overlap area times month days supplies weights. The aggregate is
an equal mean of these four group errors; it is not a global geographic mean.
Three India profiles have nonpositive lowest-interface N²: April native cell59,
May cell59 and May cell60. Their raw signed values and exclusions are retained;
no stable inferred mode is generated for them. Valid India area/day coverage
is 97.59%. A positive constant or lapse reference is still recorded for those
cases but cannot create an observational comparison by replacing the invalid
proxy. All other groups have complete valid coverage.

The Mexican ocean regression remains explicit. It may reflect real thermal
structure missing from the fixed lapse/cap reference, the coarse diagnosis,
or sparse sampling. It is not a reason to invent a region-specific N correction.
Broader independent coverage and moist stability are needed before selecting
a climate reference.

## Verification and publication

Ten new lapse-reference tests cover the hydrostatic power law, ideal-gas
density, analytic stability, isothermal limit, cap continuity, independently
rooted pressure-depth inversions and invalid lapses. Five new diagnostic tests
cover exact isothermal hypsometry/stability on unequal pressure cells, pressure
mass, recovery of an independently prescribed lapse temperature anchor, signed
unstable profiles without mode fabrication, and invalid coordinate orders.
The full focused suite passes 232 tests.

The publisher rechecks all 192 raw monthly cell profiles against cached height
data, exact native masks/calendar, actual weights and exclusions. It computes
reference log-theta by independently integrating its vertical derivative,
checks pressure depth with scalar roots, and solves full dense generalized
eigenmatrices independently of the production tridiagonal solver. Raw profiles,
derived states, mode speeds, exclusions and provenance travel with the figure
in the research companion and the portable atlas bundle.

## Implications for the next climate experiment

This identifies a physical reference-structure issue outside ordinary tuning
of rainfall coefficients. The prior dry mode demonstrations and resolved
fixed-wind moisture/phase tests remain valid within their declared references.
The lapse reference provides a more physical alternative to prescribing an
independent constant N, without treating this diagnostic as a precipitation fit.

The next major step still needs a consistent moist thermal-pressure-momentum
state and its energy/work budget. Adding smooth-mode adiabatic cooling to
moist-static-energy transport would count the expansion cooling twice. The
shared vertical grid resolves the old two-box shape mismatch but does not by
itself solve nonlinear pressure/kinetic work or reference-maintenance energy.

When that coupling is available, declare a bounded Earth rainfall comparison
with fixed terrestrial planetary priors, regional tradeoffs in mean loss,
temperature/physics guards and independent geographic/time checks. Regional
unanimity should not be the acceptance rule. Multiple separated starts and
different physical structures can test whether the adopted solution is merely
a local calibration minimum; neither this audit nor a unique linear solve
proves a global nonlinear optimum.

No Earth integrations were run here. Counters remain 1934 attempts / 1929 strict
passes / four historical failures / one historical interruption. Earthr39 and
the normal world, biome and population atlas datasets remain unchanged.
