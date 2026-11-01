"""Shared selected-record editors, footwear and uniform preview controls."""

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QWidget,
    QTabWidget,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QFormLayout,
    QComboBox,
    QPushButton,
    QLabel,
    QInputDialog,
    QMessageBox,
)
from ..roster.schema import (
    EDITABLE,
    ENUM_CHOICES,
    REFERENCES,
    STRING_FIELDS,
    CONFERENCE_SCALARS,
    JERSEY_SHAPES,
)
from ..roster.shoes import FIELDS, choices, BRANDS, texture_name


def record_name(row):
    return next(
        (
            row.get(key)
            for key in (
                "display_name",
                "school_name",
                "arena_name",
                "coach_name",
                "conference_name",
            )
            if row.get(key)
        ),
        f"Record {row['index']}",
    )


def choose_reference(parent, model, table, current, title, allow_none=True):
    rows = model.rows.get(table, [])
    entries = [(None, "None")] if allow_none else []
    entries += [(r["index"], record_name(r) + f" [#{r['index']}]") for r in rows]
    values = [x[0] for x in entries]
    labels = [x[1] for x in entries]
    if not entries:
        return None, False
    text, ok = QInputDialog.getItem(
        parent,
        title,
        title,
        labels,
        values.index(current) if current in values else 0,
        False,
    )
    return (values[labels.index(text)], True) if ok else (None, False)


class ShoeTab(QWidget):
    def __init__(self, owner):
        super().__init__(owner)
        self.owner = owner
        self.table = None
        self.index = None
        self.loading = False
        form = QFormLayout(self)
        self.widgets = {}
        for key, label in zip(
            FIELDS["players"], ("Brand", "Style", "Home color", "Away color")
        ):
            box = QComboBox()
            box.setObjectName("side_" + key)
            self.widgets[key] = box
            form.addRow(label, box)
        for code, label in BRANDS.items():
            self.widgets["shoe_brand_code"].addItem(label, code)
        self.widgets["shoe_brand_code"].currentIndexChanged.connect(self.refill)
        self.note = QLabel()
        self.note.setWordWrap(True)
        form.addRow(self.note)
        apply = QPushButton("Apply shoes")
        apply.clicked.connect(self.apply)
        form.addRow(apply)
        self.side = QComboBox()
        self.side.addItems(["Home", "Away"])
        form.addRow("Preview", self.side)
        preview = QPushButton("Preview shoes")
        preview.clicked.connect(self.preview)
        form.addRow(preview)
        self.setEnabled(False)

    def show_record(self, table, row):
        self.table = table
        self.index = row["index"] if row else None
        self.setEnabled(row is not None and "shoe_brand_code" in row)
        if not self.isEnabled():
            return
        self.loading = True
        for key, box in self.widgets.items():
            box.setProperty("storedValue", row[key])
            if key != "shoe_brand_code":
                box.blockSignals(True)
                box.clear()
                box.blockSignals(False)
        brand = self.widgets["shoe_brand_code"]
        if brand.findData(row["shoe_brand_code"]) < 0:
            brand.addItem(
                f"Unmapped brand ({row['shoe_brand_code']})", row["shoe_brand_code"]
            )
        brand.setCurrentIndex(brand.findData(row["shoe_brand_code"]))
        self.loading = False
        self.refill()
        self.note.setText(
            "School brand applies to every player on this school roster. Existing compatible player styles/colors are kept; incompatible values use the first supported choice."
            if table == "teams"
            else "Edit this player’s footwear. Other players are unchanged."
        )

    def refill(self):
        if self.loading:
            return
        brand = self.widgets["shoe_brand_code"].currentData()
        for key, box in self.widgets.items():
            if key == "shoe_brand_code":
                continue
            value = (
                box.property("storedValue")
                if box.currentData() is None
                else box.currentData()
            )
            box.blockSignals(True)
            box.clear()
            for code, label in choices(key, brand).items():
                box.addItem(label, code)
            box.setCurrentIndex(max(0, box.findData(value)))
            box.blockSignals(False)

    def apply(self):
        if self.index is None or self.owner.active:
            return
        values = {key: box.currentData() for key, box in self.widgets.items()}
        model = self.owner.roster
        table = self.table
        index = self.index

        def work(job):
            if table == "teams":
                model.edit_school_shoes(index, **values)
            else:
                model.edit_shoes(table, index, **values)
            return model

        self.owner.run_job(
            "Apply shoes / school roster brand", work, self.owner.display_roster
        )

    def preview(self):
        if self.index is None or not self.owner.archive or self.owner.active:
            return self.owner.log("Open a JB folder for shoe previews.")
        values = {key: box.currentData() for key, box in self.widgets.items()}
        name = texture_name(
            values["shoe_brand_code"],
            values["shoe_style_code"],
            values["home_shoe_color_code"]
            if self.side.currentIndex() == 0
            else values["away_shoe_color_code"],
        )
        entry = next(
            (e for e in self.owner.archive.entries if e.get("name") == name), None
        )
        if not entry:
            return self.owner.log(
                "Selected shoe artwork is missing from the loaded JB."
            )
        self.owner.scene_shoes.setCurrentIndex(
            self.owner.scene_shoes.findData(entry["index"])
        )
        self.owner.preview_shoes()


class JerseyTab(QWidget):
    def __init__(self, owner):
        super().__init__(owner)
        self.owner = owner
        form = QFormLayout(self)
        self.uniform = QComboBox()
        form.addRow("Uniform", self.uniform)
        self.neck = QComboBox()
        for code, label in JERSEY_SHAPES.items():
            self.neck.addItem(label, code)
        form.addRow("Neck (preview)", self.neck)
        self.build = QComboBox()
        self.shorts = QComboBox()
        for box in (self.build, self.shorts):
            for code, label in [("thin", "Thin"), ("reg", "Regular"), ("fat", "Fat")]:
                box.addItem(label, code)
            box.setCurrentIndex(1)
        form.addRow("Jersey build", self.build)
        form.addRow("Shorts cut", self.shorts)
        self.parts = QComboBox()
        self.parts.addItems(["Top + shorts", "Top only", "Shorts only"])
        form.addRow("Render", self.parts)
        self.number=QComboBox()
        self.number.addItem("Selected player’s roster number",None)
        for code in range(101):self.number.addItem('00' if code==100 else str(code),code)
        self.number.setCurrentIndex(self.number.findData(23))
        form.addRow('Number (preview)',self.number)
        self.player_index=None
        button = QPushButton("Preview jersey")
        button.clicked.connect(self.preview)
        form.addRow(button)
        label = QLabel(
            "Preview choices do not change roster neck/shape fields. Existing artwork only; no assets are added."
        )
        label.setWordWrap(True)
        form.addRow(label)
        self.uniform.currentIndexChanged.connect(self.default_shape)
        self.setEnabled(False)

    def show_record(self, table, row):
        from ..roster.membership import player_schools
        from ..roster.uniforms import asset_name, VARIANT_NAMES

        self.uniform.blockSignals(True)
        self.uniform.clear()
        self.setEnabled(row is not None)
        self.player_index=row['index'] if row and table=='players' else None
        self.number.model().item(0).setEnabled(bool(row and table=='players'))
        self.number.setCurrentIndex(0 if row and table=='players' else self.number.findData(23))
        if row:
            model = self.owner.roster
            if table == "uniforms":
                uniforms = [row]
            else:
                schools = (
                    [row["index"]]
                    if table == "teams"
                    else player_schools(model, row["index"])
                )
                owners = {model.rows["teams"][i]["uniform_owner_id"] for i in schools}
                uniforms = [
                    u
                    for u in model.rows.get("uniforms", [])
                    if u["team_asset_id"] in owners
                ]
            for uniform in uniforms:
                try:
                    name = asset_name(uniform)
                except ValueError:
                    continue
                self.uniform.addItem(
                    VARIANT_NAMES.get(uniform["variant_code"], "Uniform")
                    + " — "
                    + name,
                    uniform,
                )
        self.uniform.blockSignals(False)
        self.default_shape()

    def default_shape(self):
        uniform = self.uniform.currentData()
        if uniform:
            self.neck.setCurrentIndex(
                max(0, self.neck.findData(uniform["jersey_shape_code"]))
            )

    def preview(self):
        uniform = self.uniform.currentData()
        if not uniform or not self.owner.archive:
            return self.owner.log("Open the JB and select a linked uniform to preview.")
        self.owner.preview_jersey(
            {**uniform,'preview_number':self.number.currentData() if self.number.currentData() is not None else self.owner.roster.rows['players'][self.player_index]['jersey_number'] if self.player_index is not None else 23,'preview_player_index':self.player_index if self.number.currentData() is None else None,'preview_name':'Reborn'},
            self.neck.currentData(),
            self.build.currentData(),
            self.shorts.currentData(),
            self.parts.currentIndex(),
        )


class RecordDetails(QTabWidget):
    def __init__(self, owner, table):
        super().__init__(owner)
        self.owner = owner
        self.table = table
        self.index = None
        self.general = self.tree("Detail")
        self.addTab(
            self.general,
            {
                "teams": "School",
                "arenas": "Arena",
                "coaches": "Coach",
                "conferences": "Conference",
                "uniforms": "Uniform",
            }[table],
        )
        self.links = self.tree("Reference")
        self.addTab(self.links, "References") if table == "teams" else None
        if table == "conferences":
            self.addTab(self.links, "Schools")
            self.history_view=self.tree('History / record');self.addTab(self.history_view,'History')
            logo = QWidget()
            logo_layout = QVBoxLayout(logo)
            logo_layout.addWidget(QLabel('Each conference uses its own logo900 + conference index record.\n'
                                         'Open it below to preview or import replacement DDS artwork.\n'
                                         'Save the replacement bank, then stage it for your manual JB build.'))
            button = QPushButton('Edit / preview conference logo…')
            button.clicked.connect(lambda: self.owner.open_conference_logo(self.index))
            logo_layout.addWidget(button)
            logo_layout.addStretch()
            self.addTab(logo, 'Logo')
        if table == "teams":
            self.roster = self.tree("Roster slot")
            self.addTab(self.roster, "Players")
            self.palette_view = self.tree("Color / role")
            self.addTab(self.palette_view, "Palette")
            self.shoes = ShoeTab(owner)
            self.addTab(self.shoes, "Shoes")
        if table in ("teams", "uniforms"):
            self.jersey = JerseyTab(owner)
            self.addTab(self.jersey, "Jersey")
        self.setEnabled(False)

    def tree(self, label):
        view = QTreeWidget()
        view.setHeaderLabels([label, "Value (double-click to edit)"])
        view.itemDoubleClicked.connect(self.edit_item)
        return view

    def item(self, tree, label, value, key=None, slot=None):
        item = QTreeWidgetItem(tree, [label, str(value)])
        if key:
            item.setData(0, Qt.ItemDataRole.UserRole, (key, slot))
        else:
            item.setToolTip(1, "Read-only metadata")
        return item

    def show_record(self, row):
        self.index = row["index"] if row else None
        self.setEnabled(row is not None)
        self.general.clear()
        self.links.clear()
        if self.table=='conferences':self.history_view.clear()
        if self.table == "teams":
            self.roster.clear()
            self.palette_view.clear()
            self.shoes.show_record("teams", row)
        if self.table in ("teams", "uniforms"):
            self.jersey.show_record(self.table, row)
        if not row:
            return
        model = self.owner.roster
        if self.table == "conferences":
            for member in row.get("team_indices", []):
                self.item(
                    self.links,
                    record_name(model.rows["teams"][member]),
                    f"School #{member}",
                )
        for key, value in row.items():
            if (
                key == "row_offset"
                or isinstance(value, (list, dict))
                or key in FIELDS.get(self.table, {})
            ):
                continue
            writable = key in EDITABLE.get(self.table, ())
            if self.table == "teams" and key in REFERENCES:
                target = REFERENCES[key][1]
                label = (
                    record_name(model.rows[target][value])
                    if value is not None
                    else "None"
                )
                self.item(
                    self.links,
                    key.replace("_index", "").replace("_", " ").title(),
                    label + (f' [#{value}]' if value is not None else ''),
                    key if writable or key == "conference_index" else None,
                )
                continue
            label = ENUM_CHOICES.get(key, {}).get(value, value)
            history_fields={'founded_year','champs_order','final_fours','prev_yr_bids','rank','last_champ_order'}
            self.item(
                self.history_view if self.table=='conferences' and key in history_fields else self.general,
                'Tournament index (legacy presentation_id)' if self.table == 'conferences' and key == 'presentation_id' else key.replace("_", " ").title(),
                label,
                key if writable else None,
            )
        if self.table == "teams":
            for slot, player in enumerate(row["roster_slots"]):
                self.item(
                    self.roster,
                    str(slot + 1),
                    record_name(model.rows["players"][player])
                    if player is not None
                    else "Empty",
                    "roster_slots",
                    slot,
                )
            from ..roster.research import palette_rows

            for color in palette_rows(model, self.index):
                item = self.item(
                    self.palette_view,
                    f"{color['slot']}: {color['role']}",
                    color["rgba"],
                    "palette_colors",
                    color["slot"],
                )
                item.setBackground(1, QColor(*bytes.fromhex(color["rgba"][1:])))
                item.setToolTip(0, color["role"])
            self.palette_view.setColumnWidth(0, 300)
        for view in (self.general, self.links):
            view.resizeColumnToContents(0)

    def apply(self, key, value, slot=None):
        if self.index is None or self.owner.active:
            return
        try:
            if key == "conference_index":
                self.owner.roster.move_team_to_conference(self.index, value)
            elif key == "roster_slots":
                self.owner.roster.edit_school_roster_slot(self.index, slot, value)
            else:
                self.owner.roster.edit(self.table, self.index, key, value, slot)
            self.owner.display_roster(self.owner.roster)
        except ValueError as error:
            QMessageBox.warning(self, "Roster edit blocked", str(error))

    def edit_item(self, item, column):
        data = item.data(0, Qt.ItemDataRole.UserRole)
        if not data or self.index is None or self.owner.active:
            return
        key, slot = data
        model = self.owner.roster
        row = model.rows[self.table][self.index]
        current = row[key][slot] if slot is not None else row[key]
        if key == "palette_colors":
            value = self.owner.pick_rgba(current, self)
            if value is not None:
                self.apply(key, value, slot)
        elif key in REFERENCES or key == "roster_slots":
            value, ok = choose_reference(
                self,
                model,
                "players" if key == "roster_slots" else REFERENCES[key][1],
                current,
                item.text(0),
                allow_none=key != "conference_index",
            )
            if ok:
                self.apply(key, value, slot)
        elif key in STRING_FIELDS.get(self.table, {}):
            from .text_edit import edit_roster_text
            value, ok = edit_roster_text(self, model, self.table, key,
                                        "Edit " + item.text(0), current)
            if ok:
                self.apply(key, value)
        elif key in ENUM_CHOICES or key in ("asset_id", "uniform_asset_id"):
            options = dict(ENUM_CHOICES.get(key, {}))
            if not options:
                options = {r[key]: str(r[key]) for r in model.rows[self.table]}
            if current not in options:
                options[current] = f"Unmapped ({current})"
            values = list(options)
            labels = list(options.values())
            text, ok = QInputDialog.getItem(
                self,
                "Edit " + item.text(0),
                item.text(0),
                labels,
                values.index(current),
                False,
            )
            if ok and values[labels.index(text)] != current:
                self.apply(key, values[labels.index(text)])
        else:
            size = CONFERENCE_SCALARS.get(key, (0, 2))[1]
            value, ok = QInputDialog.getInt(
                self,
                "Edit " + item.text(0),
                item.text(0),
                current,
                0,
                (1 << (size * 8)) - 1,
            )
            if ok:
                self.apply(key, value)
