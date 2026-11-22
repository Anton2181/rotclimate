# Tropical check (open set t), 2026-11-22

## r50 baseline on set t
Tropical land runs 1.2-1.9 C too warm (Niger bend t_13n_7w 1.6 C too cold). Rain is misplaced:
Maranhao coast t_2s_45w 5165 mm (obs 1991), SW Amazon t_10s_66w 436 (1737), central Amazon
t_1s_63w 1362 (2652), southern Congo t_7s_24e 599 (1362), Tanzania t_8s_36e 2310 (1276).

## plan_T1 (convective closure refit, objective max(S49, S_t)): FAIL, parked
Best 0.9987 (S49 0.9987, gate 0.995). The global convection knobs trade the tropics against
dev49: convective_rh_heat 0.2788 brought S_t to 0.9675 but S49 to 1.0017; sst_tropical +1
gave S49 0.9955 but S_t 1.0139. No retune reaches both.

## Diagnosis (monsoon_trace, r50)
Maranhao rains 20-24 mm/day for six months (Nov-Apr) at column RH 0.64, instab 2.5, chi 0.28:
the e92 heated-land threshold drop (convective_rh 0.708 - 0.3625) puts the closure far into
its exponential. Inland (t_1s_63w) the same heat and RH ~0.55 rain only ~1.2 mm/day: chi 0.8
there, so the e93 gate (convective_rh_chi0 0.675) cancels the e92 drop as if the forest's air
were desert air aloft. The soil bucket is near full inland, unlike Najd's.

## e103: dry-land chi for the e93 gate (declared before scoring)
chi93 = chi - convective_rh_chi_dry x (chi - chi_dry), chi_dry = the same advected land share
with land weighted by 1 - clip(annual-mean soil water / (0.75 bucket)). Default off.
Probe (=1): central Amazon wet-season rain +1.5-3 mm/day, Maranhao unchanged.
Screen: dev49 pair + set t at convective_rh_chi_dry = 1. If S49 <= ~1.000 and S_t improves,
joint refit with objective max(S49, S_t) over convective_rh_chi_dry, convective_rh_chi0,
convective_rh_heat, convective_rain, convective_rh, land_recycling; then policy v3 gates
(fine28, ONE run on sealed set r).
Screen result (=1): S49 1.0008 (T -0.03 %, P +0.18 %), S_t 0.9164. Joint refit plan_T2 declared.

## plan_T2 (e103 joint refit): FAIL, e103 parked default-off
Best 0.9992 (S49; T +0.4 %, P -0.5 %), S_t 0.92 throughout (0.904-0.943). Every e103 variant
leaves dev49 within +-0.2 % of r50 while set t improves by ~8 %: e103 is a tropical-only fix
that dev49 (4 tropical regions of 49) cannot credit. Under policy v3 it cannot be adopted.
Owner decision (not taken here): whether a tropical pool such as set t should join the dev
objective (a policy v4). Kept as calibration/tropical_check_20261122t/plan_T2_best.json.
Sealed set r stays unopened.

## e104: soft ceiling on the land convective closure (rate -> cap tanh(rate/cap)), default off
Screen vs r50:            S49      S_t
  r50 + e104 cap 12     0.9992   0.945
  r50 + e104 cap 8        -      0.920
  T2 best + cap 12      0.9984   0.872  (T +0.3 %, P -0.7 %; Maranhao Plog 1.30 -> 0.83)
  T2 best + cap 8         -      0.850
Joint refit plan_T3 declared (dev-side knobs added; sst_tropical excluded).
