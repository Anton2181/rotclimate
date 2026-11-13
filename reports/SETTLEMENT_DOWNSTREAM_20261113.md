# Reach, trade and administration rebuilt on the release-3 towns

**Outcome.** Every downstream layer that reads town positions now has a version
built on the [release-3 towns](SETTLEMENT_RELEASE3_20261113.md), and the atlas
shows those versions by default. The earlier versions remain published and
byte-identical. Nothing downstream was refitted: these are reruns of the
existing rules with one input changed.

Protocol: [plan](../calibration/settlement_downstream_20261113/plan.json),
committed before any downstream output.

## What was rebuilt

| Layer group | Method | Now shown by default |
|---|---|---|
| Effective control, hardest month, months within a day, days beyond the roads, days from the capital, what closes the roads, who reaches where | standard exporter, both climates | yes |
| Trade routes and market views | same run (directed freight) | yes |
| Imperial access (six source cases) | access audit rerun | yes |
| Administrative links (six views) | hierarchy audit rerun | yes |
| Supply-supported reach (control v2.1 and v2) | full chain rerun: market hinterlands → joint food budget → field work → soil fertility → control v2 → v2.1 | yes |

Safe sailing season does not depend on towns and is unchanged.

## Controls

- **Exporter.** Before changing anything, the unmodified exporter was run in the
  same staging setup for both climates. It reproduced every published reach and
  trade image **byte for byte**. So the differences below come from the towns.
- **Placement.** The standard placement call is routed to the reviewed release-3
  positions and refuses any other input; it was used in every run.
- **Administration.** The access cases that do not use proposed towns (recorded
  centres, marked places) are identical to the earlier audit to four decimals.
- **Fertility cache.** A cached factor file missing from this checkout was
  regenerated with its own builder; its tracked summary came out unchanged.

## What changed (corrected climate; raw is similar)

| Measure | Earlier towns | Release-3 towns |
|---|---:|---:|
| Claimed land within two days of the network | 83.1% | 81.8% |
| Land held under control v2.1 | 67.5% | 67.0% |
| Claimed but unheld land | 8.5% | 9.2% |
| Towns the joint food budget can staff | 1,011 | 1,013 of 1,053 |
| Imperial towns used as access sources | 452 | 477 |
| Imperial claim reachable all twelve months (proposed towns as sources) | 59.1% | 60.7% |
| Share of trade mass in the ten largest markets | 2.0% | 2.1% |

The pattern is consistent: towns moved towards the old heartlands, so the
heartlands are slightly better connected and the far periphery slightly thinner.
No headline number moves by more than about one and a half points.

## Update: residents now drive the supply-supported reach

By owner decision the default supply-supported reach takes its staffed towns from
the calibrated residents as fed by the [wide grain supply scenario](SETTLEMENT_WIDE_SUPPLY_20261113.md)
(one third of surplus marketed). A town is staffed when it has a polity and at
least 150 fed residents. Corrected climate: 1,042 of 1,053 towns staffed (1,013
under the 7.5% rule), 68.2% of land held (67.0%), 8.3% claimed but unheld (9.2%).
The 7.5% version stays available. The first two limits below now apply to that
earlier version only; the new default instead rests on an untested supply scenario.

## Limits

- **Sizes are not fed in.** The supply-supported reach keeps the chain's original
  town request (7.5% of served people), because that request is part of the rule
  that was blind-tested on Earth. Feeding the release-2 calibrated residents
  (about four times larger in total) would be a new, untested model.
- **Earth tests cover the rule, not this map.** The control rule's blind tests
  were run with the earlier placement rule.
- **No place-by-place ledger for the new supply-supported reach.** The
  interactive food ledger under that map still describes the earlier towns; the
  release-3 option shows the map only.
- The monthly work-calendar and visit experiments were not rerun.
- The "Towns and names" overlay marks the campaign's own places only and is
  unaffected.

## Reproduce

```sh
# reach and trade (about 17 minutes per climate; --legacy runs the control)
.venv/bin/python -I scripts/export_reach_release3.py <staging atlas>
.venv/bin/python -I scripts/publish_downstream_release3.py <raw staging> <corrected staging> <raw control cache> <corrected control cache>
# administration and the supply-supported reach chain: existing builders, output folders redirected
.venv/bin/python -I scripts/run_on_release3.py scripts/review_imperial_access.py "'output/imperial_access_20261104'=>'output/imperial_access_release3_20261113'"
.venv/bin/python -I scripts/run_on_release3.py scripts/review_administrative_hierarchy.py "'output/administrative_hierarchy_20261104'=>'output/administrative_hierarchy_release3_20261113'"
.venv/bin/python -I scripts/run_on_release3.py scripts/review_settlement_integration.py "settlement_integration_20261104=>settlement_integration_release3_20261113"
# ... extend_settlement_labour, extend_settlement_fertility, build_control_v2, build_control_v21 likewise
.venv/bin/python -I scripts/publish_supply_reach_release3.py
```

The staging atlas is a copy of `atlases/earth_fit/data` (for the corrected
climate, with the corrected files and metadata overlaid). The publishers that
write into the atlas were run in place, their outputs moved under
`data/release3/`, and the published files restored from git. Five browser checks
pass: settlements 8, reach and trade 16, access 12, links 12, supply reach 4.
