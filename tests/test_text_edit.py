import pytest
from choops_py.studio.text_edit import RosterTextDialog

pytestmark = pytest.mark.gui


def test_keyboard_warning_counts_utf16_and_does_not_truncate(qtbot):
    dialog = RosterTextDialog(None, 'Name', 'Advisory', 'A' * 16, 16)
    qtbot.addWidget(dialog)
    assert not dialog.editor.property('keyboardLimitExceeded')
    dialog.editor.setText('A' * 15 + '\U0001f600')
    assert dialog.editor.property('keyboardLimitExceeded')
    assert '17 UTF-16' in dialog.warning.text()
    assert '#F59E0B' in dialog.editor.styleSheet()
    assert dialog.editor.text() == 'A' * 15 + '\U0001f600'
    dialog.editor.setText('Short')
    assert not dialog.editor.styleSheet() and not dialog.warning.text()


def test_unestablished_keyboard_limit_has_no_invented_warning(qtbot):
    dialog = RosterTextDialog(None, 'Conference', 'Unknown', 'A' * 100)
    qtbot.addWidget(dialog)
    assert not dialog.editor.property('keyboardLimitExceeded')
    assert dialog.editor.text() == 'A' * 100


def test_qt_default_character_limit_does_not_truncate_roster_input(qtbot):
    text = 'A' * 40000
    dialog = RosterTextDialog(None, 'Name', 'Descriptor limit', text, 16)
    qtbot.addWidget(dialog)
    assert dialog.editor.text() == text
    assert dialog.editor.property('keyboardLimitExceeded')
