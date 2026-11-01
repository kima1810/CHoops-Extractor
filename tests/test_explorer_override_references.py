from types import SimpleNamespace

import pytest
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QPushButton, QTreeWidgetItem
from choops_py.archive.catalog import catalog, record_references
from choops_py.archive.hash_names import hash_name
from choops_py.studio.app import Window, set_rows


def model():
    return SimpleNamespace(rows={
        'teams':[dict(index=0,school_name='Alpha',asset_id=999,uniform_owner_id=7,
                      menu_logo_id=3,arena_index=0,roster_slots=[0],home_shoe_texture='shoe_0.iff')],
        'arenas':[dict(arena_code='258')],
        'uniforms':[dict(team_asset_id=7,uniform_asset_id=258,variant_code=i,jersey_shape_code=1) for i in range(5)],
        'players':[dict(index=0,display_name='Player One',home_shoe_texture='shoe_1.iff')],
        'conferences':[dict(index=0,conference_name='Conference Alpha')]})


@pytest.mark.parametrize('bank','haxyz')
def test_uniform_selection_and_paired_payload_follow_actual_uniform_owner(bank):
    names=[f'selu{bank}258.iff',f'selu{bank}258.cdf',f'selu{bank}999.iff']
    rows=catalog([dict(name=n,hash=hash_name(n),index=i) for i,n in enumerate(names)],model())
    assert 'Alpha' in rows[0]['references'] and 'selection menu' in rows[0]['references']
    assert rows[1]['references']==rows[0]['references']
    assert not rows[2]['references']
    nested=record_references(names[0],[dict(name='jersey'),dict(name=None)],model())
    assert all('Alpha' in r['references'] for r in nested)


def test_other_confirmed_asset_owners_and_no_guessed_portraits():
    names=['cloth_v_reg.iff','cloth_shorts.iff','s258.iff','shoe_1.iff','teamselectlogo.cdf','p999.iff']
    rows=catalog([dict(name=n,hash=hash_name(n),index=i) for i,n in enumerate(names)],model())
    assert all('Alpha' in r['references'] for r in rows[:5])
    assert 'Player One' in rows[3]['references']
    assert 'Conference Alpha' in rows[4]['references']
    assert rows[-1]['references']==''


@pytest.mark.gui
def test_explorer_controls_and_full_reference_panel(qtbot):
    window=Window();qtbot.addWidget(window)
    window.navigate_to('Explorer')
    owner=next(w for w in window.pages.findChildren(QPushButton) if w.text()=='Select overrides folder…')
    assert owner.parent() is window.pages.currentWidget()
    assert owner.parent() is not window.mod_path.parent()
    assert not any(b.text()=='Dry run' for b in window.findChildren(QPushButton))
    text='Alpha '+('long school name '*20)+'; Beta school'
    set_rows(window.explorer,[dict(references=text)],[('references','Roster references')])
    window.explorer.selectionModel().selectionChanged.connect(window.show_explorer_references)
    window.explorer.selectRow(0)
    assert window.explorer.columnWidth(0)>=480
    assert window.explorer_references.toPlainText()==text.replace('; ','\n')
    assert window.explorer.model().index(0,0).data(Qt.ItemDataRole.ToolTipRole)==text.replace('; ','\n')
    window.nested.setColumnCount(4)
    item=QTreeWidgetItem(window.nested,['logo900','TXTR','0','Conference Alpha; Conference Beta'])
    window.nested.setCurrentItem(item)
    assert window.explorer_references.toPlainText()=='Conference Alpha\nConference Beta'


@pytest.mark.gui
def test_worker_result_display_error_is_reported_without_escaping_qt(qtbot,monkeypatch):
    window=Window();qtbot.addWidget(window)
    errors=[]
    monkeypatch.setattr(window,'show_error',lambda message:errors.append(message))
    def broken_display(result):raise TypeError('invalid override record label')
    window.run_job('Inspect override',lambda job:{},broken_display)
    qtbot.waitUntil(lambda:bool(errors) and window.active is None)
    assert errors==['TypeError: invalid override record label']
