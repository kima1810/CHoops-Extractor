import pytest
from support import roster_fixture
from choops_py.roster.appearance import FIELDS
from choops_py.roster.schema import PROPERTY_FIELDS,ENUM_CHOICES
from choops_py.core.errors import ToolError

pytestmark=pytest.mark.unit

@pytest.mark.parametrize('field',FIELDS,ids=[f['name'] for f in FIELDS])
def test_localized_options_change_only_their_packed_field_and_undo(field):
    model=roster_fixture();key=PROPERTY_FIELDS[field['name']]
    start=model.row_offset('players',0)+field['offset'];size=field['size']
    model.data[start:start+size]=b'\xa5'*size;model.reload();original=bytes(model.data)
    selected=len(field['options'])-1
    model.edit('players',0,key,selected)
    before=int.from_bytes(original[start:start+size],'big');after=int.from_bytes(model.data[start:start+size],'big')
    assert (before^after)&~(((1<<field['bits'])-1)<<field['shift'])==0
    assert model.data[:start]==original[:start] and model.data[start+size:]==original[start+size:]
    assert model.rows['players'][0][key]==selected
    assert model.rows['players'][0]['properties'][field['name']]==selected
    assert ENUM_CHOICES[key][selected]==field['options'][selected]
    with pytest.raises(ToolError):model.edit('players',0,key,len(field['options']))
    model.undo();assert bytes(model.data)==original
