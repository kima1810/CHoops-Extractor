"""Large team assignment matrix and checked-category expansion workflow."""
from pathlib import Path
import uuid

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QTableWidget, QTableWidgetItem, QAbstractItemView, QCheckBox, QPlainTextEdit, QSplitter,
    QMenu, QFileDialog, QDialog, QDialogButtonBox)

from ..archive.manifests import OUTPUT
from ..modding import team_assets as backend


class TeamAssetsPanel(QWidget):
    def __init__(self, owner):
        super().__init__(); self.owner = owner; self.plan = None; self.rows = []; self.clone_rows = set()
        layout = QVBoxLayout(self)
        heading = QLabel('Team assets'); heading.setStyleSheet('font-size:24px;font-weight:600')
        layout.addWidget(heading)
        explanation = QLabel('Existing assets start checked. * (team names) marks a shared asset. Check missing categories to add them. To separate shared assets, select teams and use Clone checked assets, or change the target ID. Clearing a check does not remove an existing assignment.')
        explanation.setWordWrap(True); layout.addWidget(explanation)
        toolbar = QHBoxLayout(); layout.addLayout(toolbar)
        self.refresh = QPushButton('Load / refresh teams'); toolbar.addWidget(self.refresh)
        self.refresh.clicked.connect(self.reload)
        self.use_roster = QCheckBox('Include roster editor changes'); self.use_roster.setChecked(True); toolbar.addWidget(self.use_roster)
        self.search = QLineEdit(); self.search.setPlaceholderText('Search teams, IDs, filenames or Active / Inactive / Missing')
        toolbar.addWidget(self.search, 1); self.search.textChanged.connect(self.filter)
        copy_bar=QHBoxLayout();layout.addLayout(copy_bar)
        for direction,title,choices in [('from','Copy assignments from…',('Roster editor','Source JB','Selected overrides','External roster / save…')),
                                        ('to','Copy assignments to…',('Roster editor','Selected overrides','Overrides using JB roster','External roster / save copy…'))]:
            button=QPushButton(title);menu=QMenu(button)
            for choice in choices:menu.addAction(choice,lambda checked=False,d=direction,c=choice:self.copy_assignments(d,c))
            button.setMenu(menu);copy_bar.addWidget(button)
        copy_bar.addWidget(QLabel('Copies selected teams only; art files are separate.'))
        controls = QHBoxLayout(); layout.addLayout(controls)
        for text, callback in [('Check all types for selected teams', lambda:self.check_selected(True)),
                               ('Clear selected checks', lambda:self.check_selected(False)),
                               ('Check missing alternates for visible teams', self.check_missing)]:
            button = QPushButton(text); controls.addWidget(button); button.clicked.connect(callback)
        self.clone = QPushButton('Clone checked assets for selected teams'); controls.addWidget(self.clone); self.clone.clicked.connect(self.clone_selected)
        self.table = QTableWidget(0, 13)
        self.table.setHorizontalHeaderLabels(['Team ID / school', 'Asset ID', 'Uniform owner', 'Menu ID', 'Shared by teams',
                                             'S / stadium', 'UH / home', 'UA / away', 'UX', 'UY', 'UZ', 'Menu logo', 'Target ID'])
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.table.setAlternatingRowColors(True)
        self.table.setWordWrap(False)
        self.table.verticalHeader().hide()
        self.table.setColumnWidth(0, 240)
        for column in range(5, 12):self.table.setColumnWidth(column, 150)
        for column in (1, 2, 3, 12):self.table.setColumnWidth(column, 85)
        self.table.setColumnWidth(4, 215)
        self.table.itemChanged.connect(self.invalidate)
        split = QSplitter(Qt.Orientation.Vertical); layout.addWidget(split, 1); split.addWidget(self.table)
        self.details = QPlainTextEdit(); self.details.setReadOnly(True); split.addWidget(self.details); split.setSizes([650, 130])
        bottom = QHBoxLayout(); layout.addLayout(bottom)
        self.preview = QPushButton('Review checked changes'); bottom.addWidget(self.preview); self.preview.clicked.connect(self.review)
        self.apply = QPushButton('Apply to new overrides folder'); bottom.addWidget(self.apply); self.apply.setEnabled(False); self.apply.clicked.connect(self.publish)
        self.state = QLabel('Open a College Hoops 2K8 JB, then load teams.'); layout.addWidget(self.state)

    def invalidate(self, *_):
        self.plan = None; self.apply.setEnabled(False)

    def reload(self):
        if self.owner.active:
            QTimer.singleShot(100,self.reload);return
        if not self.owner.archive:return self.owner.log('Open a College Hoops 2K8 JB first.')
        try:
            archive = self.owner.preview_archive()
            payload = bytes(self.owner.roster.data) if self.use_roster.isChecked() and self.owner.roster else None
        except ValueError as error:return self.owner.show_error(str(error))
        def load(job):
            _, model = backend.roster_model(archive)
            if payload is not None:
                from ..roster.adapters import load_bytes
                from ..roster.editor_model import EditorModel
                model = EditorModel(load_bytes(payload))
            return archive, model, backend.inventory(archive, model), backend.available_ids(archive, model)
        self.owner.run_job('Read team asset assignments', load, self.loaded)

    def loaded(self, result):
        self.asset_archive, self.model, self.rows, self.free = result
        self.clone_rows.clear()
        self.source_key = (id(self.owner.archive), self.owner.mod_path.text(), self.owner.preview_overrides.isChecked())
        self.loaded_payload = bytes(self.owner.roster.data) if self.use_roster.isChecked() and self.owner.roster else None
        self.table.blockSignals(True); self.table.setRowCount(len(self.rows))
        for row, data in enumerate(self.rows):
            values = [f"{data['index']} — {data['school']}", data['asset_id'], data['owner_id'], data['menu_id'], data['shared']]
            for column, value in enumerate(values):
                item = QTableWidgetItem(str(value)); item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable); self.table.setItem(row, column, item)
            for column, kind in enumerate(backend.KINDS, 5):
                key = 'menu_logo' if kind == 'menu_logo' else kind
                value = data[key]
                if kind in 'haxyz' and ' — ' in value:
                    value = value.split(' / ',1)[0] + ' · ' + value.split(' — ',1)[1]
                peers = data['shared_assets'].get(kind, [])
                sharing = ' * (' + ', '.join(peers) + ')' if peers else ''
                item = QTableWidgetItem(value + sharing); item.setToolTip(data[key] + sharing + '\nExisting assets start checked; newly checked categories are added. Use Clone checked assets or change the Target ID for independent copies. Missing prior alternate banks are filled in order.')
                item.setFlags((item.flags() | Qt.ItemFlag.ItemIsUserCheckable) & ~Qt.ItemFlag.ItemIsEditable)
                item.setCheckState(Qt.CheckState.Checked if kind in data['present_assets'] else Qt.CheckState.Unchecked); self.table.setItem(row, column, item)
            item = QTableWidgetItem(str(data['asset_id'])); item.setToolTip('Starts with the original team Asset ID. Existing assignments stay unchanged. New categories reuse a unique uniform owner when possible; shared routes allocate a free ID during review. Enter a different unused ID (0–1023) to copy all checked categories there. Per-asset cells show actual mixed/shared routes.')
            self.table.setItem(row, 12, item)
        self.table.blockSignals(False); self.invalidate(); self.filter(self.search.text())
        self.state.setText(f'{len(self.rows)} teams · {len(self.free)} entirely unused IDs · Active = linked, unlock conditions may still apply')
        self.details.setPlainText('Each checked uniform bank includes its SELU selection asset. Missing X/Y before a checked later bank are filled automatically because the game selects by list order.\nMenu logo creates a texture record inside teamselectlogo.iff + .cdf; it is not a standalone logo IFF.\nS clones the normal day/night stadium route and assigns an independent arena row. Special mode 2/3 arenas remain blocked.\nThe general Asset ID, team classification, conferences, players and coaches are preserved. Original artwork is copied as an editable starting point. Gameplay compatibility remains unverified.')

    def filter(self, text):
        for row, data in enumerate(self.rows):
            self.table.setRowHidden(row, text.casefold() not in ' '.join(str(v) for v in data.values()).casefold())

    def check_selected(self, checked):
        for index in self.table.selectionModel().selectedRows():
            for column in range(5, 12):
                self.table.item(index.row(), column).setCheckState(Qt.CheckState.Checked if checked else Qt.CheckState.Unchecked)

    def check_missing(self):
        for row, data in enumerate(self.rows):
            if not self.table.isRowHidden(row) and 'Active' in data['h'] and 'Active' in data['a']:
                for column, bank in ((8, 'x'), (9, 'y'), (10, 'z')):
                    if data[bank].startswith('Inactive'):
                        self.table.item(row, column).setCheckState(Qt.CheckState.Checked)

    def clone_selected(self):
        self.clone_rows.update(index.row() for index in self.table.selectionModel().selectedRows())
        self.invalidate()
        self.state.setText(f'{len(self.clone_rows)} teams marked for independent copies · Review checked changes to inspect the plan')

    def requests(self):
        free = iter(self.free); reserved = set(); result = []
        checked = []
        for row, data in enumerate(self.rows):
            kinds = [k for column, k in enumerate(backend.KINDS, 5) if self.table.item(row, column).checkState() == Qt.CheckState.Checked]
            text = self.table.item(row, 12).text().strip()
            if text == str(data['asset_id']):text = 'auto'
            if row not in self.clone_rows and text.casefold() == 'auto':
                kinds = [k for k in kinds if k not in data['present_assets']]
            if kinds:checked.append((row, data, kinds, text))
        # Reserve explicitly chosen IDs before allocating Auto values.
        for _, _, _, text in checked:
            if text.casefold() != 'auto':
                value = int(text)
                if value in reserved:raise ValueError('Each planned team requires a distinct target ID')
                reserved.add(value)
        for _, data, kinds, text in checked:
            if text.casefold() == 'auto':
                unique = sum(r['owner_id'] == data['owner_id'] for r in self.rows) == 1
                if unique and set(kinds).issubset(set('haxyz')) and data['owner_id'] not in reserved:
                    target = data['owner_id']
                else:target = next((i for i in free if i not in reserved), None)
                if target is None:raise ValueError('No entirely unused ID remains for these independent assets')
                reserved.add(target)
            else:target = int(text)
            result.append(dict(team=data['index'], id=target, assets=kinds))
        return result

    def unchanged_context(self):
        if self.source_key != (id(self.owner.archive), self.owner.mod_path.text(), self.owner.preview_overrides.isChecked()):
            raise ValueError('The JB or override source changed; refresh teams before applying')
        current = bytes(self.owner.roster.data) if self.use_roster.isChecked() and self.owner.roster else None
        if current != self.loaded_payload:raise ValueError('Roster editor changes changed; refresh teams before applying')

    def review(self):
        if not self.rows:return self.owner.log('Load the team list first.')
        try:
            self.unchanged_context(); requests = self.requests()
        except (ValueError, AttributeError) as error:return self.owner.show_error(str(error))
        self.invalidate()
        if not requests:
            self.details.setPlainText('No asset changes requested. Existing checked assets keep their assignments. Check a missing category to add it, or select teams and use Clone checked assets for independent copies.')
            return
        def complete(plan):
            self.plan = plan; self.apply.setEnabled(True)
            lines = [f"{len(plan['teams'])} teams · {len(plan['additions'])} new IFFs · {len(plan['replacements'])} updated containers"]
            lines += [f"Team {r['team']} {r['school']} → ID {r['id']}: {', '.join(r['assets'])}" for r in plan['teams']]
            lines += ['New files:', *plan['additions'], 'Updated files:', *plan['replacements'], 'Apply creates a separate overrides folder and selects it for normal previews / Build JB copy.']
            lines += ['Fallback: '+item['message'] for item in plan.get('fallbacks',[])]
            self.details.setPlainText('\n'.join(lines))
        payload = bytes(self.model.data)
        self.owner.run_job('Validate checked team asset changes', lambda job:backend.prepare(self.asset_archive, requests, roster_payload=payload, job=job), complete, cancellable=True)

    def publish(self):
        if self.plan is None:return
        try:self.unchanged_context()
        except ValueError as error:return self.owner.show_error(str(error))
        source = self.owner.source; plan = self.plan
        folder = OUTPUT / 'overrides' / ('team_assets_' + uuid.uuid4().hex[:10])
        workspace = OUTPUT / 'builds' / ('team_assets_' + uuid.uuid4().hex[:10])
        archive = self.asset_archive
        def apply(job):
            return backend.apply_plan(source,plan,archive,folder,workspace,job)
        def complete(result):
            self.owner.builder_completed(result, 'staging')
            synchronize_editor(self.owner,plan['replacements']['roster_english.iff'])
            self.state.setText('Applied. Editable folder: ' + str(folder) + ' · Build JB copy writes the selected assets into a new JB.')
            self.plan = None; self.apply.setEnabled(False)
            QTimer.singleShot(0,self.reload)
        self.owner.run_job('Apply team assets to overrides', apply, complete, cancellable=True)

    def copy_assignments(self,direction,choice):
        if not self.rows:return self.owner.log('Load teams, then select team rows to copy.')
        indices=[self.rows[i.row()]['index'] for i in self.table.selectionModel().selectedRows()]
        if not indices:return self.owner.log('Select the team rows whose assignments should be copied.')
        from ..roster.editor_model import EditorModel
        from ..roster.adapters import load_bytes
        from ..roster.asset_assignments import copy_assignments,apply_to_editor
        other_archive=None
        try:
            self.unchanged_context()
            if choice=='Roster editor':
                if not self.owner.roster:raise ValueError('Open a roster in Roster Editor first.')
                other=self.owner.roster
            elif choice.startswith('External'):
                path,_=QFileDialog.getOpenFileName(self,'Choose roster / decrypted save','','Roster / save (*.iff *.rost *.bin *.zip);;All files (*)')
                if not path:return
                other=EditorModel.open(path)
                if hasattr(other,'game'):raise ValueError('Choose a College Hoops 2K8 roster')
            else:
                other_archive=self.owner.preview_archive(choice=='Selected overrides') if choice!='Overrides using JB roster' else self.owner.archive
                _,other=backend.roster_model(other_archive)
            donor=self.model if direction=='to' else other
            target=other if direction=='to' else self.model
            payload,changes=copy_assignments(target,donor,indices)
        except (ValueError,OSError,KeyError) as error:return self.owner.show_error(str(error))
        dialog=QDialog(self);dialog.setWindowTitle('Review asset assignment copy');dialog.resize(950,500)
        layout=QVBoxLayout(dialog);text=QPlainTextEdit();text.setReadOnly(True)
        text.setPlainText('\n'.join(f"Team {r['team']} {r['school']} ← {r['source_school']}: owner {r['owner']}; active {r['active']}; inactive {r['inactive']}" for r in changes)+'\n\nOnly asset IDs, arena routing and uniform activation/assignments are copied. Destination names, players, ratings, classification and conferences stay intact. Asset artwork is not copied; missing alternate containers can use Home during building. Check the matrix for missing assets.')
        layout.addWidget(text);buttons=QDialogButtonBox(QDialogButtonBox.StandardButton.Ok|QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(dialog.accept);buttons.rejected.connect(dialog.reject);layout.addWidget(buttons)
        if dialog.exec()!=QDialog.DialogCode.Accepted:return
        if direction=='from':
            self.model=EditorModel(load_bytes(payload))
            self.loaded((self.asset_archive,self.model,backend.inventory(self.asset_archive,self.model),backend.available_ids(self.asset_archive,self.model)))
            self.details.setPlainText('Copied selected assignments into the matrix. Review/check expansions, or use Copy assignments to → Selected overrides to save them.')
        elif choice=='Roster editor':
            apply_to_editor(other,payload);self.owner.display_roster(other)
            self.loaded_payload=bytes(other.data) if self.use_roster.isChecked() else None
            self.invalidate();self.state.setText('Copied asset assignments to Roster Editor as one undoable edit.')
        elif choice.startswith('External'):
            output,_=QFileDialog.getSaveFileName(self,'Save a separate roster / save copy',str(OUTPUT/'rosters'/'asset_assignments.iff'),'All files (*)')
            if output:
                from ..archive.manifests import write_bytes
                try:write_bytes(output,other.source.encode(payload),[other.source.source_path])
                except (ValueError,OSError) as error:return self.owner.show_error(str(error))
                self.state.setText('Saved assignment copy: '+output)
        else:
            selected=self.owner.preview_archive(True) if (Path(self.owner.mod_path.text())/'overrides.json').is_file() else self.owner.archive
            def refreshed():
                self.use_roster.setChecked(False);self.reload()
            save_payload_to_overrides(self.owner,payload,selected,refreshed)


def synchronize_editor(owner,encoded_roster):
    from ..roster.adapters import load_bytes
    from ..roster.editor_model import EditorModel
    from ..roster.asset_assignments import apply_to_editor
    model=EditorModel(load_bytes(encoded_roster))
    if owner.roster:
        if bytes(owner.roster.data)!=bytes(model.data):apply_to_editor(owner.roster,bytes(model.data))
        model=owner.roster
    owner.display_roster(model)


def save_payload_to_overrides(owner,payload,archive=None,after=None):
    if not owner.source or not owner.archive:return owner.log('Open a College Hoops 2K8 JB first.')
    try:
        if archive is None:
            archive=owner.preview_archive(True) if (Path(owner.mod_path.text())/'overrides.json').is_file() else owner.archive
        plan=backend.roster_plan(archive,payload)
    except (ValueError,OSError) as error:return owner.show_error(str(error))
    token=uuid.uuid4().hex[:10]
    folder=OUTPUT/'overrides'/('roster_'+token);workspace=OUTPUT/'builds'/('roster_'+token)
    def complete(result):
        owner.builder_completed(result,'staging')
        owner.log('Saved edited roster to overrides: '+str(folder))
        if after:after()
    owner.run_job('Save edited roster to overrides',lambda job:backend.apply_plan(owner.source,plan,archive,folder,workspace,job),complete,cancellable=True)
