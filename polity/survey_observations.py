"""Conservative field-survey evidence parsing; missing is never absence."""
import math


def yes_no_evidence(value):
    raw='' if value is None else str(value).strip()
    state={'yes':'recorded_yes','no':'recorded_no'}.get(raw.casefold(),'missing' if not raw else 'unresolved')
    return dict(raw=raw,state=state)


def north_east_evidence(north,east):
    def numeric(v):
        try:x=float(str(v).strip())
        except (ValueError,TypeError):return None
        return x if math.isfinite(x) else None
    lat,lon=numeric(north),numeric(east)
    numeric_pair=lat is not None and lon is not None
    global_pair=numeric_pair and -90<=lat<=90 and -180<=lon<=180
    regional=global_pair and 18.756600<=lat<=21.735785 and 75.295495<=lon<=80.950312
    return dict(numeric_pair=numeric_pair,documented_latitude_longitude_valid=bool(global_pair),
        inside_declared_vidarbha_envelope=bool(regional),coordinate_swap_applied=False)
