"""Always-visible player details, ratings and scholarship editor."""

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QComboBox,
    QInputDialog,
    QLabel,
    QMessageBox,
    QPushButton,
    QTabWidget,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
    QApplication,
    QHBoxLayout,
    QStyledItemDelegate,
    QSpinBox,
)
from ..roster.presentation import height_inches, height_text
from ..roster.schema import (
    ENUM_CHOICES,
    PROPERTY_CHOICES,
    PROPERTY_FIELDS,
    RATING_NAMES,
    TENDENCY_NAMES,
    PLAYER_SCALARS,
)


class RatingDelegate(QStyledItemDelegate):
    def __init__(self, panel):
        super().__init__(panel)
        self.panel=panel

    def createEditor(self,parent,option,index):
        target=index.siblingAtColumn(0).data(Qt.ItemDataRole.UserRole)
        if index.column()!=1 or not target:return None
        box=QSpinBox(parent);box.setRange(35 if target[0]=='attribute_ratings' else 0,99)
        return box

    def setEditorData(self,editor,index):editor.setValue(int(index.data()))

    def setModelData(self,editor,model,index):
        key,slot=index.siblingAtColumn(0).data(Qt.ItemDataRole.UserRole)
        player=self.panel.player_index;value=editor.value()
        QTimer.singleShot(0,lambda:self.panel.apply(key,value,slot) if self.panel.player_index==player else None)


class PlayerDetails(QTabWidget):
    def __init__(self, owner):
        super().__init__(owner)
        self.owner = owner
        self.player_index = None
        self.loading = False
        self.details = QTreeWidget()
        self.details.setHeaderLabels(["Player detail", "Value (double-click to edit)"])
        self.details.itemDoubleClicked.connect(self.edit_item)
        self.addTab(self.details, "Player")
        self.ratings = QTreeWidget()
        self.ratings.setHeaderLabels(["Rating / tendency", "Value"])
        self.ratings.setItemDelegateForColumn(1,RatingDelegate(self))
        ratings_page=QWidget();rating_layout=QVBoxLayout(ratings_page);rating_layout.addWidget(self.ratings)
        actions=QHBoxLayout()
        for caption,callback in (("Copy ratings",self.copy_ratings),("Paste to selected players",self.paste_ratings)):
            control=QPushButton(caption);control.clicked.connect(callback);actions.addWidget(control)
        rating_layout.addLayout(actions)
        self.addTab(ratings_page, "Ratings")
        scholarship = QWidget()
        layout = QVBoxLayout(scholarship)
        layout.addWidget(QLabel("Selected player scholarship status"))
        self.status = QComboBox()
        self.status.setObjectName("scholarshipStatus")
        for value, label in ENUM_CHOICES["scholarship_status"].items():
            self.status.addItem(label, value)
        layout.addWidget(self.status)
        button = QPushButton("Apply scholarship status")
        button.clicked.connect(self.apply_status)
        layout.addWidget(button)
        note = QLabel(
            "Choose Scholarship or Walk-on, then save a roster copy. Legacy recruiting restrictions are not reproduced."
        )
        note.setWordWrap(True)
        layout.addWidget(note)
        layout.addStretch()
        self.addTab(scholarship, "Scholarship")
        from .roster_panels import ShoeTab,JerseyTab
        self.shoes=ShoeTab(owner);self.addTab(self.shoes,'Shoes')
        self.jersey=JerseyTab(owner);self.addTab(self.jersey,'Jersey')
        assignment=QWidget();form=QVBoxLayout(assignment)
        self.school_state=QLabel('Select a player');self.school_state.setWordWrap(True);form.addWidget(self.school_state)
        self.school=QComboBox();self.school.setObjectName('playerSchool');form.addWidget(self.school)
        button=QPushButton('Apply school assignment');button.clicked.connect(self.apply_school);form.addWidget(button)
        note=QLabel('Moves the player between roster slots and updates school counts. Attributes and current shoes are kept. Shared records, full rosters and inconsistent links are blocked.');note.setWordWrap(True);form.addWidget(note);form.addStretch()
        self.addTab(assignment,'School')
        self.setEnabled(False)

    def add(self, tree, label, value, key=None, slot=None):
        item = QTreeWidgetItem(tree, [label, str(value)])
        if key:
            item.setData(0, Qt.ItemDataRole.UserRole, (key, slot))
            if tree is self.ratings:item.setFlags(item.flags()|Qt.ItemFlag.ItemIsEditable)
        else:
            item.setToolTip(1, "Read-only: no confirmed writer for this field")

    def show_player(self, row):
        self.loading = True
        self.details.clear()
        self.ratings.clear()
        self.player_index = row["index"] if row else None
        from .app import selected
        multiple=bool(self.owner.roster and self.owner.roster_views['players'].model() and len(selected(self.owner.roster_views['players']))>1)
        self.setEnabled(row is not None or multiple)
        self.shoes.show_record('players',row);self.jersey.show_record('players',row)
        self.school.clear()
        if row:
            from ..roster.membership import player_schools
            schools=player_schools(self.owner.roster,row['index'])
            self.school.addItem('Unassigned',None)
            for school in self.owner.roster.rows.get('teams',[]):self.school.addItem(school['school_name']+f" [#{school['index']}]",school['index'])
            self.school.setCurrentIndex(max(0,self.school.findData(schools[0] if len(schools)==1 else None)))
            names=[self.owner.roster.rows['teams'][i]['school_name'] for i in schools]
            self.school_state.setText('Current school: '+(', '.join(names) if names else 'Unassigned')+(' — shared record; transfer blocked' if len(schools)>1 else ''))
            for key, label in [
                ("first_name", "First name"),
                ("last_name", "Last name"),
                ("jersey_number", "Number"),
                ("height_inches", "Height"),
                ("position_code", "Position"),
                ("class_code", "Class"),
                ("redshirt_code", "Redshirt"),
                ("redshirt_used", "Redshirt used"),
                ("jump_shot_code", "Jump shot animation"),
            ]:
                value = (
                    height_text(row[key])
                    if key == "height_inches"
                    else ENUM_CHOICES.get(key, {}).get(row[key], row[key])
                )
                self.add(self.details, label, value, key)
            self.add(self.details,'Player ID',row['player_id'])
            for label, value in row["properties"].items():
                key = PROPERTY_FIELDS.get(label) or {
                    "Hand": "hand_code",
                    "Weight": "weight_lbs",
                    "Potential": "potential",
                    "Confidence": "confidence",
                }.get(label)
                options = PROPERTY_CHOICES.get(label, {})
                fallback = (
                    ("None" if value == 0 else f"Style {value}")
                    if any(k in label for k in ("Band", "Pad"))
                    else f"Unmapped option ({value})"
                    if options
                    else value
                )
                text = options.get(value, fallback)
                self.add(self.details, label, text, key)
            self.add(
                self.details,
                "Scholarship",
                ENUM_CHOICES["scholarship_status"][row["scholarship_status"]],
                "scholarship_status",
            )
            for slot, (label, value) in enumerate(
                zip(RATING_NAMES, row["attribute_ratings"])
            ):
                self.add(self.ratings, label, value, "attribute_ratings", slot)
            for slot, (label, value) in enumerate(
                zip(TENDENCY_NAMES, row["shot_tendencies"])
            ):
                self.add(
                    self.ratings, label + " tendency", value, "shot_tendencies", slot
                )
            self.status.setCurrentIndex(self.status.findData(row["scholarship_status"]))
        self.details.resizeColumnToContents(0)
        self.ratings.resizeColumnToContents(0)
        self.loading = False

    def apply(self, key, value, slot=None):
        if self.loading or self.player_index is None or self.owner.active:
            return
        try:
            self.owner.roster.edit("players", self.player_index, key, value, slot)
            self.owner.display_roster(self.owner.roster)
        except ValueError as error:
            QMessageBox.warning(self, "Player edit blocked", str(error))

    def apply_status(self):
        self.apply("scholarship_status", self.status.currentData())

    def copy_ratings(self):
        if self.player_index is None:return
        from ..roster.bulk import rating_document
        QApplication.clipboard().setText(rating_document(self.owner.roster.rows['players'][self.player_index]))

    def paste_ratings(self):
        if not self.owner.roster or self.owner.active:return
        from .app import selected
        from ..roster.bulk import paste_ratings
        indices=[row['index'] for row in selected(self.owner.roster_views['players'])]
        if not indices:return
        text=QApplication.clipboard().text();model=self.owner.roster
        self.owner.run_job('Paste ratings to selected players',lambda job:(paste_ratings(model,indices,text),model)[1],self.owner.display_roster)

    def apply_school(self):
        if self.player_index is None or self.owner.active:return
        try:
            self.owner.roster.move_player_to_school(self.player_index,self.school.currentData())
            self.owner.display_roster(self.owner.roster)
        except ValueError as error:QMessageBox.warning(self,'School assignment blocked',str(error))

    def edit_item(self, item, column):
        target = item.data(0, Qt.ItemDataRole.UserRole)
        if not target or self.player_index is None or self.owner.active:
            return
        key, slot = target
        row = self.owner.roster.rows["players"][self.player_index]
        if key in ENUM_CHOICES:
            options = dict(ENUM_CHOICES[key])
            if row[key] not in options:
                options[row[key]] = f"Unmapped option ({row[key]})"
            captions = list(options.values())
            labels = [
                label
                if captions.count(label) == 1
                else f"{label} (variant {chr(65 + captions[:i].count(label))})"
                for i, label in enumerate(captions)
            ]
            value, ok = QInputDialog.getItem(
                self,
                "Edit " + item.text(0),
                item.text(0),
                labels,
                max(0, list(options).index(row[key]) if row[key] in options else 0),
                False,
            )
            if ok:
                code = list(options)[labels.index(value)]
                if code != row[key]:
                    self.apply(key, code)
        elif key == "height_inches":
            heights=[height_text(n) for n in range(36,101)]
            value, ok = QInputDialog.getItem(
                self, "Edit height", "Feet and inches", heights,row[key]-36,False
            )
            if ok:
                try:
                    self.apply(key, height_inches(value))
                except ValueError as error:
                    QMessageBox.warning(self, "Height edit blocked", str(error))
        elif key in ("first_name", "last_name"):
            from .text_edit import edit_roster_text
            value, ok = edit_roster_text(self, self.owner.roster, 'players', key,
                                        "Edit " + item.text(0), row[key])
            if ok:
                self.apply(key, value)
        elif key=='weight_lbs':
            weights=[str(n)+' lb' for n in range(70,401)]
            value,ok=QInputDialog.getItem(self,'Edit weight','Weight',weights,max(0,row[key]-70),False)
            if ok:self.apply(key,int(value.split()[0]))
        else:
            current = row[key][slot] if slot is not None else row[key]
            value, ok = QInputDialog.getInt(
                self,
                "Edit " + item.text(0),
                item.text(0),
                current,
                PLAYER_SCALARS[key][4] if key in PLAYER_SCALARS else 35 if key == "attribute_ratings" else 0,
                PLAYER_SCALARS[key][5] if key in PLAYER_SCALARS else 99,
            )
            if ok:
                self.apply(key, value, slot)
