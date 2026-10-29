# Exact transport factor reuse: frozen numerical controls

The prototype solves vapor and gas enthalpy transport using identical air-mass
operators at each coupling iterate. A new scoped backend reuses a sparse LU
factor only when the CSC shape, dtype, index arrays and coefficient values match
exactly. It preserves the original matrix assembly and transport function body.
The cache ends after each dynamics advance. Failed factorization cannot install
a new cache key with a stale factor; repeated singular inputs still fail.

Five targeted tests and the full 374-test physics/numerical suite pass. Tests
cover actual two-scalar fluxes, complete coupled trajectories, matrix mutations,
failed-factorization retries and isolation of original dependency namespaces.
These checks have started no new Earth-input integrations.

The literal protocol in `calibration/shared_transport_20261029/plan.json` declares
six paired 24-hour, 900-second controls in north India, Mexico and the Pacific
Northwest. Both backends use the already qualified fast liquid-phase root. The
reference factorizes every scalar solve; the candidate reuses exact factors.
Each reference must reproduce the preceding fast-phase candidate's saved arrays
and scalar history exactly. Candidate field tolerances are frozen in the plan.
Independent saved-state energy and water checks remain required.

Backend order alternates by region. Every physical call is timed, including the
cold first step, with solve/factorization/reuse counts. There is no speed gate,
no discarded timing sample and no repeated-timing confidence claim. Six starts
would bring the separate prototype record from 81 starts /77 completions /four
retained earlier failures to 87 /83 /four if all finish. Legacy 1934/1929 remains
unchanged. Failed and partial outcomes must be retained.

No result from these six cases is known in this declaration. This is numerical
work to reduce the cost of longer soil-water spin-up and physical experiments.
It is not a rainfall skill improvement, parameter calibration or adoption of the
new physical model. Earth r39 and normal atlas fields remain unchanged.
