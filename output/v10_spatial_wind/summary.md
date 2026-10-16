# Spatial background wind check

Status: complete. Four fixed cases; no search or atlas export.

| Case | Uniform → spatial MAE | Uniform → spatial rain/reference | Uniform → spatial coverage | Settled | Provisional screen |
|---|---:|---:|---:|---|---|
| california_humidity_08 | 33.70 → 31.58 | 0.77 → 0.06 | 80.7% → 41.3% | True | False |
| iberia_humidity_08 | 32.01 → 34.87 | 0.23 → 0.03 | 75.0% → 25.6% | True | False |
| california_humidity_10 | 41.66 → 29.88 | 1.28 → 0.12 | 85.9% → 59.1% | True | False |
| iberia_humidity_10 | 32.07 → 34.91 | 0.46 → 0.05 | 79.2% → 34.9% | True | False |

The broad screen is retained unchanged. Positive skill against zero rain, coastal/interior winter/summer responses and rain concentration must accompany an apparent improvement; neither development region is independent validation. The seasonal driver records signed thermal terms, layer rainfall, maximum projection adjustment and full water/energy budgets.

Monthly spatial winds remain imposed forcing. Offshore boundary humidity and synthetic storm heat/moisture covariance remain limitations. Bilinear interpolation smooths native grid steps but adds no information beyond the coarse reference. Existing terrain drag may overlap resolved terrain effects; this matched experiment keeps it fixed.

Temperature remains observation-informed. No automatic promotion or fantasy atlas update.
