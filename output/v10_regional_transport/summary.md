# Fixed regional transport comparison

Status: needs_diagnosis; 6/8 cases. Atlas unchanged.

| Case | Coast winter rain | Change | Monthly MAE change | Med still arid | Settled | Mechanism screen |
|---|---:|---:|---:|---:|---|---|
| control_california_bulk | 56.91mm | +0.00mm | +0.000mm | 92.8% | True | False |
| control_iberia_bulk | 33.26mm | +0.00mm | +0.000mm | 97.5% | True | False |
| control_california_parcel_lower | 92.96mm | +0.00mm | +0.000mm | 78.3% | True | False |
| control_iberia_parcel_lower | 61.28mm | +0.00mm | +0.000mm | 94.4% | True | False |
| candidate_california_bulk | 90.23mm | +33.32mm | -1.901mm | 79.7% | False | False |
| candidate_iberia_bulk | 59.15mm | +25.89mm | -1.269mm | 93.9% | False | False |

Four exact upwind controls, four fixed FCT climates. Prescribed incoming water, flow and clouds stay paired. The screen requires reduced reference-arid summer MAE, coastal winter loss <=2mm, settled cycles and existing temperature guards; it is not an atlas publication rule. Seasonal spatial errors are saved in each summary.

Stopped for diagnosis: Ascending parcel condensate exceeds transported water.
