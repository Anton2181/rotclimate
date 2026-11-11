from polity.role_composition import GROUPS,nucleated_partition,nonroadside


def test_partition_preserves_colabels_without_inventing_functions():
    cases=[([' Village ','roadside settlement'],'village_only',False),
           (['vicus','FORT'],'vicus_only',True),
           (["unwalled 'small town'",'villa'],'small_town_only',True),
           (['village','vicus','roadside settlement'],'mixed_nonroadside_labels',False),
           (['roadside settlement'],'roadside_only',False)]
    for labels,group,strict in cases:
        assert nucleated_partition(labels)==group and group in GROUPS
        assert nonroadside(labels)==strict


def test_non_nucleated_records_stay_unassigned_and_duplicates_do_not_split_roles():
    assert nucleated_partition(['farm','villa','fort']) is None
    assert nucleated_partition([]) is None
    assert nucleated_partition(['VICUS','vicus'])=='vicus_only'
    assert not nonroadside([' ROADSIDE SETTLEMENT '])
