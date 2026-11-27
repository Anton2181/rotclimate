"""Materialize the prospectively declared private cap; never edit main source."""
import difflib
import fcntl
import json
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from local_benchmark_protocol import file_hash, freeze

PLAN = ROOT / 'calibration/marine_target_cap_20261127/plan.json'
OUT = ROOT / 'output/marine_target_cap_20261127'
MODEL = OUT / 'model'


def replace_once(text, old, new):
    assert text.count(old) == 1, old
    return text.replace(old, new, 1)


def build_sources():
    config = (ROOT / 'rotclimate/config.py').read_text()
    marker = '    inflow_rh: float = 0.0            # e91: target column humidity (fraction of land saturation); 0 = ocean_rh\n'
    config = replace_once(config, marker, marker + '    inflow_source_cap: bool = False  # experimental: cap land target at nearest-sea equilibrium column water\n')
    model = (ROOT / 'rotclimate/model.py').read_text()
    old = ('                lamE = lamE + np.where(ocean, 0.0, land_rate)\n'
           '                W_ocean = np.where(ocean, W_ocean, (p.inflow_rh or p.ocean_rh) * Ws)\n')
    new = ('                if p.inflow_source_cap:\n'
           '                    from .marine_inflow import capped_marine_target\n'
           '                    W_ocean, land_rate = capped_marine_target(\n'
           '                        W_ocean, Ws, ocean, self.inflow_near,\n'
           '                        p.inflow_rh or p.ocean_rh, land_rate)\n'
           '                lamE = lamE + np.where(ocean, 0.0, land_rate)\n'
           '                if not p.inflow_source_cap:\n'
           '                    W_ocean = np.where(ocean, W_ocean, (p.inflow_rh or p.ocean_rh) * Ws)\n')
    model = replace_once(model, old, new)
    helper = ROOT / 'calibration/marine_target_cap_20261127/marine_target.py'
    return {'rotclimate/config.py':config, 'rotclimate/model.py':model,
            'rotclimate/marine_inflow.py':helper.read_text()}


def patch_text(changes):
    patch = ''
    for name, text in changes.items():
        old = ROOT / name
        patch += ''.join(difflib.unified_diff(old.read_text().splitlines(keepends=True) if old.exists() else [],
            text.splitlines(keepends=True), fromfile='a/' + name if old.exists() else '/dev/null', tofile='b/' + name))
    return patch


def main():
    plan = json.loads(PLAN.read_text())
    OUT.mkdir(parents=True, exist_ok=True)
    lock = (OUT / '.lock').open('a')
    fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    assert subprocess.check_output(['git', 'show', 'HEAD:' + str(PLAN.relative_to(ROOT))], cwd=ROOT) == PLAN.read_bytes()
    assert not list(OUT.glob('*/attempt.json')), 'Preparation cannot modify an attempted study'
    for name, digest in plan['main_model_sources_sha256'].items():
        assert file_hash(ROOT / name) == digest, name
    changes = build_sources()
    assert patch_text(changes) == (PLAN.parent / 'marine_target_cap.patch').read_text()
    mappings = [(plan['main_model_sources_sha256'], ROOT),
                (plan['cache_seed_sha256'], ROOT / plan['cache_seed_origin']),
                (plan['helper_sources_sha256'], ROOT)]
    for mapping, origin in mappings:
        for name, digest in mapping.items():
            source, destination = origin / name, MODEL / name
            assert source.is_file() and not source.is_symlink() and file_hash(source) == digest, name
            if destination.exists():
                assert file_hash(destination) == plan['private_files_sha256'][name], name
                continue
            destination.parent.mkdir(parents=True, exist_ok=True)
            if name in changes:
                destination.write_text(changes[name])
            else:
                shutil.copyfile(source, destination)
    extra = MODEL / 'rotclimate/marine_inflow.py'
    if not extra.exists():
        extra.write_text(changes['rotclimate/marine_inflow.py'])
    for name, digest in plan['private_files_sha256'].items():
        f = MODEL / name
        assert not f.is_symlink() and f.stat().st_nlink == 1 and file_hash(f) == digest, name
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / '.gitignore').write_text('model/\n.lock\nstatus.json\nrun.log\n')
    freeze(OUT / 'preparation.json', dict(plan_sha256=file_hash(PLAN),
        preparer_sha256=file_hash(Path(__file__)), private_declared_files=len(plan['private_files_sha256']),
        main_source_unchanged=True, integrations=0))
    print('Prepared private cap/source epoch; no main changes or integrations')


if __name__ == '__main__':
    main()
