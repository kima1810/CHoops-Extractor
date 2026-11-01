import json
from types import SimpleNamespace
import pytest
from choops_py.archive.catalog import catalog
from choops_py.archive.hash_names import hash_name
from choops_py.archive.manifests import digest
from choops_py.studio.preview_source import PreviewArchive
from choops_py.texture_tools.conversion_cache import cached_conversion
from choops_py.studio.build_summary import summary

pytestmark=pytest.mark.unit


def test_catalog_uses_arena_pointer_and_exact_menu_subrecord():
    from choops_py.archive.catalog import record_references
    model=SimpleNamespace(rows={'teams':[dict(school_name='Alpha',asset_id=999,arena_index=0,menu_logo_id=7,uniform_owner_id=1)],'arenas':[dict(arena_code='256')],'uniforms':[]})
    rows=catalog([dict(index=i,hash=hash_name(n),name=n) for i,n in enumerate(('s256.iff','s999.iff'))],model)
    assert 'Alpha' in rows[0]['references'] and rows[1]['references']==''
    records=record_references('teamselectlogo.iff',[dict(name='logo007'),dict(name='logo008')],model)
    assert records[0]['references']=='Alpha' and records[1]['references']==''


def test_scene_identity_follows_name_after_record_reordering():
    from choops_py.studio.services import scene_record_index
    records=[dict(index=0,type='TXTR',name='floor'),dict(index=5,type='SCNE',name='floor'),dict(index=2,type='SCNE',name='arena')]
    assert scene_record_index(records,2,'floor')==5
    with pytest.raises(ValueError,match='missing'):
        scene_record_index(records,2,'cloth')
    records.append(dict(index=6,type='SCNE',name='floor'))
    with pytest.raises(ValueError,match='ambiguous'):
        scene_record_index(records,2,'floor')


def test_cache_reuses_content_rejects_corruption_and_separates_layout(tmp_path):
    calls=[]
    def convert():calls.append(1);return b'converted'
    assert cached_conversion('dds2gtf',b'input',False,convert,tmp_path)==(b'converted',False)
    assert cached_conversion('dds2gtf',b'input',False,convert,tmp_path)==(b'converted',True)
    assert len(calls)==1
    next(tmp_path.glob('*.bin')).write_bytes(b'corrupt')
    assert cached_conversion('dds2gtf',b'input',False,convert,tmp_path)[1] is False
    assert cached_conversion('dds2gtf',b'input',True,convert,tmp_path)[1] is False
    assert len(calls)==3


def test_staged_preview_checks_original_and_override(tmp_path):
    entry=dict(index=0,hash=hash_name('s000.iff'),name='s000.iff',size=4)
    archive=SimpleNamespace(path=tmp_path,entries=[entry],read=lambda e:b'base',chunks=lambda e:iter([b'base']))
    asset=tmp_path/'replacement';asset.write_bytes(b'override')
    (tmp_path/'overrides.json').write_text(json.dumps([dict(archive='s000.iff',kind='archive',subfile=None,path='replacement',sha256=digest(b'override'))]))
    (tmp_path/'source_preconditions.json').write_text(json.dumps(dict(schema=1,entries=[dict(index=0,hash=entry['hash'],sha256=digest(b'base'))])))
    preview=PreviewArchive(archive,tmp_path)
    assert preview.read(entry)==b'override' and b''.join(preview.chunks(entry))==b'override'
    assert entry['size']==4 and preview.entries[0]['size']==8
    asset.write_bytes(b'changed')
    with pytest.raises(ValueError,match='checksum'):preview.read(entry)
    asset.write_bytes(b'override');archive.read=lambda e:b'other'
    with pytest.raises(ValueError,match='changed JB'):preview.read(entry)


def test_categories_and_gui_summary_are_readable():
    rows=catalog([dict(hash=hash_name(n),name=n,index=i) for i,n in enumerate(('s000.iff','uh000.iff','shoe_100_00.iff','teamselectlogo.iff'))])
    assert [r['category'] for r in rows]==['Stadiums','Uniforms','Shoes','Logos']
    text=summary(dict(staged=1,imports=[dict(archive='s000.iff',binary_records=2,dds_imports=[dict(width=64,artwork_resampled=True,cache_hit=True)])]))
    assert '1 cached' in text and '1 resized' in text and 's000.iff' in text
