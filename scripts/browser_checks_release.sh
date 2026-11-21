#!/usr/bin/env bash
# Browser checks on the promoted atlas (atlases/earth_fit), as run for r49: smoke + release-3 views + forest/herding layers.
#   bash scripts/browser_checks_release.sh output/atlas_r50/browser output/rebuild_r50/browser_r50.json
set -uo pipefail
cd "$(dirname "$0")/.."
B=$1; J=$2; PORT=${PORT:-8766}; mkdir -p "$B"
curl -s -o /dev/null http://127.0.0.1:$PORT/ || { (python3 -m http.server $PORT --bind 127.0.0.1 > /dev/null 2>&1 &); sleep 2; }
timeout 900 node scripts/check_atlas_smoke.js http://127.0.0.1:$PORT/atlases/earth_fit/ > $B/smoke.json 2> $B/smoke.err; echo "smoke exit $?"
for c in settlement_release3 wide_supply_release3 supply_reach_release3 downstream_release3 administration_release3 hierarchy_release3 forest_layer herding_layer; do
  printf "%s: " $c; timeout 900 node scripts/check_${c}_browser.js $B/$c http://127.0.0.1:$PORT > $B/$c.log 2>&1; echo "exit $? | $(tail -n 1 $B/$c.log | cut -c1-200)"
done
.venv/bin/python -I - "$B" "$J" <<'PYEOF'
import json, sys
from pathlib import Path
B, J = Path(sys.argv[1]), Path(sys.argv[2]); res = {}
for log in sorted(B.glob('*.log')): res[log.stem] = (log.read_text().strip().splitlines() or ['(empty)'])[-1]
try:
    s = json.load(open(B / 'smoke.json')); s = s if isinstance(s, list) else [s]
    res['smoke'] = ['passed' if p.get('passed') else 'FAILED' for p in s]
except Exception as e:
    res['smoke'] = f'FAILED ({e})'
J.parent.mkdir(parents=True, exist_ok=True)
J.write_text(json.dumps(dict(date='2026-11-21', server='local http.server', results=res), indent=1) + '\n'); print(json.dumps(res))
PYEOF
