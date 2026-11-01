"""Recruit diagnostics stay read-only and cannot become a save-transfer workflow."""

from types import SimpleNamespace

import pytest
from test_recruit_pool import pool_fixture

pytestmark = pytest.mark.gui


def diagnostics(qtbot, payload=None):
    from PySide6.QtWidgets import QWidget

    from choops_py.studio.legacy_recruiting import RecruitingDiagnostics

    owner = QWidget()
    qtbot.addWidget(owner)
    raw = pool_fixture()[0] if payload is None else payload
    owner.roster = SimpleNamespace(data=bytearray(raw), edits=[], history=[])
    dialog = RecruitingDiagnostics(owner, owner.roster)
    qtbot.addWidget(dialog)
    return owner, dialog


def test_metadata_preferences_and_filtering_leave_all_source_bytes_untouched(qtbot):
    owner, dialog = diagnostics(qtbot)
    before = bytes(owner.roster.data)
    dialog.display(dialog.inspect(None))
    assert dialog.view.model().rowCount() == 1
    assert "3 reserved records" in dialog.status.text()
    assert "2 blank" in dialog.status.text()
    assert "not certified" in dialog.status.text()
    assert "Recruit slot 1" in dialog.details.toPlainText()
    assert "weight 1.00" in dialog.details.toPlainText()
    assert "history continuity" in dialog.status.text()
    dialog.search.setText("not a recruit")
    assert dialog.view.model().rowCount() == 0
    assert dialog.details.toPlainText() == ""
    dialog.search.clear()
    assert dialog.view.model().rowCount() == 1
    assert bytes(owner.roster.data) == before
    assert owner.roster.edits == [] and owner.roster.history == []


def test_unknown_preferences_are_unresolved_and_ordinary_rosters_fail_gracefully(qtbot):
    import struct

    data, start = pool_fixture()
    struct.pack_into(">I", data, start + 0xD8 + 0x40, (15 << 21) | (127 << 7))
    _, dialog = diagnostics(qtbot, data)
    dialog.display(dialog.inspect(None))
    assert "Uninitialized profile" in dialog.details.toPlainText()
    assert "unestablished_class_code" in dialog.details.toPlainText()
    _, invalid = diagnostics(qtbot, bytes(0xB0))
    invalid.display(invalid.inspect(None))
    assert "Recruiting records unavailable" in invalid.status.text()
    assert invalid.view.model() is None


@pytest.mark.parametrize("change", ["new_source", "changed_bytes", "closed"])
def test_delayed_worker_results_cannot_populate_changed_or_closed_views(qtbot, change):
    owner, dialog = diagnostics(qtbot)
    report = dialog.inspect(None)
    if change == "new_source":
        owner.roster = SimpleNamespace(data=bytearray(dialog.payload))
    elif change == "changed_bytes":
        owner.roster.data[-1] ^= 1
    else:
        dialog.mark_closed()
    dialog.display(report)
    assert dialog.view.model() is None
    if change != "closed":
        assert "source roster changed" in dialog.status.text()


def test_editor_button_inspects_without_exposing_transfer_mutations(qtbot, monkeypatch):
    from PySide6.QtWidgets import QPushButton
    from support import roster_fixture

    from choops_py.studio.app import Window

    window = Window()
    qtbot.addWidget(window)
    model = roster_fixture()
    window.display_roster(model)
    before = bytes(model.data)
    monkeypatch.setattr(
        window, "run_job", lambda _label, work, display: display(work(None))
    )
    button = next(
        b
        for b in window.findChildren(QPushButton)
        if b.text() == "Recruiting diagnostics…"
    )
    button.click()
    dialog = window.recruiting_diagnostics
    assert "Recruiting records unavailable" in dialog.status.text()
    assert bytes(model.data) == before and model.edits == []
    # No transfer, signing, applying or saving controls exist in the diagnostic view.
    assert not dialog.findChildren(QPushButton)
    window.display_roster(model)
    assert dialog.closed
