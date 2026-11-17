# Ploughing needs an operator and a draft service

17 November 2026. The Roman source supports treating ploughing as a claim on
qualified human operator time **and** a simultaneous draft service. It does not
supply the world's operator pool, ox teams, usable working hours or complete
animal/household budget. Keep those as missing inputs instead of deriving them
from the model's40% effective rural workforce.

The [bounded source screen](../calibration/roman_benchmark_20261117/plough_resource_contract.json)
uses one English text witness of Columella bookII, chapters4 and12. Its bytes
match the exact source originally recorded for the cereal task counts. The
site identifies a1941 Loeb translation; no new scan or Latin collation was done.
Only these two chapters are analyzed, despite the full book being downloaded.

## Source findings

| Passage | What the prescription establishes | Consequence for the model |
| --- | --- | --- |
|2.12.1–2|Counts belong to named ploughmen and other occupations.|Operator time is a subset of human work.|
|2.12.7|A tree-free200-iugerum example lists two yokes, two ploughmen and six common labourers; trees alter staffing.|One operator per yoke is a conditional example, not a population-derived capacity.|
|2.4.8|Four days include repeated working, ridging and sowing.|Do not treat the count as identical passes or charge sowing twice.|
|2.4.5–11|Moisture, soil, slope, field quality and timing qualify work.|No universal moisture cutoff or calendar follows.|
|2.12.1–2;2.4.8|The crop list uses seed volume; the method example names area.|The prior seed-volume/area mapping is not independently certified by this screen.|
|2.12.8–9|Another land context changes work totals and reserves time for nonplough days and other duties.|Keep context; do not turn this into a universal annual allowance.|

Read [Columella2.4](https://penelope.uchicago.edu/Thayer/E/Roman/Texts/Columella/de_Re_Rustica/2%2A.html#4)
and [2.12](https://penelope.uchicago.edu/Thayer/E/Roman/Texts/Columella/de_Re_Rustica/2%2A.html#12).
These are agronomic prescriptions from a Roman text, not measurements of AD200
farm occupations. The existing hectare/day conversions and calendar qualifications
remain explicit assumptions. No earlier task coefficient is corrected or adopted.

## Implementable resource equations

For a supplied plough package on area `A`, require three compatible capacities
in the **same** allowed period:

* Total human hours cover the supplied human requirement on `A`.
* Qualified operator hours cover its operator requirement; these hours are
  charged against the same total human pool, not added as a new pool of people.
* Draft-team hours cover a separately supplied team-service requirement.

The operator availability must not exceed the human availability in a period.
An ox-team budget cannot be inferred from human headcount. Human hours in one
period and team hours in another cannot complete the same coupled operation.
The existing `harvest.labour` scheduler already supports simultaneous resource
claims, so no second scheduling algorithm is needed.

A one-operator/one-team scenario may be supplied explicitly, following the
relationship in the source's estate example. Its numeric hours, team endurance,
feed and availability are still scenario inputs. Neither that example nor the
current annual allowance certifies actual resources on an atlas cell. Harrowing
must not silently become draft-free merely because this screen focuses on ploughs.

The next implementation is therefore a **plough-package completion adapter**
around the existing scheduler, with supplied human/operator/team quantities and
windows. Its output must be completed plough-package hectares, not grain,
complete crop area or newly supported people. Manufactured numerical controls
can establish resource accounting without pretending to provide an Earth
calendar or an animal population.

## Missing inputs before a seasonal atlas result

The large ploughing demand in the
[operation assessment](CEREAL_OPERATION_DEMANDS_20261117.md) still has no
qualified operator subset, draft supply or usable weather/soil window. Its
barley three-day aggregate has no qualified per-pass decomposition here.
Processing, animal care/feed, competing tasks, seed/area linkage and the
all-barley crop-choice limitation remain unresolved. An adapter passing its
accounting tests cannot close those empirical gaps.

The screen records20 paragraph digests and10 located claims in
`output/plough_resource_contract_20261117/`. Original HTML and analytical text
stay under ignored `source/`; the source receipt preserves URL/hash/access.
An independent streaming parser checks the selected paragraph boundaries and
digests, located quantities and claim references. Prior scientific and atlas
identities are checked; fresh scientific exports match byte for byte. This is
source/provenance qualification, not independent historical validation.

```sh
.venv/bin/python scripts/qualify_plough_resource_contract.py
.venv/bin/python scripts/qualify_plough_resource_contract.py --out output/plough_resource_contract_20261117/fresh
.venv/bin/python scripts/review_plough_resource_contract.py
```

No model scenario, rate fit, population, atlas default or climate change occurs.
