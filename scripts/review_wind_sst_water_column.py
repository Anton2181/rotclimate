"""Compare completed wind/SST water columns with their existing Earth reference."""
from pathlib import Path
import importlib.metadata
import json
import shutil
import sys
import h5py
import numpy as np
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from local_benchmark_protocol import file_hash,write_json
from circulation_components import bilinear_monthly
OUT=ROOT/'output/wind_sst_diagnostic_20261127'


def main():
    assert not (OUT/'water_column_review.json').exists()
    reference=OUT/'model/data/cache/earth'
    raw=reference/'ncep/pr_wtr.mon.ltm.nc'; cache=reference/'ncep_pw_2p5.npz'
    decode=lambda x:bytes(x).decode() if isinstance(x,(bytes,np.bytes_)) else str(x)
    with h5py.File(raw) as f:
        assert decode(f['time'].attrs['climo_period'])=='1991/01/01 - 2020/12/31'
        variable=f['pr_wtr']
        assert decode(variable.attrs['units'])=='kg/m^2'
        assert np.asarray(variable.attrs['scale_factor']).item()==1.
        assert np.asarray(variable.attrs['add_offset']).item()==0.
        values=variable[...]
        assert values.shape==(12,73,144) and np.isfinite(values).all() and (values>=variable.attrs['valid_range'][0]).all() and (values<=variable.attrs['valid_range'][1]).all()
        latitude,longitude=f['lat'][...],f['lon'][...]
        np.testing.assert_array_equal(latitude,90-2.5*np.arange(73))
        np.testing.assert_array_equal(longitude,2.5*np.arange(144))
    with np.load(cache) as z:
        np.testing.assert_array_equal(z['pw'],np.maximum(values.astype(np.float32),0.))
        np.testing.assert_array_equal(z['lat'],latitude);np.testing.assert_array_equal(z['lon'],longitude)
        pw=z['pw'].astype(float)
    for source,name in [(raw,'column_reference.nc'),(cache,'column_reference.npz')]:
        assert not (OUT/name).exists();shutil.copyfile(source,OUT/name)
    review=json.loads((OUT/'review.json').read_text())
    plan=json.loads((ROOT/'calibration/wind_sst_diagnostic_20261127/plan.json').read_text())
    records,curves=[],{}
    for spec in plan['cases']:
        path=OUT/spec['name']/'capture.npz'
        assert file_hash(path)==review['files_sha256'][spec['name']+'/capture.npz']
        with np.load(path) as z:
            observed=bilinear_monthly(pw,z['lat'],z['lon'])
            assert np.isfinite(observed).all() and (observed>=0).all() and (observed.mean(1)>0).all()
            negative_weight = bilinear_monthly((values<0).astype(float), z['lat'], z['lon'])
            water=z['W'].mean(1);reference_water=observed.mean(1)
            rain=z['P'].mean(1);reference_rain=z['obs_P'].astype(float).mean(1)
            model_proxy=float(rain.sum()/(365*water.mean()))
            obs_proxy=float(reference_rain.sum()/(365*reference_water.mean()))
            records.append(dict(name=spec['name'],region=spec['region'],wind=spec['arm'],sst=spec['sst'],
                mean_water_mm=float(water.mean()),reference_mean_water_mm=float(reference_water.mean()),
                water_bias_ratio=float(water.mean()/reference_water.mean()),
                sample_fraction_with_clipped_raw_corner=float((negative_weight>0).mean()),
                mean_negative_corner_interpolation_weight=float(negative_weight.mean()),
                july_water_mm=float(water[6]),reference_july_water_mm=float(reference_water[6]),
                annual_rain_mm=float(rain.sum()),reference_annual_rain_mm=float(reference_rain.sum()),
                apparent_rain_per_water_day_inverse=model_proxy,reference_proxy_day_inverse=obs_proxy,
                proxy_ratio=model_proxy/obs_proxy,
                monthly_mean_water_mm=water.tolist(),reference_monthly_water_mm=reference_water.tolist(),
                monthly_mean_rain_mm=rain.tolist(),reference_monthly_rain_mm=reference_rain.tolist()))
            curves[spec['region'],spec['arm'],spec['sst']]=(water,reference_water,rain,reference_rain)
    figure(plan,curves)
    write_json(OUT/'water_column_review.json',dict(status='descriptive_existing_column_reference_comparison_not_independent_validation',
        parent_review_sha256=file_hash(OUT/'review.json'),script_sha256=file_hash(__file__),
        reference=dict(url='https://psl.noaa.gov/thredds/fileServer/Datasets/ncep.reanalysis.derived/surface/pr_wtr.mon.ltm.nc',
            period='1991-2020',units='kg/m^2 = mm liquid water',resolution_degrees=2.5,
            raw_sha256=file_hash(OUT/'column_reference.nc'),normalized_sha256=file_hash(OUT/'column_reference.npz'),
            h5py_version=importlib.metadata.version('h5py'),
            raw_negative_count=int((values<0).sum()),raw_minimum=float(values.min()),
            normalization='Unchanged existing builder clips published negative raw values to zero; no climate inputs altered.'),
        statistics=records,figure_sha256=file_hash(OUT/'water_column.png'),integrations=0,
        definition='Apparent annual rain-per-water proxy = regional mean annual rain / (365 * regional mean monthly water). It is a ratio of regional means, not mean of cell ratios, microphysical efficiency, an isolated causal effect or a diagnosed residence time.',
        limits='PW is already used as Earth boundary conditioning, so this is not independent validation. Coarse interpolation is not independent56km observations; terrain/vertical column differences and rain/WOA/reanalysis climatological periods limit comparison. No solver uses these new calculations, no fitting/adoption.'))


def figure(plan,curves):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig,axes=plt.subplots(2,3,figsize=(15,7))
    for col,(region,title) in enumerate(zip(plan['regions'],['Somalia','Sahara','North India'],strict=True)):
        for wind,color in [('model','#377d8d'),('observed','#b47552')]:
            for sst,style in [('model','-'),('observed',':')]:
                water,ref,rain,rainref=curves[region,wind,sst]
                label=wind+' wind / '+sst+' SST'
                axes[0,col].plot(np.arange(1,13),water,label=label,color=color,linestyle=style)
                axes[1,col].plot(np.arange(1,13),rain/(365/12*water),color=color,linestyle=style)
        axes[0,col].plot(np.arange(1,13),ref,'--',color='#777777',label='NCEP PW reference')
        axes[1,col].plot(np.arange(1,13),rainref/(365/12*ref),'--',color='#777777',label='Rain/PW reference proxy')
        axes[0,col].set_title(title)
        for row,ylabel in [(0,'Column water (mm)'),(1,'Apparent rain / column (1/day)')]:
            axes[row,col].set(xticks=[1,4,7,10,12],xlabel='Model month',ylabel=ylabel);axes[row,col].grid(alpha=.15)
    axes[0,0].legend(fontsize=7)
    fig.suptitle('Column water and rain-per-water proxy in completed wind × SST diagnostics')
    fig.text(.5,.035,'NCEP PW (1991–2020, 2.5 degree) is already used at Earth boundaries; this comparison is not independent validation.\nRatios of regional means are descriptive: not microphysical efficiency, isolated causality or a diagnosed water residence time.',ha='center',fontsize=8)
    fig.subplots_adjust(left=.07,right=.98,top=.89,bottom=.14,hspace=.35,wspace=.32)
    fig.savefig(OUT/'water_column.png',dpi=160);plt.close(fig)


if __name__=='__main__':main()
