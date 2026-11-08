"""The atlases that are built, refreshed and published.

Owner, 8 Nov 2026: the free and Whittaker fits are retired; work focuses on the Earth fit. Their folders stay as the last
published snapshot (and their hosted pages as they were); add a name back to ACTIVE to build one again.
"""
ACTIVE = ("earth_fit",)
RETIRED = ("free_fit", "whittaker_fit")


def active(names):
    """Keep the atlas names (or tuples that start with one) whose atlas is active, in their order."""
    return [n for n in names if (n[0] if isinstance(n, tuple) else n) in ACTIVE]
