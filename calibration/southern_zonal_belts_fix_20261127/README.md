# Southern extra-tropical wind belts: unfitted correctness correction

The background routine had southern trades but no southern westerly or polar
belts. In a symmetric equinox case45N had7m/s westerlies,45S zero;75N had
−3m/s polar easterlies,75S zero. Eleven known-answer/reflection regressions
failed before the correction (one rotation check passed).

The source now adds southern westerlies and polar easterlies with the reversed
seasonal strength and meridional sign. Existing friction, retrograde spin and
map rotation apply afterward. An outer guard restricts the new work to grids
reaching the southern extra-tropics; northern field bytes remain unchanged even
when the mixed grid enters that guard. No coefficient, other circulation cell,
temperature, precipitation or Earth parameter is changed. This does not make
the model a complete global circulation model.

All39 relevant regressions pass, including13 new tests and20 pre-edit golden
northern profiles on mixed grids. The saved actual-case scope proof verifies
ALL97 r58 full-grid case IDs and shows that the new branch cannot activate
in ANY season, including primer: all lie above−27.562666degrees in the model
frame. Exact source comparison proves this guarded addition is the only edit.
Their original protocols/certificates remain historical, with explicit source
compatibility; they are not relabeled as97 new integrations.

Exactly TWO prospective coupled source checks, committed before preflight:
- Ordinary native Somalia,1100km pad: every saved control T/P/observation/
  coordinate array and scored monthly wind must match current97/default-off
  references byte-for-byte; the correction branch must be inactive.
- Wider native Somalia,4012km pad: original numerical checks, input pairing,
  finite/nonnegative fields and archive-rounding scores must pass; the new
  branch must activate. Report actual T/P/wind changes without an accuracy
  improvement claim or fitted coefficient selection.

The wider control is the ordinary native parent from the CLOSED14-run nested
study. This reruns no nested intervention and reopens no failed alternative.
Original solver tolerances/iterations/primer, parameters, forcing, geometry and
calendar remain fixed. One nice10 worker, four thread variables1, literal venv
Python, private231 regular files. Stop and preserve numerical/identity failure;
no automatic retry or tolerance relaxation. Existing raw failures/test logs
are preserved. Production source changed only after the14-run worker finished.
No AA/fine/world fit, parameter refit, new atlas or independent validation.
W18/W18c remain permanently closed. Retain r58; atlasr51 unchanged.

Qualification is engineering source correctness plus explicit inactive-branch
compatibility of the97 reference, not a new climate-accuracy adoption. A new
calibration still needs its prospective development/fine/fresh-validation gates.
