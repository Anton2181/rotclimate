# Tibesti / Libyan desert summer rain (u_21n_21e), diagnosed under r61 (2026-11-28)
Model Jun-Sep rain 32/73/85/51 mm against ~0-1 observed (rain loss ~1.7, second only to Somalia).
- Not the convection closure: instability boost 1.0, closure 0; the rain is the large-scale term at column RH 0.63-0.81.
- The column is far too moist: model July-August precipitable water 49-52 mm vs NCEP 17-19. Observed PW falls
  43 -> 37 -> 27 -> 19 -> 17 mm from 10 to 21 N along 21 E; the model is flat (~49) across the box.
- Model wind at 21 N in July: southerly 2.7 m/s, westerly 1.3 (monsoon inflow toward the box's own heat low): the
  monsoon/Harmattan boundary sits too far north at 21 E, where the real boundary lies further south and dry northerlies
  dominate. Observed 500 hPa descent is weak there in July (+0.005-0.007 Pa/s), so e141 does not act.
- Same window-truncation family as Somalia: the box sees its own heat low, not the larger-scale Saharan low that sits
  further west. e140 (observed SLP for the e55/e83 gates) touched this but failed sealed BB. A world-legal fix would need
  the inflow strength tied to the moisture gradient it can sustain (shallow monsoon layer), not more forcing.
Not attempted further this cycle.
