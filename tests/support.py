import struct
import shutil
import unittest
import uuid
from pathlib import Path
from choops_py.archive.manifests import OUTPUT,safe_output
from choops_py.roster.adapters import load_bytes
from choops_py.roster.editor_model import EditorModel
class WorkspaceTest(unittest.TestCase):
    def setUp(self):
        self.work=OUTPUT/'temp'/('unittest_'+uuid.uuid4().hex);self.work.mkdir(parents=True)
        self.builds=[]
    def tearDown(self):
        for p in self.builds+[self.work]:
            if p.exists():shutil.rmtree(safe_output(p))
    def build_path(self):
        p=OUTPUT/'builds'/('unittest_'+uuid.uuid4().hex);self.builds.append(p);return p

def literal(data,shift=8):
    body=b''.join(b'\0'+data[i:i+8] for i in range(0,len(data),8))
    return struct.pack('>5I',0x0e4837c3,len(data),20+len(body),7,shift)+body

def iff_fixture(blocks=None,records=None,compressed=False,padding=0):
    blocks=blocks or [b'abcd'];records=records or [(0x5c369069,[0])]
    bc=len(blocks);fc=len(records);size=32+bc*32+fc*4+sum(12+4*len(offsets) for _,offsets in records)
    stored=[literal(b) if compressed else b for b in blocks];end=size+sum(map(len,stored))
    header=bytearray(struct.pack('>8I',0xff3bef94,size,end,0,bc,13,fc,bc*32+5));start=size
    for logical,data in zip(blocks,stored):header.extend(struct.pack('>8I',1,1,16,len(logical),7,start,len(data),0));start+=len(data)
    pointer=len(header);recpos=pointer+4*fc
    for i,(_,offsets) in enumerate(records):header.extend(struct.pack('>I',recpos-(pointer+i*4)+1));recpos+=12+4*len(offsets)
    for i,(typ,offsets) in enumerate(records):header.extend(struct.pack('>3I',i+1,typ,len(offsets))+b''.join(struct.pack('>I',x) for x in offsets))
    return bytes(header)+b''.join(stored)+b'\0'*padding

def txtr_fixture(format=0xa1,width=4,height=4,split=False):
    head=bytearray(176);head[0x58:0x5c]=bytes([format,1,2,0]);struct.pack_into('>HHH',head,0x60,width,height,1);struct.pack_into('>I',head,0x68,width if format==0xa1 else 0)
    from choops_py.texture_tools.dds import FORMATS,image_size
    size=image_size(width,height,FORMATS[format&0x9f]);struct.pack_into('>II',head,0xa4,13,size)
    image=bytes(i%256 for i in range(size))
    return [bytes(head),image+b'KEEP'] if split else [bytes(head)+image+b'KEEP']

def pair_fixture():
    iff=bytearray(180)
    def u(off,val):struct.pack_into('>I',iff,off,val)
    u(0,0xf0985030);u(4,180);u(16,1);u(24,1);u(32,76-32+1);u(36,48-36+1)
    iff[48:60]='x.cdf\0'.encode('utf-16-be');u(76,140-76+1);u(104,120-104+1)
    for off,val in zip(range(120,140,4),[1,0x1aedda1f,2,0,0]):u(off,val)
    for off,val in zip(range(140,156,4),[0,4,4,4]):u(off,val)
    return bytes(iff),b'HEADdataTAIL'

def game_fixture(path,payload):
    from choops_py.archive.hash_names import hash_name
    usr=path/'PS3_GAME'/'USRDIR';usr.mkdir(parents=True);data=bytearray(4096)
    struct.pack_into('>6I',data,0,0xaa00b3bf,2048,1,0,1,0);struct.pack_into('>II8s',data,24,2,0,'0A\0\0'.encode('utf-16-be'));struct.pack_into('>4I',data,40,hash_name('ua000.iff'),1,0,len(payload));data[2048:2048+len(payload)]=payload;(usr/'0A').write_bytes(data);(path/'PS3_DISC.SFB').write_bytes(b'disc metadata')
    return path

def roster_fixture():
    tables={'players':(0x40,2,308),'arenas':(0x400,2,28),'teams':(0x500,2,704),'coaches':(0xb00,2,44)};raw=bytearray(4096);heap=0xc00
    for i in range(2):
        off=0x40+i*308
        for rel,text in [(0x10,['Lee','May'][i]),(0x14,['Ana','Bob'][i])]:
            value=text.encode('utf-16-le')+b'\0\0';struct.pack_into('>i',raw,off+rel,heap-(off+rel));raw[heap:heap+len(value)]=value;heap+=len(value)
        struct.pack_into('>H',raw,off+0x1a,10+i);raw[off+0x3a]=72;raw[off+0x3b]=i
        team=0x500+i*704
        for rel in (0x18c,0x190,0x194):struct.pack_into('>H',raw,team+rel,i)
        struct.pack_into('>H',raw,team+0x18e,i)
    return EditorModel(load_bytes(bytes(raw)),tables)
