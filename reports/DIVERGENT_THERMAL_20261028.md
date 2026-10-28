# Retained divergent return plus thermal rotation — fixed structural test

The two temperature-profile tests failed rainfall criteria. Their successful
numerical conservation did not establish a realistic circulation response.
An architecture reassessment found a concrete limit: at flat terrain and
constant Coriolis, geostrophic thermal shear is nondivergent. Requiring both
branches to keep that difference while a common correction enforces column
dry continuity removes the original lower ageostrophic convergence. A
manufactured example reduces upward dry exchange from1e-6/s to2.6e-21/s.
This is a mathematical diagnostic, not proof that it causes every Earth bias.

A default-off structural closure now separates those components. With P the
existing exact stationary dry-mass projection, let L be the original lower
wind, B=P(L), and S=P(raw thermal shear). Set

    lower = L
    upper = (B−0.25L)/0.75 + S

The historical divergent return is retained. The new thermal contribution is
mass-balanced and adds only rotational flow above. Total dry divergence still
cancels, with conservative donor water exchange. The lower wind is exactly the
original per-step construction; climate feedbacks may change its inputs later.
Actual total shear equals the historical divergent component plus S, NOT the
full raw geostrophic shear. Both decomposition error and departure from raw
thermal shear are exposed. No humidity ratio enters this construction.

This does not solve the source of lower convergence, free-atmosphere momentum,
or vertical energy. It retains their existing conditional/empirical laws and
fixed observed cloud/remote-monsoon backgrounds. It is a structural test of
rotational/divergent separation, not another decay-exponent search. The existing
single-pattern and stable separated temperature laws are fixed beforehand.
Earth constants, all rain/drying/storm/ocean laws and numerical settings remain.

76 focused tests pass: manufactured convergence retention, zero-shear historical
limit, uniform-q transport over terrain, shared parameter guards, per-step lower
wind capture, coupled layer/column ledgers and prior thermal/pressure checks.
Both older thermal modes and original winds reproduce their pre-edit toy arrays
bit-for-bit with the new flag off. Two scorer tests require original-wind
baselines and keep regional regressions visible. None are Earth integrations.

## Literal18-run declaration before outcomes

Three northern regions ×two ocean settings ×three modes: six exact original
controls, six split-return cases with the single thermal pattern, and six with
the stable separated pattern. Compare each ocean/pattern candidate against the
ORIGINAL wind closure. Require mean paired rainfall loss<=0.95 and mean monthly
temperature MAE increase<=0.25C. No individual rain-score veto. Require every
strict conservation/solver check and actual step certificate, exact control
arrays/cases/nonflag parameters, branch speeds<=80m/s and the applicable dry
stability bound. No observed wind/humidity forcing, regional fitting or new
profile constants are introduced. Preserve all failed attempts and outcomes.

Freeze explicit three-file Git transition7a9f6b4→336a7ea and bind the new
operator, tests, runner, all comparison archives and parent634sources before
any integrations. Counter before:1916attempts/1911strict passes/4old failures/
1old interruption; at most18additionalattempts (1934cumulative). Independent
reconstruction must verify actual upper flow from saved lower flow, dry-mass
projection and independently recovered thermal shear. A qualifying development
result still needs excluded-region/resolution/transfer tests before adoption.
If this split fails, move to dynamically forced circulation and atmospheric
energy equations rather than another kinematic/profile variant.

## Completed outcome

All18 integrations passed strict checks; all six original controls reproduced
full historical arrays and extra PNW native fields exactly. All682 frozen
sources/inputs and594 seasonal solves were checked. Independent complex-step/
48-node pressure integration plus mass projections reconstruct actual upper
flow within1.33e-11m/s. The target is the decomposed return, not full raw shear.
Counter:1934attempts,1929strict passes,4historical failures and1old interruption.

| Ocean / thermal pattern | Mean rainfall-loss ratio | Mean temperature MAE change C |
|---|---:|---:|
| Legacy / single |1.04913| −0.0172 |
| Legacy / separated |1.11816| −0.0209 |
| Hydrostatic half / single |1.02547| −0.0273 |
| Hydrostatic half / separated |1.09579| −0.0317 |

None meets the0.95rain threshold. All temperature guards pass. The split reduces
the much larger damage of the common projection but is still worse than the
ORIGINAL winds; that original baseline determines the outcome. Mexico improves,
while India and PNW regress in the location/month-sensitive rainfall loss.
No adoption, shortlist or extra temperature/kinematic search follows.

The architecture diagnosis is supported in its manufactured limit: preserving
lower convergence is necessary to avoid the common-projection collapse, but it
is insufficient to deliver a rainfall gain. Lower-convergence forcing, thermal
energy, pressure adjustment, terrain lift and storm/rain closures still need
independent physical assessment. Do not infer a unique real-world cause from
these steady budget terms or sparse native comparisons.

The next architecture milestone is now an isolated steady forced/damped
baroclinic mode that solves momentum and thermal-thickness adjustment, rather
than another prescribed shear/profile. Nine analytic/conservation tests pass,
including a discrete modal energy identity and heating-generated convergence.
It adds no Earth integrations and is not yet connected to climate. See
[the dry-mode prototype](BAROCLINIC_MODE_20261028.md) for equations, manufactured
example and boundary/heating prerequisites. Normal atlas climates remain.
