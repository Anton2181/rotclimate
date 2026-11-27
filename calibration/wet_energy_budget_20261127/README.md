# Shared solar limit on wet-soil cooling: prospective fixed97-region experiment

One structural hypothesis, no fitted coefficient or parameter search. The two
existing empirical wetness temperature decrements jointly imply cooling
C*lambda*(positive delta_wet + positive delta_sun). C is the existing EBM
atmosphere+soil heat capacity times r58's land_heat_capacity; lambda is the
ACTUAL regional land relaxation rate, checked byte-exact in every step.
Both positive terms share ONE limit (1-alpha_free_land(latitude))*daily_TOA_S.
Scale both by min(1, bound/implied_cooling), preserving dry-soil warming.

The identification of regional effective heat capacity with the EBM column is
a new explicit modeling assumption. Ice-free absorbed TOA sunlight is an upper
bound, not measured surface net radiation. Existing latent heat, cloud, snow,
heat storage and advective energy are not jointly closed by this construction.
Do not call it a proven physical correction or infer evaporation from this flux.
It is a unit-consistent, unfitted hypothesis for excessive summer cooling.

Commit before preparation/runs. Exactly99 integrations: two default-off repeat
controls (Middle Volga and warm Ungava) must reproduce ALL saved cell arrays
byte-for-byte; then the SAME fixed candidate on ALL97 exposed development
regions. No early stopping or finalist selection on accuracy; stop/preserve on
original numerical or physical-identity failure. No scientific retry, tolerance
change, amplitude rescue or gate relaxation. First8 span cold/warm interiors,
maritime climate, monsoon and Somalia, then remaining89 regardless accuracy.

Evaluation is the existing policy-v6 dev6 rule: paired region-bootstrap 90%
upper S97 <1; mean T and P loss each <=1% worse; every existing regime's point
S<=1.02. Report individual harms even if the aggregate passes. This replaces
no policy and creates no requirement for every individual region to improve.
Failure closes THIS fixed solar-bound candidate. Passing is only development
evidence; a new declared validation protocol would still be needed before any
fine/fresh-sealed evaluation or adoption. No fine28 or AA access in this study.
W18/W18c remain permanently closed.

Production89 source files and retained r58 parameters remain unchanged. Private
source differs by one default-off branch in model.py plus the hashed helper;
actual intervention flag is recorded in each protocol. The same private source
runs off/on, using current-source97 qualified controls. Actual input IDs and
all source/input/cache/library/thread hashes checked before every integration.
One nice10 worker, four thread variables1, literal venv interpreter. Capture
actual before/after land targets and both cooling terms, conductance, available
flux, scale and implied flux; verify full-grid bound and unchanged warming.
Bound checks include spinup; archive all sampled steps and identify scored year.
Raw float32 scores independently checked with propagated rounding bounds.
No changes to source model, atlasr51, parameters, targets or seen_by records.
