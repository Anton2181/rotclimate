"""Publish completed r39 reference controls; prototype month scores stay pending."""
from pathlib import Path
import argparse,json,shutil,sys
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from PIL import Image
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'scripts')]
from local_benchmark_protocol import file_hash,write_json
from analyze_regional_rainfall import analyze


def publish(source,out):
    out.mkdir(parents=True,exist_ok=True);analyze(source,out/'analysis');a=json.loads((out/'analysis/analysis.json').read_text());plan=json.loads((source/'frozen_protocol.json').read_text());regions=['north_india','mexico','pacific_nw'];controls={};records=[]
    for region in regions:
        spec=next(c for c in plan['cases'] if c['kind']=='legacy' and c['region']==region);folder=source/spec['name'];r=json.loads((folder/'verification.json').read_text());assert r['qualified_r39_reproduced'] and r['legacy_strict_passes_added']==1
        controls[region]=dict(protocol=json.loads((folder/'frozen_plan.json').read_text()),verification=r,raw_sha256=file_hash(folder/'raw.npz'));row=a['baselines'][region];assert row['qualified'];m=row['metrics'];records.append(f'<tr><td>{region.replace("_"," ")}</td><td>{row["month"]}</td><td>{m["cells"]}</td><td>{m["observed_mean_mm_day"]:.3f}</td><td>{m["predicted_mean_mm_day"]:.3f}</td><td>{m["mae_mm_day"]:.3f}</td><td>{m["bias_mm_day"]:.3f}</td></tr>')
    fig,axes=plt.subplots(1,2,figsize=(12,4.8));x=np.arange(3);rows=[a['baselines'][r]['metrics'] for r in regions]
    axes[0].bar(x-.17,[r['observed_mean_mm_day'] for r in rows],.34,label='WorldClim monthly normal',color='#2482ac');axes[0].bar(x+.17,[r['predicted_mean_mm_day'] for r in rows],.34,label='Qualified r39',color='#ac6a3e');axes[0].set_title('Mean rain on fixed common footprints');axes[0].legend(fontsize=9)
    axes[1].bar(x,[r['mae_mm_day'] for r in rows],color='#ac6a3e');axes[1].set_title('Area-weighted r39 rainfall MAE')
    for ax in axes:ax.set_xticks(x,['India / July','Mexico / August','PNW / July']);ax.set_ylabel('mm/day');ax.grid(axis='y',alpha=.2)
    fig.suptitle('Verified baseline for the declared regional monthly rainfall test',fontsize=14);fig.text(.5,.01,'Exact archived r39 reproduction • Gregorian calendar • same fixed observation footprints • prototype month scores pending',ha='center',fontsize=9);fig.tight_layout(rect=(0,.04,1,.94));fig.savefig(out/'regional_rainfall_reference.png',dpi=160);plt.close(fig)
    with np.load(out/'analysis/evaluation_fields.npz') as fields:np.savez_compressed(out/'reference_fields.npz',**{k:fields[k] for k in fields.files if '_reference_' in k or k.endswith('_r39_rate')})
    result=dict(status='three_qualified_r39_controls_reproduced',legacy_benchmark_attempts_added=3,legacy_strict_passes_added=3,legacy_attempts=1937,legacy_strict_passes=1932,prototype_integrations_added_by_reference_study=0,reference_metrics=a['baselines'],prototype_month_scores='pending; no pooled candidate comparison in this reference publication',physical_adoption=False,recalibration=False,figure_sha256=file_hash(out/'regional_rainfall_reference.png'),fields_sha256=file_hash(out/'reference_fields.npz'),publisher_sha256=file_hash(Path(__file__)),analyzer_sha256=a['analyzer_sha256'],scope='Completed baseline/reference milestone only. Three reused region/month pairs under fixed footprints, not annual/global or held-out skill. No new prototype result is substituted for an incomplete calendar month.')
    write_json(out/'publication.json',result);dest=ROOT/'atlases/climate_accuracy/data';shutil.copyfile(out/'regional_rainfall_reference.png',dest/'regional_rainfall_reference.png');shutil.copyfile(out/'reference_fields.npz',dest/'regional_rainfall_reference_fields.npz');write_json(dest/'regional_rainfall_reference.json',dict(protocol=plan,controls=controls,publication=result))
    with Image.open(out/'regional_rainfall_reference.png') as im:w,h=im.size
    section=f'''<!--regional-rainfall-reference-start--><section aria-labelledby="regional-rainfall-reference-h"><h2 id="regional-rainfall-reference-h">Verified r39 reference for the complete-month rainfall test</h2>
<p>All three r39 controls reproduce their archived monthly float32 temperature and rain fields exactly and pass strict numerical checks. Their raw annual output is reaggregated with the Gregorian interval-overlap calendar. These new reference runs establish the baseline before interpreting any new prototype month.</p>
<figure><a href="data/regional_rainfall_reference.png"><img src="data/regional_rainfall_reference.png" width="{w}" height="{h}" loading="lazy" alt="WorldClim and qualified r39 rainfall means and r39 absolute errors on the fixed region/month footprints; prototype scores are pending"></a><figcaption>The baseline substantially underestimates the selected monsoon-month rainfall in India and Mexico. These are the new test footprints, not a replacement for the model's annual development score.</figcaption></figure>
<div class="table"><table><caption>WorldClim monthly climatology and exactly reproduced r39 on identical scored land area</caption><thead><tr><th>Region</th><th>Month</th><th>Cells</th><th>Observed mm/day</th><th>r39 mm/day</th><th>MAE mm/day</th><th>Bias mm/day</th></tr></thead><tbody>{''.join(records)}</tbody></table></div>
<p>The centered 224-km footprints use fine-cell projection-area weights and at least 80% valid reference land coverage. The same fixed masks will score every prototype branch. The seven month-long prototype trials are separate: both wet/dry starts in each region at 900 seconds, plus Mexico wet at 450 seconds as a numerical check. A fourteen-day prelude is not assumed to erase soil-water memory.</p>
<p class="note">Prototype month scores remain pending here. The primary comparison will average six independently scored wet/dry losses, permitting regional tradeoffs while avoiding selection of a favorable initialization. It will be withheld if a primary case is incomplete, budget-invalid, or lacks its verified r39 control. Three reused summer region/month pairs do not establish annual/global validation. This reference milestone adds three legacy attempts and three strict passes: 1937/1932. It adds zero prototype integrations and changes no normal atlas climate, biome or population fields.</p>
<p><a href="data/regional_rainfall_reference.json" download>Download fixed benchmark protocol, all three r39 controls and reference metrics</a> · <a href="data/regional_rainfall_reference_fields.npz">Observation masks, areas and Gregorian r39 rainfall fields</a> · <a href="../../reports/REGIONAL_RAINFALL_REFERENCE_20261029.md">Reference results</a> · <a href="../../reports/REGIONAL_RAINFALL_BENCHMARK_DECLARATION_20261029.md">Frozen complete-month test</a></p></section><!--regional-rainfall-reference-end-->'''
    page=ROOT/'atlases/climate_accuracy/index.html';text=page.read_text();start,end='<!--regional-rainfall-reference-start-->','<!--regional-rainfall-reference-end-->'
    if start in text:
        before,tail=text.split(start,1);_,after=tail.split(end,1);text=before+section+after
    else:text=text.replace('<!--research-list-start-->',section+'\n<!--research-list-start-->',1)
    page.write_text(text);print(json.dumps(result,indent=2))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args();publish(a.source,a.out)
