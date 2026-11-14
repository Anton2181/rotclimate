"""Capture the declared full weather packet with added rainfall on the fixed grid."""
from concurrent.futures import ThreadPoolExecutor,as_completed
import json
from pathlib import Path
import subprocess

import capture_regional_reference_weather as parent

ROOT=Path(__file__).resolve().parents[1]
PLAN=ROOT/'calibration/matched_regional_weather_20261114/plan.json'
DEST=ROOT/'data/source/matched_regional_weather_20261114'


def main():
    assert subprocess.check_output(['git','show','HEAD:'+str(PLAN.relative_to(ROOT))],cwd=ROOT)==PLAN.read_bytes()
    plan=json.loads(PLAN.read_text());DEST.mkdir(parents=True,exist_ok=True);parent.DEST=DEST
    records=[]
    with ThreadPoolExecutor(max_workers=4) as pool:
        tasks=[pool.submit(parent.capture,cell,plan['weather_grid']) for cell in plan['weather_grid']['cells']]
        for task in as_completed(tasks):
            record=task.result();records.append(record);print('Captured',len(records),'/30',record['cell']['id'],flush=True)
    records.sort(key=lambda row:row['cell']['id'])
    receipt=dict(status='captured_before_matched_weather_aggregation',plan_sha256=parent.digest(PLAN.read_bytes()),capturer_sha256=parent.digest(Path(__file__).read_bytes()),parent_capturer_sha256=parent.digest(Path(parent.__file__).read_bytes()),sources=records,adopt=False)
    (DEST/'sources.json').write_text(json.dumps(receipt,indent=2)+'\n')


if __name__=='__main__':main()
