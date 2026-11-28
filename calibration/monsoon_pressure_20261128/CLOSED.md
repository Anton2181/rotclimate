# e140 observed-pressure monsoon gates: REJECTED at the sealed stage (2026-11-28)

Finalist W22 w1_003 (r59 + monsoon_obs_pressure 0.661, trade_obs_pressure 0.880, monsoon_westerly 0.454,
monsoon_pressure_hpa 5.06, trade_heat_low 0.538):
- dev6 vs r59: S97 0.9856 [q95 0.9957], T -0.8 %, P -2.1 %, worst regime temperate 1.007 -> PASS
- fine28 vs r59: S28 0.9997 -> PASS
- sealed BB (ONE run, 15 regions) vs r59: S 1.0043 [0.9954, 1.0129], T -0.7 %, P +1.6 % -> FAIL. BB now SPENT.

Only the monsoon/tropical boxes moved, all drier: Kashmir 137 -> 116 mm (obs 826), Myanmar coast 1127 -> 1075
(obs 3030), Congo 946 -> 890 (obs 1648); Sulawesi 3381 -> 3307 (obs 2073) the only rain gain; Myanmar T 2.31 -> 2.06.
Reading: the refit bought its dev gain (Sahel, Sahara, Zambia drier) by weakening the monsoon inflow in general
(monsoon_westerly 0.68 -> 0.45, trade_heat_low 0.18 -> 0.54), which dries the monsoon coasts that were already too dry.
The plain e140 switch (op1t1, no refit) was 0.9925 [0.9824, 1.0028] on dev. Not continued: no fresh sealed set,
and a continuation would have to be declared before it runs. e140 stays in code, off by default.
Process note: `ppe.py propose` was called twice on W22 (second call rewrote the same 12 proposals; none ran).
A first sealed launch without --regions ran the default dev regions under the BB output name; it was stopped and deleted
before any BB region ran.
