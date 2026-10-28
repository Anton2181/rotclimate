# Six-case layer-transport diagnosis — 28 October 2026

This is a diagnostic milestone, not a new calibration or climate improvement.
The previous finite broad searches have not established a global optimum, and
repeated rainfall biases justify inspecting the physical equations before
another coefficient search. Only six regional reruns are authorized by the
literal plan: North India, Mexico and the Pacific Northwest, at the existing
legacy3.5m/s (global04) and hydrostatic-half3.5m/s (global06) profiles. No knob,
background, objective or adopted atlas climate changes.

The observer is isolated from the physical solution: its arrays and closure
inputs are copies, and its return is unused. The default and enabled coupled
toy climates reproduce the pre-edit T/P/W/layer-water/days bit-for-bit. Tests
also attempt to corrupt callback payloads and check that current and next-step
water remain unchanged; reconstruct nonzero counterflow/diffusion/storm terms;
and distinguish mean(q*u) from mean(q)*mean(u).

Source transition: committed5917086 →985ba41 changes only the core
reservoir_moisture observer hook. The new runner verifies both Git bytes,
replaces only that one parent source hash, verifies every other parent source,
and freezes new exporter/recorder/reference code and all cached inputs before
any real integrations. The literal six-run plan must be committed first.
Every original climate NPZ field and actual case/parameters must reproduce the
saved ocean-pilot counterpart exactly. Failures are preserved and counted.

The sidecars save all33 solved seasonal steps, including8 primer steps and25
scored steps: actual branch winds, layer water and relative dry mass, dry donor
exchange and vertical water flux, simultaneous upwind vapor faces, diffusion,
surface evaporation, storm exchange, drying, recycled upper rain, ground-rain
components and equation residual. Projected velocities point right/up; y-face
flux points down; signed vertical water flux points upward. Flux divergences
and equation residuals apply only to the solved interior. These are steady
seasonal balances, without an atmospheric storage tendency. Relative dry mass
must be multiplied by101325Pa/g before interpreting W/mass as kg/kg.

New925–300hPa winds integrate the two-box piecewise q and branch velocity over
actual pressure overlaps at every step before averaging, instead of comparing
a full-column modeled wind against a partial observed column. Both old audit
arrays and new matched arrays remain available, with their distinct definitions.
Land P/PW/winds use identical observed-rain land pixels, Gregorian month overlap,
true projected area and fully covered native footprints (>=80%). Low925hPa
reference heights and modeled surface pressure exclude below-ground columns.
The geometry-only preflight finds11 matched India land cells,1 Mexico land
cell,0 PNW land cells; Mexico has1 matched ocean cell and PNW3. No fallback
pressure or footprint is selected after seeing results. Full-score land budgets
are separate. NCEP monthly q*u omits submonthly covariance, and WorldClim rain
has a different reference period; these inputs cannot close an observed water
budget or establish independent validation.

Mexico's new NOAA PSL NCEP/NCAR1981–2010 monthly subset is held in a separate
cache with exact URL/byte/SHA provenance. Earlier frozen caches and outcomes
remain untouched. The new reference plan and sources manifest are fixed before
outcomes. No observed humidity or winds enter the climate forcing. Inherited
WorldClim cloud and remote-monsoon backgrounds still make the regional solver
conditional, rather than a fully independent global forecast.

Before this diagnosis:1879 actual Earth integrations,1875 strict passes and4
historical failures. A completed six-case diagnosis brings this to1885 attempts;
all attempts, failures and interrupted jobs are retained. Toy and geometry-only
preflights do not count as Earth climate runs.

After the six cases, use transport, storm redistribution and rain conversion
signatures to choose one bounded physical hypothesis with a predicted response.
Actual rainfall gains must be reported independently of native-state objective
improvements. No parameter proposal or adoption follows automatically from a
signed budget term. See the [recovery plan](RAINFALL_RECOVERY_PLAN_20261028.md).
