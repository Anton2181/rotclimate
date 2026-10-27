"""Publish verified PNW native circulation inside its parent climate study."""
from pathlib import Path
import json,shutil,sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from local_benchmark_protocol import file_hash,write_json


def main():
    out=ROOT/'output/pnw_transport_20261027';protocol=json.loads((out/'protocol.json').read_text());review=json.loads((out/'review.json').read_text())
    if not review['complete'] or not review['all_checks_passed'] or review['physics_or_atlas_adoption']:raise ValueError('Need successful diagnostic audit')
    for name,sha in protocol['sources'].items():
        if file_hash(ROOT/name)!=sha:raise ValueError('Changed diagnostic source: '+name)
    for name,row in review['rows'].items():
        if not row['parent_climate_exact'] or file_hash(out/(name+'.npz'))!=row['arrays_sha256']:raise ValueError('Unverified diagnostic climate')
    data=ROOT/'atlases/climate_accuracy/data';images={}
    for source_name,target_name in [('native_vectors.png','pnw_native_vectors.png'),('monthly_diagnostics.png','pnw_monthly_diagnostics.png')]:
        source=out/source_name
        if file_hash(source)!=review['images_sha256'][source_name]:raise ValueError('Changed audit picture')
        shutil.copyfile(source,data/target_name);images[target_name]=file_hash(data/target_name)
    write_json(data/'pnw_transport.json',dict(review,plan=protocol['plan'],protocol_sha256=file_hash(out/'protocol.json'),review_sha256=file_hash(out/'review.json'),publisher_sha256=file_hash(Path(__file__)),published_images_sha256=images))
    counts=review['rows']['reference']['circulation']['coverage']
    names={'reference':'r39','reservoir_control':'Previous independent water','column_no_mix':'Corrected convection/recycling'};table=[]
    for name,label in names.items():
        row=review['rows'][name];wind=row['circulation']['scores']['q925_300']['ocean']
        humidity=row['circulation'].get('humidity',{}).get('scores',{}).get('ocean')
        q='—' if humidity is None else f'{humidity["model_partial_q_ratio"]:.3f}'
        table.append(f'<tr><td>{label}</td><td>{row["rain"]["sim_mean_annual_mm"]:.0f}</td><td>{wind["vector_rmse_ms"]:.2f}</td><td>{q}</td></tr>')
    section=f'''<!--pnw-transport-start--><div data-pnw-transport><h3>Pacific Northwest: check the incoming circulation</h3>
<p><strong>Separate diagnostic, three actual climate reruns; no tuning or adoption.</strong> Every run reproduces the parent rainfall cells and temperature scores; r39 also reproduces archived monthly temperature/rain cells. New NCEP/NCAR pressure-level data use the same verified units, true-area native aggregation, projected-vector conversion, calendar weights and terrain/coast exclusions as the earlier circulation audits. Coverage retains{counts['ocean_cells']}ocean and{counts['land_cells']}land native footprints.</p>
<figure><a href="data/pnw_native_vectors.png"><img src="data/pnw_native_vectors.png" width="2030" height="1160" loading="lazy" alt="Winter and summer matched native Pacific Northwest geographic wind vectors in reanalysis, r39 and both moisture implementations"></a><figcaption>The reference is a q-weighted925–300hPa partial column; modeled vectors are whole-column moisture diagnostics. This approximation and monthly-mean reference omit vertical detail and transient moisture covariance. Arrows share a speed scale.</figcaption></figure>
<div class="table"><table><caption>Identical PNW climates; matched native ocean diagnostics</caption><thead><tr><th>Profile</th><th>Annual land rain mm</th><th>Ocean vector RMSE m/s</th><th>Partial upper/lower q</th></tr></thead><tbody>{''.join(table)}</tbody></table></div>
<figure><a href="data/pnw_monthly_diagnostics.png"><img src="data/pnw_monthly_diagnostics.png" width="2030" height="783" loading="lazy" alt="Pacific Northwest monthly eastward ocean circulation, land rainfall and actual partial humidity shape"></a><figcaption>More or less rainfall is not evidence by itself of better circulation. The coarse, model-assisted1981–2010 reanalysis differs from the WorldClim1970–2000 rainfall period. Native footprints are reused diagnostics, not a new global validation set.</figcaption></figure>
<p><a href="data/pnw_transport.json" download>Download Pacific Northwest circulation and humidity audit</a> · <a href="../../reports/PNW_TRANSPORT_20261027.md">Sources, measurements and limitations</a></p></div><!--pnw-transport-end-->'''
    page=ROOT/'atlases/climate_accuracy/index.html';content=page.read_text();start='<!--pnw-transport-start-->';end='<!--pnw-transport-end-->'
    if start in content:
        before,rest=content.split(start,1);_,after=rest.split(end,1);content=before+section+after
    else:
        anchor='<p><a href="data/column_rain.json" download>'
        if content.count(anchor)!=1:raise ValueError('Publish parent column-rain study first')
        content=content.replace(anchor,section+'\n'+anchor)
    content=content.replace('Updated 26 October 2026','Updated 27 October 2026');page.write_text(content)
    write_json(out/'publication.json',dict(scope='PNW diagnostic only',page_sha256=file_hash(page),metadata_sha256=file_hash(data/'pnw_transport.json'),images_sha256=images,publisher_sha256=file_hash(Path(__file__))))


if __name__=='__main__':main()
