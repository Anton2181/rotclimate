"""Certified place identity for group-aware settlement-size comparisons."""


def place_groups(site_ids, identities) -> dict:
    """Group references by certified place identity.

    Several estimates for one place are one group, never independent labels.
    A site without a certified identity stays a flagged singleton: it cannot
    merge by name, and it cannot be counted as joined.
    """
    site_ids = list(site_ids)
    if len(set(site_ids)) != len(site_ids) or any(not isinstance(s, str) or not s for s in site_ids):
        raise ValueError('Site identifiers must be unique nonempty strings')
    if set(identities) - set(site_ids):
        raise ValueError('Identity supplied for an unknown site')
    groups = {}
    for site in site_ids:
        place = identities.get(site)
        if place is None:
            place = 'unjoined:' + site
        elif not isinstance(place, str) or not place or place.startswith('unjoined:'):
            raise ValueError('A certified place identity must be a nonempty catalogue reference')
        groups.setdefault(place, []).append(site)
    return groups
