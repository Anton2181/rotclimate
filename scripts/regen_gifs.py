"""Re-render every GIF (year animations + experiments) with fixed legends."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from rotclimate import experiments as X  # noqa: E402
from rotclimate import render as R  # noqa: E402
from rotclimate.atlas import copy_media  # noqa: E402
from rotclimate.config import Params  # noqa: E402
from rotclimate.model import ClimateModel  # noqa: E402

P = "calibration/best_params.json"
p = Params.from_json(P)
r = ClimateModel(p.replace(downsample=8, steps_per_year=73, picard_iters=3)).run()
fr = R.FullRes(r)
R.season_gif(fr, "output/year_temperature.gif", "T")
R.season_gif(fr, "output/year_precipitation.gif", "P")
X.spin_flip(p, "output/spin_flip.gif")
X.tilt_sweep(p, "output/tilt_sweep.gif")
X.surroundings(p, "output/surroundings.gif")
X.history("output/improvement.gif")
copy_media()
print("ok")
