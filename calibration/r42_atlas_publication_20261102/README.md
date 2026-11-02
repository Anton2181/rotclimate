Active declaration: plan_v2.json. Its completion job is running in a persistent
execution session (95390). Watch output/atlas_r42/final_qa/automation_status.json
and output/atlas_r42/finalization.log.

The original plan.json was never executed and is superseded. Version 2 fixes
handling of an already-staged deletion and freezes all current producer,
method-page, template and published-fit dependencies.

The completion job waits for the existing release, verifies its exact r42
physics/checkpoint and current correction models, checks browser flows and a
Windows-style checkout, creates/tests the portable bundle, then commits only
its declared release artifacts and pushes the resulting commit. It preserves
unrelated staged work and excludes backups, checkpoints and transient status.

Do not edit the guarded producers, normal map data or research companion while
it is waiting. Independent experimental code/data outside these paths may
continue. A changed source fails publication with a receipt; do not silently
rewrite the frozen declaration or force a push.
