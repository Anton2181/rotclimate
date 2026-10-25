"""Recompute the de facto tables of an atlas (people and control per polity for
every gap fill) and write them to data/polities.csv and atlas.json, without
redrawing the layers.

    python3 -I scripts/polity_tables.py atlases/whittaker_fit [atlases/free_fit ...]
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from polity import defacto as DF  # noqa: E402
from polity.export import write_polities_csv  # noqa: E402
from polity.fields import compute  # noqa: E402

if __name__ == "__main__":
    for path in sys.argv[1:]:
        data = Path(path) / "data"
        r = compute(path)
        dfs = DF.map_fields(r)
        tables = {}
        for c, d in dfs.items():
            rows, total = DF.polity_table(r, d)
            tables[str(c)] = dict(rows=rows, total=total)
        write_polities_csv(data, tables)
        meta = json.loads((data / "atlas.json").read_text())
        meta.setdefault("reach", {})["defacto"] = tables
        (data / "atlas.json").write_text(json.dumps(meta, ensure_ascii=False))
        print(path, "tables written", flush=True)
