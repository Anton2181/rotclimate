import json
import pytest
from PIL import Image
from scripts.build_r39_earth_stage import verify_packet


def packet(tmp_path):
    (tmp_path/'atlas.bin').write_bytes(bytes(8))
    Image.new('RGB',(4,2),'white').save(tmp_path/'base.webp')
    Image.new('RGB',(4,2),'black').save(tmp_path/'variant.webp')
    return dict(width=4,height=2,arrays=dict(cls=dict(dtype='uint8',shape=[2,4],offset=0)),
                layers=[dict(file='base.webp',variants=dict(options=[dict(file='variant.webp')]))])


def test_complete_packet_includes_variant_assets(tmp_path):
    meta=packet(tmp_path)
    Image.new('RGB',(8,4),'white').save(tmp_path/'base.webp')
    assert verify_packet(tmp_path,meta)['layer_assets']==2


def test_truncated_binary_is_rejected_before_serving(tmp_path):
    meta=packet(tmp_path);(tmp_path/'atlas.bin').write_bytes(bytes(7))
    with pytest.raises(ValueError,match='Truncated'):verify_packet(tmp_path,meta)


def test_diagnostic_downloads_must_be_present_in_portable_packet(tmp_path):
    meta=packet(tmp_path);meta['layers'][0]['download']='values.csv'
    with pytest.raises(ValueError,match='Missing'):verify_packet(tmp_path,meta)
    (tmp_path/'values.csv').write_text('value\n1\n')
    assert verify_packet(tmp_path,meta)['layer_assets']==3


def test_initialization_check_metadata_and_chart_are_required(tmp_path):
    meta=packet(tmp_path);meta['initialization_check']=dict(metadata='check.json',image='check.png')
    with pytest.raises(ValueError,match='Missing'):verify_packet(tmp_path,meta)
    (tmp_path/'check.json').write_text('{}')
    Image.new('RGB',(7,3)).save(tmp_path/'check.png')  # a chart need not have the map's aspect ratio
    assert verify_packet(tmp_path,meta)['layer_assets']==4


def test_missing_variant_and_incorrect_map_size_are_rejected(tmp_path):
    meta=packet(tmp_path);(tmp_path/'variant.webp').unlink()
    with pytest.raises(ValueError,match='Missing'):verify_packet(tmp_path,meta)
    Image.new('RGB',(2,2)).save(tmp_path/'variant.webp')
    with pytest.raises(ValueError,match='dimensions'):verify_packet(tmp_path,meta)
