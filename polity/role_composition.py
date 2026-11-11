"""Source-label partitions, not economic or military role assignments."""
GROUPS=('village_only','vicus_only','small_town_only','mixed_nonroadside_labels','roadside_only')
LABELS={'village':'village_only','vicus':'vicus_only',"unwalled 'small town'":'small_town_only'}


def nucleated_partition(labels):
    normalized={str(x).strip().casefold() for x in labels}
    selected=normalized&LABELS.keys()
    if len(selected)>1:return 'mixed_nonroadside_labels'
    if selected:return LABELS[next(iter(selected))]
    if 'roadside settlement' in normalized:return 'roadside_only'
    return None


def nonroadside(labels):
    return 'roadside settlement' not in {str(x).strip().casefold() for x in labels}
