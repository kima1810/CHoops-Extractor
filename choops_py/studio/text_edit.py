"""Growing roster text with advisory game-keyboard warnings."""
from PySide6.QtWidgets import QDialog, QDialogButtonBox, QLabel, QLineEdit, QVBoxLayout


class RosterTextDialog(QDialog):
    def __init__(self, parent, title, hint, text, keyboard_limit=None):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.keyboard_limit = keyboard_limit
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel(hint))
        self.editor = QLineEdit(text)
        # Qt's default 32,767 is not the game's ceiling. Keep the full input;
        # backend checks the traced descriptor limit without silent truncation.
        self.editor.setMaxLength(0x7FFFFFFF)
        self.editor.setText(text)
        layout.addWidget(self.editor)
        self.warning = QLabel()
        self.warning.setWordWrap(True)
        layout.addWidget(self.warning)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        self.editor.textChanged.connect(self.update_warning)
        self.update_warning()

    def update_warning(self):
        units = len(self.editor.text().encode('utf-16-le', errors='surrogatepass')) // 2
        exceeded = self.keyboard_limit is not None and units > self.keyboard_limit
        self.editor.setProperty('keyboardLimitExceeded', exceeded)
        self.editor.setStyleSheet('QLineEdit { border: 2px solid #F59E0B; }' if exceeded else '')
        self.warning.setText(
            f'{units} UTF-16 units exceeds the game keyboard limit of {self.keyboard_limit}. '
            'This edit is allowed; the engine display limit is not established.' if exceeded else '')


def edit_roster_text(parent, model, table, field, title, text):
    dialog = RosterTextDialog(parent, title, model.text_hint(table, field), text,
                              model.text_entry_capacity(table, field))
    accepted = dialog.exec() == QDialog.DialogCode.Accepted
    return dialog.editor.text(), accepted
