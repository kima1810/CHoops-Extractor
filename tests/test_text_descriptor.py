import pytest
from support import roster_fixture

from choops_py.core.errors import ToolError
from choops_py.roster.text_limits import TEXT_DESCRIPTOR_MAX


def test_shared_formatter_maximum_counts_utf16_units_and_preserves_undo():
    model = roster_fixture()
    before = bytes(model.data)
    text = '\U0001f600' * 32767 + 'A'
    assert len(text.encode('utf-16-le')) // 2 == TEXT_DESCRIPTOR_MAX
    model.edit('players', 0, 'first_name', text)
    assert model.rows['players'][0]['first_name'] == text
    model.undo()
    assert bytes(model.data) == before


def test_formatter_count_overflow_is_blocked_without_mutation():
    model = roster_fixture()
    before = bytes(model.data)
    with pytest.raises(ToolError) as error:
        model.edit('players', 0, 'first_name', 'A' * 65536)
    assert error.value.code == 'roster_text_descriptor_overflow'
    assert bytes(model.data) == before and not model.history and not model.edits
