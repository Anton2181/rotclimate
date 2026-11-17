# Storage and dispatch evidence: next development direction — 17 November 2026

The numerical controls are now sufficient to identify the immediate problem:
the monthly model depends strongly on where grain can be held and how it is
released. Existing documentation does **not** qualify an ancient capacity or
loss coefficient. The next useful work is source and interface qualification,
rather than another capacity sweep or a climate adjustment.

This completes the [declared scope](../calibration/urban_diagnosis_20261117/storage_dispatch_source_scope.json):
nine existing source/interface contracts and three bibliographic leads. No
new archaeological quantity, site intersection, population estimate or fitted
parameter was extracted. No food, phenology or climate kernel ran. The
[contract manifest](../output/urban_storage_source_scope_20261117/existing_contracts.csv)
preserves exact existing quotes and what each source cannot establish.

## What is already supported

The reserve algebra and stock kernels support energy conservation and minimum
repeating reserves under supplied harvest and demand. They do not reconstruct
historical stocks, construction, ownership or risk management. The early
presence/mobility prototype explicitly called its one-year export store an
assumption, so its reuse cannot become historical evidence through repetition.

The existing consultation log for the
[FAO bulk-store manual](https://www.fao.org/4/t1838e/t1838e19.htm)
already separates short harvest receipts, dispatch schedules and finite buffer
capacity. This is modern mechanism/context, not an ancient storage estimate.
The old Erdkamp publisher-excerpt log also separates physical supply from
entitlement. Neither complete monograph nor new manual measurements were read
in this stage. Freight costs likewise do not determine trip duration, fleet
capacity or historical seasonal shipment quantities.

The [fixed-quota control](URBAN_FIXED_DISPATCH_20261117.md) isolates the local
quota feedback: 18 of the 19 previously losing city cells improve, and one
recovers to equality against the five-percent control. It does not establish
the best dispatch policy. The tested commercial-capacity effect is much larger
than the quota effect in aggregate, but that does not choose an empirically
correct granary size. Archaeological evidence must distinguish physical stores
and institutions before their capacities can be assigned to modeled origins.

## Three leads, with access limits

| Lead | Access in this stage | Potential interface | Still unqualified |
|---|---|---|---|
| Javier Salido Domínguez (2018), [rural horrea capacity critique](https://revistas.ucm.es/index.php/GERI/en/article/view/60294) | Journal metadata and abstract | Assumptions behind archaeological capacity calculations | Full-text methods, example provenance, usable volume and model relevance |
| Astrid Van Oyen (2020), [Control (Flow): Ostia and Portus](https://www.cambridge.org/core/books/abs/socioeconomics-of-roman-storage/control-flow-warehouses-in-the-ports-of-ostia-and-portus/CD3841AF3DA4A937E875B6197014450B) | Publisher metadata and summary | Commodity turnover and institutional/time distinctions | Chapter body, primary claims and any numerical store/dispatch relation |
| Geoffrey Rickman (1971), [Roman Granaries and Store Buildings](https://agris.fao.org/search/en/providers/122535/records/65de068d0f3e94b9e5c9760f) | AGRIS/National Agricultural Library catalogue | Granary classification and primary-source trail | Monograph body and every physical/institutional inference |

Salido's abstract challenges capacity proposals through construction and grain
organization factors. Van Oyen's chapter summary treats port storage through
different commodities and temporal registers. These justify reading the methods
and questioning the interface; they do not supply a replacement coefficient.
Rickman's catalogue authenticates a bibliographic lead, not its archaeological
claims. No full article, chapter or monograph body was read during scoping.

The [exposure record](../output/urban_storage_source_scope_20261117/exposure.json)
retains the two discovery queries and access scope. Search snippets can expose
quantitative statements incidentally; none was transcribed or used. A military
granary search hit is explicitly recorded as excluded/unopened. These leads and
search exposure are development material, not an unseen validation pool.

## The practical plan

1. **Next: qualify one accessible methods source.** The
   [frozen declaration](../calibration/urban_diagnosis_20261117/storage_capacity_method_qualification.json)
   targets Salido's full article. Verify source bytes and page locators, then
   separate observations, author estimates, modern analogies and unknowns.
   Start with function, geometry, grain form and chronology. No site measurement
   table or model fit is authorized by that declaration.
2. **Define the storage/dispatch interface.** A warehouse footprint is not
   usable grain volume; volume is not edible stock; stock is not capacity;
   capacity is not throughput. Rural retention, commercial export staging,
   urban warehouses and military/state/household stocks need distinct provenance.
   Days of *modeled* marketed energy also need a defensible flow denominator.
3. **Only then declare the next model integration.** A defensible interface
   must precede another capacity/dispatch variant or coupled occupancy stage.
   Food, workers and remaining rural population must stay on the same physical
   source ledger. Full diet/resources/work, rights and independent transfer
   still require their separate gates before atlas adoption.
4. **Return to climate later.** The logistics uncertainty is not a target for
   climate fitting. The archived steppe experiment and reserved Buringh size/
   climate `l` pools remain unopened.

This stage qualifies **zero new historical numerical parameters**. It identifies
a narrow next primary-source task and moves the project away from accumulating
numerical variants without evidence. Published defaults and actual population
remain unchanged.

## Checks and reproduction

The scope checks all nine exact existing quotes, parent qualification/file
identities and all 1103 protected identities before and after inventory. The
[bibliographic manifest](../output/urban_storage_source_scope_20261117/bibliographic_leads.json)
records author/year, source URLs, access limits and cannot-infer fields; the
[receipt](../output/urban_storage_source_scope_20261117/qualification.json)
does not claim to validate unread source bodies. Replay with
`scripts/scope_urban_storage_sources.py` then
`scripts/seal_urban_storage_sources.py`; redirect OUT to an empty directory
for fresh replay because completed outputs refuse overwrite. No network
request is necessary to replay the recorded local scope. Live access metadata
can change and should be checked again when obtaining the full source.
