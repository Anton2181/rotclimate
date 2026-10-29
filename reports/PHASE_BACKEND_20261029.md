# Equivalent phase backend: complete-state checks and timing

The faster liquid root is qualified for future prototype integrations. All six
predeclared24-hour numerical controls completed with the same physical equations,
forcing and initial states. Candidate final fields match the reference far inside
the frozen tolerances, and actual energy/water budgets remain closed. This is a
numerical performance improvement, not a rainfall-accuracy gain or adoption of
the new physical climate model.

The declaration was committed in `c4bee73` before Earth-input outcomes. It reuses
the frozen dynamics, convection, transport and surface code bodies in independent
dependency namespaces. The original modules remain unchanged. Reference/candidate
order alternates by region. All96 coupled calls per case are timed, including
cold first-step factorization; no timing sample is dropped and there is no
minimum-speed acceptance gate.

| Region | Reference coupled calls s | Candidate coupled calls s | Measured speedup | Time reduction |
|---|---:|---:|---:|---:|
| North India | 38.35 | 27.47 | 1.40× | 28.4% |
| Mexico | 36.67 | 31.00 | 1.18× | 15.5% |
| Pacific Northwest | 27.12 | 19.67 | 1.38× | 27.5% |

These totals measure actual evolution calls, excluding file hashing, preparation
and publication. They are one paired experiment per region, not repeated timing
confidence intervals. The separate synthetic phase-kernel experiment measured
3.4–9× speedups; that should not be presented as a complete-model speedup.

Every reference initial/final field and every recorded scalar history exactly
reproduces the archived900-second baseline. Candidate final maximum differences
are1.43e−11 K in atmospheric temperature and3.58e−11 kg/m² in rainfall. Rain
enthalpy differs by at most2.71e−6 J/m². These are numerical differences under
the same equations, not changes to a calibrated climate state.

Saved gas + kinetic + surface energy and atmospheric + surface water are
independently reconstructed against recorded radiation/lateral supply. Maximum
relative errors are1.61e−15 for energy and2.91e−16 for water. The check is
independent accounting, not a second flux discretization. The focused suite has
**369 passes**, including1,800 randomized equilibrium states, cold rain and
near-boiling brackets, explicit reference fallback, independent namespaces and
complete synthetic moist coupling.

The new root skips already solved all-evaporated endpoints, uses analytic Newton
steps safeguarded by the original bracket and retains the old64-iteration
bisection solver as fallback. Actual positivity, saturation and enthalpy checks
remain enforced. No gravity feedback, opacity, drag, orbital parameter or target
rainfall is changed.

The next numerical cost to address is duplicate transport factorization: vapor
and enthalpy use the same advection/reaction matrix at a given coupling iterate,
but the current implementation assembles/factorizes it twice. Exact factor reuse
can be tested separately under the same state-equivalence and physical guards.
It is not implemented or accepted by this result.

The physical uncertainties remain: strong initial soil-water memory, limited
spinup, flat terrain, partial upper atmosphere, grey/neutral forcing and omitted
nonlinear momentum. Faster numerics make broader searches and longer checks
cheaper; they do not establish a global climate-calibration optimum.

Six new numerical controls bring the prototype record to **81 starts /77
completions /four retained earlier numerical failures**. Legacy1934 attempts /
1929 strict passes /four historical failures /one interruption remain unchanged.
No monthly skill, recalibration or production-atlas adoption. Earth r39 and all
normal world, biome and population map fields remain unchanged. The `.bat`-served
research atlas includes the measured timings and complete raw control states.
