# Atlas and population development — 23 October 2026

## Milestone 1: controls follow the selected map

Occupation now appears only where changing frontier / central / settled core
changes the selected map. Expected density shows both occupation and malaria;
settlement potential shows malaria alone. Climate, crops and other static maps
hide both. Choices remain saved when controls disappear and survive shared links.
The rule compares the actual image variants rather than maintaining a list of
special layer names.

Each atlas also displays the outside-diagram percentage read from its loaded
metadata. The current repository's Whittaker data and local HTTP browser both
show **1.21%**, and the local launcher sends `Cache-Control: no-store`.
This identifies the loaded dataset; it does not claim that a separate hosted
copy or an older extracted bundle has been updated. The user's viewing URL is
needed to identify the reported older copy.

Desktop and mobile browser checks pass for all three active atlases, including
selector visibility, hidden-state persistence, population scenarios, province
controls and saved links. Evidence is in `output/iteration_20261023/`.
