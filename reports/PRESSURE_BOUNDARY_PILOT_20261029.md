# Regional boundary and initial-wind controls — 29 October 2026

Prescribed boundary flow and archived simulated initial winds do not resolve the
startup problem. India and the Pacific Northwest still put essentially all
six-hour rainfall in the outer grid cells. Mexico improves to 77% at the finer
step, but remains dominated by the perimeter. This is not a monthly rainfall
accuracy result, and no configuration is adopted.

## Fixed comparison

The literal declaration was committed in `2047035` before the twelve integrations.
The three regions retain the previous post-conversion temperature/water fields,
224 km sampling, six pressure cells, Earth rotation, five-day drag and one-hour
convective relaxation. Each integrates six hours. Initial conversion rain is
excluded from all rainfall below.

For each region the controls are: closed boundaries with archived initial winds
(900 s), prescribed boundary flow with resting interiors (900 s), and prescribed
flow with archived initial winds (900 and 450 s). The previous closed/resting
900 s case is retained as a control. All twelve declared runs completed, with
no replacement cases or parameter changes after outcomes.

Only the source simulation's lower projected-right/up winds are used. They are
staggered onto faces and the up component is converted to grid-south. A uniform
upper return compensates the lower dry-mass flux at every face. The source's
upper/barotropic winds are not retained, and this transfer does not ensure
geostrophic balance. Observed wind, humidity and rainfall are not inputs.

## Result at the finer prescribed-flow/seeded step

| Region | Six-hour mean rain mm | Outer-cell rain | Max profile change K | Net imported water kg/m² |
|---|---:|---:|---:|---:|
| North India | 0.000382 | 100.0% | 7.47 | +0.4321 |
| Mexico | 0.008699 | 77.0% | 10.80 | +0.0886 |
| Pacific Northwest | 0.027542 | 99.8% | 12.32 | −0.2460 |

Mexico's initial winds create some interior rain: even the closed/seeded case
puts 11.7% inside the perimeter. That is a real difference from the resting
control, but neither interior rainfall nor increased rainfall establishes skill.
The tropical means remain very small and lack sustained surface/radiative forcing.

Between 900 and 450 s, temperature RMS differences are 0.02455, 0.01943 and
0.02668 K; rainfall RMS differences are 0.001434, 0.007128 and 0.014537 mm,
respectively. This does not establish convergence of monthly rainfall.

The maximum initial momentum residual remains about 0.00396, 0.00378 and
0.00435 m/s² with seeded ports. Importing the source simulation's winds therefore
does not make this different pressure-coordinate thermal state balanced. The
large startup thermal adjustment persists. Boundary inflow alone is insufficient.

## Conservation and scope

Normal boundary flow is prescribed with zero depth-mass mean at each face.
Incoming gas enthalpy and vapor use fixed adjacent initial model values; outgoing
donors are local. Exterior velocity faces have no kinetic storage degrees of
freedom. The regional energy identity includes advected gas enthalpy, outward
geopotential work, and work exchanged with the reservoir maintaining the
prescribed Coriolis-coupled boundary velocities. Coriolis does not create energy
in a system that includes that external reservoir.

The publisher independently reconstructs final gas/kinetic/rain energy and water
from saved fields, against separately summed solver-recorded boundary flux
scalars. This checks accounting; it is not an independent boundary-flux solver.
Maximum relative reconstructed errors are 8.70e−16 (energy) and 8.41e−16 (water).
Eight boundary/seed tests plus the existing focused suite give **308 passes**.

These are conditional inflow/outflow boundaries, not transparent wave radiation.
The prototype still lacks barotropic and nonlinear momentum dynamics, resolved
terrain, ice and sustained surface/radiative forcing. Its dry/dilute pressure
geometry and partial atmosphere remain explicit approximations.

## Next physics decision

Investigate balanced initialization before further rainfall-coefficient search.
In particular, quantify whether the fixed thermal state admits physically
plausible, weakly divergent winds in the discrete operator. Simply prescribing
a steady wind is not a balanced coupled temperature/water solution. A subsequent
initialization method must disclose changes in fields, kinetic energy and water,
and must not silently erase real variability or force agreement with observed
rainfall. ECMWF's [gravity-wave control documentation](https://www.ecmwf.int/sites/default/files/elibrary/2021/81269-ifs-documentation-cy47r3-part-ii-data-assimilation_1.pdf)
discusses normal-mode and digital-filter approaches to initial imbalance; this
prototype has not implemented either method.

Twelve new Earth-input smoke integrations plus the previous six give **18** in
this new prototype. They are counted separately from the unchanged legacy
1934 benchmark attempts /1929 strict passes /four failures /one interruption.
No monthly skill score, recalibration or adoption is claimed. Earth r39 and all
normal world, biome and population map datasets are unchanged. The `.bat`-served
research companion contains these results, raw fields and the frozen declaration.
