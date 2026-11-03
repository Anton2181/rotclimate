"""Publish the complete fixed drying-rate qualification, including its rejection."""
from pathlib import Path
import json
import re
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'scripts')]
from local_benchmark_protocol import file_hash,write_json
from validate_r42_multistart import paired_score
from organize_climate_accuracy import organize


def main():
    import numpy as np
    source=ROOT/'output/dry_branch_validation_20261103'
    read=lambda name:json.loads((source/name).read_text())
    plan=read('plan.json');result=read('result.json');control=read('numerical_control.json')
    if result['adoption'] or result['sealed_run'] or result['outcome']!='rejected' or not control['passes']:
        raise ValueError('This publisher describes the completed rejected qualification')
    summaries={name:read(folder+'/summary.json') for name,folder in
               [('reference','reference61'),('candidate','dry_branch_040_dev61')]}
    packets={}
    for name,summary in summaries.items():
        if not summary.get('complete') or set(summary['regions'])!=set(plan['regions']):
            raise ValueError('Incomplete declared development comparison')
        folder=source/('reference61' if name=='reference' else 'dry_branch_040_dev61')
        for region,row in summary['regions'].items():
            path=folder/'cells'/(region+'.npz')
            if row['status']!='passed' or file_hash(path)!=row['cells_sha256']:
                raise ValueError('Incomplete or modified packet: '+region)
            packets[str(path.relative_to(ROOT))]=row['cells_sha256']
            with np.load(path) as z,np.load(source/'reference61/cells'/(region+'.npz')) as ref:
                for key in ['i','j','To','Po','lat','lon','elev','elev_max','coast_km']:
                    if not np.array_equal(z[key],ref[key]):raise ValueError('Changed comparison footprint')
    score=paired_score(summaries['reference']['regions'],summaries['candidate']['regions'],plan['regions'])
    historical=paired_score({n:summaries['reference']['regions'][n] for n in plan['historical49']},
                            {n:summaries['candidate']['regions'][n] for n in plan['historical49']},plan['historical49'])
    if score!=result['dev61']['dry_branch_040'] or historical!=result['S49_reported']['dry_branch_040']:
        raise ValueError('Recorded and recomputed complete scores differ')
    out=ROOT/'output/dry_branch_validation_review_20261103';out.mkdir(exist_ok=True)
    evidence=dict(result=result,control=control,summaries=summaries,packets_sha256=packets,
        result_sha256=file_hash(source/'result.json'),plan_sha256=file_hash(source/'plan.json'),
        publisher_sha256=file_hash(Path(__file__)),
        scope='One prospectively fixed candidate; all61 regions included, historical49 separately reported; no fine-grid or reserved-f run, no adoption. Earlier8-region gains were reused development evidence.')
    destination=ROOT/'atlases/climate_accuracy/data/dry_branch_validation.json'
    write_json(destination,evidence);write_json(out/'review.json',evidence)
    commit=subprocess.check_output(['git','log','-1','--format=%H','--',str((source/'result.json').relative_to(ROOT))],cwd=ROOT,text=True).strip()
    if not commit:raise ValueError('Complete raw result must be committed before publication')
    section=f'''<!--dry-branch-validation-start--><section aria-labelledby="dry-branch-validation-h">
<h2 id="dry-branch-validation-h">The drying-bound gain fails broader validation</h2>
<p>A stronger setting of the existing descending-branch drying process improved combined error by 2.54% on eight reused development regions. One exact candidate, changing only that rate to 0.4/day, was then frozen before a new complete 61-region comparison. The broader comparison <strong>rejects the candidate</strong>.</p>
<div class="table"><table><caption>Equal-region ratios versus a fresh verified r43 control; lower is better</caption><thead><tr><th>Declared pool</th><th>Combined score</th><th>Temperature error change</th><th>Rain loss change</th></tr></thead><tbody>
<tr><td>All 61 development regions</td><td>{score['S']:.6f}</td><td>{100*score['T']:+.3f}%</td><td>{100*score['P']:+.3f}%</td></tr>
<tr><td>Historical 49, separately reported</td><td>{historical['S']:.6f}</td><td>{100*historical['T']:+.3f}%</td><td>{100*historical['P']:+.3f}%</td></tr>
</tbody></table></div>
<p>The fresh baseline passed all original monthly-state reproduction tolerances and every forcing/observation footprint matched. The candidate did not meet the predeclared aggregate gate. No fine-grid or reserved-f evaluation ran; the unused holdout stays unused. Published r43 climate and all three normal atlases retain their adopted physics.</p>
<p>This result weakens the case for extrapolating a favorable small-region screen or moving a parameter bound. It does not prove a global optimum: multistart searches and boundary probes remain finite, and structural model error can dominate parameter optimization.</p>
<p><a href="data/dry_branch_validation.json" download>Complete qualification, regional errors, numerical control and packet hashes</a> · <a href="https://github.com/Anton2181/rotclimate/tree/{commit}/output/dry_branch_validation_20261103">Immutable raw monthly cell packets and results</a></p>
</section><!--dry-branch-validation-end-->'''
    page=ROOT/'atlases/climate_accuracy/index.html'
    text=re.sub(r'<!--dry-branch-validation-start-->[\s\S]*?<!--dry-branch-validation-end-->','',page.read_text())
    text=text.replace('</main>',section+'\n</main>');text,studies=organize(text)
    if organize(text)[0]!=text:raise ValueError('Navigation must be idempotent')
    page.write_text(text);write_json(out/'publication.json',dict(status='prepared',page_sha256=file_hash(page),newest=studies[0]))
    print('Published complete rejected drying-rate qualification')


if __name__=='__main__':main()
