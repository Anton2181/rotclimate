# Wild-food foraging models and source boundaries

The foraging side project separates a published human energy model from the
resource assumptions needed to apply it to the atlas. The map scenario uses
monthly simulated climate and an existing Miami productivity estimate. It does
not reproduce the original ORCHIDEE–FORGE ecosystem simulation, agricultural
support, or a census for the setting's c.200 AD societies.

The source and assumption catalogue is
[`data/foraging_model.json`](../data/foraging_model.json). In particular,
resource turnover, seasonal production weights, grass allocation and animal
production are exposed assumptions. They are not additional climate tuning
parameters and do not feed back into the climate integration.

## FORGE human energy and time allocation

[Zhu et al. (2021)](https://doi.org/10.1038/s41559-021-01548-3) developed FORGE,
FORager dynamics in Global Ecosystem model. Its human component follows food
acquisition, expenditure and reserve-dependent demography. The original daily
resource forcing comes from ORCHIDEE vegetation and a grazer/browser model.
The original inputs are archived at
[Figshare](https://doi.org/10.6084/m9.figshare.14995320.v2).

In the paper's area convention, food stocks are kg dry matter per square
metre. Convert population density `P` from persons/km² to
`p = P / 1,000,000` persons/m² before calculating human biomass `B_h = 50 p`
or landscape food depletion. For food stock `B`, acquisition
efficiency is `e = e_max B / (B + c B_h)`. With search area
`a = 4000 m²/person/hour`, per-person plant and animal intake are
`I_v = B_v t_g e_g a` and `I_a = B_a t_h e_h a`.

The implementation API instead stores food and food input in kg dry
matter/km² and population in persons/km². It applies the corresponding
`1 / 1,000,000` factor inside per-person search intake. This is the same area
conversion, not a new efficiency coefficient. For that API,
`1 g dry matter/m² = 1000 kg dry matter/km²`. Do not supply per-m² food values
to a per-km² API or apply the area conversion twice.

Daily intake energy is `9.8 (I_v + I_a)` MJ/person; expenditure is
`8.37 + 1.25 (t_g + t_h)` MJ/person. Reserve change divides an energy deficit
by 39.3 MJ/kg and a surplus by 54.6 MJ/kg. The 50 kg representative person has
a maximum fat reserve of 15 kg. A negative effective reserve used to diagnose
starvation is not literal negative physical fat; implementations must account
for any energy debt explicitly.

Total foraging time changes by one hour per day within 0.5–8 hours, responding
to the preceding reserve change. Hunting's share responds to the two food
benefits and the previous meat share. These rules are behavioural assumptions,
not an optimization of every individual's choices. Empty-resource branches,
intake limits, annual prey replacement and the order of reserve/demographic
updates need explicit numerical conventions. Such conventions prevent invalid
stocks but cannot establish replication of the original source code.

The paper's intake subsection states crowding `c=100`, while its final standard
configuration states `c=200`. The configuration records both and identifies
the chosen value. Reproduction removes a published energy cost, but the text
does not unambiguously specify which reserve conversion coefficient applies
to that annual deduction. Any chosen conversion is documented separately.

## Resource adapter

Annual Miami NPP is g dry matter/m²/year, not edible food. The published plant
allocation uses `0.015 × (0.065 × total NPP + f_below × grass NPP)`, where
`f_below = max(0.2, (88.3 − 0.0534 MAP) / 100)` and `MAP` is annual rainfall in
mm. Converting NPP to kg and preserving its annual integral are necessary
before supplying daily food pools.

The first atlas scenario assigns half of NPP to grass everywhere. This is an
explicit mixed-vegetation assumption, rather than an invented lookup ranking
biomes by subsistence ease. Climate-based seasonal weights redistribute the
annual input; they are not daily photosynthesis observations. A uniform
fallback when every weight vanishes preserves the annual budget and must be
reported as a fallback.

Plant-pool loss of 0.02/day represents perishable natural resources. It is not
human food storage. An illustrative annual accessible-animal budget uses
0.0005 of annual NPP as dry matter. It is introduced as one annual stock pulse,
then depleted by hunting, with unused stock accounted before replacement.
This substitutes for missing herbivore ecology; it is not the paper's fitted
animal production or trophic efficiency. Changing either assumption is a
sensitivity experiment, not a confidence interval.

The original study runs FORGE for 300 years and summarizes its last 50 years.
The adapted model similarly reports a late-run average, while retaining an
explicit annual-state convergence flag and density variability. Demographic
cycles can persist even when every resource and energy ledger closes; an
annual-cycle mean is then a scenario statistic, not a converged equilibrium.

These wild-food scenarios must remain distinct from agricultural settlement
estimates. Adding full-area wild-food potential to full-area farming or
pasture potential would count the same land and productivity twice.

## Related models and what is not yet reproduced

[Tallavaara, Eronen and Luoto (2018)](https://doi.org/10.1073/pnas.1715638115)
fit empirical hunter-gatherer densities using productivity, biodiversity and
environmental pathogen exposure. Their
[reproduction archive](https://doi.org/10.5281/zenodo.1167852) includes an R
analysis, ethnographic observations and global predictor rasters under CC BY
4.0. Its pathogen predictor combines ten diseases and its biodiversity
predictor combines several taxonomic groups. A fantasy biome class and a
malaria suitability map cannot be substituted for those inputs while claiming
to reproduce the fitted model. Its FAO ecological zones also differ from the
atlas's Whittaker classification. No empirical coefficient should be invented
from biome names.

[Ordonez and Riede (2022)](https://doi.org/10.1038/s41467-022-32750-x) examine
changing ecological constraints on European foragers through a specific
palaeoclimatic transition. Their results motivate checking which constraints
matter in each context, rather than transferring one biome ranking to every
period. Their fitted palaeodemographic model is not implemented here.

[Matranga (2024)](https://doi.org/10.1093/qje/qjae012) models how seasonality,
storage and incentives can relate to agriculture's emergence. Its economic
adoption model is not reproduced by giving natural food stocks a longer
lifetime. A future storage implementation needs harvested inventories,
spoilage, capacity, work costs and an explicit comparison of consumption
through time.

None of these models establishes that subsistence effort alone determines a
society's development. The atlas can compare food constraints and effort
under specified assumptions; it cannot infer political institutions,
innovation, surplus extraction or historical population solely from climate.

## Attribution and implementation

The implementation is written independently from described equations. No
publisher supplementary Python code has been copied or vendored. The public
FORGE input archive is CC BY 4.0; that does not by itself establish the license
of every supplementary software file. Published constants are distinguished
from adapter assumptions in the machine-readable catalogue.

[Atlas results and biome comparison](../reports/FORAGING_20261027.md).
