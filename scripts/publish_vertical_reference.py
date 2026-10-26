"""Portable publication of the frozen native Earth vertical-reference audit."""
from pathlib import Path
import json,shutil,sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from local_benchmark_protocol import file_hash,write_json


def main():
    out=ROOT/'output/vertical_reference_20261026';protocol=json.loads((out/'protocol.json').read_text());review=json.loads((out/'review.json').read_text())
    if not review['complete'] or review['climate_integrations']!=0 or review['physics_or_atlas_adoption']:raise ValueError('Need completed diagnostic-only audit')
    for name,sha in protocol['sources'].items():
        if file_hash(ROOT/name)!=sha:raise ValueError('Changed reference epoch: '+name)
    data=ROOT/'atlases/climate_accuracy/data';pictures={}
    for original,target in [('native_profiles.png','vertical_reference_native.png'),('capacity_profiles.png','vertical_reference_capacity.png')]:
        source=out/original
        if file_hash(source)!=review['images_sha256'][original]:raise ValueError('Changed reference image')
        shutil.copyfile(source,data/target);pictures[target]=file_hash(data/target)
    write_json(data/'vertical_reference.json',dict(review,protocol_sha256=file_hash(out/'protocol.json'),review_sha256=file_hash(out/'review.json'),
        publisher_sha256=file_hash(Path(__file__)),published_images_sha256=pictures))
    section='''<!--vertical-reference-start--><section aria-labelledby="vertical-reference-h"><h2 id="vertical-reference-h">Earth vertical temperature and moisture</h2>
<p><strong>Cached reference diagnostic; no climate integration or new rainfall accuracy score.</strong> Both hydrostatic profiles start from observed925hPa temperature, withholding higher temperatures and humidity. They are compared on the same native925–300hPa nodes and ocean footprints as the preceding circulation audit:3 California cells and20 Iberian cells.</p>
<figure><a href="data/vertical_reference_native.png"><img src="data/vertical_reference_native.png" width="1740" height="1160" loading="lazy" alt="NCEP native ocean vertical temperatures and partial-column water compared with environmental-lapse and saturated-moist profiles"></a><figcaption>The moist profile gives a closer humidity shape than extending the fitted surface lapse through the atmosphere. Shown column RH0.60 is the fixed middle value in the declared design; all six profile/humidity combinations remain in the download.</figcaption></figure>
<p>Observed upper/lower partial-column q ratios are0.300/0.243, compared with lapse capacity0.475/0.474 and moist capacity0.324/0.320 (California/Iberia). These925–700 and700–300hPa layers do not equal the model's full-column dry-mass split. Lower declared column humidity improves these partial water comparisons, but no new values are fitted or added to the running Earth plan.</p>
<figure><a href="data/vertical_reference_capacity.png"><img src="data/vertical_reference_capacity.png" width="1740" height="696" loading="lazy" alt="Pressure-integrated whole-column saturation and temperature-dependent humidity capacity shape compared with the legacy fixed vapor scale"></a><figcaption>Saturation capacity is not actual water. The prescribed200K upper thermal boundary, omitted water above100hPa, liquid approximation and lack of inversions remain physical limitations; cold capacity ratios can be high while total water is tiny.</figcaption></figure>
<p>NCEP1981–2010 is model-assisted and differs from the WorldClim rainfall period. These small ocean samples and observed-temperature anchors do not validate land rainfall, surface RH, full-column dynamics or fantasy geography. Existing atlas climates and headline scores remain unchanged.</p>
<p><a href="data/vertical_reference.json" download>Download native thermal and humidity comparisons</a> · <a href="../../reports/VERTICAL_REFERENCE_20261026.md">Reference footprints, all measurements and limitations</a> · <a href="../../reports/PRESSURE_COLUMN_20261026.md">Coupled Earth comparison protocol</a></p></section><!--vertical-reference-end-->'''
    page=ROOT/'atlases/climate_accuracy/index.html';content=page.read_text();start='<!--vertical-reference-start-->';end='<!--vertical-reference-end-->'
    if start in content:
        before,rest=content.split(start,1);_,after=rest.split(end,1);content=before+section+after
    else:content=content.replace('</main>',section+'\n</main>')
    page.write_text(content)
    write_json(out/'publication.json',dict(scope='Reference audit only; no climate adoption',metadata_sha256=file_hash(data/'vertical_reference.json'),page_sha256=file_hash(page),images_sha256=pictures,publisher_sha256=file_hash(Path(__file__))))


if __name__=='__main__':main()
