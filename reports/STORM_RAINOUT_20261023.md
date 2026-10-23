# Explicit condensation during storm moisture transport

The r31 rainfall maps show opposing errors: California's coast is too dry
while its interior is too wet; Japan misses wet coastal terrain; eastern
Australia is broadly too wet. Global convergence and evaporation adjustments
did not pass the wider development gate. This round tests the placement of
storm condensation instead.

## New opt-in physical closure

`eddy_moisture_scheme="conservative-rainout"` takes six short storm-exchange
hops, testing local crest saturation after each. Its capacity is the existing
crest-column saturation divided by `eddy_rainout`. Vapor above that capacity
condenses locally; subsequent hops carry only the remaining vapor. The
condensate stays at its formation cell and becomes rainfall.

Each hop uses the symmetric conductances from the conservative exchange
operator. With local loss L and incoming term I, choose an event frequency
f = max(L) and use the nonnegative transition

    W_next = (1 - L/f) W + I(W)/f.

The Gaussian width per hop is the full storm scale divided by sqrt(6).
At constant rate and air-column mass, with no condensation, the six hops
approximate the original wide Gaussian. The finite kernels are truncated,
so this is an approximate Gaussian composition. At varying rates/masses it
defines a different, explicitly conservative storm closure. Optional terrain
column mass remains supported. With zero storm activity the event is inactive
and cannot condense water.

Let V(W) be surviving vapor and C(W) the sum of local condensate. Over the
closed full grid, sum(V + C) = sum(W). The steady moisture solve uses
f V(W) as the incoming source and f W as the implicit outgoing term. Its
reported rainfall is ordinary rain plus f C(W). Adding another condensation
sink to the matrix would remove the same water twice; that is avoided.

Local equation diagnostics use V + C as the transport target and include
condensation in the rain sink:

    E - (P_ordinary + f C) + f (V + C - W)
      = E - P_ordinary + f (V - W).

The numerical certificate checks storm cancellation and records condensation,
net vapor loss and supply across the prescribed boundary ring at every step.
This closes the storm event's accounting, not the entire atmospheric model:
mean-wind concentration transport and the existing positive convergence import
are unchanged. The closure does not resolve cloud trajectories, latent heating
or falling-rain evaporation; it is an experiment in unresolved storm transport.

The default legacy scheme and the existing conservative scheme retain their
behavior. Legacy crest clipping is preserved for reproducibility; its removed
vapor must not be described as accounted rainfall. The new scheme explicitly
requires finite positive `eddy_rainout`.

## Verification and comparison protocol

The focused climate, transport, solver, Earth calibration and benchmark tests
pass **137/137**. Tests include an analytic two-box example proving that rain
does not move with later vapor hops, variable storm rates/column masses,
nonnegative water, closed-domain vapor-plus-rain conservation, a mountain
barrier reducing delivery to its dry side, inactive storms, in-place cache
invalidation and a steady moisture problem with known W = 5 mm and P = 3 mm/day.
A coupled seasonal mountain case passes the actual local equation tolerance
and storm budget checks.

The control was rerun under the new source fingerprint on all **31 development
regions at 56 km**. Every regional temperature/rain metric and monthly-cell
file hash exactly matches the historical r31 reference; all observed numerical
checks pass. The overall monthly temperature MAE remains **2.101623 °C**,
monthly rainfall MAE **31.528858 mm**, rainfall loss **0.480956**.
`output/storm_rainout_20261023/reference_reproduction.json` records the pairing.

Before pilot results, `calibration/storm_rainout_20261023/plan.json` freezes
two candidates: the new scheme with `eddy_rainout=0.75` or `1.0`, with all
other r31 parameters fixed. The same six development regions and rainfall,
temperature and individual-region protections apply. Pilot review now accepts
exact predeclared parameter combinations, allowing a scheme and its required
strength to change together; mixed combinations and extra changes are rejected.
No error threshold or development gate is loosened.

Reproduce the paired control:

```sh
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 .venv/bin/python -I scripts/benchmark_local.py \
  --fit calibration/local_accuracy_20261023/r31_params.json \
  --regions dev31 --workers 2 --out output/storm_rainout_20261023/reference
```

For either candidate, use the same command with the six pilot region names,
the appropriate output folder, and for example
`--set '{"eddy_moisture_scheme":"conservative-rainout","eddy_rainout":0.75}'`.
As with previous campaigns, observation archives and monthly cell NPZs are
local ignored caches; a fresh checkout recomputes missing cells. Frozen
protocols and regional numerical/metric evidence are tracked in the repository.

Only a successful full dev31 gate can advance to the finer-resolution and
established validation comparisons. These are reused development/validation
regions, not a newly independent test set. A passing local benchmark would
still require map calibration and native atlas verification before publication.

## First pilot outcome

All **12 candidate regional simulations** pass their numerical and storm
conservation checks, but neither setting meets the predeclared accuracy limits.

| Scheme / crest coefficient | Rainfall loss | Monthly rain MAE | Monthly temperature MAE |
|---|---:|---:|---:|
| r31 legacy control | 0.476515 | 36.423 mm | 1.99206 °C |
| Conservative rainout, 0.75 | 0.516734 | 38.553 mm | 2.00666 °C |
| Conservative rainout, 1.00 | 0.662955 | 58.263 mm | 2.03336 °C |

The 0.75 setting improves eastern Australia's loss **0.55227 → 0.39948** and
Mexico's **0.64823 → 0.60430**, but worsens California, Central Asia, China
and Japan. California, Central Asia and Japan exceed the individual monthly
error limits. At 1.00, Japan becomes much too wet and mean temperature error
also exceeds its limit. `pilot_review.json` selects neither candidate.

These results establish accounting, not an accuracy gain. The scheme remains
opt-in; r31 parameters and published atlases are unchanged. No full candidate
dev31, finer-grid or validation run is justified by this first screen. The
retained evidence covers **43 verified regional simulations**: the 31-region
reference plus 12 candidate regions. Further diagnosis should distinguish the
effect of conservative storm transport from that of local condensation before
attempting another rainout setting.

## Transport and condensation controls

The follow-up `attribution_plan.json` predeclares three comparisons: the existing
wide conservative exchange, six conservative hops with effectively unlimited
capacity (`eddy_rainout=0.000001`), and one weaker crest coefficient (0.5).
All **18 regional simulations** pass numerical checks. The unlimited-capacity
case has **zero actual condensation at every seasonal step in every region**.

| Scheme / crest coefficient | Rainfall loss | Monthly rain MAE | Monthly temperature MAE |
|---|---:|---:|---:|
| r31 legacy control | 0.476515 | 36.423 mm | 1.99206 °C |
| Wide conservative exchange, no rainout | 0.493426 | 35.606 mm | 2.01527 °C |
| Six conservative hops, no condensation | 0.488019 | 35.677 mm | 2.00212 °C |
| Six conservative hops, 0.50 | 0.490237 | 35.626 mm | 1.99869 °C |

None passes the unchanged pilot limits. The wide operator worsens rainfall
loss, Central Asia's monthly error and temperature error. Short hops improve
some of those effects but still worsen mean rainfall loss and exceed
California's monthly-error limit. The weaker crest cap does not resolve this.
`attribution_review.json` selects no candidate for dev31.

The mechanism is clearer after these controls. Regional mean annual rainfall
in eastern Australia falls from **1,066 to 922 mm** under short conservative
hops, against **641 mm observed**, even without condensation. Its large
improvement comes primarily from transport. In Central Asia, however, the
same change lowers rainfall from **200 to 136 mm**, against **228 mm observed**.
The current fit relies partly on the legacy exchange's nonconservative
moisture supply; a conservative replacement needs a broader physical retune.
The data do not support treating an accounting fix as an accuracy fix.

Japan also illustrates why regional annual totals are insufficient. With
rainout 0.75, its annual regional mean moves from **1,238 to 1,318 mm** toward
the observed **1,601 mm**, while monthly cell MAE worsens **65.53 → 83.22 mm**
and rainfall loss **0.40005 → 0.50878**. More water alone does not put rainfall
in the correct months and locations. At 1.00 the regional mean overshoots to
**2,408 mm**.

The completed campaign retains **61 verified regional simulations** and the
unchanged **137 passing targeted tests**; `verification.json` checks all saved
monthly-cell hashes, current scientific-source hashes and storm certificates.
Both experiment families are complete, with no candidate promoted, no use
of the established validation regions and no simulation left running. The
new operator remains available for future joint physical calibration; no
r31 fit or atlas packet is replaced.
