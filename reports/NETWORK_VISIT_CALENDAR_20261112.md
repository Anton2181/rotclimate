# Worker-calendar audit checkpoint — 12 November 2026

Declaration `bdd6135c` preceded outputs. The owner's usage-limit request takes
priority: save and push this computational checkpoint; normal research-atlas
publication and figures remain pending. Existing maps/defaults are unchanged.

The same four food/collection parents and eight original b3_p0 point-visit plans
are retained. Integer supported workers have 50 duty hours per bin and a common
7×365/12-hour calendar. Mandatory divisible home services are shared equally.
Whole collector trips are packed first, longest duration first, using earliest
available workers. Original visits then use synchronized supported crews at
their original providers. Collection failure blocks visits in that provider/bin.
No extra visits, worker-hours, food, people, providers or reassignment is allowed.

Seven manufactured controls pass. All 144 schedule packets and results reproduce
byte exactly in a fresh run. Independent sorted-list reproduction and explicit
interval, task-identity, crew, duty-cap and monthly-ledger checks are implemented
in scripts/review_visit_calendars.py; its completed certificate is review.json.

## Collection packing

|Parent|Required trips|Unpacked trips|Mandatory-failed / relevant provider-bins|
|---|---:|---:|---:|
|raw_h600_load120000_all_open|3,063,143|11,630|444 / 10,332|
|raw_h300_load120000_all_open|2,295,444|4,825|190 / 8,700|
|corrected_h600_load120000_all_open|3,133,456|10,932|398 / 10,668|
|corrected_h300_load120000_all_open|2,351,679|4,214|157 / 9,060|

## Original planned visits

|Case|Planned|Packed within bin|Blocked by mandatory collection|Greedy crew shortfall|
|---|---:|---:|---:|---:|
|raw_h600_crew1|171,885|147,819|1,209|22,857|
|raw_h600_crew4|155,572|137,796|387|17,389|
|raw_h300_crew1|150,501|135,630|469|14,402|
|raw_h300_crew4|136,787|125,940|167|10,680|
|corrected_h600_crew1|179,097|156,465|886|21,746|
|corrected_h600_crew4|163,423|145,972|263|17,188|
|corrected_h300_crew1|157,726|143,809|367|13,550|
|corrected_h300_crew4|144,383|133,867|113|10,403|

These are per-bin packing results, not a new annual food-supported visit map.
Any missing mandatory collector trip means this constructed annual schedule
does not certify the unchanged food deliveries. Greedy failure is not proof
that no schedule exists: collection-first packing can fragment workers' spare
hours before longer visits are attempted. Test any alternative ordering under
a separately committed declaration; do not label these gaps physical collapse.

Availability and divisible services are supplied assumptions. Individual task
intervals are constructive under those assumptions; actual staff functions,
daily food issues, observed visits, dated occupation/sizes, prospective transfer,
complete diets/household/draft work and mobile/nonstate/unaffiliated resources
remain open. No authority or calibrated default is inferred.

Next resume this checkpoint: finish/confirm independent review, publish the
four collection/eight visit tables, calendar/shortfall figures and downloads in
the normal research atlas, post every figure, run browser/mobile/Windows checks,
review the whole programme and push. Preserve all original maps and limitations.
