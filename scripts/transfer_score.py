"""Meta M1: the share of an Earth gain that transfers to the invented world.

    .venv/bin/python -I scripts/transfer_score.py OUTDIR REF_WORLD_PARAMS NAME CAND_WORLD_PARAMS [NAME CAND ...]

Runs the policy v6 development pool (97 regions, the screen_v6 parts) with ROTCLIMATE_WORLD_LEGAL=1, i.e. with every
Earth-only observed field withheld (NCEP PW, 500/700 hPa omega, 500 hPa RH, SLP fall, albedo), using WORLD parameter
sets (rXXw: edge_pw_source "zonal"). Prints S97 with its bootstrap interval for each candidate against the reference,
both run world-legal. Compare with the ordinary (Earth-observed) S97 of the same step: transferable share =
(1 - S_world) / (1 - S_earth).
"""
import json, os, sys
from pathlib import Path
os.environ["ROTCLIMATE_WORLD_LEGAL"] = "1"          # inherited by the benchmark subprocesses
ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT / "scripts"))
import numpy as np
import refit_e75 as R
from gate_v3 import paired, score
from score_ci import ci

out = ROOT / sys.argv[1]; ref_p = json.loads((ROOT / sys.argv[2]).read_text())
R.PARTS.update(tropical_t="calibration/tropical_check_20261122t/regions.json", sealed_r="calibration/sealed_20261122r/regions.json",
               sealed_S18="calibration/sealed_20261123S18/regions.json", sealed_U18="calibration/sealed_20261124U18/regions.json")
# 1. the reference, world-legal, as its own named run; then expose it under the name "wl" for pairing
R.OUT = out; refdir = out / "_refrun"; refdir.mkdir(parents=True, exist_ok=True)
links = out / "_ref"; links.mkdir(exist_ok=True)
R.REF, R.REF_NAME = links, "wl"
for part in R.PARTS:
    o = refdir / f"candidate_{part}"
    if not (o / "summary.json").is_file():
        import subprocess
        spec = R.PARTS[part]; regs = ["dev31"] if spec is None else list(json.loads((ROOT / spec).read_text()))
        (refdir / "candidate_params.json").write_text(json.dumps(ref_p, indent=1))
        cmd = [R.PY, "-I", str(ROOT / "scripts/benchmark_local.py"), "--fit", str(refdir / "candidate_params.json"),
               "--regions", *regs, "--workers", "4", "--out", str(o)] + (["--region-specs", str(ROOT / spec)] if spec else [])
        subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    lk = links / f"wl_{part}"
    if not lk.is_symlink(): lk.symlink_to(o.resolve())
# 2. each candidate against it
args = sys.argv[3:]
for name, pf in zip(args[::2], args[1::2]):
    R.evaluate(name, json.loads((ROOT / pf).read_text()))
    Rr, Cc = paired(out / name, "wl", None, list(R.PARTS))
    s = score(Rr, Cc, list(Rr))
    a = np.array([[Cc[n]["temperature"]["monthly_mae_C"], Rr[n]["temperature"]["monthly_mae_C"],
                   Cc[n]["rain"]["loss"], Rr[n]["rain"]["loss"]] for n in Rr])
    b = ci(a)
    res = dict(name=name, params=pf, n=len(Rr), S=s, q05=b["q05"], q95=b["q95"], world_legal=True)
    (out / name / "transfer.json").write_text(json.dumps(res, indent=1))
    print(f"== {name} world-legal S{len(Rr)} {s['S']:.4f} [{b['q05']:.4f}, {b['q95']:.4f}] (T {s['T']:+.3f} P {s['P']:+.3f})", flush=True)
