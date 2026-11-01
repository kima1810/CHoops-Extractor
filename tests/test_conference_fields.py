"""Conference scalar writes preserve all unrelated bytes and undo exactly."""
import pytest
from test_roster_semantics import header_roster

from choops_py.core.errors import ToolError
from choops_py.roster.adapters import load_bytes
from choops_py.roster.editor_model import EditorModel
from choops_py.roster.schema import CONFERENCE_SCALARS, EDITABLE

pytestmark = pytest.mark.unit


@pytest.mark.parametrize('field', [f for f in CONFERENCE_SCALARS if f in EDITABLE['conferences']])
def test_conference_scalar_preserves_neighbors_and_reopens(field):
    data, starts = header_roster()
    model = EditorModel(load_bytes(bytes(data)))
    before = bytes(model.data)
    relative, size = CONFERENCE_SCALARS[field]
    value = 0x1234 if size == 2 else 0xab
    model.edit('conferences', 0, field, value)
    offset = starts['conferences'] + relative
    expected = bytearray(before)
    expected[offset:offset + size] = value.to_bytes(size, 'big')
    assert bytes(model.data) == bytes(expected)
    assert model.validate()['valid']
    reopened = EditorModel(load_bytes(bytes(model.data)))
    assert reopened.rows['conferences'][0][field] == value
    model.undo()
    assert bytes(model.data) == before


@pytest.mark.parametrize('field', [f for f in CONFERENCE_SCALARS if f in EDITABLE['conferences']])
@pytest.mark.parametrize('overflow', [False, True])
def test_conference_bounds_reject_without_mutation(field, overflow):
    data, _ = header_roster()
    model = EditorModel(load_bytes(bytes(data)))
    before = bytes(model.data)
    size = CONFERENCE_SCALARS[field][1]
    with pytest.raises(ToolError) as error:
        model.edit('conferences', 0, field, 1 << (size * 8) if overflow else -1)
    assert error.value.code == 'conference_value_out_of_range'
    assert bytes(model.data) == before
    assert not model.history
