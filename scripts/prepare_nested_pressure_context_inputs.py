"""Build six matched child/parent input grids; performs no climate integration."""
import fcntl
import importlib.metadata
import json
import os
from pathlib import Path
import shutil
import sys
import numpy as np
ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT/'scripts')]
from local_benchmark_protocol import case_hash,file_hash,freeze,write_json
OUT = ROOT/'output/nested_pressure_context_20261127'
MODEL = OUT/'model'


def main():
    assert os.getpriority(os.PRIO_PROCESS,0)>=10
    for name in ['OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS']:
        assert os.environ.get(name)=='1'
    base=json.loads((ROOT/'calibration/current_climate_reference_20261127/plan.json').read_text())
    six=json.loads((ROOT/'calibration/pressure_zonal_exterior_20261127/plan.json').read_text())
    for section in ['model_sources_sha256','helper_sources_sha256']:
        for name,digest in base[section].items():
            assert file_hash(ROOT/name)==digest,name
    for name,version in base['libraries'].items():
        assert importlib.metadata.version(name)==version
    OUT.mkdir(parents=True,exist_ok=True)
    lock=(OUT/'.lock').open('a')
    fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    assert not (OUT/'input_inventory.json').exists() and not (OUT/'input_preparation_failure.json').exists()
    for name,digest in base['private_files_sha256'].items():
        target=MODEL/name
        origin=ROOT if name in base['model_sources_sha256'] or name in base['helper_sources_sha256'] else ROOT/base['cache_origin']
        assert file_hash(origin/name)==digest
        if not target.exists():
            target.parent.mkdir(parents=True,exist_ok=True)
            shutil.copyfile(origin/name,target)
        assert file_hash(target)==digest and not target.is_symlink() and target.stat().st_nlink==1
    (OUT/'.gitignore').write_text('model/\n.lock\nstatus.json\ninput_status.json\nrun.log\ninput.log\n')
    assert not any(n=='rotclimate' or n.startswith('rotclimate.') for n in sys.modules)
    sys.path[:0]=[str(MODEL/'scripts'),str(MODEL)]
    from rotclimate import earth
    assert earth.CACHE.resolve().is_relative_to(MODEL.resolve())
    specs=json.loads((ROOT/six['region_specs']).read_text())
    earth.REGIONS.update(specs)
    cases=[]
    try:
        for s in six['cases']:
            name=s['region']
            write_json(OUT/'input_status.json',dict(region=name,stage='building_input_grids',integrations=0))
            child=earth.region_case(name,56.,1100.)
            assert case_hash(child)==s['case_identity']
            parent=earth.region_case(name,56.,4012.)
            offset=int((4012.-1100.)/56.)
            assert offset==52
            sl=(slice(offset,offset+child.grid.ny),slice(offset,offset+child.grid.nx))
            assert parent.grid.ny==child.grid.ny+2*offset and parent.grid.nx==child.grid.nx+2*offset
            for attr in ['land','land_frac','elev','elev_max','lat']:
                np.testing.assert_array_equal(getattr(parent.grid,attr)[sl],getattr(child.grid,attr),err_msg=(name,attr))
            np.testing.assert_array_equal(parent.lon[sl],child.lon)
            # Only the original scored footprint is scored in parent/child.
            for attr in ['obs_T','obs_P']:
                np.testing.assert_array_equal(getattr(parent,attr)[(slice(None),)+sl],getattr(child,attr))
            cases.append(dict(region=name,part=s['part'],child_case_identity=case_hash(child),
                parent_case_identity=case_hash(parent),child_shape=[child.grid.ny,child.grid.nx],
                parent_shape=[parent.grid.ny,parent.grid.nx],offset_cells=52,shared_geography_and_observations_exact=True))
            print('Prepared paired inputs:',name,flush=True)
    except BaseException as error:
        write_json(OUT/'input_preparation_failure.json',dict(exception=repr(error),integrations=0,automatic_retry=False))
        raise
    private={str(p.relative_to(MODEL)):file_hash(p) for p in sorted(MODEL.rglob('*')) if p.is_file() and '__pycache__' not in p.parts}
    for name,digest in base['private_files_sha256'].items():
        assert private[name]==digest,name
    freeze(OUT/'input_inventory.json',dict(status='prepared_six_exact_nested_geographies_no_climate_runs',
        cases=cases,model_sources_sha256=base['model_sources_sha256'],helper_sources_sha256=base['helper_sources_sha256'],
        private_files_sha256=private,libraries=base['libraries'],cell_km=56.,child_pad_km=1100.,parent_pad_km=4012.,
        preparer_sha256=file_hash(__file__),region_specs=six['region_specs'],region_specs_sha256=file_hash(ROOT/six['region_specs']),
        input_integrations=0,AA_opened=False,W18c_reopened=False))
    print('Input inventory frozen:',len(private),'files; zero climate integrations',flush=True)


if __name__=='__main__':
    main()
