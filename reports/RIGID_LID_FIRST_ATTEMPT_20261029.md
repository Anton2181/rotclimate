# Rigid-lid mean-flow test: retained numerical failures

The literal plan and original constrained core were committed in `5fd189f`
before the twelve Earth-input integrations. All twelve started; eight completed
and four stopped on the existing native pressure-lid dry-mass continuity guard:
India and Pacific Northwest, both mean-flow scenarios, at 450 s. Failures occurred
after 11/10 steps in India and 30/29 steps in the Pacific Northwest. Complete
histories and partial fields are retained in `output/rigid_lid_20261029`.

The mixed momentum/constraint saddle solve left column-mass residuals around
several 1e−13 kg/m²/s. The small analytic tests passed; the focused suite had
328 passes, but that did not establish robustness on these Earth inputs.
No comparison winner or climate improvement is claimed from this incomplete set.

The next declaration repeats **all twelve** cases, without changing the equations,
source fields, initial wind constructions, physical parameters, timesteps,
duration or physical tolerances. It uses three LU residual-correction solves
with extended-precision residual evaluation and checks each row's backward error
against eight machine epsilons. Three new tests check mixed-scale constraint
precision, the old small-core limit, and native continuity plus energy closure
on a larger synthetic domain. These tests pass; repeated Earth outcomes are
not yet known when this declaration is committed.

These twelve starts bring the separate prototype smoke count to **30 started /
26 completed /four numerical failures**. They do not alter the legacy benchmark
1934 attempts /1929 strict passes /four historical failures /one interruption.
The proposed repeat would add twelve new starts, retaining these four failures.
No calibration, monthly skill score or production atlas adoption is claimed.
