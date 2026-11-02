"""Render existing r41/r42 default climate layers without running a model."""
from pathlib import Path
import hashlib
import io
import json
import subprocess

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap, LogNorm
from matplotlib.patches import Patch
from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
REFERENCES = [('7fe0755a', 'r41: previous atlas default'),
              ('c55e705c', 'r42: rebuilt atlas default')]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    sources = {}
    def read(commit, name):
        key = commit + ':' + name
        data = subprocess.check_output(['git', 'show', key], cwd=ROOT)
        sources[key] = hashlib.sha256(data).hexdigest()
        return data
    variants = []
    for short, title in REFERENCES:
        commit = subprocess.check_output(['git', 'rev-parse', short], cwd=ROOT, text=True).strip()
        meta = json.loads(read(commit, 'atlases/earth_fit/data/atlas.json'))
        if not meta.get('corrected_climate'):
            raise ValueError('Both references must use their published corrected defaults')
        variants.append((commit, meta['corrected_climate'], title))
    new_meta = variants[1][1]
    fig, axes = plt.subplots(2, 2, figsize=(15, 8.3), facecolor='#fcfcfb')
    fig.subplots_adjust(top=.88, bottom=.24, left=.015, right=.985, hspace=.2, wspace=.025)
    for col, (commit, meta, title) in enumerate(variants):
        for row, key in enumerate(('precip', 'whittaker')):
            layer = next(x for x in meta['layers'] if x['id'] == key)
            data = read(commit, 'atlases/earth_fit/data/' + layer['file'])
            im = Image.open(io.BytesIO(data)).convert('RGBA')
            bg = Image.new('RGBA', im.size, '#d6e4ef'); bg.alpha_composite(im)
            ax = axes[row, col]
            ax.imshow(bg.resize((1600, round(im.height * 1600 / im.width)), Image.Resampling.LANCZOS))
            ax.set_title(title if row == 0 else 'Potential Whittaker biomes', loc='left', fontsize=12)
            ax.axis('off')
    layer = next(x for x in new_meta['layers'] if x['id'] == 'precip')
    cmap = LinearSegmentedColormap.from_list('rain', layer['stops'])
    cbax = fig.add_axes([.3, .195, .4, .014])
    bar = fig.colorbar(plt.cm.ScalarMappable(norm=LogNorm(layer['vmin'], layer['vmax']), cmap=cmap),
                       cax=cbax, orientation='horizontal', ticks=[100, 300, 1000, 3000])
    bar.ax.set_xticklabels(['100', '300', '1,000', '3,000'])
    bar.ax.tick_params(labelsize=8)
    bar.set_label('Annual precipitation, mm/year (logarithmic colours)', fontsize=9)
    handles = [Patch(facecolor=b['color'], label=b['label']) for b in new_meta['biomes']]
    fig.legend(handles=handles, loc='lower center', bbox_to_anchor=(.5, .06),
               ncol=4, frameon=False, fontsize=8.5)
    fig.suptitle('Earth atlas climate update', fontsize=19, x=.015, ha='left', y=.97)
    fig.text(.015, .925, 'Same world geometry and surroundings layouts 1–3 · Earth-trained corrections applied in both columns',
             fontsize=11, color='#555555')
    fig.text(.015, .022, 'Published atlas defaults: r41 (7fe0755a) and r42 (c55e705c). Map colours show climate and potential biomes, not accuracy.',
             fontsize=10, color='#555555')
    image = OUT / 'r41_r42_default_climate.png'
    fig.savefig(image, dpi=130, facecolor=fig.get_facecolor())
    plt.close(fig)
    receipt = dict(purpose='Existing atlas climate layers, not a new climate simulation or accuracy test',
                   sources_sha256=sources, image_sha256=sha(image))
    (OUT / 'receipt.json').write_text(json.dumps(receipt, indent=2) + '\n')
    print(image)


if __name__ == '__main__':
    main()
