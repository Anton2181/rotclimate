# e138 / e138b observed zonal SST: closed (2026-11-28)

Screened vs r59 on 97 regions (output/ppe_20261127/zg, paired with ref59):
- zg35_55 (w 0.6, ramp 35->55): S97 1.0008 [0.9932, 1.0091]
- zg40_60 (w 0.8, ramp 40->60): S97 1.0018 [0.9932, 1.0117]
- zg30_50 (w 0.5, ramp 30->50): S97 1.0012 [0.9939, 1.0088]
None goes to gates. Together with W21 (uniform blend refit, dev6 0.9974 [0.9887, 1.0063], FAIL) the line is closed.

Reading: observed zonal SST fixes Tierra del Fuego (0.86-0.88), British Isles (0.85-0.90), BC coast, Alps, Patagonia,
but the model's local warm-current terms (current_strength, subpolar_current, inland_sea_warming) are added on top
of the sea and already supply the NH ocean warmth -> western Europe +1.5 C, Hudson Bay (u2_59n_76w) 1.27-1.41,
Nova Scotia, Hokkaido, Okhotsk too warm. A zonal blend cannot separate "zonal sea too cold" from "currents too warm";
the error is in the local current terms, not the zonal sea. Any further attempt has to re-derive the current terms
against WOA18 anomalies (regional SST minus zonal mean) rather than blend the zonal mean. Left for the r65 recalibration.
Sealed BB stays UNOPENED.
