from dataclasses import asdict
import json
import pytest

from rotclimate.config import Params
from scripts.tag_atlas_physics import tag


def test_wrong_physics_cannot_relabel_an_atlas(tmp_path):
    atlas = tmp_path / 'atlas'; (atlas / 'data').mkdir(parents=True)
    p = Params(); (atlas / 'params.json').write_text(json.dumps(asdict(p)))
    raw = tmp_path / 'release.json'; raw.write_text(json.dumps(asdict(p.replace(wet_sun=.7))))
    meta = atlas / 'data/atlas.json'; meta.write_text('{}')
    with pytest.raises(ValueError, match='differs'):
        tag(atlas, raw, 'r43', 'reports/R43_20261103.md')
    assert meta.read_text() == '{}'
    raw.write_text(json.dumps(asdict(p)))
    tag(atlas, raw, 'r43', 'reports/R43_20261103.md')
    assert json.loads(meta.read_text())['physics_profile'] == 'r43'
