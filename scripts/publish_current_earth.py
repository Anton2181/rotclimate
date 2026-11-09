"""Refresh the current Earth overview while retaining labelled historical studies."""
import hashlib
import json
from pathlib import Path
import re
import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / 'scripts')]


def main():
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    import numpy as np
    from check_v22_release_inputs import verify_correction
    physics = ROOT/'calibration/local_accuracy_20261023/r44_params.json'
    cal = ROOT/'calibration/earth_correction_r44_20261107'
    adopted = json.loads((ROOT/'calibration/local_accuracy_20261023/r44_adoption.json').read_text())
    assert adopted['adopted']=='r44' and all(adopted['scores'][k] for k in ['dev_pass','fine_pass','sealed_pass'])
    assert hashlib.sha256(physics.read_bytes()).hexdigest()==adopted['params_sha256']
    correction = {name:json.loads((cal/name/'protocol.json').read_text())['meta'] for name in ['temperature','rain_pattern']}
    hashes = {name:verify_correction(cal/name, physics) for name in correction}
    source = ROOT/'output/east_asia_p6_20261107/gate_d15'; regions = {}; paths = []
    for part in ['candidate_dev31','candidate_retired_a','candidate_retired_b','candidate_retired_c']:
        path = source/part/'summary.json'; paths.append(path); summary=json.loads(path.read_text())
        assert summary['complete']
        for name, row in summary['regions'].items():
            assert name not in regions and row['status']=='passed' and row['numerics']['all_checks_passed']
            regions[name]=row
    assert len(regions)==49
    raw49 = dict(regions=49,monthly_temperature_mae_C=sum(r['temperature']['monthly_mae_C'] for r in regions.values())/49,
        rain_loss=sum(r['rain']['loss'] for r in regions.values())/49)
    cv31 = dict(regions=31,raw_temperature_mae_C=correction['temperature']['raw_monthly_mae_C'],
        corrected_temperature_mae_C=correction['temperature']['held_out_monthly_mae_C'],
        raw_rain_loss=correction['rain_pattern']['raw_loss'],corrected_rain_loss=correction['rain_pattern']['held_out_loss'])
    data=ROOT/'atlases/climate_accuracy/data'; data.mkdir(parents=True,exist_ok=True)
    result=dict(profile='r44',date='2026-11-09',raw_development49=raw49,correction_cluster_cv31=cv31,
        adoption=adopted,recovered_model_sha256=hashes,
        source_files_sha256={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in [*paths,physics,cal/'release_receipt.json']},
        interpretation='Original r44 adoption evidence plus correction-reconstruction replay. 49 raw regions and31 correction regions are different pools; never subtract their errors as a paired improvement. No new unseen validation.')
    (data/'current_earth_r44.json').write_text(json.dumps(result,indent=2)+'\n')
    fig,axes=plt.subplots(1,2,figsize=(10.5,4.3),layout='constrained');fig.patch.set_facecolor('#f1f3ef')
    previous=ROOT/'calibration/earth_correction_r43_20261103'
    for ax,name,raw_key,cv_key,metric in [(axes[0],'temperature','raw_monthly_mae_C','held_out_monthly_mae_C','Monthly temperature MAE · °C'),(axes[1],'rain_pattern','raw_loss','held_out_loss','Rain loss · lower is better')]:
        old=json.loads((previous/name/'protocol.json').read_text())['meta'];new=correction[name];x=np.arange(2)
        ax.bar(x-.17,[old[raw_key],new[raw_key]],.34,label='Raw physics',color='#ad7c54')
        ax.bar(x+.17,[old[cv_key],new[cv_key]],.34,label='Cluster CV correction',color='#367a71')
        ax.set(xticks=x,xticklabels=['r43 reference','Recovered r44'],ylabel=metric)
        for i,v in enumerate([old[cv_key],new[cv_key]]): ax.text(i+.17,v,f'{v:.4f}',ha='center',va='bottom',fontsize=9)
        ax.set_ylim(0,max(old[raw_key],new[raw_key])*1.18);ax.grid(axis='y',alpha=.15);ax.legend(fontsize=8)
    fig.suptitle('Recovered Earth correction models · the same 31-region study',fontsize=13)
    fig.supxlabel('Fixed recipe; leave whole clusters out; weights selected within that CV.\nReused development data, not a new blind test. Corrected changes include refitting the correction.',fontsize=9)
    fig.savefig(data/'r44_reconstruction.png',dpi=145);plt.close(fig)
    section=f'''<!--current-earth-overview-start--><h2>Current adopted raw Earth physics: r44</h2>
<p>On the original 49-region development pool, monthly temperature MAE is <strong>{raw49['monthly_temperature_mae_C']:.4f} °C</strong> and rain loss <strong>{raw49['rain_loss']:.5f}</strong>. At adoption, combined error was {100*(1-adopted['scores']['dev49']['S']):.2f}% below r43; the paired finer-grid check passed, and then-unseen set g passed with combined error {100*(1-adopted['scores']['sealed_g']['S']):.2f}% below r43. Set g is now spent. These are regional checks, not a global accuracy percentage.</p>
<p>The r44 temperature and rainfall correction models were missing from Git. Rebuilding the unchanged recipe reproduces their previous rounded results: <strong>{cv31['corrected_temperature_mae_C']:.4f} °C</strong> and rain loss <strong>{cv31['corrected_rain_loss']:.5f}</strong> on the separate 31-region cluster-CV study. Its raw values are {cv31['raw_temperature_mae_C']:.4f} °C / {cv31['raw_rain_loss']:.5f}. The recovered files have new identities; this is reconstruction on reused data, not fresh validation. The 49-region and31-region errors are not a paired comparison.</p>
<figure><img src="data/r44_reconstruction.png" alt="Raw and cluster-cross-validated errors for r43 and reconstructed r44 on the same31 development regions"><figcaption>Temperature and rainfall corrections reconstructed on the original development pool; no new unseen accuracy claim.</figcaption></figure>
<p>Earth orbital forcing remains fixed in joint calibration. The new terrain-file input belongs to world geography, while plateau steering remains shared physics. A later coast-coupling candidate passed development but failed its unseen test and was rejected; r44 remains adopted.</p>
<p><a href="data/current_earth_r44.json" download>Current measurements and provenance</a> · <a href="../../reports/R44_RECONSTRUCTION_20261109.md">Reconstruction and input-boundary checks</a></p>
<h2>Historical r39 benchmark · 27 October 2026</h2><p class="note">The cards and audit immediately below retain their original r39 measurements and sample definitions. They are not current r44 city accuracy.</p><!--current-earth-overview-end-->'''
    page=ROOT/'atlases/climate_accuracy/index.html';html=page.read_text()
    if '<!--current-earth-overview-start-->' not in html: raise ValueError('Missing current/historical overview boundary')
    html=re.sub(r'<!--current-earth-overview-start-->.*?<!--current-earth-overview-end-->',lambda m:section,html,count=1,flags=re.S)
    html=re.sub(r'Updated \d+ \w+ \d{4} · current results and historical benchmarks','Updated 9 November 2026 · current results and historical benchmarks',html,count=1)
    page.write_text(html)
    print('Published current r44 overview; historical experiments retained with their original labels')


if __name__=='__main__':main()
