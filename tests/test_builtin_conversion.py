import os
import struct
import shutil
import uuid
from pathlib import Path
import pytest
from choops_py.texture_tools import dds,gtf,external_converters
from choops_py.texture_tools.builtin_converter import to_gtf,to_dds,_swizzle
from choops_py.archive.manifests import OUTPUT,ROOT


def texture(fmt,width,height,mips=1,cube=False):
    header=bytearray(128);header[:4]=b'DDS '
    values={4:124,8:0x2100f,12:height,16:width,20:width,28:mips,76:32,108:0x401008 if mips>1 else 0x1000,112:0xfe00 if cube else 0}
    if fmt.startswith('DXT'):values[80]=4;header[84:88]=fmt.encode()
    elif fmt=='RGBA16F':values.update({80:4,84:113})
    elif fmt=='L8':values.update({80:0x20000,88:8,92:255})
    else:values.update({80:0x41,88:32,92:0xff0000,96:0xff00,100:0xff,104:0xff000000})
    for field,value in values.items():struct.pack_into('<I',header,field,value)
    size=dds.image_size(width,height,fmt,mips)*(6 if cube else 1)
    return bytes(header)+bytes((i*73+i//251)%256 for i in range(size))


@pytest.mark.parametrize('fmt',['L8','ARGB8','DXT1','DXT3','DXT5','RGBA16F'])
@pytest.mark.parametrize('swizzle',[False,True])
@pytest.mark.parametrize('shape',[(8,4,3),(4,8,4),(5,7,3),(1,1,1),(16,16,5)])
def test_every_mip_preserves_input_pixels(fmt,swizzle,shape):
    original=texture(fmt,*shape)
    converted=to_gtf(original,swizzle)
    info,_,_=gtf.parse(converted)
    assert (info['width'],info['height'],info['mip_count'])==shape
    assert to_dds(converted)[128:]==original[128:]


@pytest.mark.parametrize('fmt',['L8','ARGB8','DXT1','DXT3','DXT5','RGBA16F'])
@pytest.mark.parametrize('swizzle',[False,True])
def test_all_six_cube_faces_and_mips_are_preserved(fmt,swizzle):
    original=texture(fmt,8,8,4,True)
    converted=to_gtf(original,swizzle)
    assert gtf.parse(converted)[0]['cubemap']
    assert to_dds(converted)[128:]==original[128:]


def test_rectangular_morton_coordinates_and_wide_texel_words():
    # X/Y bits interleave until the shorter axis ends; remaining bits are contiguous.
    image=bytes(range(32))
    expected=bytes([0,1,8,9,2,3,10,11,16,17,24,25,18,19,26,27,4,5,12,13,6,7,14,15,20,21,28,29,22,23,30,31])
    assert _swizzle(image,8,4,1)==expected
    assert _swizzle(expected,8,4,1,True)==image


def test_no_external_tool_is_launched_by_default(tmp_path,monkeypatch):
    def forbidden(*args,**kwargs):raise AssertionError('External executable launched')
    monkeypatch.setattr(external_converters,'run_tool',forbidden)
    monkeypatch.setattr(external_converters,'find',lambda *a,**kw:None)
    source=tmp_path/'art.dds';source.write_bytes(texture('DXT5',8,8,4))
    work=OUTPUT/'temp'/('builtin_test_'+uuid.uuid4().hex)
    try:
        report=external_converters.convert('dds2gtf',source,work/'out.gtf',swizzle=True)
        assert report['backend']=='builtin-python'
        assert external_converters.status()['import_dds_ready']
        external_converters.convert('gtf2dds',work/'out.gtf',work/'out.dds')
        assert (work/'out.dds').read_bytes()[128:]==source.read_bytes()[128:]
    finally:
        if work.exists():shutil.rmtree(work)


@pytest.mark.windows
@pytest.mark.skipif(os.name!='nt' or not (ROOT/'tools/dds2gtf.exe').is_file(),reason='Optional native reference tool unavailable')
def test_native_reference_matches_descriptors_and_pixels():
    work=OUTPUT/'temp'/('reference_conversion_'+uuid.uuid4().hex);work.mkdir(parents=True)
    try:
        for fmt in ('L8','ARGB8','DXT1','DXT3','DXT5','RGBA16F'):
            for swizzle in (False,True):
                for shape in ((8,4,3,False),(5,7,3,False),(8,8,4,True)):
                    label=fmt+str(swizzle)+'_'+str(shape[0])+'_'+str(shape[3])
                    original=texture(fmt,*shape);source=work/(label+'.dds');source.write_bytes(original)
                    native=work/(label+'.gtf')
                    external_converters.convert('dds2gtf',source,native,override=ROOT/'tools/dds2gtf.exe',swizzle=swizzle)
                    builtin=to_gtf(original,swizzle)
                    assert gtf.parse(native.read_bytes())[1]==gtf.parse(builtin)[1],label
                    assert to_dds(native.read_bytes())[128:]==original[128:],label
                    output=work/(label+'_reverse.dds')
                    (work/(label+'_builtin.gtf')).write_bytes(builtin)
                    external_converters.convert('gtf2dds',work/(label+'_builtin.gtf'),output,override=ROOT/'tools/gtf2dds.exe')
                    assert output.read_bytes()[128:]==original[128:],label
    finally:shutil.rmtree(work)
