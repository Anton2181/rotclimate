"""Re-render the atlas map layers at 3x resolution for crisp zooming."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from rotclimate.__main__ import simulate  # noqa: E402
from rotclimate.atlas import build_hires_layers  # noqa: E402
from rotclimate.config import Params  # noqa: E402

p = Params.from_json("calibration/best_params.json").replace(downsample=4, steps_per_year=73, picard_iters=3)
build_hires_layers(simulate(p, quiet=True), scale=int(sys.argv[1]) if len(sys.argv) > 1 else 3)
print("ok")
