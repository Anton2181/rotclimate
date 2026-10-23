"""Write the local entry page comparing the three completed atlas fits."""
from html import escape
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]


def main():
    descriptions={
        'free_fit':('Free fit','World and physics fitted to the seasonal painted zones.'),
        'earth_fit':('Earth fit','World fitted with Earth r35 physics held fixed.'),
        'whittaker_fit':('Whittaker fit','World and physics fitted to the proposed annual-biome targets.')}
    cards=[];rows=[];population_rows=[];density_cards=[]
    for name,(title,description) in descriptions.items():
        summary=json.loads((ROOT/'atlases'/name/'summary.json').read_text())
        verified=bool(summary.get('observed_numerics',{}).get('all_checks_passed'))
        strict=summary['whittaker']['strict']
        metadata=json.loads((ROOT/'atlases'/name/'data/atlas.json').read_text())
        outside=metadata['biomes'][0]['share']
        if summary.get('fit_objective')=='whittaker-covered':
            description+=' A coverage guard limits land outside the original biome diagram.'
        h=summary['harvest'];pop=h['population']['endemic']
        population_rows.append(f'<tr><th scope="row">{title}</th><td>{h["food_capacity"]/1e6:.1f} M</td><td>{pop["frontier"]/1e6:.1f} M</td><td>{pop["central"]/1e6:.1f} M</td><td>{pop["core"]/1e6:.1f} M</td></tr>')
        density_cards.append(f'<article><a href="{name}/#layer=land_density&amp;occupation=central&amp;disease=endemic"><img src="{name}/data/land_density_central_endemic.webp" alt="{title} central population density scenario"><h2>{title}: land and people</h2></a><p>{pop["central"]/1e6:.1f} M people in the central scenario</p></article>')
        cards.append(f'<article><a href="{name}/"><img src="{name}/data/whittaker.webp" alt="{escape(title)} potential biome map"><h2>{escape(title)}</h2></a>'
                     f'<p>{escape(description)}</p><p class="status">Numerical checks: {"passed" if verified else "unverified"} · outside diagram: {outside:.2%}</p></article>')
        rows.append(f'<tr><th scope="row"><a href="{name}/">{title}</a></th><td>{summary["zonefit"]:.4f}</td>'
                    f'<td>{strict["score"]:.4f}</td><td>{summary["strict_accuracy"]:.1%}</td><td>{strict["macro_hard"]:.1%}</td>'
                    f'<td>{outside:.2%}</td><td>{summary["mediterranean"]["dry_share"]:.1%}</td><td>{summary["mediterranean"]["cs_share"]:.1%}</td></tr>')
    html='''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Rotclimate · Three Fits</title><style>
:root{font-family:system-ui,sans-serif;color:#1b3037;background:#edf2ef}body{max-width:1200px;margin:auto;padding:38px 22px 70px}h1{font-family:Georgia,serif;font-size:clamp(2rem,5vw,3.8rem);margin:.3em 0}h2{margin:14px 18px 8px}a{color:#145f67}p{line-height:1.6;max-width:85ch}.cards{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:18px;margin:30px 0}article{background:white;border:1px solid #c9d6d2;border-radius:10px;overflow:hidden}article img{width:100%;aspect-ratio:2.16;object-fit:cover}article p{margin:10px 18px 18px}article a{text-decoration:none}.status{font-size:.85rem;color:#327257}.table{overflow-x:auto}table{width:100%;border-collapse:collapse;background:#fff}th,td{text-align:left;border-bottom:1px solid #d8e0dd;padding:14px}thead th{background:#e0e9e3;font-size:.85rem}.note{font-size:.9rem;color:#4b6268}@media(max-width:750px){.cards{grid-template-columns:1fr}}
</style><header><p class="note">ROTCLIMATE · THREE CALIBRATION OBJECTIVES · UPDATED 23 OCTOBER 2026</p><h1>One world, three climate fits</h1>
<p>Compare the seasonal map fit, the fit constrained by Earth physics, and the fit to proposed Whittaker biomes. Each atlas uses the mean climate over the same three layouts of the unknown surroundings.</p></header>
<section class="cards">'''+''.join(cards)+'''</section><section><h2>Compare the same measures</h2><div class="table"><table><thead><tr><th>Atlas</th><th>Seasonal zone objective</th><th>Whittaker objective</th><th>Exact zone agreement</th><th>Mean biome agreement</th><th>Land outside diagram</th><th>Med. dry</th><th>Med. Cs</th></tr></thead><tbody>'''+''.join(rows)+'''</tbody></table></div>
<p class="note">Each target zone counts equally in mean biome agreement. Objective scores measure different definitions of a match and are not interchangeable. These figures classify the mean climate fields; calibration logs average scores across individual layouts.</p>
<p class="note">Med. dry and Med. Cs are the shares of the painted Mediterranean zone classified as Köppen dry climates and Mediterranean climates, respectively.</p>
<p>The Whittaker atlas includes the proposed biome target map and a separate match layer. Annual temperature and rainfall do not determine Mediterranean summer drought or swamp hydrology, so those seasonal diagnostics remain separate.</p>
<h2>Explore a population budget</h2><p>The Population topic adds six maps: allocated residents, local pressure, spare food support, redistribution, walking to markets and settlement attraction. Supply a total and choose even occupation, water and terrain, or market access. Province totals and CSV downloads follow your chosen census; unsupported people are reported separately.</p>
<p>Compare the same 50 million people: <a href="free_fit/#layer=pop_density&amp;population=50000000&amp;pattern=markets">Free fit</a> · <a href="earth_fit/#layer=pop_density&amp;population=50000000&amp;pattern=markets">Earth fit</a> · <a href="whittaker_fit/#layer=pop_density&amp;population=50000000&amp;pattern=markets">Whittaker fit</a>.</p>
<h2>Land and people around 200 AD</h2><p>Every atlas includes Harvest farming layers, malaria potential, place readouts, province totals and CSV downloads. Choose a map topic to see a small set of related layers. Overview contains the combined settlement-potential and expected-density maps. The occupation scenarios below estimate totals from environmental food support and historical analogues; the Population lab takes a supplied total and explores its distribution.</p>
<div class="cards">'''+''.join(density_cards)+'''</div>
<div class="table"><table><thead><tr><th>Atlas</th><th>Mixed food ceiling</th><th>Frontier scenario</th><th>Central scenario</th><th>Settled-core scenario</th></tr></thead><tbody>'''+''.join(population_rows)+'''</tbody></table></div>
<p class="note">Low-input Han, Roman and Parthian technology; environmental malaria potential included. Occupation scenarios are historical analogues, not confidence intervals or reconstructed censuses. Each atlas exposes the assumptions and a choice to remove the malaria penalty. All three density maps share one colour scale.</p>
<p><a href="../reports/ITERATION_20261023.md">Population lab and latest milestones</a> · <a href="../reports/HARVEST_MIGRATION_20261022.md">Food, disease and settlement models</a> · <a href="../reports/THREE_FIT_20261022.md">Campaign report</a> · <a href="../docs/BIOMES.md">Biome methods</a></p></section></html>'''
    (ROOT/'atlases/index.html').write_text(html)


if __name__=='__main__':main()
