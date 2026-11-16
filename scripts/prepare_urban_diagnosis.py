"""Restore spent transfer inputs and replay their archived conventions in isolation.

Raw Mexico workbook is supplied by the owner and remains in the ignored cache.
Only paths are redirected; the archived producer files are not edited.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import urllib.request

ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'scripts')]
from polity import earth as E

OUT=ROOT/'output/urban_diagnosis_20261116'
PLAN=ROOT/'calibration/urban_diagnosis_20261116/plan.json'
OLDWORLD=ROOT/'output/land_people/earth_restored_20261113/earth.npz'
MEXICO=OUT/'restored_mexico_newworld/earth.npz'


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def main(workbook=None):
    assert subprocess.check_output(['git','show','HEAD:'+str(PLAN.relative_to(ROOT))],cwd=ROOT)==PLAN.read_bytes()
    plan=json.loads(PLAN.read_text())
    for name,digest in plan['protected_sha256'].items():assert sha(ROOT/name)==digest,name
    OUT.mkdir(parents=True,exist_ok=True)
    zipfile=ROOT/'data/cache/floodplains_archiraq/archiraq-master.zip'
    wanted=json.loads((ROOT/'output/floodplains_blind_20261115/results.json').read_text())['source_zip_sha256']
    if not zipfile.exists():
        zipfile.parent.mkdir(parents=True,exist_ok=True)
        with urllib.request.urlopen('https://codeload.github.com/bnza/archiraq/zip/refs/heads/master',timeout=60) as response:data=response.read()
        assert hashlib.sha256(data).hexdigest()==wanted;zipfile.write_bytes(data)
    assert sha(zipfile)==wanted
    target=ROOT/'data/cache/valley_of_mexico/site-survey-data.xlsx'
    if workbook:
        target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(workbook,target)
    if not target.exists():raise FileNotFoundError('Restore the owner-supplied site-survey-data.xlsx to data/cache/valley_of_mexico; public tDAR download requires login')
    oldmex=json.loads((ROOT/'output/valley_of_mexico_blind_20261116/results.json').read_text())
    assert sha(target)==oldmex['source_sha256'],'Workbook differs from the archived transfer source'
    if not OLDWORLD.exists():
        subprocess.run([sys.executable,str(ROOT/'scripts/restore_earth_harvest_inputs.py')],cwd=ROOT,check=True)
    restoration=json.loads((ROOT/'output/earth_harvest_restoration_20261113/restoration.json').read_text())
    assert sha(OLDWORLD)==restoration['baseline_sha256'][str(OLDWORLD.relative_to(ROOT))]
    if not MEXICO.exists():
        subprocess.run([sys.executable,str(ROOT/'scripts/land_people_earth.py'),'--window','7,33,-118,-77','--extra-crops','maize','--new-world','--out',str(MEXICO.parent)],cwd=ROOT,check=True)
    assert sha(MEXICO)==oldmex['newworld_run_sha256'],'New World reconstruction differs; do not call it the archived input'
    recipes=[('floodplains','floodplains_blind.py','output/land_people/earth/earth.npz',OLDWORLD,'output/floodplains_blind_20261115'),('mexico','valley_of_mexico_blind.py','output/maize_20261116/mexico_newworld/earth.npz',MEXICO,'output/valley_of_mexico_blind_20261116')]
    checks={};inputs={str(p.relative_to(ROOT)):sha(p) for p in [PLAN,zipfile,target,OLDWORLD,MEXICO]}
    saved_earth=E.EARTH_NPZ;saved_k=os.environ.pop('ROTCLIMATE_CONFLUENCE_K',None)
    try:
        for pool,script,oldpath,earth,archived in recipes:
            producer=ROOT/'scripts'/script;source=producer.read_text();assert source.count(oldpath)==1
            E.EARTH_NPZ=earth
            namespace={'__name__':'spent_transfer_replay','__file__':str(producer)}
            exec(compile(source.replace(oldpath,str(earth.relative_to(ROOT))),str(producer),'exec'),namespace)
            path=OUT/'archived_replay'/pool;namespace['main'](path)
            previous=ROOT/archived/'results.json';actual=path/'results.json'
            a=json.loads(previous.read_text());b=json.loads(actual.read_text())
            assert a['grids']==b['grids'],pool+' archived numerical replay differs'
            assert a['model_sha256']==b['model_sha256'],pool+' archived model arrays differ'
            checks[pool]=dict(numerical_grids_exact=True,model_archive_byte_exact=True,results_byte_exact=sha(previous)==sha(actual),archived_results_sha256=sha(previous),replayed_results_sha256=sha(actual),path_substitution={oldpath:str(earth.relative_to(ROOT))},producer_sha256=sha(producer))
            for p in [actual,path/'model.npz',path/'inputs_3km.npz',path/'inputs_9km.npz',producer]:inputs[str(p.relative_to(ROOT))]=sha(p)
    finally:
        E.EARTH_NPZ=saved_earth
        if saved_k is not None:os.environ['ROTCLIMATE_CONFLUENCE_K']=saved_k
    for name,digest in plan['protected_sha256'].items():assert sha(ROOT/name)==digest,name
    receipt=dict(status='both_spent_transfer_baselines_replayed',preparer_sha256=sha(Path(__file__)),plan_sha256=sha(PLAN),inputs=inputs,checks=checks,archived_results_overwritten=False,reserved_sources_opened=False,adopt=False)
    (OUT/'input_receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
    print('Both archived numerical grids and model archives reproduced exactly; inputs frozen',flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--mexico-workbook',type=Path)
    main(p.parse_args().mexico_workbook)
