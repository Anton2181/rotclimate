"""Preflight daily reference ETo before any captured-weather ETo outputs."""
import argparse
import json
from pathlib import Path
import subprocess
import sys
import urllib.request

import numpy as np

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'scripts')]
from harvest.reference_eto import daily_reference,extraterrestrial_radiation,pressure_at_elevation,saturation_vapour_pressure,wind_at_2m
from reference_eto_scalar import scalar_reference
from settlement_locations_earth import sha,write

PLAN=ROOT/'calibration/reference_eto_20261114/plan.json'
OUT=ROOT/'output/reference_eto_20261114/core'


def main(out):
    plan=json.loads(PLAN.read_text());cache=ROOT/'data/cache/reference_eto_20261114';cache.mkdir(parents=True,exist_ok=True)
    for name,source in plan['sources'].items():
        p=cache/name
        if not p.exists():
            request=urllib.request.Request(source['url'],headers={'User-Agent':'Mozilla/5.0'})
            with urllib.request.urlopen(request,timeout=30) as response:data=response.read()
            assert __import__('hashlib').sha256(data).hexdigest()==source['sha256']
            p.write_bytes(data)
        assert sha(p)==source['sha256'],name
    tests=['reference_eto','crop_stage','rain_timing','river_fields','field_clock','soil_drying','flood_storage','flood_water','flood_timing','flood_gauge_quality']
    controls=subprocess.run([sys.executable,'-m','pytest','-q',*[f'tests/test_{name}.py' for name in tests]],cwd=ROOT,capture_output=True,text=True,check=True)
    lo,hi=12.3,21.5
    vap=float((saturation_vapour_pressure(lo)*.84+saturation_vapour_pressure(hi)*.63)/2)
    sunshine=extraterrestrial_radiation(50.8,187)
    rs=float((.25+.5*9.25/sunshine['daylight_hours'])*sunshine['ra_mj_m2_day'])
    example=daily_reference(16.9,lo,hi,vap,wind_at_2m(10/3.6,10),pressure_at_elevation(100),rs,50.8,187,100)
    published={'pm_mm_day':(3.9,.05),'ra_mj_m2_day':(41.09,.02),'es_kpa':(1.997,.001),'ea_kpa':(1.409,.001),'rn_mj_m2_day':(13.28,.03),'pm_radiation_mm_day':(2.81,.02),'pm_aerodynamic_mm_day':(1.07,.02)}
    benchmark=[]
    for name,(target,tolerance) in published.items():
        value=float(example[name]);assert abs(value-target)<=tolerance
        benchmark.append(dict(quantity=name,published=target,tolerance=tolerance,value=value))
    assert abs(float(extraterrestrial_radiation(-20,246)['ra_mj_m2_day'])-32.2)<.05
    rng=np.random.default_rng(14112026);maximum=0.;cells=0
    for case in range(1000):
        lo=rng.uniform(-10,30);hi=lo+rng.uniform(2,20);t=(lo+hi)/2
        ea=float(saturation_vapour_pressure(lo-rng.uniform(0,15)))
        lat=float(rng.uniform(-50,50));day=int(rng.integers(1,367));z=float(rng.uniform(0,1500))
        ra=float(extraterrestrial_radiation(lat,day)['ra_mj_m2_day'])
        args=[t,lo,hi,ea,float(rng.uniform(0,8)),float(rng.uniform(85,102)),float(rng.uniform(0,1.3)*(.75+2e-5*z)*ra),lat,day,z]
        actual=daily_reference(*args);reference=scalar_reference(*args)
        for name,value in reference.items():
            error=abs(float(actual[name])-value);maximum=max(maximum,error);cells+=1
            assert error<2e-11,(case,name,error)
    out.mkdir(parents=True,exist_ok=True)
    paths=[Path(__file__),ROOT/'scripts/reference_eto_scalar.py',ROOT/'harvest/reference_eto.py',ROOT/'tests/test_reference_eto.py',PLAN]
    write(out/'review.json',dict(status='passed_before_weather_eto_outputs',controls_stdout=controls.stdout,fao18=benchmark,fao8_radiation_mj_m2_day=float(extraterrestrial_radiation(-20,246)['ra_mj_m2_day']),synthetic_weather_days=1000,scalar_decimal_cells=cells,max_scalar_decimal_error=maximum,producers={str(p.relative_to(ROOT)):sha(p) for p in paths},weather_eto_scored=False,adopt=False))
    print(controls.stdout.strip());print('Passed published examples and',cells,'independent scalar/Decimal cells;max error',maximum)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--out',type=Path,default=OUT)
    main(parser.parse_args().out)
