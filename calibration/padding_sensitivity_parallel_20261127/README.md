# Prospective private scheduling amendment

This replaces the **unrun** padding study's scheduling restriction so the
existing diagnostic can produce physical evidence while W18c computes.
Before the amendment there were zero padding attempts and zero physical
padding results. The waiting queue (PID8757) was stopped and its source,
protocol, launch and preparation evidence were preserved. A retirement
sentinel prevents the original plan from later consuming a second budget.

The amended study retains the same nine integrations, r58 physical source,
parameters, three regions, exact scored cells/observations, padding levels,
controls, numerical tolerances and failure policy. The scientific design is
checked against the parent plan. Only execution timing, output namespace and
reuse of the six already prepared private derived-cache files change.
This is not another W18c candidate, a rescue of W18c or a validation-policy
change. The original plan and pre-amendment preparation are not rewritten.

One worker runs at nice priority10 or lower and one BLAS/OpenMP thread.
Physical code/cache files are regular private copies; no writable symlinks
are used. While W18c is active, each integration also verifies that its main
physical source remains unchanged. All three exact1100km controls still run
before any expanded-domain integration; a failed control closes the study.
Failed or interrupted attempts cannot be automatically repeated.

Run the fixed worker and subsequent independent reviewer:

```sh
nice -n 10 .venv/bin/python -u -I scripts/run_padding_parallel.py
```

The driver uses a singleton lock, fixed source hashes and persistent attempt
receipts, and stops on any command failure or missing output. It does not
apply the pending main-source budget correction, adopt physics, select a
padding from observed rain, open validation targets, commit results or build
an atlas. Inspect the actual figure and write scientific findings afterward.

W18c continues with its original source, inputs, design, candidate budget,
selection rule, proposal sequence and gates. Results of this exposed-case
diagnostic cannot influence its candidate selection. The historical r52/r53
padding/edge-moisture failures remain counterevidence; larger domains are not
presumed more accurate and retain the regional projection's limitations.
