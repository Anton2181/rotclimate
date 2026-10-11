"""Run ExoPlaSim on boundary files from scripts/exoplasim_export.py.

Runs inside the environment ExoPlaSim is installed in (it is not a
dependency of rotclimate). Earth-like planet: 1 bar, Earth's sun, CO2 and
year, Earth spin (reversed spin is the mirrored map), a 50 m slab ocean, the
calibrated axial tilt. The run advances one year at a time and can resume
after an interruption from the restart file it keeps.

    venv/bin/python scripts/exoplasim_run.py --sra exo/earthlike --name earthlike --res T21 \
        --tilt 16.95 --years 20 --ncpus 4
"""
from __future__ import annotations

import argparse
import glob
import os
import shutil
import time
from pathlib import Path


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sra", required=True, help="folder with <name>_surf_0172.sra and _0129.sra")
    ap.add_argument("--name", required=True)
    ap.add_argument("--res", default="T21")
    ap.add_argument("--layers", type=int, default=10)
    ap.add_argument("--tilt", type=float, required=True)
    ap.add_argument("--years", type=int, default=20)
    ap.add_argument("--ncpus", type=int, default=4)
    ap.add_argument("--timestep", type=float, default=45.0)
    a = ap.parse_args()
    # containers often run everything as root, which OpenMPI refuses by default
    os.environ.setdefault("OMPI_ALLOW_RUN_AS_ROOT", "1")
    os.environ.setdefault("OMPI_ALLOW_RUN_AS_ROOT_CONFIRM", "1")
    import exoplasim as exo

    sra = Path(a.sra).resolve()
    work = sra / f"run_{a.res}"
    out = sra / f"out_{a.res}"
    out.mkdir(parents=True, exist_ok=True)
    done = sorted(glob.glob(str(out / "MOST.*.npz")))
    start = len(done)
    restart = out / "restart"
    model = exo.Model(workdir=str(work), modelname=a.name, ncpus=a.ncpus, resolution=a.res,
                      layers=a.layers, precision=8, inityear=start, crashtolerant=True)
    model.configure(landmap=str(sra / f"{a.name}_surf_0172.sra"), topomap=str(sra / f"{a.name}_surf_0129.sra"),
                    obliquity=a.tilt, eccentricity=0.0167, pN2=0.78, pO2=0.21, pAr=0.0093, pCO2=360e-6,
                    pH2O=None, mldepth=50.0, wetsoil=True, vegetation=False, timestep=a.timestep,
                    restartfile=str(restart) if start and restart.exists() else None)
    model.exportcfg(str(out / f"{a.name}.cfg"))
    for year in range(start, a.years):
        t = time.time()
        model.run(years=1)
        # keep each year's output and the latest restart outside the work dir
        for f in sorted(glob.glob(str(work / "MOST.*.npz"))):
            shutil.copy(f, out / Path(f).name)
        if (work / "plasim_restart").exists():
            shutil.copy(work / "plasim_restart", restart)
        print(f"year {year + 1}/{a.years} in {time.time() - t:.0f}s", flush=True)


if __name__ == "__main__":
    main()
