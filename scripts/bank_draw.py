"""Meta M2: hand out sealed boxes from the bank, once each, in bank order.

    .venv/bin/python -I scripts/bank_draw.py BANKDIR SETNAME 'B2,B3' N [CANDIDATE_NOTE]

Writes calibration/sealed_bank_draws/SETNAME/regions.json (N boxes, taken round-robin over the named bands,
each band in its bank order, skipping boxes any earlier draw used) and appends the draw to BANKDIR/ledger.json.
The declaration (bands, N, candidate) must be committed BEFORE this runs; a set is run ONCE.
"""
import json, sys, datetime
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]


def main():
    bdir, setname, bands, n = ROOT / sys.argv[1], sys.argv[2], sys.argv[3].split(","), int(sys.argv[4])
    note = sys.argv[5] if len(sys.argv) > 5 else ""
    bank = json.loads((bdir / "bank.json").read_text()); led = json.loads((bdir / "ledger.json").read_text())
    if any(d["set"] == setname for d in led["draws"]): raise SystemExit(f"{setname} already drawn")
    used = {b for d in led["draws"] for b in d["boxes"]}
    queues = {b: [x for x in bank[b] if x[0] not in used] for b in bands}
    pick = {}
    while len(pick) < n and any(queues.values()):
        for b in bands:
            if queues[b] and len(pick) < n:
                nm, spec = queues[b].pop(0); pick[nm] = spec
    if len(pick) < n: raise SystemExit(f"bank exhausted in {bands}: {len(pick)} < {n}")
    od = ROOT / "calibration/sealed_bank_draws" / setname; od.mkdir(parents=True, exist_ok=True)
    (od / "regions.json").write_text(json.dumps(pick, indent=1) + "\n")
    led["draws"].append(dict(set=setname, bands=bands, n=n, boxes=list(pick), note=note,
                             utc=datetime.datetime.utcnow().isoformat(timespec="seconds")))
    (bdir / "ledger.json").write_text(json.dumps(led, indent=1) + "\n")
    left = {b: len([x for x in bank[b] if x[0] not in used | set(pick)]) for b in bank}
    print(setname, list(pick), "left", left)


if __name__ == "__main__":
    main()
