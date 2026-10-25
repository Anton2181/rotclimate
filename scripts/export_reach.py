"""Write the Political reach layers into atlases (polity/export.py).

    python3 -I scripts/export_reach.py atlases/free_fit atlases/earth_fit atlases/whittaker_fit
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from polity.export import export  # noqa: E402
from scripts.add_market_views import render_views  # noqa: E402

if __name__ == "__main__":
    for path in sys.argv[1:]:
        export(path)
        render_views(path,Path(__file__).resolve().parents[1]/'output/polity_map'/f'{Path(path).name}.npz')
