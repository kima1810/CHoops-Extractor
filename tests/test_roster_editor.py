import pytest
pytestmark = pytest.mark.unit
import struct
from support import WorkspaceTest,roster_fixture,iff_fixture
from choops_py.roster.adapters import load_bytes
from choops_py.roster.editor_model import EditorModel
from choops_py.roster.workflow import save_model
from choops_py.core.errors import ToolError
class RosterTests(WorkspaceTest):
    def test_decode_safe_fields_unknown_bytes_and_undo(self):
        m=roster_fixture();self.assertTrue(m.validate()['valid']);self.assertEqual(m.rows['players'][0]['first_name'],'Ana');before=bytes(m.data)
        m.edit('players',0,'jersey_number',23);m.edit('players',0,'height_inches',75);m.edit('players',0,'position_code',4)
        self.assertEqual(m.rows['players'][0]['jersey_number'],23);self.assertEqual(m.rows['players'][0]['position'],'C');self.assertEqual(m.data[0x40+0x18:0x40+0x1a],before[0x40+0x18:0x40+0x1a])
        m.undo();self.assertEqual(m.rows['players'][0]['position_code'],0);m.revert();self.assertEqual(bytes(m.data),before)
    def test_same_length_name_and_invalid_edit(self):
        m=roster_fixture();m.edit('players',0,'first_name','Ann');self.assertEqual(m.rows['players'][0]['first_name'],'Ann')
        m.edit('players',0,'first_name','Alex');self.assertEqual(m.rows['players'][0]['first_name'],'Alex')
        m.edit('players',0,'first_name','A'*17);self.assertEqual(m.rows['players'][0]['first_name'],'A'*17)
        with self.assertRaises(ToolError):m.edit('players',0,'first_name','A\0B')
        with self.assertRaises(ToolError):m.edit('players',0,'position_code',8)
        with self.assertRaises(ToolError):m.edit('players',0,'skin_tone',1)
    def test_shared_string_and_invalid_pointer_validation(self):
        m=roster_fixture();target=0x40+0x14+struct.unpack_from('>i',m.data,0x40+0x14)[0];field=0x40+308+0x14;struct.pack_into('>i',m.data,field,target-field);m.reload()
        m.edit('players',0,'first_name','Ann');self.assertEqual(m.rows['players'][1]['first_name'],'Ana')
        struct.pack_into('>i',m.data,0x40+0x10,0x7fffffff);self.assertFalse(m.validate()['valid'])
    def test_team_assignments_and_reference_bias(self):
        m=roster_fixture();m.edit('teams',0,'roster_slots',1,slot=0);self.assertEqual(m.rows['teams'][0]['roster_slots'][0],1)
        pos=0x500+0x6c;self.assertEqual(pos+struct.unpack_from('>i',m.data,pos)[0],0x40+308+0x11)
        m.edit('teams',0,'arena_index',1);m.edit('teams',0,'coach_index',1);m.edit('teams',0,'rival1_index',1);m.edit('teams',0,'asset_id',1)
        self.assertEqual(m.rows['teams'][0]['arena_index'],1);self.assertEqual([struct.unpack_from('>H',m.data,0x500+i)[0] for i in (0x18c,0x190,0x194)],[1,1,1])
        with self.assertRaises(ToolError):m.edit('teams',0,'roster_slots',9,slot=0)
    def test_source_wrapper_preservation(self):
        m=roster_fixture();payload=m.original
        sources=[load_bytes(payload),load_bytes(struct.pack('>I',len(payload))+payload),load_bytes(iff_fixture([payload],[(0xc61649b2,[0])],compressed=True,padding=128))]
        for i,source in enumerate(sources):
            model=EditorModel(source,m.tables);model.edit('players',0,'jersey_number',24);out=self.work/f'roster{i}'
            save_model(model,out);loaded=load_bytes(out.read_bytes());self.assertEqual(loaded.kind,source.kind);self.assertEqual(loaded.payload,bytes(model.data));self.assertEqual(source.original,sources[i].original)
    def test_patch_requires_matching_source(self):
        m=roster_fixture()
        with self.assertRaises(ToolError):m.apply_document({'source_sha256':'wrong','edits':[]})
    def test_patch_is_atomic(self):
        m=roster_fixture();before=bytes(m.data)
        with self.assertRaises(ToolError):m.apply_document({'source_sha256':m.document()['source_sha256'],'edits':[
            {'table':'players','index':0,'field':'jersey_number','value':24},
            {'table':'players','index':0,'field':'position','value':99}]})
        self.assertEqual(bytes(m.data),before);self.assertEqual(m.edits,[]);self.assertEqual(m.history,[])
    def test_overlapping_string_storage_is_blocked(self):
        m=roster_fixture();field=0x40+0x14;target=field+struct.unpack_from('>i',m.data,field)[0]
        other=0x40+308+0x14;struct.pack_into('>i',m.data,other,target+2-other);m.reload();before=bytes(m.data)
        m.edit('players',1,'first_name','XY')
        self.assertEqual(m.rows['players'][0]['first_name'],'Ana')
        self.assertEqual(m.rows['players'][1]['first_name'],'XY')
        self.assertEqual(m.data[target:target+8],before[target:target+8])

    def test_preexisting_bad_string_allows_rating_edit_and_save_unchanged(self):
        original=roster_fixture();data=bytearray(original.original)
        field=0x40+0x14;target=field+struct.unpack_from('>i',data,field)[0]
        data[target:target+2]=b'\x01\0'
        model=EditorModel(load_bytes(bytes(data)),original.tables)
        self.assertTrue(model.validate()['preserved_source_string_issues'])
        model.edit('players',1,'attribute_ratings',87,slot=2)
        self.assertEqual(model.data[target:target+2],b'\x01\0')
        report=save_model(model,self.work/'ratings.rost')
        self.assertTrue(report['validation']['valid'])
        self.assertTrue(report['validation']['preserved_source_string_issues'])
        # Newly changed invalid string data remains fatal.
        model.data[target:target+2]=b'\x02\0'
        self.assertFalse(model.validate()['valid'])

    def test_community_zip_preserves_members_and_exports_game_iff(self):
        import io,zipfile
        from choops_py.roster.workflow import export_game_roster
        original=roster_fixture();payload=bytearray(original.original)
        field=0x40+0x14;target=field+struct.unpack_from('>i',payload,field)[0];payload[target:target+2]=b'\x19\0'
        data=io.BytesIO()
        with zipfile.ZipFile(data,'w') as archive:
            archive.writestr('Community roster/USERDATA',struct.pack('>I',len(payload))+payload)
            archive.writestr('Community roster/ICON0.PNG',b'ICON unchanged')
            archive.writestr('Community roster/PARAM.SFO',b'SFO unchanged')
        model=EditorModel(load_bytes(data.getvalue()),original.tables)
        self.assertIn('\x19',model.rows['players'][0]['first_name'])
        model.edit('players',1,'attribute_ratings',90,slot=3)
        saved=self.work/'community.zip';save_model(model,saved)
        with zipfile.ZipFile(saved) as archive:
            self.assertEqual(archive.read('Community roster/ICON0.PNG'),b'ICON unchanged')
            self.assertEqual(archive.read('Community roster/PARAM.SFO'),b'SFO unchanged')
        base=iff_fixture([original.original],[(0xc61649b2,[0])],compressed=True)
        out=self.work/'roster_english.iff';export_game_roster(model,base,out)
        loaded=load_bytes(out.read_bytes());self.assertEqual(loaded.kind,'standard-iff');self.assertEqual(loaded.payload,bytes(model.data))

    def test_preexisting_out_of_bounds_pointer_is_still_fatal(self):
        original=roster_fixture();data=bytearray(original.original)
        struct.pack_into('>i',data,0x40+0x14,0x7fffffff)
        model=EditorModel(load_bytes(bytes(data)),original.tables)
        self.assertFalse(model.validate()['valid'])
        with self.assertRaises(ToolError):model.edit('players',1,'attribute_ratings',90,slot=3)
