"""Re-render only the experiment GIFs (tilt, surroundings, history) and copy media to the atlas."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from rotclimate import experiments as X  # noqa: E402
from rotclimate.atlas import copy_media  # noqa: E402
from rotclimate.config import Params  # noqa: E402

p = Params.from_json("calibration/best_params.json")
X.tilt_sweep(p, "output/tilt_sweep.gif")
X.surroundings(p, "output/surroundings.gif")
X.history("output/improvement.gif")
copy_media()
print("ok")
