# Complete local moisture accounts for the padding response

All six separately declared diagnostic replays passed. Every archived scored
monthly T/P/E/W/u/v value, instantaneous gain/sink/water/rain trace and calendar
matches in dtype, shape and bytes. All original numerical certificates pass.
The complete exported local concentration equations pass the unchanged 0.01
scaled residual criterion with explicit float32 export rounding bounds.
The independent reviewer verified raw references, attempt/result receipts,
source/protocol hashes, all terms and instantaneous residuals. No failed or
missing replay remains; no physical parameter, solver tolerance or main model
source was changed by these captures.

These are six additional diagnostic integrations following the completed
nine-case padding experiment, not retries or another candidate search. The
first operational launch failed its Python-library guard before any physical
import/attempt/integration; the preserved recovery used the correct venv path
without a source or numerical change. All six scientific attempts then passed.

## What compensates for the import changes

Values below are changes from 1100 to 4012 km padding, averaged over the
same scored cells, in mm/model year. Positive values add to the local equation;
positive drying changes mean less water removal. Rain equals the sum of seven
source terms minus the signed equation residual. Monsoon drying is already
inside total linear drying and must not be added again.

| Local equation component | Somalia | Sahara | North India |
|---|---:|---:|---:|
| Surface evaporation | -2.52 | -205.37 | -0.83 |
| Marine humidity exchange | +398.59 | 0.00 | +62.74 |
| Total linear drying | +0.41 | +260.05 | -3.08 |
| Convergence import | -665.79 | -462.35 | -164.98 |
| Advection | +302.81 | +5.47 | +198.66 |
| Diffusion | +7.10 | +8.71 | -4.65 |
| Storm exchange | -7.85 | +185.59 | -165.64 |
| Signed equation residual | -0.021 | -0.065 | +0.002 |
| **Rain** | **+32.78** | **-207.82** | **-77.78** |

Somalia's large import reduction is compensated mainly by increased marine
humidity exchange and advection. Marine exchange changes from -12.68 to
+385.91 mm/year; advection from 1585.34 to 1888.15. The previously unpartitioned
remainder is now accounted for by actual recorded terms, not a large missing
numerical residual. This explains the local equation's response while leaving
the original 3556 versus 3589 mm/year rainfall unchanged.

Sahara has zero marine humidity exchange at both sizes. Reduced import,
reduced surface E, weaker drying and increased storm exchange respond together.
Its rainfall reduction therefore cannot be assigned to the convergence filter
alone. These records also cannot distinguish which initial change triggered
the coupled rain/soil/evaporation feedback.

North India loses nearly 165 mm/year in each of convergence import and storm
exchange. More positive advection (+199) and marine exchange (+63) offset
part of that loss. Both endpoint source accounts close locally even though
the expanded-domain rain loss is worse than the control's. Annual rainfall
or import alone would hide these differences.

## Residual evidence without annual cancellation

| Region / padding km | Mean absolute residual mm/day | Maximum absolute residual mm/day | Maximum scaled residual |
|---|---:|---:|---:|
| Somalia / 1100 | 0.001320 | 0.006929 | 0.001696 |
| Somalia / 4012 | 0.000035 | 0.000221 | 0.000018 |
| Sahara / 1100 | 0.000867 | 0.002488 | 0.003952 |
| Sahara / 4012 | 0.000218 | 0.000904 | 0.000361 |
| North India / 1100 | 0.000441 | 0.002407 | 0.009488 |
| North India / 4012 | 0.000210 | 0.001335 | 0.009262 |

The independent review also preserves RMS residuals and checks every saved
instantaneous point against the production scaling. Tiny signed annual
residuals are not used as a substitute for those checks. The float32 bounds
cover export rounding; no numerical criterion was relaxed.

## What this establishes and what it does not

The missing marine-exchange export matters in real regional runs, including
about 189 and 251 mm/year of supply in the North Indian control/large domain.
The tested diagnostic correction can represent that already-existing term
without changing the saved physical solution. Its main-source application
still waits for W18c's complete validation and supervisor exit.

These are signed local nonconservative concentration-equation terms. They
are not a conservative planetary water budget, measured boundary transports,
moisture-source tags or independent interventions on each process. All terms
can respond to changed domain geometry and winds. The paper's Earth-conditioned
boundary and descent forcings also remain active. Keep the original padding
findings: no deployment padding is selected and larger domains do not fix
Somalia or improve North India's rainfall.

## Next physical hypothesis

Source inspection shows a concrete distinction worth testing after the
current campaign: `model.py` gates marine inflow using nearest-sea SST, but
sets the land relaxation target to `(inflow_rh or ocean_rh) * Ws`, where `Ws`
is saturation water for the receiving land column. The configuration explicitly
documents this as a fraction of land saturation. It is an intended empirical
closure, not an implementation mismatch.

An upstream marine-water availability limit would be a different physical
closure. It could reduce a warm receiving column's imposed humidity target,
but the coupled response and effects on beneficial monsoon moisture are
unknown. The current records do not establish its outcome or justify adopting
it, switching inflow off, fitting an intermediate coefficient or reopening
W18c. A future bounded comparison should retain the current law as an exact
control, hold warm/onshore/distance gates fixed, include Sahara and North
India alongside Somalia, and declare its budget before any new integration.

First finish W18c's original validation, apply/retest the already validated
diagnostic export patch in a new source epoch, then use this component-level
evidence to define that comparison. Do not mix old qualifications with changed
source or prescribe an atlas update from these diagnostic replays.

## Artifacts

`output/padding_budget_capture_20261127/review.json` contains all six accounts,
three endpoint differences, instantaneous residual statistics and hashes of
18 raw attempt/result/capture files. `term_changes.png` was visually inspected:
three regions, seven signed source changes and separate rain markers are
readable, with units and the local/coupled interpretation visible.
`term_changes.csv` and `figure_provenance.json` retain the values and figure
hashes. Reproduce the figure from its reviewed input with `plot_review.py`
in a fresh output destination; the script preserves an existing completed
figure. Six guard/accounting tests passed before execution. No new climate
adoption or atlas rebuild follows from this study.
