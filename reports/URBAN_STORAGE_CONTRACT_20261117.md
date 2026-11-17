# Explicit physical-store conversion contract — 17 November 2026

The source review now has a working isolated contract in
[polity/storage_capacity.py](../polity/storage_capacity.py). It keeps missing
physical inputs unknown, validates units/material definitions and separates a
geometric edible-energy equivalent from an operational or historical storage
capacity. It is disconnected from the food producers and atlas.

All six existing central/low rural, commercial and town budgets retain their
original values and **scenario** status. The
[interface audit](../output/urban_storage_contract_20261117/model_interfaces.csv)
does not supply physical-store measurements for any class. It records the
missing geometry/material and building-function/phase/access evidence rather
than treating modeled flow-day capacities as archaeological observations.
The model's grid coordinates are known; locations of corresponding physical
storage facilities are not supplied by those budgets.

## What the contract does

Each `Quantity` carries a value or explicit unknown, canonical unit, evidence
kind, source and locator. Evidence kinds distinguish observation, author
estimate, analogy, scenario and unknown. Numerical labels are not independently
authenticated by the module. A `PhysicalStore` records identity, role,
location, phase, access, commodity, stored state and target edible-energy pool.
Labels describe the proposed context; they do not establish rights or dates.

For a **single commodity allocated to usable space**, the declared scalar
arithmetic is area × effective depth → volume × matching stored-state density
→ mass × net-edible yield × edible energy/kg. All factors are explicit; none
is inferred from the article or supplied by a default. Canonical units are
`m2`, `m`, `kg_stored/m3`, `kg_edible/kg_stored` and `kcal/kg_edible`.
This is our bookkeeping relation, not Salido's storage law.

Gross footprint and unallocated mixed space are rejected. Density must match
both commodity and stored state. A known structural limit (`kg_stored/m2`)
rejects a proposed fill above that limit. Unknown support, preservation,
duration, phase or access remains visible. A structural check passing does
not establish safe long-term storage. Already-net edible material must be
labelled `net_edible` and cannot receive another seed/processing deduction.

An explicit positive `kcal/year_365` reference can convert geometric energy
to flow-days only when commodity, location, phase and energy pool match.
Zero, missing or incompatible flow yields **undefined days**, not zero,
infinity or a guessed buffer. Energy and day results remain conditional.
`operational_capacity_kcal` stays unset and `empirically_qualified` stays false;
this arithmetic component cannot award historical qualification.

## Verification and read-only application

Twenty-three meaningful tests pass: explicit unit arithmetic, missing depth
or density, unallocated/mixed/gross space, material/state mismatch, unsupported
load, unknown operational constraints, repeated deductions, husked material
mislabelled as already edible, zero/unknown/mismatched flow and invalid values.
The seven public
[manufactured examples](../output/urban_storage_contract_20261117/manufactured.json)
use invented inputs labelled scenario/unknown. Their numbers are not ancient
densities, fill heights or conversion factors.

A separate reviewer recomputes 18 volume/mass/energy/day results with Decimal,
checks five explicit invalid-input rejections and verifies all six model
capacity totals exactly against the existing buffer table. Unknown depth and
density leave energy unset. Unknown operational support can coexist with a
conditional geometric calculation, but never with an automatically qualified
operational capacity. Even an `observation` label alone cannot change that.

The existing budgets remain 365 days of rural meals, 365 days of original
baseline marketed energy and 90 days of city meals. The interface audit reads
their saved summary only, without rerunning stocks or changing capacities.
Their capacity totals are energy equivalents, not residents or observed grain
volumes. The new module does not attach a building, infer ownership or alter
dispatch. Zero new site measurements, food scenarios, fits or validation
claims were created; all 1103 protected parent identities remain unchanged.

## Next concrete evidence task

The [next declaration](../calibration/urban_diagnosis_20261117/ostia_store_source_qualification.json)
targets one primary archaeological chapter already cited by the reviewed
article: Boetto, Bukowiecki, Monteix and Rousse (2016), *Les Grandi Horrea
d'Ostie*. Its body has not been read yet. The task is to verify the source and
record its explicit function, phase, commodity, physical geometry, structural
and operational evidence for this one complex. Source measurements, estimates,
reconstructions and unknowns must remain distinct.

That stage may produce an indeterminate capacity; missing height, density or
usable space will not be invented. It will not turn the complex into a modeled
origin store or divide by modeled export flow. No new food scenario follows
automatically. Actual population, atlas/defaults and policy shares stay fixed;
complete diet/work, rights and independent transfer remain separate gates.
Climate and the archived steppe experiment remain deferred.

Reproduce in `.venv`: `scripts/audit_storage_capacity_contract.py`,
`scripts/review_storage_capacity_contract.py`, then
`scripts/seal_storage_capacity_contract.py`. See the
[qualification](../output/urban_storage_contract_20261117/qualification.json)
and [test receipt](../output/urban_storage_contract_20261117/tests.json).
Completed outputs refuse overwrite; redirect OUT consistently to a fresh
directory for replay. Original food code and outputs remain frozen.
