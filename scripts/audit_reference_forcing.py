"""Verify shared-world reference algebra, tile boundaries and bin conservation."""
import argparse
from decimal import Decimal
import json
from pathlib import Path
import subprocess
import sys

import numpy as np

ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'scripts')]
from harvest.reference_eto import saturation_vapour_pressure
from harvest.reference_forcing import daily_from_radiation,mean_year_bin_totals
from reference_forcing_scalar import supplied_radiation_reference
from settlement_locations_earth import sha,write

OUT=ROOT/'output/regional_reference_forcing_20261114/core'


def main(out):
    tests=['reference_forcing','reference_eto','crop_stage','rain_timing','river_fields','field_clock','soil_drying','flood_storage','flood_water','flood_timing','flood_gauge_quality']
    control=subprocess.run([sys.executable,'-m','pytest','-q',*[f'tests/test_{name}.py' for name in tests]],cwd=ROOT,capture_output=True,text=True,check=True)
    rng=np.random.default_rng(1411202602);maxerror=0.;cells=0
    for case in range(1000):
        lo=rng.uniform(-10,30);hi=lo+rng.uniform(2,20);t=(lo+hi)/2
        vap=float(saturation_vapour_pressure(lo-rng.uniform(0,15)))
        ra=float(rng.uniform(.05,50));z=float(rng.uniform(0,1500))
        args=[t,lo,hi,vap,float(rng.uniform(0,8)),float(rng.uniform(85,102)),float(rng.uniform(0,1.3)*(.75+.00002*z)*ra),ra,z]
        actual=daily_from_radiation(*args);ref=supplied_radiation_reference(*args)
        for name,value in ref.items():
            error=abs(float(actual[name])-value);maxerror=max(maxerror,error);cells+=1
            assert error<2e-11,(case,name,error)
    maxbin=0.
    for case in range(100):
        years=np.repeat(np.arange(5),12*3);bins=np.tile(np.repeat(np.arange(12),3),5)
        amounts=rng.uniform(0,20,(len(years),3));actual=mean_year_bin_totals(years,bins,amounts)
        for b in range(12):
            for field in range(3):
                independent=sum(Decimal(str(amounts[i,field])) for i in range(len(years)) if bins[i]==b)/5
                error=abs(float(actual[b,field])-float(independent));maxbin=max(maxbin,error)
                assert error<1e-12
    base=ROOT/'output/reference_eto_20261114';r=json.loads((base/'results.json').read_text());protected=dict(r['unchanged_sha256'])
    for name in ['results.json','daily.csv','review.json']:protected[str((base/name).relative_to(ROOT))]=sha(base/name)
    for name,digest in protected.items():assert sha(ROOT/name)==digest,name
    paths=[Path(__file__),ROOT/'harvest/reference_forcing.py',ROOT/'scripts/reference_forcing_scalar.py',ROOT/'tests/test_reference_forcing.py',ROOT/'harvest/reference_eto.py']
    out.mkdir(parents=True,exist_ok=True)
    write(out/'review.json',dict(status='passed_before_regional_eto_and_fields',controls_stdout=control.stdout,synthetic_weather_days=1000,scalar_decimal_cells=cells,max_weather_numeric_error=maxerror,synthetic_bin_tests=100,decimal_bin_cells=3600,max_bin_amount_error_mm=maxbin,producers={str(p.relative_to(ROOT)):sha(p) for p in paths},unchanged_sha256=protected,regional_fields_scored=False,adopt=False))
    print(control.stdout.strip());print('Shared world-radiation adapter:',cells,'scalar/Decimal cells;3600bin cells;maxerrors',maxerror,maxbin)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--out',type=Path,default=OUT)
    main(parser.parse_args().out)
