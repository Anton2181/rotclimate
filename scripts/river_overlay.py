"""Add the simulated river network to the existing atlas data (no re-render)."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from rotclimate.atlas import ATLAS, river_segments  # noqa: E402
from rotclimate.config import Params  # noqa: E402
from rotclimate.model import ClimateModel  # noqa: E402

p = Params.from_json("calibration/best_params.json").replace(downsample=8, steps_per_year=73, picard_iters=3)
segs = river_segments(ClimateModel(p).run())
mp = ATLAS / "data" / "atlas.json"
meta = json.loads(mp.read_text())
meta["rivers_sim"] = segs
mp.write_text(json.dumps(meta, ensure_ascii=False))
print(len(segs), "segments; max discharge", max(s[4] for s in segs))
