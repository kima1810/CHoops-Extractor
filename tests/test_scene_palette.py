import pytest
from choops_py.formats.scene_palette import associate_palette, palette_tint
from choops_py.roster.schema import CONFIRMED_PALETTE_CAPTIONS


def test_floor_layers_preserve_arena_vertices_and_unknown_materials():
    from choops_py.formats.scene_palette import floor_layers
    batches = [{'material_hash': h, 'first': i * 3, 'count': 3} for i, h in
               enumerate((2310823066, 2600458314, 2218775043, 123))]
    source = [{'court_surface': True, 'vertices': [(0, 0, 0)], 'batches': batches},
              {'court_surface': False, 'vertices': [(1, 2, 3)], 'batches': batches}]
    filtered = floor_layers(source, False, False)
    assert filtered[0]['batches'] == batches
    assert filtered[1]['batches'] == batches
    assert filtered[0]['vertices'] is source[0]['vertices']
    assert source[0]['batches'] == batches
    assert floor_layers(source)[0]['batches'] == batches


def test_missing_floor_layers_use_authored_game_coordinates_not_apron_bounds():
    from choops_py.formats.scene_palette import supplement_floor_layers, floor_layers
    apron = {'court_surface': True, 'name': 'floor/floor', 'vertices': [(-500, 0, -500)],
             'batches': [{'material_hash': 123, 'first': 0, 'count': 1}]}
    lines = {'court_surface': True, 'name': 'floor/lines', 'vertices': [(17, 0, 4), (18, 0, 5)],
             'batches': [{'material_hash': 2310823066, 'first': 0, 'count': 1, 'texture': 'ink'},
                         {'material_hash': 2218775043, 'first': 1, 'count': 1, 'texture': 'ink'}]}
    selected = {'meshes': [apron], 'images': {'wood': b'art'}, 'warnings': []}
    original = {'meshes': [lines], 'images': {'ink': b'lines'}, 'warnings': []}
    result = supplement_floor_layers(selected, original)
    overlay = result['meshes'][1]
    assert overlay['vertices'] == [(17, 1, 4), (18, 1, 5)]
    assert lines['vertices'] == [(17, 0, 4), (18, 0, 5)]
    assert overlay['batches'][0]['texture'] is None
    assert overlay['batches'][0]['reference_overlay'] is True
    assert result['images'] == selected['images']
    assert floor_layers(result['meshes'], False, True)[1]['batches'][0]['first'] == 1
    assert len(supplement_floor_layers(result, original)['meshes']) == 2
    assert len(selected['meshes']) == 1 and lines['batches'][0]['texture'] == 'ink'


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


def test_key_and_center_guides_use_authored_outlines_and_curve_uv_axis():
    from choops_py.formats.scene_palette import supplement_floor_layers, floor_layers
    vertices=[(12,0,30,0,0),(14,0,30,1,0),(14,0,32,1,1)]
    routes={2:1723127071,10:3117775956,20:1460891455,19:2324736937}
    original={'meshes':[dict(court_surface=True,vertices=vertices,batches=[
        dict(first=0,count=3,material_hash=identity) for identity in routes.values()])],'warnings':[]}
    selected={'meshes':[dict(name='floor',court_surface=True,vertices=vertices,batches=[dict(first=0,count=3,material_hash=123)])],'warnings':[],'images':{}}
    result=supplement_floor_layers(selected,original);guide=result['meshes'][1]
    assert {b['reference_slot'] for b in guide['batches']}=={2,10,20}
    assert {b['reference_slot']:b['reference_axis'] for b in guide['batches']}=={2:2,10:2,20:1}
    assert guide['vertices']==[(x,y+1,z,u,v) for x,y,z,u,v in vertices]
    assert not floor_layers(result['meshes'],False,False,False)[1]['batches']
    assert len(floor_layers(result['meshes'],False,False,True)[1]['batches'])==3
    assert floor_layers(result['meshes'],False,False,True)[0]['batches']==selected['meshes'][0]['batches']
    assert original['meshes'][0]['vertices']==vertices


@pytest.mark.gui
def test_key_center_toggle_is_independent_in_scene_panel(qtbot,monkeypatch,tmp_path):
    from choops_py.studio.app import Window
    window=Window();qtbot.addWidget(window);shown=[]
    monkeypatch.setattr(window.scene_view,'set_meshes',lambda meshes,**kwargs:shown.append(meshes))
    result=dict(meshes=[dict(name='guide',game_floor_layer=True,vertices=[(0,1,0,0,0)]*3,
                            batches=[dict(first=0,count=3,reference_slot=s,reference_overlay=True) for s in (4,18,2,10,20)])],textures=[],images={},warnings=[])
    window.show_scene_preview(result,tmp_path/'s256.iff')
    assert window.scene_key_center.isEnabled() and not window.scene_key_center.isChecked()
    window.scene_key_center.setChecked(True)
    assert {b['reference_slot'] for b in shown[-1][0]['batches']}=={2,10,20}
    assert not window.scene_three_point.isChecked() and not window.scene_border.isChecked()
    window.scene_key_center.setChecked(False)
    assert not shown[-1][0]['batches']
