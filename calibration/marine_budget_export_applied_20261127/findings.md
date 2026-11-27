# Marine humidity exchange is now included in main diagnostic exports

The previously validated two-file patch is applied to `rotclimate/model.py`
and `rotclimate/transport.py` after W18c permanently closed at its failed
fine-resolution gate and both supervisors exited. The main model's 89 source
hashes exactly match the private patched source that passed paired toy
comparisons and all six real scored regional replays. This application changes
diagnostic accounting, with no physical parameter or solver-setting change.

The local equation and vapor ledger now include the existing signed land
marine-humidity exchange separately from surface evaporation. Saved reports
expose that component and explain its sign. Independent reservoirs already
include this exchange in their returned E, so their additional component is
zero and is not counted twice. The physical T/Tsl/P/W/u/v/E and applicable
layer-water results were unchanged in the paired validation. All six regional
captures reproduced their saved scored monthly fields and traces byte for byte.

**27 focused tests pass, with no failures, errors or skips on the actual
applied main source.** They cover moisture solves, local/flux transport,
independent reservoirs and coupled certificates, plus the six promoted
functional marine checks. Those six exercise real positive and negative
relaxation sources, asymmetric ocean sink rates and signed saved report
components. The private-only import-context guard was excluded from promotion.

Evidence is under `output/marine_budget_export_applied_20261127/`:
application plan, regression log/XML and `qualification.json` with all source
and evidence hashes. The earlier private patch plan/qualifications and failed
diagnostics remain unchanged as historical artifacts. The six-capture findings
are under `calibration/padding_budget_capture_20261127/`.

This is a new **diagnostic source epoch**, not a new adopted climate or a new
97-region paired-reference qualification. Future benchmarks must create new
source/protocol records. Do not rerun the closed W18c supervisor under its
old qualification or relabel any old failed certificate. Earth climate remains
r58, atlas r51, sealed AA unopened. This correction does not reduce Somalia's
rainfall or cure the rejected finalist's fine-resolution degradation.

The next physical investigation should distinguish the current land-relative
marine humidity target from a bounded upstream marine-equilibrium target,
holding the existing warm/onshore/distance gates fixed and retaining dry and
monsoon controls. That is a separate prospective experiment, not another
W18c finalist or permission to tune against its fine results.
