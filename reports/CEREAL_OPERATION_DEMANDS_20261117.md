# Ploughing is the first seasonal resource question

17 November 2026. The operation breakdown is complete on the same retained
cereal hectares and physical workers. **Ploughing accounts for46.15% of the
listed barley work**, compared with15.38% for reaping. Before adding another
harvest or logistics mechanism, we need a defensible ploughing resource and
workability contract: the human crew, draft service and usable window must
refer to the same activity.

This implements the [declared preparation](../calibration/roman_benchmark_20261117/cereal_operation_demands.json)
using only the qualified [origin activity packet](CEREAL_ACTIVITY_PACKET_20261117.md)
and the existing Columella2.12 task transcription. The packet's all-barley choice
is retained as a model limitation, not adopted as a historical crop mix. No new
climate, crop, field-support, food, freight, population or calendar run occurs.

## Fixed demand, conditional allocation thresholds

| Prescribed barley operation | Days/iugerum | Assumed hours/ha | Share of listed work | Maximum full8-hour-worker days at600h allowance | At300h |
| --- | ---: | ---: | ---: | ---: | ---: |
| Ploughing |3|96|46.15%|34.62|17.31|
| Harrowing |1|32|15.38%|11.54|5.77|
| First hoeing |1.5|48|23.08%|17.31|8.65|
| Reaping |1|32|15.38%|11.54|5.77|
| All listed operations |6.5|208|100%|75.00|37.50|

The conversion assumes0.25ha/iugerum and eight hours per workday. A task's
threshold is its hours on the retained area divided by that origin's actual
effective workers, then by eight. A34.62-day threshold means the supplied
workforce would all have to devote34.62 full eight-hour days to that task.
It does **not** establish that such days, crews or animals are available, that
they fall in one continuous window, or that the source's workday was eight hours.
Tiny departures in unrounded maxima reflect the existing encoded-rate residuals.

The threshold maxima are nearly identical across the16 physical cases within
each allowance, because most origins are limited by the same annual hours and
use the same prescribed barley task proportions. This is an algebraic property
of the current scenario, not new regional empirical agreement. The downloadable
medians weight each defined origin equally; they are not person-weighted results
or archaeological uncertainty intervals. No workers move between origins.

For corrected central600h, the retained45.3164million hectares imply:

| Operation | Normative hours, billion |
| --- | ---: |
| Ploughing |4.3504|
| Harrowing |1.4501|
| First hoeing |2.1752|
| Reaping |1.4501|
| Total |9.4258|

Reaping is already part of that total. Adding another reaping charge would
double count it. In this baseline the30-day/eight-hour peak allowance exceeds
the11.54-day reaping threshold. That explains the preceding zero reaping-limit
count; it does not show that harvest weather or competing duties were harmless.

## Unknown tasks and rounding stay explicit

The barley transcription does not prescribe separate second-hoeing or weeding
counts. Their demand stays undefined, rather than becoming an asserted zero
historical workload. Origins without a selected cereal also retain undefined
task demand. Positive task hours with zero effective workers would have undefined
worker-days, not zero days or a fabricated crew. The reader preserves these
distinctions in its arrays.

Normative operations are computed from hectares, while the archived annual and
reaping totals use encoded float32 work-per-calorie coefficients. Their signed
differences are retained separately. Corrected central600h has canonical minus
normative listed work of−194.94hours across the grid; its reaping difference is
+10.91hours. Neither is redistributed into a task, added to available hours or
silently clamped. The canonical grain/work accounts are unchanged.

## What must be constrained next

**Next: qualify the human/draft meaning of the ploughing prescription.** Inspect
the already relevant Columella bookII task-count and ploughing-method passages
as one finite primary-source screen. Identify whether the stated days describe
human work, a crew/yoke service or another unit; which implement, soil and
ploughing passes they include; and which quantities remain absent. A plough-day
cannot automatically become one interchangeable worker-day when draft capacity
is missing. The result should specify separate resource claims before any
seasonal constraint is added.

The existing [calendar witness](COLUMELLA_CALENDAR_20261117.md) already qualifies
ploughing by soil, moisture, weather and region. Its unresolved edition variants
and conditional prescriptions cannot supply a universal sowing date or measured
soil-workability threshold. Processing, animal care/feed, irrigation, maintenance
and household duties also remain outside these four task counts. The next source
screen must leave missing requirements unresolved instead of inventing a full
occupation or drawing a new feasible-population map from partial work.

## Artifacts and verification

[Operation summaries](../output/cereal_operation_demands_20261117/operations.csv)
contain64 case/task rows; [case accounting](../output/cereal_operation_demands_20261117/cases.csv)
retains canonical and normative totals and residuals. The
[recipe](../output/cereal_operation_demands_20261117/recipe.json) references the
same16 physical cases rather than duplicating source land/workers across32
marketed-share alternatives. Its per-origin demands are materialized from the
existing tracked activity packets, with no second large binary copy.

The separate review checks all per-origin task/worker-day values, every summary,
the normative-total and reaping-subset identities, missing-prescription behavior,
zero-worker behavior, prior protected outputs and byte-exact fresh reproduction.
These are numerical/source-transcription controls, not empirical workload or
seasonal-feasibility validation. The atlas and climate remain unchanged.

```sh
.venv/bin/python scripts/cereal_operation_demands.py
.venv/bin/python scripts/cereal_operation_demands.py --out output/cereal_operation_demands_20261117/fresh
.venv/bin/python scripts/review_cereal_operation_demands.py
```

Completed receipts are preserved. The Python `demands()` reader returns aligned
normative hours, hours per effective worker and conditional full8-hour-day
equivalents, retaining `NaN` for unknown quantities.
