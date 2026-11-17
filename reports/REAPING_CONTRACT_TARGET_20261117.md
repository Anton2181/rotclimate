# The reaping contract gives area and crew, but no completed-work rate

17 November 2026. The bounded alternative target screen found a primary
contract with a stated wheat area and a contracted reaper complement.
**It does not establish their elapsed work on that area.** No reaping-rate
fit, ploughing-rate fit or annual labour-capacity calibration is justified.

The [declaration](../calibration/roman_benchmark_20261117/documented_task_target.json)
allowed three searches and two source bodies. Those limits are complete:
Llewellyn Howes's2023 discussion and its cited primary P.Sarap.51/TM17068,
with metadata for that same record. No other primary contract was opened.

## The citation needs care

[Howes, pp.57–75](https://doi.org/10.1017/S0028688522000303) quotes a54-aroura,
six-per-worker agreement with5/6artaba remuneration and cites P.Sarap.51 in
note189. The [official digital P.Sarap.51 edition](https://github.com/papyri/idp.data/blob/0adcd9651ec240726a5b62028cd5c153bf45ffd0/DDbDP/17/17068.xml)
instead records130arourai, ten supplied reapers plus three from the other
party, and remuneration fractions encoded as1/2 and1/12. This is an unresolved
quotation/citation mismatch. Neither source is silently amended, and the
quotation's numbers are not substituted into the primary record.

[HGV17068](https://github.com/papyri/idp.data/blob/0adcd9651ec240726a5b62028cd5c153bf45ffd0/HGV_meta_EpiDoc/HGV18/17068.xml)
dates the contract to12April125 at Hermopolis. It is not an exactAD200
observation. The encoded primary text has a main start-date clause and a
different start indication in the subscription, plus a one-day unpaid-service
clause. None supplies the completed duration of the130-aroura job. The
day-count clause cannot be used to claim130arourai reaped in one day.

## What can and cannot be extracted

| Quantity | Primary-record status |
| --- | --- |
| Contracted wheat area |130arourai, line6 |
| Required reapers |10+3=13, lines12–14; a contractual complement |
| Area per contracted reaper |130/13=10arourai; an allotment ratio, not area/day |
| Remuneration |Encoded fractions1/2 and1/12 in lines7–8; kept in their original scope |
| One-day clause |Unpaid additional service, lines17–19; not the complete job duration |
| Actual job worker-days |Unqualified |
| Contractual area/day requirement |No usable value extracted from this record |
| Realized reaping productivity |Unqualified |

The numeric markup is read with its line and operation context, including gaps,
supplied readings and original/regularized alternatives. Dates and advance or
wage payments do not become labour exposure. The full job's crop-work scope and
the employer's gathering/support responsibilities must also remain distinct.
No assumed conversion to hectares or eight-hour days is needed for this decision.

The discussion's general range of reaping speeds is a secondary synthesis;
it is not adopted as an independently measured target. Its quoted contract and
the cited primary edition must be reconciled before their quantities can be
combined. No papyrus-image or independent critical Greek collation was performed.

## Decision

This candidate closes with **zero qualified area/work-time calibration pairs**.
It usefully constrains the distinction between a labour contract and an observed
production rate. It does not change the proposed ploughing estimand or supply
an alternative reaping-rate estimate. All existing task coefficients, worker
allowances, atlas populations and climate fields remain unchanged.

Further generic accounting adapters or repeated checks of the same prescription
are not a route to an empirical fit. Any next numerical calibration must target
an outcome for which observations actually exist, with the agricultural work
and draft assumptions labelled as fixed scenarios where they remain unmeasured.

## Source record

Original discussion HTML/text and publisher-owned XML stay under ignored
`output/reaping_contract_target_20261117/source/`. Duke DDbDP/HGV CC-BY3.0
attribution is retained. Current primary files are pinned to repository commit
`0adcd9651ec240726a5b62028cd5c153bf45ffd0`; official Git blob identities, TM/
edition/date joins, line-scoped quantities, article citation/excerpt and previous
science/publication identities are checked. This is provenance and quantity-scope
qualification, not independent historical verification of the contract's fulfillment.

```sh
.venv/bin/python scripts/check_reaping_contract_target.py
```
