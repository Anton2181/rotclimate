#!/bin/bash
cd /home/user/rotclimate
while ! grep -q "SCREENS9 DONE" output/desert_heat_20261101/screen9.log; do sleep 60; done
echo "export $(date +%H:%M)"
OMP_NUM_THREADS=1 .venv/bin/python -u -I scripts/add_foraging_to_atlas.py atlases/earth_fit atlases/free_fit atlases/whittaker_fit --out output/foraging_lifeways_20261101 > output/forager_binford_20261031/lifeway_export.log 2>&1
echo "export done $(date +%H:%M)"
