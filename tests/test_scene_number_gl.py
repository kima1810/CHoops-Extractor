import pytest
from PySide6.QtCore import Qt
from PySide6.QtGui import QImage,QOpenGLContext
from choops_py.studio.scene_view import SceneView

pytestmark=pytest.mark.gui


@pytest.mark.parametrize("kind",["number","back_number","name","palette","prelit","lightmap","glow"])
def test_number_sampler_uses_integer_uniforms_and_authored_colour(qtbot,kind):
    context=QOpenGLContext()
    if not context.create():pytest.skip('OpenGL context unavailable on this Qt platform')
    view=SceneView();qtbot.addWidget(view)
    view.setAttribute(Qt.WidgetAttribute.WA_DontShowOnScreen,True);view.resize(300,300)
    vertices=[(-1,-1,0,0,1),(1,-1,0,1,1),(1,1,0,1,0),(-1,-1,0,0,1),(1,1,0,1,0),(-1,1,0,0,0)]
    batch=dict(first=0,count=6,texture='base')
    if kind=='number':batch.update(number_texture='num',number_uv=(1,1,0,0))
    elif kind=='back_number':batch.update(number_texture='num',number_uv=(1,1,10,10),back_number_uv=(1,1,0,0))
    elif kind=='name':batch.update(name_texture='num',name_placement=(.5,1.,.5,1.),name_scale=1.)
    elif kind=='palette':batch.update(palette_tint=(1,0,0,1))
    else:
        colour=(1.,1.,1.,1.) if kind=='lightmap' else (.5,0.,0.,1.) if kind=='glow' else (1.,0.,0.,1.)
        vertices=[(*v,*colour,*v[3:5]) for v in vertices]
        batch['shader_mode']='glow' if kind=='glow' else 'prelit'
        if kind=='lightmap':batch['lightmap_texture']='num'
    view.set_meshes([dict(name='plane',vertices=vertices,batches=[batch])])
    base=QImage(1,1,QImage.Format.Format_RGBA8888);base.fill(Qt.GlobalColor.white)
    glyph=QImage(1,1,QImage.Format.Format_RGBA8888);glyph.fill(Qt.GlobalColor.red)
    view.set_material_images({'base':base,'num':glyph});view.yaw=0;view.pitch=0;view.fit_camera();view.show()
    qtbot.waitUntil(view.isValid,timeout=5000)
    frame=view.grabFramebuffer();colour=frame.pixelColor(150,150)
    assert not view.error and colour.red()>100 and colour.green()<10 and colour.blue()<10


@pytest.mark.parametrize('automatic', [True, False])
def test_alignment_guide_ignores_texture_palette_and_lighting(qtbot, automatic):
    context = QOpenGLContext()
    if not context.create():
        pytest.skip('OpenGL context unavailable on this Qt platform')
    view = SceneView()
    qtbot.addWidget(view)
    view.setAttribute(Qt.WidgetAttribute.WA_DontShowOnScreen, True)
    view.resize(300, 300)
    vertices = [(-1,-1,0,0,1),(1,-1,0,1,1),(1,1,0,1,0),
                (-1,-1,0,0,1),(1,1,0,1,0),(-1,1,0,0,0)]
    batch = dict(first=0, count=6, texture='transparent', reference_overlay=True,
                 palette_tint=(0,0,0,0), shader_mode='glow', reference_axis=2)
    image = QImage(1,1,QImage.Format.Format_RGBA8888)
    image.fill(Qt.GlobalColor.transparent)
    view.set_meshes([dict(name='guide', vertices=vertices, batches=[batch])])
    view.set_material_images({'transparent':image})
    view.set_image(image)
    view.automatic = automatic
    view.yaw = view.pitch = 0
    view.fit_camera()
    view.show()
    qtbot.waitUntil(view.isValid, timeout=5000)
    colour = view.grabFramebuffer().pixelColor(150,150)
    assert not view.error
    assert colour.red() > 250 and 185 < colour.green() < 198 and 32 < colour.blue() < 45
    outside = view.grabFramebuffer().pixelColor(150, 110)
    assert outside.red() < 100
