"""Review-first CSV and roster comparison controls."""

from pathlib import Path
from PySide6.QtCore import Qt, QAbstractTableModel, QModelIndex, QSortFilterProxyModel
from PySide6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QTableView, QLineEdit, QFileDialog, QMessageBox
from ..roster import bulk
from ..roster.editor_model import EditorModel
from ..roster.schema import ENUM_CHOICES,RATING_NAMES,TENDENCY_NAMES,PALETTE_HINTS
from ..roster.presentation import height_text


def field_label(change):
    field,slot=change['field'],change['slot']
    if field=='attribute_ratings':return RATING_NAMES[slot]
    if field=='shot_tendencies':return TENDENCY_NAMES[slot]+' tendency'
    if field=='palette_colors':return f"Palette {slot}: {PALETTE_HINTS.get(slot,'unresolved role')}"
    return field.replace('_',' ').title()


def value_label(change,key):
    value=change[key];field=change['field']
    if field=='height_inches':return height_text(value)
    if field=='weight_lbs':return str(value)+' lb'
    return str(ENUM_CHOICES.get(field,{}).get(value,value))


class ChangeTable(QAbstractTableModel):
    """Keep bulk edits as data, rather than allocating a widget per cell."""
    headers = ("School / record", "Field", "Current", "Incoming")

    def __init__(self, changes, parent=None):
        super().__init__(parent)
        self.changes = changes
        self.checked = set()

    def rowCount(self, parent=QModelIndex()):
        return 0 if parent.isValid() else len(self.changes)

    def columnCount(self, parent=QModelIndex()):
        return 0 if parent.isValid() else 4

    def headerData(self, section, orientation, role=Qt.ItemDataRole.DisplayRole):
        if role == Qt.ItemDataRole.DisplayRole and orientation == Qt.Orientation.Horizontal:
            return self.headers[section]
        return super().headerData(section, orientation, role)

    def data(self, index, role=Qt.ItemDataRole.DisplayRole):
        if not index.isValid():
            return None
        row, column = index.row(), index.column()
        if role == Qt.ItemDataRole.CheckStateRole and column == 0:
            return Qt.CheckState.Checked if row in self.checked else Qt.CheckState.Unchecked
        if role == Qt.ItemDataRole.DisplayRole:
            change = self.changes[row]
            if column == 0:
                return change.get("school", "") + " / " + change["record"]
            if column == 1:
                return field_label(change)
            return value_label(change, "old" if column == 2 else "value")
        return None

    def flags(self, index):
        flags = super().flags(index)
        return flags | Qt.ItemFlag.ItemIsUserCheckable if index.column() == 0 else flags

    def setData(self, index, value, role=Qt.ItemDataRole.EditRole):
        if not index.isValid() or index.column() != 0 or role != Qt.ItemDataRole.CheckStateRole:
            return False
        if value in (Qt.CheckState.Checked, Qt.CheckState.Checked.value):
            self.checked.add(index.row())
        else:
            self.checked.discard(index.row())
        self.dataChanged.emit(index, index, [Qt.ItemDataRole.CheckStateRole])
        return True

    def mark(self, rows, state):
        rows = set(rows)
        if state == Qt.CheckState.Checked:
            self.checked.update(rows)
        else:
            self.checked.difference_update(rows)
        if rows:
            self.dataChanged.emit(self.index(min(rows), 0), self.index(max(rows), 0), [Qt.ItemDataRole.CheckStateRole])


class ChangeReview(QDialog):
    def __init__(self, owner, changes, unmatched=()):
        super().__init__(owner)
        self.owner, self.changes = owner, changes
        self.setWindowTitle("Review roster changes")
        self.resize(950, 550)
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel(f"{len(changes)} compatible changes; {len(unmatched)} missing/ambiguous matches. Check fields to import."))
        search = QLineEdit(); search.setPlaceholderText("Filter by school, player or field")
        layout.addWidget(search)
        self.table_model = ChangeTable(changes, self)
        self.proxy = QSortFilterProxyModel(self)
        self.proxy.setSourceModel(self.table_model)
        self.proxy.setFilterKeyColumn(-1)
        self.proxy.setFilterCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        self.tree = QTableView(); self.tree.setModel(self.proxy)
        self.tree.setSortingEnabled(True)
        self.tree.setWordWrap(False)
        layout.addWidget(self.tree)
        for column, width in enumerate((330, 230, 160, 160)):
            self.tree.setColumnWidth(column, width)
        search.textChanged.connect(self.filter)
        actions = QHBoxLayout()
        for caption, callback in (("Select visible", lambda: self.mark(Qt.CheckState.Checked)), ("Clear visible", lambda: self.mark(Qt.CheckState.Unchecked)), ("Import selected", self.apply)):
            button = QPushButton(caption); button.clicked.connect(callback); actions.addWidget(button)
        layout.addLayout(actions)
        if unmatched:
            note=QLabel("Missing or ambiguous records are excluded. Player IDs/names and school ownership must match uniquely.")
            note.setToolTip("\n".join(unmatched[:100]));layout.addWidget(note)

    def filter(self, text):
        self.proxy.setFilterFixedString(text)

    def mark(self, state):
        rows = (self.proxy.mapToSource(self.proxy.index(i, 0)).row() for i in range(self.proxy.rowCount()))
        self.table_model.mark(rows, state)

    def apply(self):
        selected=[self.changes[i] for i in sorted(self.table_model.checked)]
        if not selected:return
        model=self.owner.roster
        self.owner.run_job("Import selected roster edits",lambda job: (bulk.apply_changes(model,selected),model)[1],self.owner.display_roster)
        self.accept()


def export_csv(owner):
    if not owner.roster or owner.active:return
    path,_=QFileDialog.getSaveFileName(owner,"Export editable roster CSV","roster.csv","CSV (*.csv)")
    if path:
        try:Path(path).write_text(bulk.export_csv(owner.roster),encoding="utf-8-sig",newline="")
        except (ValueError,OSError) as error:QMessageBox.warning(owner,"CSV export failed",str(error))


def import_csv(owner):
    if not owner.roster or owner.active:return
    path,_=QFileDialog.getOpenFileName(owner,"Import edited roster CSV","","CSV (*.csv)")
    if path:
        def prepare(job):return bulk.csv_changes(owner.roster,Path(path).read_text(encoding="utf-8-sig"))
        owner.run_job("Check CSV changes",prepare,lambda changes:ChangeReview(owner,changes).exec())


def compare_roster(owner):
    if not owner.roster or owner.active:return
    path,_=QFileDialog.getOpenFileName(owner,"Compare another roster","","Roster files (*)")
    if path:
        owner.run_job("Compare roster",lambda job:bulk.compare(owner.roster,EditorModel.open(path)),lambda result:ChangeReview(owner,result["changes"],result["unmatched"]).exec())
