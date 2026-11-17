# Plough-package completion now requires people and draft service together

17 November 2026. A small adapter now makes the
[Roman resource distinction](PLOUGH_RESOURCE_CONTRACT_20261117.md) executable:
a supplied plough package requires total human hours, a qualified operator
subset and draft-team service in the same permitted period. It reuses the
existing seasonal farm scheduler and adds no Roman rate, worker fraction,
animal stock or calendar default.

The result is **completed plough-package hectares**. It is not complete crop
area, grain, a full annual farm budget or supported population. No atlas cell
or existing food scenario is rerun.

## Resource behavior

| Manufactured control | Completed package hectares |
| --- | ---: |
| Human20h, operator6h, team9h; rates4/2/3h per ha |3|
| Human8h is the binding resource |2|
| Operator4h is the binding resource |2|
| Team3h is the binding resource |1|
| No team service available |0|
| Operator and team hours occur in different periods |0|
| All supplied hours fall outside the allowed window |0|
| Supplied area ceiling is1.5ha |1.5|
| Three-period window includes the first and last periods |3|

These are deliberately manufactured accounting controls, not reconstructed
ancient farms. Their exact answers follow from the minimum of the three
resource capacities in each permitted period, capped by the supplied area.
The scheduler's results match those separate analytical bounds.

At three hectares the first case spends12 total human hours, of which6 are
operator hours, plus9 draft-team hours. Adding the two human columns to claim18
human hours would double count the operator subset. Conversely, supplying a
generic human budget cannot create qualified operators or ox teams.

The API requires one explicit physical origin, all three per-hectare resource
claims, net time-by-resource availability and a boolean operation window. It
rejects missing or zero draft requirements, impossible operator subsets,
nonfinite/negative quantities and invalid dimensions. Zero *available* team
hours is valid and yields zero completion. All availability is supplied net of
other duties; the adapter does not decide which household tasks can be displaced.
Raw unused-hour residuals are retained without adding rounding credits.

```python
from harvest.plough_resources import plan_plough_package

p = plan_plough_package(
    origin_id='manufactured-origin', maximum_package_hectares=10,
    human_hours_per_hectare=4, operator_hours_per_hectare=2,
    draft_team_hours_per_hectare=3,
    allowed=[True], available_hours=[[20, 6, 9]],
)
assert p.completed_hectares == 3
```

One team-hour denotes a supplied team-service unit, not one animal head or a
feed ration. The coupled package uses fixed proportions in each period and
divisible area, following the existing linear scheduler. It does not infer
pass order, work quality, travel, animal endurance or full resource occupation.
If the caller's package already includes ridging/sowing, those cannot be charged
again as though absent. Other operations, including any draft requirement for
harrowing, still need their own explicit resource definitions.

## Checks and next input

All62 focused adapter and existing farm-scheduler tests pass. They cover
resource binding, disjoint availability, operator double-counting, net human
competition, calendar rotation, time-unit rescaling, fractional area and invalid
contracts. Nine exported analytical controls reproduce byte for byte in a fresh
directory. Original science, source and atlas identities remain fixed.

Artifacts: `output/plough_completion_adapter_20261117/`; implementation:
`harvest/plough_resources.py`. The closed-form checks establish numerical resource
accounting, not empirical AD200 performance. The currently unknown atlas operator
and team capacities remain unknown; the adapter does not consume the current
40% effective-worker count as an operator estimate.

Before adapting the cereal task rates into a seasonal activity, close the
specific seed-volume/land-area link flagged by the source screen: inspect the
same book's cereal sowing-rate passage against its task-count passage, keeping
soil and crop qualifiers. This can establish which part of the existing
per-hectare conversion is text-supported, without changing coefficients or
inventing draft supply. The broader empirical work/animal/window gaps remain.

```sh
.venv/bin/python -m pytest -q tests/test_plough_resources.py tests/test_farm_labour.py
.venv/bin/python scripts/check_plough_completion_adapter.py
.venv/bin/python scripts/check_plough_completion_adapter.py --out output/plough_completion_adapter_20261117/fresh
.venv/bin/python scripts/seal_plough_completion_adapter.py
```

Completed receipts are preserved. Main atlas, population and climate remain unchanged.
