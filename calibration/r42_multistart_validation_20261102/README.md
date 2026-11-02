# Paired validation after all three starts

This declaration precedes completion of the third start. The unchanged search
rule chooses one candidate from all 39 evaluations. Every scalar search result,
the finalist parameters and source identities are committed before fresh scoring.

The driver reconstructs both full 49-region development error vectors, checks
their reproduction to 1e-10 and the reference's actual forcing footprints, then
applies policy v3. If that passes, it runs fresh paired 28 km integrations in
California, western Europe, Japan and New Zealand. Only a passing candidate gets
a committed qualification receipt and one paired evaluation of unseen set e.
Regional regressions are reported; they are not individual vetoes.

No candidate is adopted and no atlas is changed by this driver. All validation
outcomes and raw packets are retained and published. A stopped run resumes the
same frozen finalist and reuses verified complete regional packets, without
selecting from sealed outcomes.

```sh
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 .venv/bin/python -u -I \
  scripts/validate_r42_multistart.py \
  --plan calibration/r42_multistart_validation_20261102/plan.json --workers 2
```

Status and receipts: `output/r42_multistart_validation_20261102/`.
