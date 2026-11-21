# T2 Mexico circulation — findings (21 Nov 2026)

## e95: summer western flanks of the ocean highs: screen A FAIL
- **Pass rule:** the four target regions must average ≤ 0.98 (each region scored 0.5 × T-MAE ratio + 0.5 × rain-loss ratio, against r50), and no guard region may exceed 1.02.

| subtropical_high_west (m/s) | Target mean | Mexico | Texas | SE US | E China | Worst guard |
|---|---|---|---|---|---|---|
| 1 | 1.000 | 1.001 | 0.995 | 1.009 | 0.996 | SW Australia 1.002 |
| 2 | 1.001 | 1.002 | 0.991 | 1.019 | 0.993 | SW Australia 1.003 |
| 4 | 1.004 | 1.004 | 0.983 | 1.032 | 0.995 | SW Australia 1.005 |

- Mexico does not respond to Gulf southerlies at all. The south-east US gets worse.
- So the missing Mexican summer rain is not a missing wind from the Gulf.
- Run in a scratch worktree with the patch applied (e95.patch). With e95 off, the worktree reproduced r50's Mexico case exactly. The repo code is unchanged (r50).

## e96: no monsoon-westerly turning in the plateau-anchored band: screen A FAIL
| anchor_trades | Target mean | Mexico | Texas | Worst guard | North India | Tibet |
|---|---|---|---|---|---|---|
| 0.5 | 0.999 | 1.003 | 0.995 | Bengal 1.011 | 1.009 | 0.992 |
| 1.0 | 0.999 | 1.006 | 0.991 | Bengal 1.024 | 1.021 | 0.984 |

- Restoring the Gulf trades over Mexico does not raise its summer rain either. The Indian side gets worse because the Tibetan anchor's band reaches north India and Bengal.
- **Note:** California scores 0.983 in every e95/e96 setting. That points to a small identity difference between this worktree's California case and the recorded validate94 case, not an effect of the changes. It is common to all settings, so the ranking is unaffected.

## T2 parked (per the declared plans)
- Two wind mechanisms (e95, e96) and four earlier attempts (e88, e91, e92, e93 alone) leave Mexico's summer peak about 1/3 of observed.
- Sealed set q stays unopened.
