"""Write the local entry page comparing the three completed atlas fits."""
from html import escape
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]


def main():
    descriptions={
        'free_fit':('Free fit','World and physics fitted to the seasonal painted zones.'),
        'earth_fit':('Earth fit','World fitted with Earth r29 physics held fixed.'),
        'whittaker_fit':('Whittaker fit','World and physics fitted to the proposed annual-biome targets.')}
    cards=[];rows=[]
    for name,(title,description) in descriptions.items():
        summary=json.loads((ROOT/'atlases'/name/'summary.json').read_text())
        verified=bool(summary.get('observed_numerics',{}).get('all_checks_passed'))
        strict=summary['whittaker']['strict']
        cards.append(f'<article><a href="{name}/"><img src="{name}/data/whittaker.webp" alt="{escape(title)} potential biome map"><h2>{escape(title)}</h2></a>'
                     f'<p>{escape(description)}</p><p class="status">Numerical checks: {"passed" if verified else "unverified"}</p></article>')
        rows.append(f'<tr><th scope="row"><a href="{name}/">{title}</a></th><td>{summary["zonefit"]:.4f}</td>'
                    f'<td>{strict["score"]:.4f}</td><td>{summary["strict_accuracy"]:.1%}</td><td>{strict["macro_hard"]:.1%}</td>'
                    f'<td>{summary["mediterranean"]["dry_share"]:.1%}</td><td>{summary["mediterranean"]["cs_share"]:.1%}</td></tr>')
    html='''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Rotclimate · Three Fits</title><style>
:root{font-family:system-ui,sans-serif;color:#1b3037;background:#edf2ef}body{max-width:1200px;margin:auto;padding:38px 22px 70px}h1{font-family:Georgia,serif;font-size:clamp(2rem,5vw,3.8rem);margin:.3em 0}h2{margin:14px 18px 8px}a{color:#145f67}p{line-height:1.6;max-width:85ch}.cards{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:18px;margin:30px 0}article{background:white;border:1px solid #c9d6d2;border-radius:10px;overflow:hidden}article img{width:100%;aspect-ratio:2.16;object-fit:cover}article p{margin:10px 18px 18px}article a{text-decoration:none}.status{font-size:.85rem;color:#327257}.table{overflow-x:auto}table{width:100%;border-collapse:collapse;background:#fff}th,td{text-align:left;border-bottom:1px solid #d8e0dd;padding:14px}thead th{background:#e0e9e3;font-size:.85rem}.note{font-size:.9rem;color:#4b6268}@media(max-width:750px){.cards{grid-template-columns:1fr}}
</style><header><p class="note">ROTCLIMATE · THREE CALIBRATION OBJECTIVES · 22 OCTOBER 2026</p><h1>One world, three climate fits</h1>
<p>Compare the seasonal map fit, the fit constrained by Earth physics, and the fit to proposed Whittaker biomes. Each atlas uses the mean climate over the same three layouts of the unknown surroundings.</p></header>
<section class="cards">'''+''.join(cards)+'''</section><section><h2>Compare the same measures</h2><div class="table"><table><thead><tr><th>Atlas</th><th>Seasonal zone objective</th><th>Whittaker objective</th><th>Exact zone agreement</th><th>Mean biome agreement</th><th>Med. dry</th><th>Med. Cs</th></tr></thead><tbody>'''+''.join(rows)+'''</tbody></table></div>
<p class="note">Each target zone counts equally in mean biome agreement. Objective scores measure different definitions of a match and are not interchangeable. These figures classify the mean climate fields; calibration logs average scores across individual layouts.</p>
<p class="note">Med. dry and Med. Cs are the shares of the painted Mediterranean zone classified as Köppen dry climates and Mediterranean climates, respectively.</p>
<p>The Whittaker atlas includes the proposed biome target map and a separate match layer. Annual temperature and rainfall do not determine Mediterranean summer drought or swamp hydrology, so those seasonal diagnostics remain separate.</p>
<p><a href="../reports/THREE_FIT_20261022.md">Campaign report</a> · <a href="../docs/BIOMES.md">Biome methods</a></p></section></html>'''
    (ROOT/'atlases/index.html').write_text(html)


if __name__=='__main__':main()
