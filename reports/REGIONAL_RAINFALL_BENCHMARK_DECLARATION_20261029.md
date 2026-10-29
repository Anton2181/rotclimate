# Fixed observed-rainfall development benchmark

The next benchmark will compare complete calendar months with WorldClim on the
same geographical footprints, with both wet and dry initial water states. It
moves beyond first-day resolution responses without assuming fourteen days can
erase soil-water memory. No parameter is optimized in this experiment.

Three qualified r39 controls will reproduce the archived strict numerical checks
and float32 monthly fields before their raw climate is used for comparison.
Their input identities already match the original records exactly. Raw 25-step
annual output will be reaggregated with the existing Gregorian interval-overlap
method, avoiding a comparison between old equal-month totals and new calendar
months. These are three new legacy benchmark attempts, counted separately from
prototype trajectories. No failed control is silently replaced.

Seven prototype trajectories use the completed four-part first-cell grid at
224 km: wet 50 and dry 0 kg/m² starts in India/July, Mexico/August and Pacific
Northwest/July, all at 900 seconds, plus Mexico/wet at 450 seconds. The extra
Mexico control is numerical sensitivity only; its earlier spatial timestep
rain difference was the largest of the three regions. Each trajectory has a
fixed fourteen-day prelude followed by its complete 31-day evaluation month.
The prelude is not claimed to eliminate initialization uncertainty.

The fixed solver cap is 1024 with the original 0.01 K target tolerance and
3600-second convective relaxation. The atmospheric initial state is identical
across wet/dry starts. The ground is rebuilt from the common raw temperature,
then receives actual conversion rain and enthalpy once; different initial water
also changes heat capacity. No observed wind, humidity or rain is supplied as
prototype forcing. Lateral simulated monthly reservoirs stay fixed and inherit
their older model backgrounds, making this a conditional regional experiment.

The scoring footprints are centered projected 224-km cells. Fine end pixels
contribute half widths, rather than substituting shifted 4×4 blocks or point
observations. Areas include the projection Jacobian. The primary mask requires
an interior model-land center and at least 80% valid reference land area, using
the same masks and weights for r39 and every prototype branch. It has 24, 23 and
12 eligible cells respectively. Masks are fixed before any new forecast score.

The primary metric is area-weighted rainfall MAE in mm/day per region/branch,
then an equal mean over the six 900-second losses. Branches are scored before
averaging; averaging wet/dry predictions first can cancel large errors. Scenario
weights are declared choices, not inferred probabilities. Regional tradeoffs
are allowed. A pooled comparison is withheld if a primary monthly trajectory is
incomplete, its saved budgets fail, or its r39 control does not reproduce.

The literal plan also specifies bias/RMSE, rainfall and initialization ranges,
fixed elevation/coast attributions, Mexico timestep sensitivity and diagnostics
for liquid surfaces below freezing. No clipping or outcome-based mask change
is permitted. All failures and available partial states remain in the record.
Three reused region/month pairs do not establish annual or held-out global skill.
Terrain, partial upper atmosphere, neutral exchange and liquid-only physics
remain limitations. The benchmark adopts no physical model or atlas climate.

All ten case preparations pass without integration. Four new geometry/scoring
tests and a 31-test focused suite pass. The benchmark controller waits for the
current fine-grid batch receipt, freezes its actual counters, and runs two
independent worker processes. No benchmark trajectory has started at declaration.
