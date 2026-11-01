import uuid
import struct
import pytest
from pathlib import Path
from support import game_fixture,iff_fixture
from choops_py.archive.manifests import OUTPUT
from choops_py.archive.usrdir_reader import Archive
from choops_py.archive.add_assets import build,plan,meaningful_iff
from choops_py.archive.hash_names import hash_name
from choops_py.roster.uniforms import append_uniform,asset_name
from choops_py.formats.binary import Binary


def test_append_archive_preserves_existing_payload_and_actual_byte_lengths(tmp_path):
    old=iff_fixture([b'old payload'])
    source=game_fixture(tmp_path/'game',old)
    arc=Archive(source)
    before=arc.read(arc.entries[0])
    addition=iff_fixture([b'new payload'])
    output=OUTPUT/'builds'/('asset_test_'+uuid.uuid4().hex)
    report=build(source,{'uy777.iff':addition},output)
    new=Archive(output);by_hash={e['hash']:e for e in new.entries}
    assert new.read(by_hash[hash_name('ua000.iff')])==before
    e=by_hash[hash_name('uy777.iff')]
    assert e['content_size']==len(meaningful_iff(addition))
    assert e['stored_size']==e['content_size']
    assert e['name']=='uy777.iff'
    assert report['source_unchanged'] and not report['runtime_verified']
    assert Archive(source).read(arc.entries[0])==before
    assert [e['hash'] for e in new.entries]==sorted(e['hash'] for e in new.entries)
    with pytest.raises(ValueError):plan(source,{'UA000.iff':addition})


def test_uniform_table_append_preserves_old_addresses_and_unlocks_new_row():
    payload=bytearray(512);start=256
    struct.pack_into('>II',payload,0x70,2,start-0x74+1)
    rows=[((7<<22)|(77<<12)|(1<<8)|35,0x48001000),((7<<22)|(77<<12),0x48002000)]
    for i,row in enumerate(rows):struct.pack_into('>II',payload,start+i*8,*row)
    result=append_uniform(bytes(payload),0,888,3,4)
    b=Binary(result);target=b.relative(0x74)
    assert b.u32(0x70)==3
    assert result[0x78:512]==payload[0x78:]
    assert result[target:target+16]==payload[start:start+16]
    a,c=struct.unpack_from('>II',result,target+16)
    assert (a>>22)&1023==7 and (a>>12)&1023==888 and (a>>8)&7==3
    assert a&127==0 and (c>>27)&7==4
    assert asset_name({'variant_code':3,'uniform_asset_id':888})=='uy888.iff'
    with pytest.raises(ValueError):append_uniform(result,0,889,3)
    with pytest.raises(ValueError):append_uniform(bytes(payload),0,888,5)


def test_first_alternate_and_roster_iff_growth_roundtrip():
    from test_roster_semantics import header_roster
    from choops_py.roster.uniforms import encode_roster_iff
    from choops_py.roster.editor_model import EditorModel
    from choops_py.roster.adapters import load_bytes
    data,starts=header_roster()
    start=starts['uniforms']
    for i,variant in enumerate((0,1)):
        struct.pack_into('>II',data,start+i*8,(3<<22)|(77<<12)|(variant<<8),0x48000000)
    original=iff_fixture([bytes(data)],records=[(0xc61649b2,[0])],compressed=True)
    payload=append_uniform(bytes(data),1,888,2)
    rebuilt=encode_roster_iff(original,payload)
    model=EditorModel(load_bytes(rebuilt))
    linked=[r for r in model.rows['uniforms'] if r['team_asset_id']==3]
    assert [r['variant_code'] for r in linked]==[0,1,2]
    assert linked[-1]['uniform_asset_id']==888 and linked[-1]['unlock_id']==0
    assert bytes(model.data[:0x70])==data[:0x70]
    assert bytes(model.data[0x78:len(data)])==data[0x78:]


def test_expanded_existing_iff_is_relocated_without_changing_other_entries(tmp_path):
    source=game_fixture(tmp_path/'game',iff_fixture([b'small']))
    old=Archive(source);offset=old.entries[0]['offset']
    grown=iff_fixture([b'new roster bytes'*300])
    extra=iff_fixture([b'new alternate'])
    output=OUTPUT/'builds'/('relocation_test_'+uuid.uuid4().hex)
    report=build(source,{'uy777.iff':extra},output,{'ua000.iff':grown})
    new=Archive(output);entry=next(e for e in new.entries if e['name']=='ua000.iff')
    assert entry['offset']!=offset
    assert new.read(entry)[:len(meaningful_iff(grown))]==meaningful_iff(grown)
    assert report['verified_existing_entry_count']==1


def test_insertion_refuses_bad_compressed_payload_and_nonzero_toc_padding(tmp_path):
    original=iff_fixture([b'old'])
    source=game_fixture(tmp_path/'game',original)
    broken=bytearray(iff_fixture([b'new'],compressed=True))
    struct.pack_into('>I',broken,84+4,999)
    with pytest.raises(ValueError):plan(source,{'uy777.iff':bytes(broken)})
    path=source/'PS3_GAME'/'USRDIR'/'0A'
    data=bytearray(path.read_bytes());data[56]=1;path.write_bytes(data)
    with pytest.raises(ValueError):plan(source,{'uy777.iff':original})


def test_large_toc_repack_and_new_split_banks_preserve_source(tmp_path):
    source=game_fixture(tmp_path/'game',iff_fixture([b'old']))
    arc=Archive(source);old=arc.read(arc.entries[0])
    output=OUTPUT/'builds'/('repack_test_'+uuid.uuid4().hex)
    additions={f'uy{i:03d}.iff':iff_fixture([b'new']) for i in range(130)}
    report=build(source,additions,output)
    new=Archive(output)
    assert report['method']=='repack' and len(new.parts)>1
    entry=next(e for e in new.entries if e['name']=='ua000.iff')
    assert new.read(entry)==old and entry['offset']!=arc.entries[0]['offset']
    assert len(new.entries)==131
    assert Archive(source).read(arc.entries[0])==old


def test_alternate_checkboxes_round_trip_preserves_asset_shape_and_unlock():
    from choops_py.roster.uniforms import set_alternate_enabled,disabled_uniforms
    payload=bytearray(512);start=256
    rows=[((46<<22)|(100<<12)|(variant<<8)|95,0xa1234567) for variant in range(5)]
    struct.pack_into('>I',payload,0x70,5);struct.pack_into('>i',payload,0x74,start-0x74+1)
    for index,row in enumerate(rows):struct.pack_into('>II',payload,start+index*8,*row)
    disabled=set_alternate_enabled(bytes(payload),46,3,False)
    b=Binary(disabled);active=list(struct.iter_unpack('>II',b.slice(b.relative(0x74),b.u32(0x70)*8)))
    assert active==rows[:3]+rows[4:]
    assert disabled_uniforms(disabled)==[rows[3]]
    # Restoration also works after saving/reopening the payload.
    enabled=set_alternate_enabled(bytes(disabled),46,3,True)
    b=Binary(enabled)
    assert list(struct.iter_unpack('>II',b.slice(b.relative(0x74),b.u32(0x70)*8)))==rows
    assert disabled_uniforms(enabled)==[]
    assert enabled[:0x70]==payload[:0x70] and enabled[0x78:len(payload)]==payload[0x78:]
    with pytest.raises(ValueError):set_alternate_enabled(enabled,47,2,True)


def test_cdf_logo_clone_and_paired_archive_insertion(tmp_path):
    import zlib
    from choops_py.formats.cdf_backed_iff_writer import clone_texture_record,name_trailer
    from choops_py.formats.cdf_backed_iff import CDFPair
    name='logos.cdf';end=148+len(name.encode('utf-16-be'))+2
    header=bytearray(end)
    struct.pack_into('>10I',header,0,0xf0985030,end,end,0,2,21,1,77,97,113)
    for off,start in ((40,end),(72,end+16)):
        struct.pack_into('>8I',header,off,1,1,16,4,0,start,4,0)
    struct.pack_into('>I',header,104,5)
    struct.pack_into('>5I',header,108,zlib.crc32(b'logo001'),0x5c369069,2,0,0)
    struct.pack_into('>I',header,128,5)
    struct.pack_into('>4I',header,132,0,4,4,4)
    header[148:]=name.encode('utf-16-be')+b'\0\0'
    original=bytes(header)+name_trailer([{'name':'logo001','type':'TXTR'}]);cdf=b'abcdWXYZ'
    new_iff,new_cdf=clone_texture_record(original,cdf,'logo001','logo1000')
    pair=CDFPair(new_iff,new_cdf)
    assert len(pair.records)==2 and new_cdf[:8]==cdf
    new=next(r for r in pair.records if r['name']=='logo1000')
    assert new_cdf[new['header_offset']:new['header_offset']+4]==b'abcd'
    source=game_fixture(tmp_path/'game',iff_fixture())
    output=OUTPUT/'builds'/('cdf_test_'+uuid.uuid4().hex)
    report=build(source,{'logos.iff':new_iff,'logos.cdf':new_cdf},output)
    assert report['source_unchanged']
    archive=Archive(output);by_hash={e['hash']:e for e in archive.entries}
    CDFPair(archive.read(by_hash[hash_name('logos.iff')]),archive.read(by_hash[hash_name('logos.cdf')]))
    with pytest.raises(ValueError,match='both matching'):plan(source,{'logos.cdf':new_cdf})
