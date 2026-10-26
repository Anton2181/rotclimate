"""Attach a verified, matched-layout initialization check to an existing atlas."""
from dataclasses import asdict
from pathlib import Path
import argparse
import json
import pickle
import shutil
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT));sys.path.insert(0,str(ROOT/'scripts'))
import numpy as np
from earth_benchmark import load_params
from local_benchmark_protocol import file_hash,write_json


def validate_pair(base,warm,atlas_params):
    expected=atlas_params.replace(downsample=16,beyond_seed=1,seasonal_spinup_years=0,seasonal_require_convergence=False)
    if asdict(base.params)!=asdict(expected) or asdict(warm.params)!=asdict(expected.replace(seasonal_spinup_years=3)):
        raise ValueError('Initialization check does not match atlas physics and layout')
    if not np.array_equal(base.days,warm.days):raise ValueError('Initialization calendars differ')
    for name in ['land','land_frac','elev','elev_max','lat','inmap','target']:
        if not np.array_equal(getattr(base.grid,name),getattr(warm.grid,name)):raise ValueError('Initialization geography differs')
    if not all(r.numerics.get('all_checks_passed') for r in [base,warm]):raise ValueError('Unverified initialization fields')


def add(atlas,pilot):
    atlas=Path(atlas).resolve();pilot=Path(pilot).resolve();data=atlas/'data'
    review=json.loads((pilot/'review.json').read_text());protocol=json.loads((pilot/'protocol.json').read_text())
    if not review['complete'] or not review['all_per_step_checks_passed']:raise ValueError('Need the complete verified pilot')
    for name,expected in protocol['source_hashes'].items():
        if name.startswith(('rotclimate/','data/source/')) and file_hash(ROOT/name)!=expected:
            raise ValueError('Initialization scientific input changed: '+name)
    # The first pilot's exact world controls also bind its historical raster
    # inputs. Verify those hashes explicitly for this supplemental export.
    historical=protocol['plan']['world_cases']['r39_candidate']['legacy_checkpoint']
    with (ROOT/historical).open('rb') as stream:historical_inputs=pickle.load(stream)['identity']['map_inputs']
    raster_sources={str((ROOT/'data/source'/name).relative_to(ROOT)):expected for name,expected in historical_inputs.items()}
    for name,expected in raster_sources.items():
        if file_hash(ROOT/name)!=expected:raise ValueError('Historical atlas raster changed: '+name)
    rows={row['extra_years']:row for row in review['records'] if row['name']=='r38_atlas'}
    if not rows[0]['legacy_exact']:raise ValueError('Legacy atlas control must reproduce archived fields')
    results=[];evidence={}
    for years in [0,3]:
        path=pilot/'r38_atlas'/f'years_{years}.pkl'
        if file_hash(path)!=rows[years]['checkpoint_sha256']:raise ValueError('Changed initialization checkpoint')
        with path.open('rb') as stream:cached=pickle.load(stream)
        if cached['identity']!=review['identity']:raise ValueError('Wrong initialization checkpoint identity')
        results.append(cached['result']);evidence[str(path.relative_to(ROOT))]=file_hash(path)
    validate_pair(*results,load_params(atlas/'params.json'))
    changes=rows[3]['change_from_default'];cycle=rows[3]['numerics']['annual_cycle']
    message=('Initialization check (layout 1, screening grid): three extra years changed monthly rain by '
             f'at most {np.ceil(changes["rain_mm_month"]["maximum_absolute"]*100)/100:.2f} mm on mapped model-grid land. '
             'This is a settling check, not measured climate accuracy.')
    image=pilot/'annual_repeatability.png'
    shutil.copyfile(image,data/'initialization_check.png')
    record=dict(scope='One fixed surroundings layout at ds16; main atlas remains layouts1–3 at ds8.',
        physical_and_geographical_match=True,baseline_exact_to_archived_fields=True,additional_years=3,
        changes=changes,annual_cycle=cycle,message=message,
        evidence_sha256=evidence,pilot_review_sha256=file_hash(pilot/'review.json'),
        scientific_sources={name:value for name,value in protocol['source_hashes'].items() if name.startswith(('rotclimate/','data/source/'))},
        historical_raster_sources=raster_sources,exporter_sha256=file_hash(Path(__file__)),image_sha256=file_hash(image))
    write_json(data/'initialization_check.json',record)
    meta=json.loads((data/'atlas.json').read_text());meta['initialization_check']=dict(
        metadata='initialization_check.json',image='initialization_check.png',message=message,
        scope=record['scope'],additional_years=3,domain_repeats=cycle['domain_repeats'])
    (data/'atlas.json').write_text(json.dumps(meta,ensure_ascii=False),encoding='utf-8')
    return dict(status='passed',atlas=str(atlas.relative_to(ROOT)),metadata_sha256=file_hash(data/'atlas.json'),
                image_sha256=file_hash(data/'initialization_check.png'),message=message)


if __name__=='__main__':
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('atlas',type=Path)
    ap.add_argument('--pilot',type=Path,default=ROOT/'output/seasonal_cycle_20261026_verified');args=ap.parse_args()
    print(json.dumps(add(args.atlas,args.pilot),indent=2))
