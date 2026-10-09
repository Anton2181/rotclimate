"""The local calendar.

Ten months of 35 days (seven five-day weeks each) followed by 15 holy days:
10 * 35 + 15 = 365 days, i.e. an Earth-length year.  A year therefore holds
exactly 73 five-day weeks, which is the model's time step.

The month names carry seasonal meaning ("middle winter", "early summer"...).
Placing the winter solstice on day 22 (Titian Marigold 23) makes all of them
line up with the astronomy *and* with the ~1 month thermal lag:

  * winter solstice    -> Titian Marigold 23      (early winter)
  * coldest weeks      -> Scarlet Violet          (middle winter)
  * spring equinox     -> Iris Rose 9             (middle spring)
  * summer solstice    -> Amber Zinnia 30         (early summer)
  * hottest weeks      -> Crimson Lantana         (middle summer)
  * autumn equinox     -> Lilac Crocus 17         (middle fall)
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

MONTH_DAYS = 35
HOLY_DAYS = 15


@dataclass(frozen=True)
class Month:
    name: str
    season: str
    short: str


MONTHS = [
    Month("Titian Marigold", "early winter", "TMa"),
    Month("Scarlet Violet", "middle winter", "SVi"),
    Month("Peony Blossom", "late winter / early spring", "PBl"),
    Month("Iris Rose", "middle spring", "IRo"),
    Month("Verdant Camellia", "late spring", "VCa"),
    Month("Amber Zinnia", "early summer", "AZi"),
    Month("Crimson Lantana", "middle summer", "CLa"),
    Month("Saffron Lotus", "late summer / early fall", "SLo"),
    Month("Lilac Crocus", "middle fall", "LCr"),
    Month("Silver Chrysanth", "late fall", "SCh"),
]
HOLY = Month("Holy Days", "turn of the year", "Hol")

YEAR_DAYS = len(MONTHS) * MONTH_DAYS + HOLY_DAYS  # 365


def month_of_day(day: int) -> tuple[Month, int, int]:
    """Return (month, day_in_month (1-based), month_index) for a 0-based day."""
    day = int(day) % YEAR_DAYS
    i = day // MONTH_DAYS
    if i < len(MONTHS):
        return MONTHS[i], day % MONTH_DAYS + 1, i
    return HOLY, day - len(MONTHS) * MONTH_DAYS + 1, len(MONTHS)


def date_label(day: float) -> str:
    m, d, _ = month_of_day(int(day))
    week = (d - 1) // 5 + 1
    if m is HOLY:
        return f"Holy Day {d}"
    return f"{m.name} {d}  (week {week})"


def month_slices(steps_per_year: int = 73):
    """Index lists of model steps belonging to each local month (+ holy days).

    With 73 steps every step is one five-day week: 7 per month, 3 holy weeks.
    """
    step_days = YEAR_DAYS / steps_per_year
    centers = (np.arange(steps_per_year) + 0.5) * step_days
    out = []
    for k in range(len(MONTHS) + 1):
        lo = k * MONTH_DAYS
        hi = lo + (MONTH_DAYS if k < len(MONTHS) else HOLY_DAYS)
        out.append(np.where((centers >= lo) & (centers < hi))[0])
    return out


def month_names(include_holy: bool = True) -> list[str]:
    names = [m.name for m in MONTHS]
    return names + [HOLY.name] if include_holy else names
