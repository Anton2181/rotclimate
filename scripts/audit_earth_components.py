"""Render the evidence ledger without scoring or changing any model."""
from pathlib import Path
import argparse
import csv
import json
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))


def main():
    from rotclimate.evidence_audit import audit
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--out',type=Path,default=ROOT/'output/earth_components_20261105');a=ap.parse_args();a.out.mkdir(parents=True,exist_ok=True)
    spec=json.loads((ROOT/'calibration/earth_components_20261105/evidence_spec.json').read_text());result=audit(ROOT,spec)
    (a.out/'ledger.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    with (a.out/'parameters.csv').open('w',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=['component','source','pointer','value','status','note','evidence']);writer.writeheader()
        for r in result['parameters']:writer.writerow(dict(r,evidence=' | '.join(r.get('evidence',[]))))
    lines=['# Earth calibration evidence ledger','',spec['scope'],'','| Component | Numeric records | Evidence categories | Next empirical test |','|---|---:|---|---|']
    for c in result['components']:lines.append('| '+c['label']+' | '+str(c['parameters_reviewed'])+' | '+', '.join(k+': '+str(v) for k,v in sorted(c['counts'].items()))+' | '+c['next_test']+' |')
    lines+=['','Published relationships are not automatically locally calibrated. Historical fits can contain reconstructed or model-derived targets. Evidence records do not establish identifiability of individual coefficients.','']
    (a.out/'ledger.md').write_text('\n'.join(lines));print('Audited',len(result['components']),'components,',len(result['parameters']),'numeric configuration records')


if __name__=='__main__':main()
