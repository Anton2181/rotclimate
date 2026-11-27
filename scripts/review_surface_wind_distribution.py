"""Expose per-cell rain errors hidden by a regional annual/seasonal mean."""
import json
from pathlib import Path
import sys
import numpy as np
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from local_benchmark_protocol import file_hash, write_json
OUT = ROOT / 'output/surface_wind_diagnostic_20261127'


def main():
    target = OUT / 'spatial_rain_review.json'
    assert not target.exists()
    review = json.loads((OUT / 'review.json').read_text())
    records = []
    for row in review['statistics']:
        suffix = dict(s_2n_43e='somalia_1100', u_21n_21e='sahara_1100', north_india='north_india_1100')[row['region']]
        f = OUT / (row['arm'] + '_' + suffix) / 'capture.npz'
        with np.load(f) as z:
            annual, observed = z['P'].sum(0), z['obs_P'].astype(float).sum(0)
            log_rmse = float(np.sqrt(np.mean(np.log((annual + 50) / (observed + 50)) ** 2)))
            seasonal = float(12 * np.abs(z['P'] - z['obs_P']).mean() / (observed.mean() + 120))
            np.testing.assert_allclose(.5 * (log_rmse + seasonal), row['rain_loss'], rtol=1e-14)
            worst = np.argsort(np.abs(annual - observed))[::-1][:4]
            records.append(dict(region=row['region'], arm=row['arm'], capture_sha256=file_hash(f),
                annual_per_cell_log_rmse=log_rmse, normalized_cell_month_absolute_error=seasonal,
                annual_rain_percentiles_0_50_100=np.percentile(annual, [0,50,100]).tolist(),
                observed_annual_percentiles_0_50_100=np.percentile(observed,[0,50,100]).tolist(),
                largest_annual_absolute_errors=[dict(latitude=float(z['lat'][i]), longitude=float(z['lon'][i]),
                    annual_rain_mm=float(annual[i]), observed_mm=float(observed[i])) for i in worst]))
    write_json(target, dict(review_sha256=file_hash(OUT/'review.json'), script_sha256=file_hash(__file__),
        statistics=records, integrations=0,
        finding='North India regional annual total and mean seasonal curve improve while both per-cell loss components worsen. Several Nepal cells exceed3200mm/year against366–772observed; mean cancellation is not spatial skill. Coarse surface reference and free-wind terrain uplift can affect this diagnostic; no tuning/adoption.'))


if __name__ == '__main__':
    main()
