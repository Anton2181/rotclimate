# M1 transfer score, r58 -> r64b (28 Nov 2026)
World-legal (ROTCLIMATE_WORLD_LEGAL=1, world parameter sets r58w vs r64bw, 97 dev regions):
  S97 0.9869 [0.9748, 0.9982] (T -1.0 %, P -1.7 %)
Earth (observed fields on), chained dev6 r59..r64b: 0.884.
Transferable share ~ (1 - 0.9869) / (1 - 0.884) = 11 %: almost all of the gain since the last rebuild rests on the
Earth-only NCEP fields (r60/r61 omega cap, r63 wet PW nudge, r64/r64b 500 hPa RH gates). Caveat: the Earth number is a
chain of paired steps, the world number one direct comparison.
Priority before the r70 rebuild: model-diagnosed stand-ins for observed 500 hPa omega and RH (and PW), so the r60-r64b
mechanisms reach the world.
