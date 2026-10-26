import json
from dataclasses import asdict
import pytest
from rotclimate.config import Params
from scripts import check_seasonal_cycle as pilot
from scripts.local_benchmark_protocol import file_hash


def test_resume_rechecks_actual_derived_earth_inputs(monkeypatch,tmp_path):
    folder=tmp_path/'test';folder.mkdir();cache=folder/'years_0.pkl';cache.write_bytes(b'local checkpoint')
    row=dict(identity='run',status='passed',case_identity='old',checkpoint_sha256=file_hash(cache))
    (folder/'years_0.json').write_text(json.dumps(row))
    monkeypatch.setattr(pilot.earth,'region_case',lambda name,km:object())
    monkeypatch.setattr(pilot,'case_hash',lambda case:'changed')
    job=('test',0,asdict(Params()),'earth','unused','run',str(tmp_path),56)
    with pytest.raises(ValueError,match='derived Earth inputs differ'):pilot.run_one(job)
    monkeypatch.setattr(pilot,'case_hash',lambda case:'old')
    assert pilot.run_one(job)==row
