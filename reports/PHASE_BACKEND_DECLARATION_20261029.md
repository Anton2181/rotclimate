# Equivalent phase numerics: kernel result and frozen trajectory comparison

The safeguarded phase root is faster in the three declared synthetic tests:
median speedups are9.04× for clear columns,3.37× for condensing columns and3.96×
for mixed columns. These measure the phase kernel, **not the complete simulator**.
The timing declaration was committed in `bd0a749` before outcomes. All paired
times and raw fields are retained in `output/fast_liquid_phase_20261029`.

Clear-column outputs are byte-identical. Across the other two cases, maximum
differences are6.03e−12 K in temperature,4.73e−12 kg/m² in rain and4.79e−7 J/m²
in rain enthalpy. Actual water/enthalpy guards remain enforced. The new root
skips solved all-evaporated endpoints, uses an analytic safeguarded Newton step
inside the original bracket and falls back to the original bisection solver.
It changes neither the saturation law nor the liquid thermodynamics.

An isolated dependency-binding adapter now allows the two roots to run through
the complete prototype. It reuses the frozen dynamics, convection and surface
function code bodies with independent namespaces. Original module globals are
unchanged. The reference binding exactly reproduces the original synthetic
trajectory; a12-step moist candidate trajectory matches it within declared
precision. The focused suite has **369 passes**, including nine root tests and
four backend/wiring tests. This is not yet an Earth trajectory acceptance.

The next frozen protocol in `calibration/phase_backend_20261029/plan.json` repeats
the three24-hour forced Earth-input cases with reference and candidate roots:
six new numerical-control integrations if all start. Reference/candidate order
alternates by region. Every coupled call is timed, including the cold first step;
there is no minimum-speed gate or dropped timing sample. Physical input fields,
forcing, parameters and code bodies match. The reference must reproduce the
archived900-second baseline exactly; candidate state tolerances are declared
before integration. Independent saved-state energy/water checks are also required.

No Earth outcome from this protocol is known in this declaration. Neither the
numerical backend nor the physical model is adopted. No monthly skill or climate
calibration is claimed. Prior prototype counts remain75 starts /71 completions /
four retained numerical failures, separate from legacy1934/1929. Normal atlas
climate/biome/population fields remain unchanged.
