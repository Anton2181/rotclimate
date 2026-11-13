"""Figure for the release-2 settlement report (aggregates and fantasy outputs only)."""
import json
from pathlib import Path
import numpy as np, pandas as pd
import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[1]; OUT = ROOT / 'output/settlement_release2_20261113'
R = json.loads((OUT / 'results.json').read_text()); t = pd.read_csv(OUT / 'fantasy_corrected_towns.csv')
fig, ax = plt.subplots(1, 3, figsize=(15, 4.6), constrained_layout=True)
rows = [r for r in R['placement']['rows'] if r['quadrant'] != 'whole']; x = np.arange(len(rows))
ax[0].bar(x - .2, [r['production_Q'] for r in rows], .4, label='Existing placement', color='#7a8791')
ax[0].bar(x + .2, [r['finalist_Q'] for r in rows], .4, label='Tested new rule (18 km / 800 km)', color='#c9772b')
ax[0].set_xticks(x, [f"{r['pool']}\n{r['quadrant'].replace('_', ' ')}" for r in rows], fontsize=7)
ax[0].set_ylabel('Placement quality Q (higher is better)'); ax[0].legend(frameon=False, fontsize=8)
ax[0].set_title('Placement: new rule wins 5 of 8 regions (needed 6)', fontsize=10)
q = [.05, .25, .5, .75, .95]; g = R['sizes']['primary']
ax[1].plot([g['observed_quantiles_ha'][str(v)] for v in q], q, 'o-', color='#222', label='Roman cities, observed')
ax[1].plot([g['generated_seed1_quantiles_ha'][str(v)] for v in q], q, 's--', color='#c9772b', label='Model on held-out provinces')
ax[1].plot(np.quantile(t.calibrated_area_ha, q), q, '^:', color='#2b7a78', label='Fantasy towns (corrected climate)')
ax[1].set_xscale('log'); ax[1].set_xlabel('Built-up area (ha)'); ax[1].set_ylabel('Share of towns at or below'); ax[1].legend(frameon=False, fontsize=8)
ax[1].set_title(f"Sizes: held-out distance {g['gate']['mean_ks']:.3f} (limit 0.10)", fontsize=10)
rank = np.arange(1, len(t) + 1)
for col, lab, c in (('legacy_request_people', 'Earlier sizes (7.5% of market area)', '#7a8791'), ('residents_low', 'Release 2, 100 people/ha', '#2b7a78'),
                    ('residents_central', 'Release 2, sliding 100–500/ha', '#c9772b')):
    ax[2].plot(rank, np.sort(t[col])[::-1], label=lab, color=c)
ax[2].set_xscale('log'); ax[2].set_yscale('log'); ax[2].set_xlabel('Town rank'); ax[2].set_ylabel('Residents'); ax[2].legend(frameon=False, fontsize=8)
ax[2].set_title('Fantasy town sizes before and after', fontsize=10)
for a in ax: a.spines[['top', 'right']].set_visible(False)
fig.savefig(ROOT / 'reports/figures/settlement_release2_20261113.png', dpi=140)
