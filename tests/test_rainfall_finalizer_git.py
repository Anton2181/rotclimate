"""The finalizer must never publish somebody else's staged change."""
import importlib.util
from pathlib import Path
import subprocess
import pytest

spec=importlib.util.spec_from_file_location('rainfall_finalizer',Path(__file__).parents[1]/'scripts/finalize_rainfall_benchmark.py');module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)


def git(root,*args):return subprocess.check_output(['git',*args],cwd=root,text=True).strip()


def test_background_artifact_commit_preserves_unrelated_staged_work(tmp_path):
    git(tmp_path,'init','-q');git(tmp_path,'config','user.email','test@example.invalid');git(tmp_path,'config','user.name','Test')
    unrelated=tmp_path/'unrelated.txt';unrelated.write_text('original\n');git(tmp_path,'add','unrelated.txt');git(tmp_path,'commit','-qm','Initial')
    unrelated.write_text('user staged change\n');git(tmp_path,'add','unrelated.txt')
    artifact=tmp_path/'atlases/climate_accuracy/data/test.json';artifact.parent.mkdir(parents=True);artifact.write_text('{"verified":true}\n')
    module.commit_artifacts(tmp_path,[artifact],'Verified own artifact')
    assert git(tmp_path,'show','HEAD:unrelated.txt')=='original'
    assert git(tmp_path,'diff','--cached','--name-only')=='unrelated.txt'
    assert git(tmp_path,'show','HEAD:atlases/climate_accuracy/data/test.json')=='{"verified":true}'


def test_commit_refuses_unrelated_or_outside_paths(tmp_path):
    source=tmp_path/'source.py';source.write_text('user code\n')
    with pytest.raises(ValueError):module.commit_artifacts(tmp_path,[source],'Wrong')
    outside=tmp_path.parent/'outside.txt';outside.write_text('outside\n')
    with pytest.raises(ValueError):module.commit_artifacts(tmp_path,[outside],'Wrong')
