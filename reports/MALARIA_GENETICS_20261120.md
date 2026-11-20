# Malaria vs its genetic footprint: Earth test, 20 November 2026

**Outcome:** the current malaria field fails validation (blind rank correlation 0.11 with the sickle-cell footprint). A simpler rule
— the share of months warm enough for transmission, with no rain gate — scores 0.55 and passes both adoption gates. It is adopted as
the Earth-validated rule. Applying it to the map changes population everywhere, so it waits for a planned rebuild (owner decision).

Protocol: [plan](../calibration/malaria_genetics_20261120/plan.json), declared before any score. One amendment (A1, before the blind
run): the code control compared against the wrong stored field (the older MARA index). It now checks against the map's own malaria
function, and matches to 3e-16; the scores did not change.

## Targets

Gene frequencies that malaria selected for over millennia, mapped by the Malaria Atlas Project from population surveys:

- **Primary:** sickle haemoglobin (HbS), Piel et al. 2013.
- **Secondary:** G6PD deficiency, Howes et al. 2012. It was mapped only inside countries endemic in 2010.

They rank long-run malaria pressure. They also carry migration history, so they are not AD 200 prevalence. Scores use 1° blocks over
the Earth run (0–56° N, 12° W–125° E); development and blind halves are a 10° checkerboard.

## Results (blind half)

| Rank correlation | Current (rain gate 0–80 mm, annual mean) | Adopted (no rain gate, share of suitable months) | Blocks |
|---|---:|---:|---:|
| Sickle cell, all | 0.11 | **0.55** | 2,778 |
| Sickle cell, Africa | 0.42 | 0.55 | 928 |
| Sickle cell, outside Africa | −0.07 | 0.18 | 1,850 |
| G6PD, all | 0.38 | **0.55** | 1,716 |
| G6PD, Africa | 0.35 | 0.42 | 670 |
| G6PD, outside Africa | 0.34 | 0.55 | 1,046 |

- **V fails:** the current field scores below 0.30 on sickle cell.
- **G1 passes:** +0.44 on sickle cell.
- **G2 passes:** +0.17 on G6PD.

On development, every rain-gate setting (20–240 mm) scored 0.12–0.21 on sickle cell; temperature alone scored 0.57–0.58.

## Why the rain gate fails

The gate sets malaria to zero in dry months and dry lands. Yet historically the dry belt's river valleys and oases (the Nile,
Mesopotamia, the Indus, Arabian oases) were notoriously malarious. They breed mosquitoes from river, flood and irrigation water, not
rain. The gate's irrigation exception (0.75 × the irrigation field) is too narrow to capture this. Temperature, which sets the
parasite's development speed, carries the long-run pattern.

**Caveat:** a temperature-only rule also rates empty hot deserts as suitable. On the map that matters little, because few people
live there.

## Adoption

- **Rule:** malaria = share of months with relative thermal suitability ≥ 0.25 (the map's existing season threshold), from the same
  Mordecai 2013 response.
- **What it changes:** the map's malaria feeds health (1 − 0.35 × malaria) and so livability, population, towns and everything
  downstream. The 0.35 penalty was not tested here.
- **Next:** a bundled rebuild, with the owner's approval, rechecking population skill against HYDE and Han before publishing.
- **Inconsistency noticed:** the Earth population runs (`polity.earth.earth_people`) use the older MARA index, while the map uses
  the Mordecai field.

Reproduce: `.venv/bin/python -I scripts/malaria_genetics.py dev` and then `blind`. The blind run has been done once.
