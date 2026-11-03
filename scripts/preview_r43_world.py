"""Compare verified raw r42/r43 world checkpoints without promoting an atlas."""
from pathlib import Path
import json
import pickle
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.local_benchmark_protocol import file_hash, write_json


def main():
    import numpy as np
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.patches import Patch
    from rotclimate.score import evaluate
    from rotclimate import biomes
    paths = [ROOT / 'output/r42_world/candidate_001.pkl',
             ROOT / 'output/atlas_r43/snapshot/output/r43_world/candidate_001.pkl']
    results = []; identities = []
    for path in paths:
        with path.open('rb') as stream: record = pickle.load(stream)
        for name, digest in record['identity']['sources'].items():
            if file_hash(ROOT / 'rotclimate' / name) != digest:
                raise ValueError('Preview must use the matching scientific code: ' + name)
        if not record['result'].numerics.get('all_checks_passed'):
            raise ValueError('Unverified simulation')
        results.append(record['result']); identities.append(record['identity'])
    if identities[0]['map_inputs'] != identities[1]['map_inputs']:
        raise ValueError('Map source inputs changed')
    if identities[0]['seeds'] != identities[1]['seeds']:
        raise ValueError('Surroundings differ')
    a, b = results
    for name in ['land', 'elev', 'lat', 'inmap', 'target']:
        if not np.array_equal(getattr(a.grid, name), getattr(b.grid, name)):
            raise ValueError('World geometry differs: ' + name)
    evaluations = [evaluate(r) for r in results]
    sl = a.grid.map_slice(); land = a.grid.land[sl]
    fig = plt.figure(figsize=(17, 8), layout='constrained')
    layout = fig.add_gridspec(4, 3, height_ratios=[1, .12, 1, .12])
    axes = np.array([[fig.add_subplot(layout[row, col]) for col in range(3)] for row in [0, 2]])
    for col, (r, ev, label) in enumerate(zip(results, evaluations, ['r42 raw world', 'r43 raw world'])):
        ix = ev['indices']; cls = biomes.classify(ix['MAT'][sl], ix['MAP'][sl], land)
        axes[0,col].imshow(biomes.rgb_image(cls), interpolation='nearest')
        axes[0,col].set_title(label + f' · zone agreement {100*ev["accuracy"]:.2f}%', fontsize=11)
        rain = axes[1,col].imshow(np.where(land, ix['MAP'][sl], np.nan), cmap='YlGnBu', vmin=0, vmax=1800, interpolation='nearest')
        axes[1,col].set_title('Annual precipitation', fontsize=10)
    dT = evaluations[1]['indices']['MAT'][sl] - evaluations[0]['indices']['MAT'][sl]
    dP = evaluations[1]['indices']['MAP'][sl] - evaluations[0]['indices']['MAP'][sl]
    t = axes[0,2].imshow(np.where(land, dT, np.nan), cmap='RdBu_r', vmin=-2, vmax=2, interpolation='nearest')
    axes[0,2].set_title('r43 minus r42: mean temperature', fontsize=10)
    p = axes[1,2].imshow(np.where(land, dP, np.nan), cmap='BrBG', vmin=-300, vmax=300, interpolation='nearest')
    axes[1,2].set_title('r43 minus r42: annual precipitation', fontsize=10)
    for ax in axes.flat:
        ax.set_xticks([]); ax.set_yticks([]); ax.set_facecolor('#d6e4ef')
        ax.spines[['top', 'right', 'left', 'bottom']].set_visible(False)
    fig.colorbar(rain, cax=fig.add_subplot(layout[3,:2]), orientation='horizontal', label='mm/year, clipped at 1,800')
    fig.colorbar(t, cax=fig.add_subplot(layout[1,2]), orientation='horizontal', label='C, clipped at ±2')
    fig.colorbar(p, cax=fig.add_subplot(layout[3,2]), orientation='horizontal', label='mm/year, clipped at ±300')
    fig.legend(handles=[Patch(facecolor=c, label=l) for c,l in zip(biomes.COLORS, biomes.LABELS)],
               loc='outside lower center', ncol=4, frameon=False, fontsize=8)
    fig.suptitle('Raw world climate preview · same geometry and surroundings layouts 1–3\nVerified simulation checkpoints; full atlas exports and additional layout/initialization checks still in progress', fontsize=13)
    folder = ROOT / 'output/r43_world_preview_20261103'; folder.mkdir(exist_ok=True)
    image = folder / 'raw_world_comparison.png'; fig.savefig(image, dpi=135); plt.close(fig)
    write_json(folder / 'receipt.json', dict(source_sha256={str(p.relative_to(ROOT)):file_hash(p) for p in paths},
        previewer_sha256=file_hash(Path(__file__)),
        image_sha256=file_hash(image), raw_target_accuracy=[ev['accuracy'] for ev in evaluations],
        land_mean_temperature_change_C=float(dT[land].mean()), land_mean_annual_rain_change_mm=float(dP[land].mean()),
        scope='Inside mapped model-grid cells. Raw simulations, no Earth statistical corrections. Target agreement is not measured fantasy-world accuracy. No publication or adoption.'))
    print((folder / 'receipt.json').read_text())


if __name__ == '__main__': main()
