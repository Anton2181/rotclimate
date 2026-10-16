# Start here — lightweight climate project handoff

Read [the current handoff](reports/HANDOFF_20261016.md), then the
[verified latest analysis](output/v10_regional_transport_review/review.md).
The latest experiment stopped at **6/8 cases**; the production atlas is unchanged.

This is an analysis/development export, **not the full experiment archive**.
It includes:

- Source code, tests, requirements, research reports and calibration settings.
- The complete current atlas, source map layers and prepared Earth/monthly atmospheric inputs.
- Historical JSON summaries/manifests, logs and static figures.
- All 16 completed annual records from the latest transport attempt, eight paired
  source anchor checkpoints, diagnostic arrays, small numerical laboratories
  and the published V9 anchor's climate fields.

It omits the local Python environment, bytecode/test caches, raw downloaded
WorldClim/OISST archives, old atlas backups, animations, most historical binary
checkpoints and large generated weather-forcing tables. Nothing was removed
from the original project. EXPORT_MANIFEST.json lists retained hashes and
omitted file paths/sizes, so missing evidence can be located in the full copy.

## What can be done from this copy

Read reports and saved data, inspect/change code in a new branch/module, run
manufactured tests after installing dependencies, and view the existing atlas.
The saved annual arrays can be inspected directly with NumPy. Markdown links
have been made relative; original code, JSON provenance and atlas files retain
their exact bytes. Absolute paths inside original JSON are historical provenance.

The original strict annual reviewers and resume runners depend recursively on
omitted historical checkpoints/forcing. **They cannot fully verify or resume
from this lightweight copy.** This is expected missing evidence, not evidence
of corrupt physics or permission to relax an integrity check. In particular,
do not run scripts/review_v10_regional_transport.py here expecting its full
parent-chain verification to succeed. Read its already verified output instead.
Request specific omitted files from the full project if they become necessary.

The handoff's original safe-review command refers to the full workspace.
For this export, verify package contents without any climate simulation:

```sh
python3 verify_export.py
```

After installing Python dependencies, the existing atlas can be served with:

```sh
python3 -m http.server -d atlas
```

Open http://localhost:8000. Do not regenerate the atlas just to view it.
All real climate simulations/calibrations remain user-run. NOAA six-hourly
downloads remain paused. Preserve frozen evidence and use a new module/output
folder for changed physics. No new long run is recommended at this handoff.
