import hashlib
import hmac
import struct

import pytest
from Crypto.Cipher import AES
from Crypto.Hash import CMAC

from choops_py.archive.sdat import SDATReader,SDAT_KEY,WRAP_KEY,WRAP_KEY_V3
from choops_py.archive.usrdir_reader import Archive
from choops_py.archive.hash_names import hash_name
from choops_py.archive.build_io import BankReader
from contextlib import ExitStack


def encrypted(data,version=4):
    wrap_key=WRAP_KEY_V3 if version==3 else WRAP_KEY
    header=bytearray(256);header[:4]=b'NPD\0';struct.pack_into('>I',header,4,version)
    header[64:80]=bytes(range(16));header[96:112]=bytes(range(16,32))
    struct.pack_into('>IIQ',header,128,0x0100003c,256,len(data))
    root=bytes(a^b for a,b in zip(header[96:112],SDAT_KEY))
    mac=CMAC.new(AES.new(wrap_key,AES.MODE_CBC,bytes(16)).decrypt(root),ciphermod=AES);mac.update(header[:160]);header[160:176]=mac.digest()
    result=bytearray(header)
    for i,start in enumerate(range(0,len(data),256)):
        block=data[start:start+256];block+=bytes((-len(block))%16)
        derived=AES.new(root,AES.MODE_ECB).encrypt(header[96:108]+struct.pack('>I',i))
        signing=AES.new(root,AES.MODE_ECB).encrypt(derived)
        signing=AES.new(wrap_key,AES.MODE_CBC,bytes(16)).decrypt(signing)
        key=AES.new(wrap_key,AES.MODE_CBC,bytes(16)).decrypt(derived)
        ciphertext=AES.new(key,AES.MODE_CBC,header[64:80]).encrypt(block)
        digest=hmac.new(signing+bytes(4),ciphertext,hashlib.sha1).digest()
        tail=digest[16:]+bytes(12)
        result+=bytes(a^b for a,b in zip(digest[:16],tail))+tail+ciphertext
    return bytes(result)


@pytest.mark.parametrize('version',[3,4])
def test_authenticated_sdat_random_reads_cross_blocks_and_corruption(tmp_path,version):
    data=bytes(range(251))*20;path=tmp_path/'0A.SDAT';encoded=encrypted(data,version);path.write_bytes(encoded)
    with SDATReader(path) as stream:
        assert stream.read(7)==data[:7]
        stream.seek(240);assert stream.read(550)==data[240:790]
        stream.seek(-3,2);assert stream.read(99)==data[-3:]
        stream.seek(0);assert stream.read()==data
        assert len(stream.cache)<=8
    damaged=bytearray(encoded);damaged[300]^=1;path.write_bytes(damaged)
    with SDATReader(path) as stream:
        with pytest.raises(ValueError,match='authentication'):stream.read(3)
    damaged=bytearray(encoded);damaged[256]^=1;path.write_bytes(damaged)
    with SDATReader(path) as stream:
        with pytest.raises(ValueError,match='authentication'):stream.read(3)
    damaged=bytearray(encoded);damaged[64]^=1;path.write_bytes(damaged)
    with pytest.raises(ValueError,match='header authentication'):SDATReader(path)
    path.write_bytes(encoded[:-80])
    with pytest.raises(ValueError,match='Truncated'):SDATReader(path)


@pytest.mark.parametrize('version',[3,4])
def test_extended_archive_mixed_banks_stream_exactly_and_block_writes(tmp_path,version):
    directory=tmp_path/'PS3_GAME/USRDIR';directory.mkdir(parents=True)
    header=bytearray(4096);struct.pack_into('>6I',header,0,0xaa00b3bf,2048,2,0,1,0)
    for i,name in enumerate(('0A','DVD:1A')):
        struct.pack_into('>II',header,24+i*72,2,0);name=name.encode('utf-16-be');header[32+i*72:32+i*72+len(name)]=name
    struct.pack_into('>QII',header,168,3000,hash_name('roster.iff'),1)
    first=bytes(header);second=b'Z'*4096
    (directory/'0A.SDAT').write_bytes(encrypted(first,version));(directory/'1A').write_bytes(second)
    archive=Archive(tmp_path)
    expected=first[2048:]+second[:952]
    assert archive.descriptor_stride==72 and archive.read_only
    assert archive.read(archive.entries[0])==expected
    assert b''.join(archive.chunks(archive.entries[0],257))==expected
    with ExitStack() as stack:assert BankReader(archive,stack).read(2048,3000)==expected
    with pytest.raises(ValueError,match='extraction and previews only'):archive.require_writable()
    from choops_py.archive.build_copy import preflight
    with pytest.raises(ValueError,match='extraction and previews only'):preflight(tmp_path,tmp_path/'missing_mod')
    mod=tmp_path/'preview_mod';mod.mkdir();(mod/'overrides.json').write_text('[]',encoding='utf8')
    checked,patches=preflight(tmp_path,mod,for_build=False)
    assert checked.read_only and not patches


@pytest.mark.parametrize('version,flags',[(2,0x0100003c),(5,0x0100003c),(3,0x0100003d),(3,0x8100003c)])
def test_other_sdat_versions_compression_and_debug_remain_blocked(tmp_path,version,flags):
    path=tmp_path/'0A.SDAT';data=bytearray(encrypted(b'opaque fixture',3))
    struct.pack_into('>I',data,4,version);struct.pack_into('>I',data,128,flags);path.write_bytes(data)
    with pytest.raises(ValueError,match='Unsupported SDAT version/flags'):
        SDATReader(path)
