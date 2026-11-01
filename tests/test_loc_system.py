import struct

import pytest

from choops_py.formats.loc_system import add_literal,entries,tokens


def fixture():
    h=bytearray(32);struct.pack_into('>III',h,0,0xe33e3b9c,2,25)
    pool=b'\x01A\0\0'
    h.extend(struct.pack('>II',1,48-36+1))
    h.extend(struct.pack('>II',0xffffffff,0x2468ace0))
    return bytes(h)+pool


def test_isolated_native_literal_keeps_existing_ids_tokens_and_metadata():
    source=fixture();result=add_literal(source,0xc8b40001,'College Hoops\nReborn')
    assert [k for k,p in entries(result)]==[1,0xc8b40001,0xffffffff]
    assert result[56:56+len(source)-48]==source[48:]
    assert tokens(result,1)==tokens(source,1)
    assert result[52:56]==source[44:48]
    with pytest.raises(ValueError,match='Reserved'):tokens(result,0xffffffff)
    encoded=tokens(result,0xc8b40001)
    assert encoded==b''.join(bytes((1,ord(c))) for c in 'College Hoops\nReborn')+bytes(2)
    assert result[:4]==source[:4] and result[8:32]==source[8:32]


def test_unknown_encoding_invalid_ids_and_malformed_tables_are_rejected():
    source=fixture()
    for key in [1,0,2,0xffffffff]:
        with pytest.raises(ValueError):add_literal(source,key,'safe')
    for text in ['','unsafe\0','café','unsafe\t']:
        with pytest.raises(ValueError):add_literal(source,3,text)
    broken=bytearray(source);struct.pack_into('>I',broken,36,0xffffffff)
    with pytest.raises(ValueError,match='pointer'):entries(bytes(broken))
    with pytest.raises(ValueError,match='Unterminated'):entries(source[:-2])
    missing=bytearray(source);struct.pack_into('>I',missing,4,1)
    with pytest.raises(ValueError,match='sentinel'):entries(bytes(missing))
    assert source==fixture()


def test_localization_iff_growth_preserves_old_tokens_and_rejects_old_text_changes():
    from support import iff_fixture
    from choops_py.formats.standard_iff import StandardIFF
    from choops_py.formats.standard_iff_writer import record_blocks,replace_records_expanding
    from choops_py.core.errors import ToolError
    source=fixture();iff=StandardIFF(iff_fixture([source],[(0xa423b39e,[0])],compressed=True))
    changed=add_literal(source,3,'College Hoops\nReborn')
    result=StandardIFF(replace_records_expanding(iff,{0:[changed]}))
    actual=record_blocks(result,result.records[0])[0][3]
    assert actual==changed and tokens(actual,1)==tokens(source,1)
    # Native startup bypasses H7A only when these descriptor lengths agree.
    # The former generic growth path retained two full tables and compressed
    # them; that representation was present in the user's failing build.
    assert result.records[0]['offsets']==[0]
    assert result.blocks[0]['logical_size']==result.blocks[0]['size']==len(changed)
    assert not result.blocks[0]['compressed']
    assert result.raw[result.blocks[0]['start']:result.file_length]==changed
    bad=bytearray(changed);bad[58]=1
    with pytest.raises(ToolError,match='unsafe_localization_growth'):
        replace_records_expanding(iff,{0:[bytes(bad)]})


def test_localization_compaction_rejects_unknown_prefix_and_other_resources():
    from support import iff_fixture
    from choops_py.formats.standard_iff import StandardIFF
    from choops_py.formats.standard_iff_writer import replace_records_expanding
    from choops_py.core.errors import ToolError
    source=fixture();changed=add_literal(source,3,'Reborn')
    prefix=StandardIFF(iff_fixture([b'KEEP'+source],[(0xa423b39e,[4])]))
    with pytest.raises(ToolError,match='offset zero'):
        replace_records_expanding(prefix,{0:[changed]})
    shared=StandardIFF(iff_fixture([source],[(0xa423b39e,[0]),(0x68b693b2,[0])]))
    with pytest.raises(ToolError,match='sole complete block'):
        replace_records_expanding(shared,{0:[changed]})


def test_growth_does_not_enable_unknown_new_token_encodings():
    from choops_py.formats.loc_system import validate_extension
    source=fixture();result=bytearray(add_literal(source,3,'Reborn'))
    result[dict(entries(bytes(result)))[3]]=2
    with pytest.raises(ValueError,match='unsupported token'):
        validate_extension(source,bytes(result))
