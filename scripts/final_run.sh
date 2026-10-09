#!/bin/sh
cd "$(dirname "$0")/.."
P=calibration/best_params.json
python3 -m rotclimate render --params $P --out output --atlas > output/render.log 2>&1
python3 -m rotclimate.experiments spin --params $P --out output/spin_flip.gif >> output/render.log 2>&1
python3 -m rotclimate.experiments snapshot --params $P --tag it05 --title "Round 6, retrograde (physics v5: asymmetric storm track)" --note "final" >> output/render.log 2>&1
python3 -m rotclimate.experiments history --out output/improvement.gif >> output/render.log 2>&1
python3 -m rotclimate.experiments tilt --params $P --out output/tilt_sweep.gif >> output/render.log 2>&1
python3 -m rotclimate.experiments surroundings --params $P --out output/surroundings.gif >> output/render.log 2>&1
python3 -c "from rotclimate.atlas import copy_media; copy_media()" >> output/render.log 2>&1
echo done > output/final.done
