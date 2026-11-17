# Where commercial storage restricts the saved grain flows — 17 November 2026

The large storage effect is closely tied to the stipulated dispatch rule:
concentrated harvested surplus enters a commercial store, but departures are
requested in twelve equal quotas. With a small store, much of that surplus
overflows before it can be dispatched. This read-only audit explains the
[completed factorial](URBAN_STORAGE_LOSS_20261117.md); it runs **zero new food
scenarios** and does not establish historically correct stores or dispatch.

## Commercial ledger

For every origin in both original baselines and six new cases, the audit
reconstructs immediate dispatch, pre-decay capacity overflow, stock loss and
the full stock path. Annual marketed energy equals paid departures plus
spoilage, overflow and final-minus-initial stock. The 451,024 source-case
records include zero-grain and blocked origins.

| Density | Loss / store days | Marketed grain | Paid departures | Commercial overflow |
|---|---|---:|---:|---:|
| Central | 5% / 365 | 30.444 | 29.447 | 0.294 |
| Central | 5% / 90 | 30.444 | 9.901 | 20.477 |
| Central | 0% / 365 | 30.918 | 30.595 | 0.323 |
| Central | 0% / 90 | 30.918 | 10.003 | 20.915 |
| Low | 5% / 365 | 13.203 | 12.765 | 0.132 |
| Low | 5% / 90 | 13.203 | 4.292 | 8.882 |
| Low | 0% / 365 | 13.416 | 13.267 | 0.149 |
| Low | 0% / 90 | 13.416 | 4.337 | 9.079 |

Units are **million grain person-years of energy**, not people. Spoilage and
stock change are retained separately in the
[complete summary](../output/urban_storage_throughput_20261117/summary.csv).
Freight losses occur after these source-store departures; paid departures are
not city meals. The original saved-peak flag that affected 100% of departures
never meant 100% would disappear: actual 5%/90 departures are about one third
of the 5%/365 departures.

## A checked throughput identity

For **zero loss**, exactly one positive marketed pulse per year and routes
open in all twelve bins, annual paid departures obey

`departures = min(annual marketed, annual marketed / 12 + fixed capacity)`.

At the harvest pulse the store can pay one monthly quota immediately, then
carry at most its capacity into later months. With no further marketed pulse,
only that stock can fund the remaining dispatch. This identity is conditional
on those requirements; it is not used for multiple pulses, blocked months or
five-percent decay. Newly eligible origins with zero reference capacity obey
it too: immediate quota is possible, carried stock is zero.

The identity passes at the original inventory tolerance for 44,895 central
and 44,888 low physical origins, covering **98.5090%/98.4578%** of marketed
grain in the zero-loss cases. It covers 99.2974%/99.2770% of 90-day departures.
Thus it accounts for most source flow in this experiment, rather than being
only a toy example. It does not predict city coverage without the downstream
transport and town ledgers. Absolute capacity still references **original**
baseline market, so 90/365 cannot be applied to each new case's marketed
energy to resize the store.

## Why some cities lose meals at zero loss

All 11 central and 8 low city cells losing meals at 90 days receive **more
annual direct arrivals**, and none changes its local protected-exporter flag.
Their combined meal changes are −276.520 and −107.883 person-years. The
[19 city records](../output/urban_storage_throughput_20261117/city_losses.csv)
and [228 monthly records](../output/urban_storage_throughput_20261117/city_loss_months.csv)
retain every case, not only examples.

Eight central and six low losing cells receive less annual intertown grain.
The remaining three central/two low have unchanged intertown receipts: their
direct-arrival gains arrive in bins where additional grain overflows, while
some later direct arrivals decrease. The town has a fixed 90-day store and
cannot turn annual extra arrivals into meals in every month. Source quota
itself rises with newly marketed annual energy while its capacity stays
fixed; saved monthly flows show the resulting temporal redistribution.
This suggests a clean quota control, rather than proving a unique cause for
every origin or an optimal alternative policy.

Across the losing central cells, direct arrivals rise 513.766, intertown
receipts fall 456.939, avoided spoilage contributes 108.130, and additional
overflow removes 441.477 meal-equivalent person-years. Across low cells those
terms are +173.340, −136.461, +35.932 and −180.695. Initial/final-stock
differences are included in the exact row ledgers. Their balances explain
the net losses without inventing missing grain. The largest fractional losses
are 1.011 central and 3.267 low percentage points, in small requested cells;
all larger and smaller cases remain in the tables.

## Review and next comparison

A separate reviewer traces each store bin from recorded initial stock,
reconstructs all public source vectors and the streamed full-source table,
checks the conditional throughput identity and every city/month delta.
Maximum stock-trace difference is 6.37e−6 of the original tolerance; the
throughput identity differs by at most 3.70e−6 of that tolerance. City meal
delta ledgers close within 1.37e−12 person-years. All parent and 1103 protected
identities remain unchanged. Neither producer nor reviewer calls a food
kernel or reads new observations.

The [compact source packet](../output/urban_storage_throughput_20261117/source_accounting.npz)
retains every source-case capacity, marketed total, departure, spoilage,
overflow, stock change, pulse count, route-open count and identity eligibility.
The redundant 60MB full source CSV is local/ignored and can be reconstructed;
the packet and smaller tables are tracked. See the
[qualification](../output/urban_storage_throughput_20261117/qualification.json).
Reproduce with `scripts/audit_urban_storage_throughput.py`,
`scripts/review_urban_storage_throughput.py` and
`scripts/seal_urban_storage_throughput.py` in `.venv`. For a fresh replay redirect
OUT consistently to an empty directory; completed stages refuse overwrite.

The [next frozen comparison](../calibration/urban_diagnosis_20261117/fixed_dispatch_loss_control.json)
holds monthly dispatch quotas at the original baseline market/12 in exactly
two zero-loss/90-day cases, one per density. Four exact existing controls must
pass first. It isolates the quota feedback while preserving absolute stores,
production, work, requests, original dates, routes and shares. No such case has
been run yet. No setting is adopted and no population or main atlas changes.
Historical infrastructure, rights, full diet/work and independent transfer
validation remain unresolved; climate and reserved pools remain unopened.
