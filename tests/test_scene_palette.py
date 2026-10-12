import pytest
from choops_py.formats.scene_palette import associate_palette, palette_tint
from choops_py.roster.schema import CONFIRMED_PALETTE_CAPTIONS


def test_runtime_material_route_uses_current_palette_and_preserves_source():
    colors = ['#BEBEBEFF']*31
    colors[19] = '#80400080'
    source = [{'batches':[{'material_hash':0x8a90aba9,'supports_diffuse_color':True,'first':0,'count':3}]}]
    result = associate_palette(source, colors)
    assert result[0]['batches'][0]['palette_tint'] == pytest.approx((.2158605,.0512695,0.,128/255))
    assert 'palette_tint' not in source[0]['batches'][0]
    colors[19] = '#FF0000FF'
    assert associate_palette(source, colors)[0]['batches'][0]['palette_tint'] == (1.,0.,0.,1.)
    assert associate_palette(source, None)[0]['batches'][0]['palette_tint'] is None


def test_default_gray_and_unrecognized_material_do_not_guess_colors():
    colors = ['#BEBEBEFF']*31
    assert palette_tint(0x8a90aba9, colors) is None
    assert palette_tint(0x12345678, colors) is None
    assert CONFIRMED_PALETTE_CAPTIONS[19] == 'Key'
    assert CONFIRMED_PALETTE_CAPTIONS[2] == 'Key Circle Outer'


def test_modded_shader_without_diffuse_uniform_declines_roster_binding():
    source = [{'batches':[{'material_hash':0x8a90aba9, 'supports_diffuse_color':False}]}]
    assert associate_palette(source, ['#FF0000FF']*31)[0]['batches'][0]['palette_tint'] is None
