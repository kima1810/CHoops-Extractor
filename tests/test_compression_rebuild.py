import struct
from choops_py.formats.compression import MAGIC, decode, encode_greedy, encode_like


def literal(data,shift=12):
    body=b''.join(b'\0'+data[i:i+8] for i in range(0,len(data),8))
    return struct.pack('>5I',MAGIC,len(data),20+len(body),123,shift)+body


def test_changed_repetition_is_recompressed_instead_of_literal_inflation():
    baseline=literal(b'A'*8192)
    original=encode_greedy(baseline,b'A'*8192)
    edited=b'ABCD'*(8192//4)
    result=encode_like(original,edited)
    assert decode(result)==edited
    assert len(result)<1200
    assert result[12:20]==original[12:20]
    assert encode_like(original,b'A'*8192)==original


def test_greedy_distance_overlap_and_incompressible_tail():
    for shift in (4,8,12,16):
        data=bytes(range(256))*3+b'ABC'*101+b'last'
        result=encode_greedy(literal(data,shift),data)
        assert decode(result)==data


def test_native_and_python_decoders_agree_on_random_and_overlapping_streams(monkeypatch):
    import random
    from choops_py.formats import native_codec
    rng=random.Random(734)
    cases=[bytes(rng.randrange(256) for _ in range(50000)),b'AB'*50000,b'\0'*150000,bytes(range(256))*300]
    for shift in (4,8,12,16):
        for data in cases:
            encoded=encode_greedy(literal(data,shift),data)
            accelerated=decode(encoded)
            with monkeypatch.context() as context:
                context.setattr(native_codec,'library',lambda:None)
                portable=decode(encoded)
            assert accelerated==portable==data
            assert encoded[12:20]==literal(data,shift)[12:20]


def test_truncated_and_invalid_backreferences_are_rejected_by_both_decoders(monkeypatch):
    import pytest
    from choops_py.formats import native_codec
    from choops_py.core.errors import ToolError
    bad=struct.pack('>5I',MAGIC,10,23,0,8)+bytes([1,0,1])
    for native in (True,False):
        with monkeypatch.context() as context:
            if not native:context.setattr(native_codec,'library',lambda:None)
            with pytest.raises(ToolError):decode(bad)


def test_encoded_backreferences_do_not_overlap_their_source_for_game_compatibility(monkeypatch):
    from choops_py.formats.compression import tokens
    from choops_py.formats import native_codec
    data=b'\0'*120000+b'ABCD'*20000+bytes(range(256))*100
    for native in (True,False):
        with monkeypatch.context() as context:
            if not native:context.setattr(native_codec,'library',lambda:None)
            encoded=encode_greedy(literal(data,13),data)
            assert decode(encoded)==data
            assert all(not distance or length<=distance for _,length,distance,_ in tokens(encoded))
