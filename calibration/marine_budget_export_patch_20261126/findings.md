# Marine-exchange export correction: tested, not applied to active source

`marine_budget.patch` fixes the known missing marine-humidity source in the
exported single-column local equation and shared-face vapor ledger. It is a
reviewable two-file correction, **not a climate-physics change**. The live
model and the pinned padding-study snapshot remain unchanged while W18c runs.

The solver already includes signed land humidity relaxation. Surface `E` in
the single-column path reports land evaporation without that atmospheric
exchange. The exported equation previously used surface E alone. The patch
adds a separate `marine_exchange` component and includes it in both ledgers,
without changing E, water, rain, temperature, transport or any solver input.
The export report includes the component and explains its sign/accounting.

Independent reservoirs have a different existing contract: their returned E
already includes surface/land humidity exchange. The patch therefore adds
**zero additional exchange** for that path. This is an accounting convention,
not a claim of physically zero marine exchange in reservoir mode.

## Bounded validation

Three predeclared toy configurations exercised concentration transport with
import/drying, single-column conservative flux, and independent two-layer
reservoirs. Each ran an unpatched diagnosed baseline, patched diagnosed run
and patched ordinary run: **nine paired-validation integrations**. The fixed
existing regression suites additionally performed four coupled toy runs.
There were **no Earth regional integrations**, parameter search, fine/sealed
target use or atlas work.

All T/Tsl/P/W/u/v/E and applicable layer-water arrays match in dtype and raw
bytes across versions and diagnostic on/off. Independent review checks
**430,560 physical scalar comparisons**, the unchanged other budget terms,
the added-source residual relation, and unchanged reservoir residuals.

| Toy path | Original local max absolute residual, mm/day | Corrected local max absolute residual, mm/day | Original / corrected scaled flux-ledger residual |
|---|---:|---:|---:|
| Concentration | 1.291872 | 0.006510 | Not a flux ledger |
| Single-column flux | 1.182032 | 0.006566 | 0.032438 / 0.001593 |
| Independent reservoirs | 0.004393 | 0.004393 | 0.000499 / 0.000499 |

Maximum scaled corrected local residuals are 0.009580, 0.008147 and 0.001560,
respectively, within the existing 0.01 criterion. Exported float32 components
are checked against explicitly bounded rounding error; solver tolerances and
iteration budgets were unchanged. The single-column flux baseline's failed
aggregate certificate is retained: its moisture solve passed, but its
incomplete ledger failed. The corrected certificate passes on identical
physical fields. This does not reclassify any historical regional experiment.

**28 regression tests pass, with no failures or skips.** The three fixed
existing suites cover moisture, local transport, independent reservoirs and
coupled certificates. Seven additional checks cover the private import
context, genuine positive/negative marine-source solves with ocean_sink=1
and 0.4, and signed marine components in saved zone reports. The extra file
is named `marine_export_checks.py` to keep private-only assumptions out of
ordinary test discovery; it was renamed after successful execution with
unchanged source bytes, then explicit collection of all seven checks passed.
`unit_test_source.json` records that provenance.

## Review and later application

The patch applies cleanly to its pinned base. The source diff touches only
budget allocation, diagnostic source assembly and report contents. Ordinary
single-column concentration runs do not execute the added accounting branch.
No active physical source, shared cache, parameter file, validation gate or
padding snapshot was changed. Original Somali/Saharan failed export checks
and separately qualified captures remain intact.

After W18c is terminal and its supervisor has exited, recheck the base source
digests and apply with:

```sh
git apply --check calibration/marine_budget_export_patch_20261126/marine_budget.patch
git apply calibration/marine_budget_export_patch_20261126/marine_budget.patch
```

Promote the six functional additional checks into the normal test suite,
adapting only the private import-context guard, and rerun the focused checks
against the actual applied code. Record a new diagnostic source/protocol epoch;
do not rewrite old qualifications or relabel historical failures. The prepared
padding study retains its own unchanged r58 source and remains comparable.
This correction alone does not reduce Somalia's rainfall bias or justify a
new adopted climate. W18c still determines any proposed r59 through its
unchanged development, fine and sealed gates.

Evidence is under `output/marine_budget_export_patch_20261126/`: full saved
baseline/patched arrays and certificates, preparation/validation protocols,
regression XML/log, independent review and diagnostic qualification.
