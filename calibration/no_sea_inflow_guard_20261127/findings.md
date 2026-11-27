# No-water source guard passes engineering and regional regressions

Warm-sea inflow now requires at least one cell in the existing modeled sea
mask. On an all-land grid, EDT's outside-grid index no longer supplies a
marine temperature/relaxation target, so this branch adds neither marine
moistening nor drying. Boundary humidity and the other moisture processes
remain available. This does not change the classification of water bodies
or adopt the rejected marine-equilibrium cap.

The pre-fix regression reproduced positive marine reach on a grid with no
modeled water, before attempting its coupled solve. After the fix, **30 tests
pass, with no failures/errors/skips**, including four genuine coupled runs:
all-land and all-sea domains with inflow enabled versus disabled. Their seven
physical arrays are byte-identical and their extra land marine exchange is
zero. A mixed-grid check retains valid nearest-water indices and land reach.
The other moisture, transport, reservoir and signed-export checks also pass.

## Seven predeclared regional comparisons

The full 97-case cached-domain audit found four all-land domains. All seven
new integrations (those four and three mixed controls) pass the original
numerical criteria. Every case retains its previous actual input identity,
observations, coordinates, scored cells and parameters. The mixed Somalia,
Sahara and North India controls reproduce both saved monthly T/P fields in
dtype, shape and bytes at float32. The all-land results are reported without
fitting or hiding degradations:

| All-land region | T MAE C, golden r58 → guarded | Rain loss, golden r58 → guarded | Annual rain mm/year, golden r58 → guarded |
|---|---|---|---|
| Kazakh steppe | 1.571333 → 1.571333 | 0.234441 → 0.234441 | 252.70747 → 252.70747 |
| r_12n_22e | 1.232126 → 1.231624 | 0.242337 → 0.242729 | 583.42191 → 583.40761 |
| r_40n_94e | 1.041373 → 1.041640 | 0.225737 → 0.226412 | 44.04603 → 43.95325 |
| s2_7n_23e | 0.639052 → 0.639112 | 0.644943 → 0.644965 | 594.47626 → 594.47330 |

Kazakh scored T/P is also byte-identical. Three other all-land cases change
slightly: the largest annual-rain difference is about 0.093 mm/year, largest
temperature-MAE change about 0.000502 C, and largest rain-loss increase about
0.30%. This is a source-geometry correction, not an accuracy win or a fix for
the large Somali/Saharan rain biases. Warm/onshore gates limit its realized
effect in these legacy configurations; other all-land parameter settings can
activate the old erroneous reach more strongly, as the regression demonstrates.

## Source epoch and limits

The comparison deliberately changes source against preserved fresh-runtime
r58 golden fields. The preceding export-only correction changes no ordinary
physical arithmetic. This is an engineering regression with matched actual
inputs, not a new 97-region paired reference for candidate selection or full
climate validation. Source/input/library hashes were checked before the seven
new integrations, and the design was committed beforehand. No integration
was retried, no solver criterion changed, and no fine or sealed-AA target was
read. Existing failed W18c validation and all historical qualifications remain
unchanged. R58 parameters are retained, atlas r51 is not rebuilt.

`output/no_sea_inflow_guard_20261127/qualification.json` records the new
source epoch, tests, domain audit and regional review. The `guarded/` folder
contains all seven raw case certificates, scored arrays, protocol and summary.
`review_regions.py` independently verifies original certificates, case inputs,
parameter dictionaries, observations/coordinates and exact mixed controls;
it writes the actual changed scores with zero integrations or gate reruns.

The main remaining Somali lead is circulation/coupled transport, rather than
the rejected receiving-land target ceiling or this no-water guard. Retain
desert and monsoon controls for the next bounded physical hypothesis. Before
future calibration or atlas use, create a current source/protocol reference
epoch instead of reusing the older source-pinned qualifications.
