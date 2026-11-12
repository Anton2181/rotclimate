"""Housing samples are conditional size references, never automatic censuses."""
from dataclasses import dataclass
import math


@dataclass(frozen=True)
class HousingSample:
    site_id: str
    properties: int
    sample_area_ha: float
    site_area_ha: float
    provenance: str
    phase_start: int | None = None
    phase_end: int | None = None
    excluded_years: tuple[int, ...] = ()
    representative_sample: bool = False
    extent_matches_phase: bool = False

    def __post_init__(self):
        if not self.site_id or not self.provenance:
            raise ValueError('Identity and source provenance are required')
        if isinstance(self.properties, bool) or not isinstance(self.properties, int) or self.properties <= 0:
            raise ValueError('Use a positive observed integer property count')
        if any(not math.isfinite(v) or v <= 0 for v in (self.sample_area_ha, self.site_area_ha)):
            raise ValueError('Areas must be finite positive hectares')
        if self.sample_area_ha > self.site_area_ha:
            raise ValueError('Investigated sample exceeds the stated whole-site extent')
        if any(v is not None and (isinstance(v, bool) or not isinstance(v, int))
               for v in (self.phase_start, self.phase_end)):
            raise ValueError('Phase endpoints must be integer years or unknown')
        if self.phase_start is not None and self.phase_end is not None and self.phase_end < self.phase_start:
            raise ValueError('Reversed sample phase')
        if any(isinstance(v, bool) or not isinstance(v, int) for v in self.excluded_years):
            raise ValueError('Explicit phase exclusions must be integer years')
        if not isinstance(self.representative_sample, bool) or not isinstance(self.extent_matches_phase, bool):
            raise ValueError('Measurement certifications must be explicit booleans')

    def reference(self, household_persons: float) -> dict:
        """Return a stated extrapolation, without upgrading its evidential status."""
        if isinstance(household_persons, bool) or not math.isfinite(household_persons) or household_persons <= 0:
            raise ValueError('Declare finite positive people per property')
        density = self.properties / self.sample_area_ha * household_persons
        people = density * self.site_area_ha
        if not math.isfinite(density) or not math.isfinite(people):
            raise ValueError('Population extrapolation overflow')
        return dict(site_id=self.site_id, people=people, people_per_ha=density,
                    sampled_fraction=self.sample_area_ha / self.site_area_ha,
                    people_per_property=household_persons,
                    kind='sample_density_extrapolation', direct_census=False)

    def blockers(self, year: int) -> tuple[str, ...]:
        """Catalogue-wide occupation dates cannot certify a housing phase."""
        if isinstance(year, bool) or not isinstance(year, int):
            raise ValueError('Comparison year must be an integer')
        reasons = []
        if year in self.excluded_years:
            reasons.append('reported_sample_phase_excludes_year')
        elif self.phase_start is None or self.phase_end is None:
            reasons.append('sample_phase_unresolved')
        elif not self.phase_start <= year <= self.phase_end:
            reasons.append('outside_sample_phase')
        if not self.representative_sample:reasons.append('site_representativeness_unresolved')
        if not self.extent_matches_phase:reasons.append('contemporaneous_extent_unresolved')
        return tuple(reasons)

    def for_calibration(self, year: int, household_persons: float) -> dict:
        reasons = self.blockers(year)
        if reasons:raise ValueError('Unqualified resident-size reference: ' + ', '.join(reasons))
        return dict(self.reference(household_persons), comparison_year=year,
                    qualification='dated_conditional_housing_reference')
