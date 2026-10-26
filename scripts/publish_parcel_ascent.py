"""Publish the isolated ascent proof inside the existing water-reservoir study."""
from pathlib import Path
import json,shutil,sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from local_benchmark_protocol import file_hash,write_json


def main():
    out=ROOT/'output/parcel_ascent_20261026'
    protocol=json.loads((out/'protocol.json').read_text());review=json.loads((out/'review.json').read_text())
    if (not review['complete'] or not review['all_checks_passed'] or review['climate_integrations']!=0
            or review['physics_or_atlas_adoption']):raise ValueError('Need completed isolated physics proof')
    for name,sha in protocol['sources'].items():
        if file_hash(ROOT/name)!=sha:raise ValueError('Changed source epoch: '+name)
    if file_hash(out/'paths.npz')!=review['arrays_sha256']:raise ValueError('Changed raw parcel paths')
    source=out/'parcel_paths.png'
    if file_hash(source)!=review['images_sha256'][source.name]:raise ValueError('Changed parcel figure')
    data=ROOT/'atlases/climate_accuracy/data';target=data/'parcel_ascent.png';shutil.copyfile(source,target)
    write_json(data/'parcel_ascent.json',dict(review,plan=protocol['plan'],protocol_sha256=file_hash(out/'protocol.json'),
        review_sha256=file_hash(out/'review.json'),publisher_sha256=file_hash(Path(__file__)),published_image_sha256=file_hash(target)))
    section='''<!--parcel-ascent-start--><div data-parcel-study>
<h3>Next physical step: cooling and condensation during ascent</h3>
<p><strong>Isolated thermodynamic proof; zero additional Earth integrations.</strong> Eighteen declared temperature, humidity and endpoint-pressure combinations each pass at three numerical resolutions. A parcel cools dry until its root-located lifting condensation level, then follows a liquid pseudoadiabatic path. Vapor plus immediate condensate is conserved per kilogram of dry air; pressure work, temperature change and latent heat satisfy the same approximate first law.</p>
<figure><a href="data/parcel_ascent.png"><img src="data/parcel_ascent.png" width="2030" height="870" loading="lazy" alt="Dry and saturated parcel cooling, retained vapor and condensation sensitivity for all declared endpoint pressures"></a><figcaption>For the fixed300K,60% RH parcel, ascent to750/500/300hPa condenses22%/66%/95% of its initial vapor. Endpoint pressure matters: no detrainment level is selected by rainfall outcomes. All18cases remain in the download.</figcaption></figure>
<p>The largest first-law residual is0.000042J/kg dry air; the water residual is below4×10⁻¹⁸kg/kg dry air. This verifies the declared approximation, not atmospheric energy closure. Constant dry heat capacity and latent heat, no entrainment or environmental heating, and liquid saturation at cold temperatures remain limitations. These parcels do not yet alter the seasonal model, rainfall scores or normal atlas climates.</p>
<p><a href="data/parcel_ascent.json" download>Download all parcel endpoints and numerical checks</a> · <a href="../../reports/PARCEL_ASCENT_20261026.md">Equations, all outcomes and coupling limits</a></p>
</div><!--parcel-ascent-end-->'''
    page=ROOT/'atlases/climate_accuracy/index.html';content=page.read_text();start='<!--parcel-ascent-start-->';end='<!--parcel-ascent-end-->'
    if start in content:
        before,rest=content.split(start,1);_,after=rest.split(end,1);content=before+section+after
    else:
        anchor='<p><a href="data/independent_water.json" download>'
        if content.count(anchor)!=1:raise ValueError('Need published parent independent-water study')
        content=content.replace(anchor,section+'\n'+anchor)
    page.write_text(content)
    write_json(out/'publication.json',dict(scope='Isolated parcel thermodynamics; no climate adoption',
        page_sha256=file_hash(page),metadata_sha256=file_hash(data/'parcel_ascent.json'),
        image_sha256=file_hash(target),publisher_sha256=file_hash(Path(__file__))))


if __name__=='__main__':main()
