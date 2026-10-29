# Fine-grid convection rejection: work-limit diagnosis

The rejected India step reproduces from the saved nineteen-step weather state.
Its original convergence error returns and every retained weather array remains
byte-identical. A passive observer captures the actual convection input and
rejected target. The observer receives copies and cannot mutate the integrator.
This replay is one new actual integration attempt, with zero completed steps;
it remains a numerical failure rather than being relabelled as a successful run.

The literal replay and five static controls were committed in `32b5030d` before
outcomes. Five work caps then act on exactly the captured convection input:

| Maximum sweeps | Converged | Actual sweeps | Remaining unstable interfaces |
|---:|---|---:|---:|
| 64 | no | 64 | 13 |
| 128 | no | 128 | 12 |
| 256 | yes | 176 | 0 |
| 512 | yes | 176 | 0 |
| 1024 | yes | 176 | 0 |

The 64-sweep output is byte-identical to the captured rejected target. The three
converged targets have byte-identical temperature, vapor, rain and actual liquid
enthalpy. The stopping tolerance remains 0.01 K. Neither phase thermodynamics,
convective relaxation nor any planetary parameter changes. This demonstrates
insufficient work allowance for this input, not a new physical closure or proof
that a particular cap is sufficient for a full finer-grid integration.

All five saved targets conserve water and enthalpy, including the nonconverged
ones. Independently reconstructed relative errors remain below 2.9e-15 in energy
and 3.8e-16 in water. Conservation therefore does not establish that a target has
met its stability criterion. Raw captured inputs and every output are retained
in `output/convection_limit_replay_20261029` and the atlas downloads.

The follow-up literal protocol in `calibration/convection_cap_20261029` declares
six full finer-grid 24-hour controls: all three regions at 900/450 seconds, with
a fixed maximum of 1024 sweeps. All three case preparations pass without any
integration. The same remapped initial arrays, pressure lids, lateral sources,
physical parameters, relaxation and stopping tolerance are retained. The larger
work limit is not increased again after outcomes; every failure and partial is
preserved. All coupled calls and their successful target sweep counts will be
recorded, including failed calls, without a timing or rainfall improvement gate.

No outcome from the full follow-up runs is known here. The old failures remain
in the record. Prototype counts through the replay are 103 starts /95 completions /
eight numerical failures, including this expected repeated rejection. Five
static closure solves add zero climate integrations. Legacy 1934/1929, Earth r39
and normal atlas fields stay unchanged. No monthly rainfall skill, recalibration
or physical-model adoption is established.
