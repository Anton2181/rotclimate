"""Regenerate only the atlas accuracy layer and layer metadata for the best params."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from rotclimate.__main__ import simulate  # noqa: E402
from rotclimate.atlas import ATLAS, _layer_meta, agreement_layer  # noqa: E402
from rotclimate.config import Params  # noqa: E402
from rotclimate.render import FullRes  # noqa: E402

p = Params.from_json("calibration/best_params.json").replace(downsample=4, steps_per_year=73, picard_iters=3)
fr = FullRes(simulate(p, quiet=True))
agreement_layer(fr)
meta_path = ATLAS / "data" / "atlas.json"
meta = json.loads(meta_path.read_text())
meta["layers"] = _layer_meta()
meta_path.write_text(json.dumps(meta, ensure_ascii=False))
print("ok")
