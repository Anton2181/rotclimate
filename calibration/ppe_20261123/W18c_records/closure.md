# W18c closed: development gain fails the fine-resolution check

The original finalist `w1_005` fails the fine28 gate: **S28 1.034725**, against
the unchanged maximum 1.01. Mean normalized temperature MAE worsens 1.749%
and rain loss 5.196% across the four declared fine regions. All eight paired
numerical certificates pass; this is an accuracy/protection failure, not a
failed numerical solve. Retain adopted r58. No r59 or atlas update follows.

| Fine region | T MAE C, r58 → finalist | Rain loss, r58 → finalist |
|---|---|---|
| California | 1.831 → 1.913 | 0.4316 → 0.4435 |
| Western Europe | 1.321 → 1.496 | 0.3199 → 0.3625 |
| Japan | 1.826 → 1.820 | 0.4444 → 0.4736 |
| New Zealand | 2.015 → 1.885 | 0.5373 → 0.5435 |

Rain loss worsens in all four fine regions. Temperature improves in Japan
and New Zealand but worsens in California and Western Europe. S28 uses ratios
of the four-region mean component losses, not the mean of individual ratios.
The independent raw-array review verifies unchanged observations/coordinates,
all eight original certificates, field hashes and the aggregate score. The
saved arrays were rounded to float32 after scoring; explicit propagated ULP
bounds cover that quantization, and the reconstructed score still fails by
far more than the bound. The original gate and its threshold are unchanged.

All 49 initial development evaluations completed without a numerical failure.
The original GP continuation rule stopped search: predicted remaining gain
0.0029349 is below 0.005. No proposed second-wave point was evaluated. The
finalist was selected solely by the original development objective and frozen
before validation. Dev6 passed: S97 0.9842206, 90% bootstrap interval
[0.9701248, 0.9983829], T -1.936%, rain loss -1.220%, worst regime 1.0179688.
That development improvement is insufficient to satisfy the independent
fine-resolution protection.

The supervisor initially stopped on a duplicate `plan_sha256` status keyword,
before any validation. Its old source, failure state and frozen finalist were
preserved; the small serialization fix passed two tests and the unchanged
physical/shared-input readiness checks. The exact same finalist then underwent
the original dev6 and fine gate sequence. The software recovery did not retry
a scientific failure or change a policy. The resumed supervisor has exited.

**W18c is permanently closed.** Do not select another sampled point, refit
against fine outcomes, relax the threshold or reopen the W18/W18c line.
Sealed AA remains UNOPENED with an empty `seen_by`; no AA target or paired
run was used. It remains available only under a future properly declared
independent candidate's rules, not a rescue of this finalist.

The separately validated marine-export correction can now be applied and
tested as a new diagnostic source epoch, preserving all original qualifications
and this failure. It corrects accounting, not the rejected climate. A later
physical hypothesis must have its own prospective evidence and complete
validation; the padding/source-capture diagnostics do not authorize choosing
a new deployed padding or publishing a map.

Run `.venv/bin/python calibration/ppe_20261123/W18c_records/review_fine_gate.py`
to reproduce `fine_array_review.json`. It reads archived arrays and gate
outputs only, with zero integrations, gate reruns or sealed-target reads.
