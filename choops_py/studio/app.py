"""Qt model/view explorer. Binary work runs on bounded background workers."""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

from PySide6.QtCore import (
    QAbstractTableModel,
    QModelIndex,
    QObject,
    QRunnable,
    QSettings,
    QSortFilterProxyModel,
    Qt,
    QThreadPool,
    QTimer,
    Signal,
)
from PySide6.QtGui import QAction, QImage, QPixmap, QColor
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QColorDialog,
    QDoubleSpinBox,
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QDockWidget,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QGridLayout,
    QLabel,
    QLineEdit,
    QInputDialog,
    QMainWindow,
    QMessageBox,
    QPlainTextEdit,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QSplitter,
    QSizePolicy,
    QStackedWidget,
    QTableView,
    QTabWidget,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
    QToolButton,
)

from ..archive.manifests import OUTPUT
from ..archive.usrdir_reader import Archive
from .services import (
    Cancelled,
    JobContext,
    extract,
    inspect_asset,
    materialize,
    stage_folder,
)


class Rows(QAbstractTableModel):
    def __init__(self, rows=None, columns=None):

        super().__init__()

        self.rows = rows or []

        self.columns = columns or []

    def rowCount(self, parent=QModelIndex()):  # noqa: B008 - Qt override signature

        return 0 if parent.isValid() else len(self.rows)

    def columnCount(self, parent=QModelIndex()):  # noqa: B008 - Qt override signature

        return 0 if parent.isValid() else len(self.columns)

    def data(self, index, role=Qt.ItemDataRole.DisplayRole):
        if not index.isValid():
            return None
        key = self.columns[index.column()][0]
        value = self.rows[index.row()].get(key, "")
        if role == Qt.ItemDataRole.UserRole and key=="name":
            return value or self.rows[index.row()].get("name_hint") or f"hash_{self.rows[index.row()].get('hash',0):08x}"
        if role == Qt.ItemDataRole.UserRole:
            return value if isinstance(value, (int, float)) else str(value or "")
        if role == Qt.ItemDataRole.ToolTipRole and key == 'references':return str(value or '').replace('; ', '\n')
        if role != Qt.ItemDataRole.DisplayRole:
            return None
        if key == "hash":
            return f"{value:08X}"
        if key == "name" and not value:
            hint=self.rows[index.row()].get("name_hint")
            if hint:return hint+f" [hash {self.rows[index.row()].get('hash',0):08X}]"
            return f"hash_{self.rows[index.row()].get('hash', 0):08x}"
        from ..roster.schema import ENUM_CHOICES
        if key == 'height_inches':
            from ..roster.presentation import height_text
            return height_text(value)
        if key in ENUM_CHOICES:
            return ENUM_CHOICES[key].get(value, f'Unknown ({value})')
        if isinstance(value, (list, dict)):
            labels = {'palette_colors':'colors; use Team palette',
                      'attribute_ratings':'ratings; shown in player panel',
                      'properties':'details; shown in player panel',
                      'roster_slots':'player slots; use Edit selected'}
            return f"{len(value)} {labels.get(key, 'entries')}"
        return str(value if value is not None else "")

    def headerData(self, section, orientation, role=Qt.ItemDataRole.DisplayRole):

        if (
            role == Qt.ItemDataRole.DisplayRole
            and orientation == Qt.Orientation.Horizontal
        ):
            return self.columns[section][1]

        return None


class Events(QObject):
    result = Signal(object)

    failed = Signal(str)

    progress = Signal(int, int, str)

    finished = Signal()


class Worker(QRunnable):
    def __init__(self, function, job):

        super().__init__()

        self.function, self.job = function, job

        self.events = Events()

        self.last_progress = 0.0

        self.job.progress = self.progress

    def progress(self, done, total, text):

        now = time.monotonic()

        if now - self.last_progress > 0.1 or done == total or done == 0:
            self.last_progress = now

            # Qt int is 32-bit: normalize large archive counts before emitting.

            self.events.progress.emit(int(1000 * done / max(1, total)), 1000, text)

    def run(self):

        try:
            self.events.result.emit(self.function(self.job))

        except Cancelled as error:
            self.events.result.emit({"status": "cancelled", "detail": str(error)})
        except Exception as error:  # noqa: BLE001 - worker boundary reports all failures
            self.events.failed.emit(f"{type(error).__name__}: {error}")

        finally:
            self.events.finished.emit()


def table():

    view = QTableView()

    view.setSelectionBehavior(QTableView.SelectionBehavior.SelectRows)

    view.setSelectionMode(QTableView.SelectionMode.ExtendedSelection)

    view.setSortingEnabled(True)

    view.setAlternatingRowColors(True)
    view.horizontalHeader().setVisible(True)
    view.horizontalHeader().setMinimumHeight(28)
    view.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
    view.setVerticalScrollMode(QTableView.ScrollMode.ScrollPerPixel)

    return view


class CategoryProxy(QSortFilterProxyModel):
    category='All'
    school=None
    def filterAcceptsRow(self,row,parent):
        data=self.sourceModel().rows[row]
        return (self.category=='All' or data.get('category')==self.category) and (self.school is None or self.school in data.get('school_indices',[])) and super().filterAcceptsRow(row,parent)
    def choose_category(self,category):
        self.category=category;self.invalidate()
    def choose_school(self,school):
        self.school=school;self.invalidate()


def set_rows(view, rows, columns, query=""):

    proxy = CategoryProxy(view)

    proxy.setSourceModel(Rows(rows, columns))
    proxy.setSortRole(Qt.ItemDataRole.UserRole)

    proxy.setFilterKeyColumn(-1)

    proxy.setFilterCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)

    proxy.setFilterFixedString(query)

    view.setModel(proxy)

    view.resizeColumnsToContents()
    for column in range(len(columns)):
        maximum = 640 if columns[column][0] == 'references' else 240
        minimum = 480 if columns[column][0] == 'references' else 80
        view.setColumnWidth(column, min(maximum, max(minimum, view.columnWidth(column))))
    view.horizontalScrollBar().setValue(0)

    return proxy


def selected(view):

    proxy = view.model()

    if proxy is None:
        return []

    return [
        proxy.sourceModel().rows[proxy.mapToSource(i).row()]
        for i in view.selectionModel().selectedRows()
    ]


class TexturePreview(QLabel):
    """Keep the entire texture visible as the preview viewport changes size."""

    def __init__(self, text):
        super().__init__(text)
        self._original = QPixmap()
        self.setMinimumSize(1, 120)
        self.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Ignored)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)

    def setPixmap(self, pixmap):
        self._original = pixmap
        self._fit()

    def setText(self, text):
        self._original = QPixmap()
        super().setText(text)

    def clear(self):
        self._original = QPixmap()
        super().clear()

    def _fit(self):
        if not self._original.isNull():
            super().setPixmap(self._original.scaled(
                self.contentsRect().size(),
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            ))

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._fit()


class Window(QMainWindow):
    def __init__(self):

        super().__init__()

        from .. import __version__
        self.setWindowTitle("CHoops Modding Studio • v" + __version__)

        self.resize(1420, 900)

        self.settings = QSettings("CHoops", "ModdingStudio")

        self.pool = QThreadPool(self)

        self.pool.setMaxThreadCount(1)

        self.active = None

        self.archive = None
        self._preview_archive_cache = {}

        self.asset_path = None

        self.roster = None

        self.source = None

        self.pages = QStackedWidget()

        self.navigation = QTreeWidget()

        self.navigation.setHeaderLabel("CHoops Studio")

        for name in (
            "Explorer",
            "Texture Editor",
            "Roster Editor",
            "Audio",
            "Models / Courts",
            "Mod Builder",
            "Team Assets",
            "Research",
            "Diagnostics",
        ):
            self.navigation.addTopLevelItem(QTreeWidgetItem([name]))

        self.navigation.currentItemChanged.connect(self.navigate)

        split = QSplitter()

        split.addWidget(self.navigation)

        split.addWidget(self.pages)

        split.setSizes([190, 1230])

        self.setCentralWidget(split)

        self.logs = QPlainTextEdit()

        self.logs.setReadOnly(True)

        self.logs.document().setMaximumBlockCount(1000)

        dock = QDockWidget("Tasks and diagnostics", self)

        dock.setWidget(self.logs)

        self.addDockWidget(Qt.DockWidgetArea.BottomDockWidgetArea, dock)

        self.progress = QProgressBar()

        self.progress.setMaximumWidth(280)

        self.cancel = QPushButton("Cancel task")

        self.cancel.setEnabled(False)

        self.cancel.clicked.connect(
            lambda: self.active.job.cancelled.set() if self.active else None
        )

        self.statusBar().addPermanentWidget(self.progress)

        self.statusBar().addPermanentWidget(self.cancel)

        menu = self.menuBar().addMenu("File")
        self.preview_overrides=QAction('Selected overrides',self)
        self.preview_overrides.setCheckable(True)
        self.preview_overrides.toggled.connect(self.reload_preview_source)
        preview_toolbar=self.addToolBar('Preview source')
        preview_toolbar.addWidget(QLabel('Preview source: '))
        self.preview_source_selector = QComboBox()
        self.preview_source_selector.addItems(['Source JB', 'Selected overrides'])
        self.preview_source_selector.setToolTip('Applies to all texture and 3D preview categories.')
        preview_toolbar.addWidget(self.preview_source_selector)
        self.preview_source_info = QLabel('Original JB assets')
        preview_toolbar.addWidget(self.preview_source_info)
        self.preview_source_selector.activated.connect(lambda index:self.preview_overrides.setChecked(index == 1))
        self.preview_overrides.toggled.connect(lambda checked:self.preview_source_selector.setCurrentIndex(int(checked)))

        for text, handler, shortcut in [
            ("Open game…", self.choose_game, "Ctrl+O"),
            ("Open extracted asset…", self.choose_asset, "Ctrl+Shift+O"),
            ("Open roster…", self.choose_roster, ""),
            ("Exit", self.close, "Ctrl+Q"),
        ]:
            action = QAction(text, self)

            if shortcut:
                action.setShortcut(shortcut)

            action.triggered.connect(handler)

            menu.addAction(action)

        self.create_explorer()

        self.create_texture()

        self.create_roster()

        self.create_audio()

        self.create_models()

        self.create_builder()

        from .team_assets import TeamAssetsPanel
        self.team_assets_panel = TeamAssetsPanel(self)
        self.pages.addWidget(self.team_assets_panel)
        self.create_research()
        self.create_diagnostics()

        self.navigation.setCurrentItem(self.navigation.topLevelItem(0))

        geometry = self.settings.value("geometry")

        if geometry:
            self.restoreGeometry(geometry)

    def navigate(self, item, previous):

        if item:
            self.pages.setCurrentIndex(self.navigation.indexOfTopLevelItem(item))

    def page(self, title, description):

        widget = QWidget()

        layout = QVBoxLayout(widget)

        heading = QLabel(title)

        heading.setStyleSheet("font-size: 24px; font-weight: 600; padding: 8px 0;")

        layout.addWidget(heading)

        label = QLabel(description)

        label.setWordWrap(True)

        layout.addWidget(label)

        self.pages.addWidget(widget)

        return layout

    def buttons(self, layout, items):
        row=QGridLayout()
        for index,(label,handler) in enumerate(items):
            button=QPushButton(label);button.clicked.connect(handler)
            row.addWidget(button,index//4,index%4)
        for column in range(4):row.setColumnStretch(column,1)
        layout.addLayout(row)

    def create_audio(self):
        from ..audio_tools.pending import PendingSongs
        self.pending_songs=PendingSongs()
        layout = self.page(
            "Audio workspace",
            "Browse Licensed Music and Fight Songs from the selected JB. WAV exports and replacement folders are prepared under output/ for you to select as overrides and build manually.",
        )

        self.audio_state = QLabel("Open a JB folder, then load its audio catalog.")
        self.audio_state.setWordWrap(True)
        layout.addWidget(self.audio_state)

        self.buttons(
            layout,
            [
                ("Load / refresh catalog", self.audio_refresh),
                ("Export selected WAVs…", self.audio_export_selected),
                ("Export this section…", self.audio_export_section),
                ("Queue selected song from WAV…", self.audio_replace_selected),
                ("Save queued songs…", self.audio_save_pending),
                ("Remove queued song", self.audio_remove_pending),
                ("Clear song queue", self.audio_clear_pending),
                ("Replace from edited export…", self.audio_replace_folder),
                ("Export shared cover art…", self.audio_export_cover),
                ("Replace shared cover art…", self.audio_replace_cover),
            ],
        )

        self.audio_tabs = QTabWidget()
        self.audio_tables = {}
        self.audio_tables["Soundtrack"] = table()
        self.audio_tables["Fight song"] = table()
        self.audio_tabs.addTab(self.audio_tables["Soundtrack"], "Licensed Music")
        self.audio_tabs.addTab(self.audio_tables["Fight song"], "Fight Songs")
        layout.addWidget(self.audio_tabs)

        self.audio_queue=table()
        self.audio_queue.setMaximumHeight(160)
        layout.addWidget(QLabel('Pending replacements — choose songs above, then save the whole queue once.'))
        layout.addWidget(self.audio_queue)
        self.audio_show_pending()

        note = QLabel(
            "Song titles and artists are informational and read-only. Fight songs share jukebox cover record 021; some soundtrack records are shared too. Unknown AUDO loops and general CDF audio growth remain unsupported."
        )
        note.setWordWrap(True)
        layout.addWidget(note)

    def navigate_to(self, name):
        matches = self.navigation.findItems(name, Qt.MatchFlag.MatchExactly)
        if len(matches) != 1:
            raise ValueError('Navigation page is missing or ambiguous: ' + name)
        self.navigation.setCurrentItem(matches[0])

    def audio_refresh(self):

        if not self.archive:
            return self.log("Open a JB folder before loading the audio catalog.")
        archive = self.archive

        def display(result):
            tracks = result["tracks"]
            columns = [
                ("title", "Title / stream"),
                ("artist", "Artist"),
                ("bank", "Bank"),
                ("index", "Index"),
                ("seconds", "Seconds"),
            ]
            for category, view in self.audio_tables.items():
                rows = [row for row in tracks if row["category"] == category]
                set_rows(view, rows, columns)
            self.audio_state.setText(
                f"{result['soundtrack_count']} licensed tracks • "
                f"{result['fight_song_count']} fight songs • source JB read-only"
            )

        from ..audio_tools.workflow import catalog

        self.run_job(
            "Load audio catalog",
            lambda job: catalog(archive, job),
            display,
            cancellable=True,
        )

    def audio_selected(self):
        view = self.audio_tables.get(
            "Soundtrack" if self.audio_tabs.currentIndex() == 0 else "Fight song"
        )
        return selected(view) if view else []

    def audio_output_path(self, title, suggested):
        path, _ = QFileDialog.getSaveFileName(self, title, str(OUTPUT / suggested))
        return Path(path) if path else None

    def audio_export_selected(self):
        rows = self.audio_selected()
        if not rows:
            return self.log("Select one or more tracks first.")
        self.audio_export_rows(rows)

    def audio_export_section(self):
        category = "Soundtrack" if self.audio_tabs.currentIndex() == 0 else "Fight song"
        view = self.audio_tables[category]
        proxy = view.model()
        if not proxy:
            return self.log("Load the audio catalog first.")
        rows = list(proxy.sourceModel().rows)
        if not rows:
            return self.log("This section has no catalog tracks.")
        self.audio_export_rows(rows)

    def audio_export_rows(self, rows):
        archive = self.archive
        if not archive:
            return self.log("Open a JB folder before exporting audio.")
        category = "licensed_music" if rows[0]["category"] == "Soundtrack" else "fight_songs"
        output = self.audio_output_path(
            "Choose a new WAV export folder", Path("rips") / category
        )
        if not output:
            return
        from ..audio_tools.workflow import export_tracks

        self.run_job(
            "Export WAV tracks",
            lambda job: export_tracks(archive, rows, output, job),
            cancellable=True,
        )

    def audio_replace_selected(self):
        rows = self.audio_selected()
        if len(rows) != 1:
            return self.log("Select exactly one track to replace from a WAV file.")
        archive = self.archive
        if not archive:
            return self.log("Open a JB folder before preparing an audio replacement.")
        wav, _ = QFileDialog.getOpenFileName(
            self, "Select replacement WAV", "", "WAV audio (*.wav)"
        )
        if not wav:
            return
        try:self.pending_songs.add(archive,rows[0],Path(wav))
        except (ValueError,OSError,EOFError) as error:return self.log(str(error))
        self.audio_show_pending()

    def audio_show_pending(self):
        rows=[dict(bank=row['bank'],index=row['index'],title=row['title'],file=str(path))
              for row,path in self.pending_songs.items.values()]
        set_rows(self.audio_queue,rows,[('title','Song'),('bank','Bank'),('index','Index'),('file','Replacement WAV')])

    def audio_remove_pending(self):
        for row in selected(self.audio_queue):
            self.pending_songs.items.pop((row['bank'],row['index']),None)
        self.audio_show_pending()

    def audio_clear_pending(self):
        self.pending_songs.clear()
        self.audio_show_pending()

    def audio_save_pending(self):
        archive=self.archive
        try:replacements=self.pending_songs.replacements(archive)
        except ValueError as error:return self.log(str(error))
        output = self.audio_output_path(
            "Choose a new replacement folder", Path("audio") / "song_edit"
        )
        if not output:
            return
        from ..audio_tools.workflow import replace_tracks

        def saved(result):
            self.pending_songs.saved(archive,replacements)
            self.audio_show_pending()

        self.run_job(
            "Save queued song replacements",
            lambda job: replace_tracks(archive, replacements, output, job),
            saved,
            cancellable=True,
        )

    def audio_replace_folder(self):
        archive = self.archive
        if not archive:
            return self.log("Open a JB folder before preparing audio replacements.")
        folder = QFileDialog.getExistingDirectory(self, "Select an edited audio export folder")
        if not folder:
            return
        output = self.audio_output_path(
            "Choose a new replacement folder", Path("audio") / "batch_edit"
        )
        if not output:
            return
        from ..audio_tools.workflow import import_wav_folder

        self.run_job(
            "Prepare edited WAV replacements",
            lambda job: import_wav_folder(archive, Path(folder), output, job),
            cancellable=True,
        )

    def audio_cover_operation(self, replace=False):
        rows = self.audio_selected()
        if len(rows) != 1:
            return self.log("Select exactly one track to choose its shared cover art.")
        cover_record = rows[0].get("cover_record")
        if not cover_record:
            return self.log("This track has no confirmed cover-art mapping.")
        archive = self.archive
        if not archive:
            return self.log("Open a JB folder before editing cover art.")
        if replace:
            image, _ = QFileDialog.getOpenFileName(
                self,
                "Select replacement cover image",
                "",
                "Images (*.dds *.png *.jpg *.jpeg *.bmp)",
            )
            if not image:
                return
            output = self.audio_output_path(
                "Choose a new jukebox.iff output path", Path("audio") / "jukebox_edited.iff"
            )
            if not output:
                return
            from ..audio_tools.workflow import replace_cover

            self.run_job(
                "Prepare shared cover-art replacement",
                lambda job: replace_cover(archive, cover_record, image, output, job),
                cancellable=True,
            )
        else:
            output = self.audio_output_path(
                "Choose a new cover-art export path",
                Path("rips") / "audio" / f"cover_{cover_record}.dds",
            )
            if not output:
                return
            from ..audio_tools.workflow import export_cover

            self.run_job(
                "Export shared cover art",
                lambda job: export_cover(archive, cover_record, output),
            )

    def audio_export_cover(self):
        return self.audio_cover_operation()

    def audio_replace_cover(self):
        return self.audio_cover_operation(replace=True)

    def run_job(self, label, function, callback=None, cancellable=False):

        if self.active:
            self.log("A task is already running. Wait for it to finish.")

            return

        self._job_label=label
        worker = Worker(function, JobContext())

        self.active = worker

        self.cancel.setEnabled(cancellable)

        self.progress.setRange(0, 0)

        self.statusBar().showMessage(label)

        self.log(label)

        worker.events.progress.connect(self.job_progress)

        worker.events.failed.connect(self.show_error)

        def deliver(result):
            try:
                if callback:callback(result)
                else:self.log(json.dumps(result, default=str)[:8000])
            except Exception as error:
                self.show_error(type(error).__name__ + ': ' + str(error))
        worker.events.result.connect(deliver)

        worker.events.finished.connect(self.job_finished)

        self.pool.start(worker)

    def job_progress(self, done, total, text):

        self.progress.setRange(0, total)

        self.progress.setValue(done)

        self.statusBar().showMessage(text)

    def job_finished(self):

        self._job_label=""
        self.active = None

        self.cancel.setEnabled(False)

        self.progress.setRange(0, 100)

        self.progress.setValue(100)

        self.statusBar().showMessage("Ready")

    def log(self, text):

        self.logs.appendPlainText(str(text))

    def show_error(self, text):

        self.log(text)

        from .build_diagnostics import failure_summary
        label=getattr(self,'_job_label','Operation') or 'Operation'
        if any(word in label.casefold() for word in ('override','jb','preflight')) or 'archive header' in str(text).casefold():
            message=failure_summary(label,text)
            self.build_details.setPlainText(message)
            QMessageBox.warning(self,"Operation could not complete",message)
        else:QMessageBox.warning(self, "Operation could not complete", text)

    def choose_game(self):

        path = QFileDialog.getExistingDirectory(
            self, "Select original JB game or USRDIR", self.settings.value("game", "")
        )

        if path:
            self.open_game(Path(path))

    def open_game(self, path):

        def loaded(archive):

            self.archive = archive
            self._preview_archive_cache.clear()
            self._jersey_preview_row=None;self.jersey_shape_controls.hide()
            self.audio_state.setText("Audio catalog has not been loaded for this JB.")
            for view in self.audio_tables.values():
                view.setModel(None)
            self.scene_uniform_images = {}
            # A newly selected JB folder must not inherit another source's roster.
            self.roster = None
            self.nba_roster=None;self.nba_panel.hide();self.ch_roster_panel.show()
            self.refresh_uniform_list()
            self.refresh_shoe_list()
            self.refresh_stadium_list()
            for view in self.roster_views.values():
                view.setModel(None)
            self.roster_state.setText('No roster loaded; load the current JB folder roster')
            self.scene_meshes = []
            self.scene_view.set_meshes([])
            self.scene_palette_state.setText("No roster associated; load the current JB folder roster")

            self.source = path
            self.preview_mod=None
            self._scene_record_index=None;self._shoe_preview_active=False;self._direct_stadium_active=False
            self.preview_overrides.blockSignals(True);self.preview_overrides.setChecked(False);self.preview_overrides.blockSignals(False)
            self.preview_source_selector.setCurrentIndex(0)

            self.settings.setValue("game", str(path))

            self.explorer_proxy = set_rows(
                self.explorer,
                self.catalog_rows(),
                [
                    ("name", "Asset"),
                    ("category", "Category"),
                    ("preview_source", "Preview source"),
                    ("references", "Roster references"),
                    ("size", "Bytes"),
                    ("hash", "CRC32"),
                    ("index", "TOC index"),
                    ("offset", "Logical offset"),
                    ("size_derived", "Derived extent"),
                ],
                self.search.text(),
            )

            self.explorer.selectionModel().selectionChanged.connect(self.show_explorer_references)

            self.identity.setText(
                f"{getattr(archive,'game_info',{}).get('TITLE','PS3 2K archive')} • {len(archive.entries):,} entries • {len(archive.parts)} split parts • original source read-only"
            )

            self.log("Archive index loaded; payloads remain lazy.")

        self.run_job("Index JB folder", lambda job: Archive(path), loaded)

    def identify_asset_names(self, candidates=()):
        if isinstance(candidates,bool):candidates=()
        if self.active or not self.archive:return
        from ..archive.identity import recover,apply
        def display(result):
            apply(self.archive,result['identities'])
            self._preview_archive_cache.clear()
            self.refresh_catalog()
            self.refresh_uniform_list();self.refresh_shoe_list();self.refresh_stadium_list()
            self.log(f"{result['matched_names']} canonical filenames verified by CRC32; {result['internal_labels']} internal-record labels. Labels preserve original hash identities.")
        self.run_job('Recover archive identities',lambda job:recover(self.archive,candidates,job),display,cancellable=True)

    def match_asset_names(self):
        if self.active or not self.archive:return
        path,_=QFileDialog.getOpenFileName(self,'Candidate filenames, one per line','','Text lists (*.txt);;All files (*)')
        if not path:return
        try:
            if Path(path).stat().st_size>2*1024*1024:raise ValueError('Filename list exceeds 2 MiB')
            candidates=Path(path).read_text(encoding='utf-8-sig').splitlines()
            self.identify_asset_names(candidates)
        except (ValueError,OSError) as error:QMessageBox.warning(self,'Filename list blocked',str(error))

    def catalog_rows(self, archive=None):
        from ..archive.catalog import catalog
        archive = archive or self.preview_archive() or self.archive
        replacements=set(getattr(archive,'replacements',{}))
        rows=catalog(archive.entries,getattr(self,'nba_roster',None) or self.roster)
        for row in rows:
            row['preview_source']='Override' if row['index'] in replacements else 'JB fallback' if self.preview_overrides.isChecked() else 'Source JB'
        return rows

    def refresh_catalog(self, archive=None):
        if not self.archive or not self.explorer.model():return
        try:rows=self.catalog_rows(archive)
        except (ValueError,OSError) as error:
            self.log('Explorer source unavailable: '+str(error));return
        model=self.explorer.model().sourceModel();model.beginResetModel()
        try:model.rows=rows
        finally:model.endResetModel()
        self.explorer.model().choose_category(self.archive_category.currentText())

    def create_explorer(self):

        layout = self.page(
            "Archive explorer",
            "Select a PS3 JB folder, including a modded rebuild. Browse assets without a full rip; double-click an IFF to inspect records and preview its textures.",
        )

        self.identity = QLabel("No game selected")

        layout.addWidget(self.identity)

        self.buttons(
            layout,
            [
                ("Open game…", self.choose_game),
                ("Select overrides folder…", self.stage_replacements),
                ("Extract selected…", self.extract_selected),
                ("Extract all raw…", lambda: self.extract_selected(True)),
                ("Identify unnamed assets", self.identify_asset_names),
                ("Match filename list…", self.match_asset_names),
            ],
        )

        self.search = QLineEdit()

        self.search.setPlaceholderText("Filter filename, CRC32, index or offset")

        self.search.textChanged.connect(
            lambda value: (
                self.explorer.model().setFilterFixedString(value)
                if self.explorer.model()
                else None
            )
        )

        layout.addWidget(self.search)
        self.archive_category=QComboBox();self.archive_category.addItems(['All','Stadiums','Uniforms','Cloth geometry','Shoes','Logos','Players','Audio','Menus','Rosters','Animation banks','Other / unresolved'])
        self.archive_category.currentTextChanged.connect(lambda category:self.explorer.model().choose_category(category) if self.explorer.model() else None)
        layout.addWidget(self.archive_category)

        self.explorer = table()

        self.explorer.doubleClicked.connect(self.inspect_selected)

        layout.addWidget(self.explorer)
        layout.addWidget(QLabel('Roster references — full text'))
        self.explorer_references = QPlainTextEdit()
        self.explorer_references.setReadOnly(True)
        self.explorer_references.setPlaceholderText('Select an asset to read its full roster references here.')
        self.explorer_references.setMinimumHeight(85)
        self.explorer_references.setMaximumHeight(180)
        layout.addWidget(self.explorer_references)

        self.nested = QTreeWidget()
        self.nested.currentItemChanged.connect(self.show_nested_references)

        self.nested.setHeaderLabels(["Nested record", "Type", "Index"])

        self.nested.header().setStretchLastSection(False)

        self.nested.setColumnWidth(0, 220)

        layout.addWidget(self.nested)

        self.explorer_texture = QComboBox()
        self.explorer_texture.setEnabled(False)
        self.explorer_texture.activated.connect(self.preview_explorer_texture)
        layout.addWidget(self.explorer_texture)
        self.explorer_image = TexturePreview("Open an IFF or double-click an archive entry to preview textures")
        self.explorer_image.setAlignment(Qt.AlignmentFlag.AlignCenter)
        preview_scroll = QScrollArea()
        preview_scroll.setWidgetResizable(True)
        preview_scroll.setWidget(self.explorer_image)
        layout.addWidget(preview_scroll)

    def show_explorer_references(self, *_):
        rows=selected(self.explorer)
        text=rows[0].get('references','') if rows else ''
        if rows and not text:
            text='No confirmed roster references for this asset.' if self.roster else 'Load a roster in Roster Editor to see asset references.'
        self.explorer_references.setPlainText(text.replace('; ', '\n'))

    def show_nested_references(self, item, previous=None):
        if item is not None:self.explorer_references.setPlainText(item.text(3).replace('; ', '\n'))

    def extract_selected(self, all_entries=False):

        if not self.archive:
            return self.log("Open a game first.")

        try:archive = self.preview_archive()
        except (ValueError, OSError) as error:return self.show_error(str(error))
        entries = list(archive.entries) if all_entries else selected(self.explorer)

        if not entries:
            return self.log("Select one or more rows to extract.")

        path = QFileDialog.getExistingDirectory(
            self, "Choose new output folder under output/", str(OUTPUT / "rips")
        )

        if path:
            self.run_job(
                "Extract raw assets",
                lambda job: extract(archive, entries, Path(path), job),
                cancellable=True,
            )

    def inspect_selected(self):

        entries = selected(self.explorer)

        if not entries:
            return

        entry = entries[0]

        try: archive = self.preview_archive()
        except ValueError as error: return self.show_error(str(error))
        self.run_job(
            "Read and inspect asset",
            lambda job: inspect_asset(materialize(archive, entry)),
            self.display_asset,
        )

    def choose_asset(self):

        path, _ = QFileDialog.getOpenFileName(
            self,
            "Open extracted IFF/TXTR/DDS",
            "",
            "Assets (*.iff *.txtr *.dds *.scne);;All files (*)",
        )

        if path and Path(path).name in ("0A","0A.SDAT"):
            self.open_game(Path(path))
        elif path:
            self.run_job(
                "Inspect extracted asset",
                lambda job: inspect_asset(Path(path)),
                self.display_asset,
            )

    def preview_archive(self, use_overrides=None):
        from .preview_source import PreviewArchive
        if not self.archive:return None
        if not (self.preview_overrides.isChecked() if use_overrides is None else use_overrides):return self.archive
        mod=self.mod_path.text()
        root=Path(mod).resolve()
        if not (root/'overrides.json').is_file():raise ValueError('Select an overrides folder before using override previews')
        try:
            fingerprints=[]
            for name in ('overrides.json','source_preconditions.json','preview_inputs.json','additions.json'):
                if name in ('preview_inputs.json','additions.json') and not (root/name).exists():continue
                info=(root/name).stat()
                fingerprints.append((info.st_size,info.st_mtime_ns,info.st_ino))
        except OSError as error:raise ValueError('Override workspace is incomplete; select the overrides folder again') from error
        key=(id(self.archive),str(root),tuple(fingerprints))
        if key not in self._preview_archive_cache:
            try:snapshot=PreviewArchive(self.archive,str(root))
            except (KeyError,TypeError,OSError) as error:raise ValueError('Invalid override workspace: '+str(error)) from error
            if len(self._preview_archive_cache)>=2:self._preview_archive_cache.clear()
            self._preview_archive_cache[key]=snapshot
        return self._preview_archive_cache[key]

    def preview_file(self,source,archive=None):
        if archive is None:return source
        matches=[e for e in archive.entries if e.get('name')==Path(source).name]
        if Path(source).name.lower().startswith('hash_'):
            from ..archive.hash_names import replacement_hash
            try:matches=[e for e in archive.entries if e['hash']==replacement_hash(Path(source).name)]
            except ValueError:pass
        if len(matches)==1:return materialize(archive,matches[0])
        return source

    def reload_preview_source(self,*_):
        if self.active:
            QTimer.singleShot(100,self.reload_preview_source);return
        self.refresh_preview_lists()
        item = self.navigation.currentItem()
        models_visible = item is not None and item.text(0) == 'Models / Courts'
        if models_visible and getattr(self,'_jersey_preview_row',None):return self.refresh_jersey_preview()
        if models_visible and getattr(self,'_shoe_preview_active',False):return self.preview_shoes()
        if models_visible and getattr(self, '_direct_stadium_active', False):return self.preview_stadium()
        try: archive=self.preview_archive()
        except ValueError as error:return self.show_error(str(error))
        if models_visible and getattr(self,'_scene_record_index',None) is not None and hasattr(self,'scene_source'):
            from .services import inspect_scene_with_game_layers
            index=self._scene_record_index
            include_all=self.scene_complete.isChecked()
            scene_source=self.scene_source
            record_name=getattr(self,'_scene_record_name',None)
            def load(job):
                source=self.preview_file(scene_source,archive)
                return source,inspect_scene_with_game_layers(source,index,archive,include_all,job,record_name=record_name)
            def display(value):
                source,result=value;self.scene_parts.clear();self.scene_textures.clear();self.show_scene_preview(result,source)
            self.run_job('Reload scene from selected preview source',load,display,cancellable=True)
        elif self.asset_path:
            source=self.asset_path
            self.run_job('Reload textures from selected preview source',lambda job:inspect_asset(self.preview_file(source,archive)),self.display_asset)

    def display_asset(self, result):

        self.asset_path = result["path"]

        self.asset_label.setText(self.asset_path.name)

        self.nested.clear()

        from ..archive.catalog import record_references
        records=record_references(self.asset_path.name,result['records'],getattr(self,'nba_roster',None) or self.roster)
        self.nested.setHeaderLabels(['Record','Type','Index','Roster references'])
        self.nested.header().setStretchLastSection(True)
        self.nested.setColumnWidth(3, 480)

        for rec in records:
            item = QTreeWidgetItem(
                self.nested,
                [str(rec.get('name') or ''), str(rec.get('type') or ''), str(rec['index']),rec['references']],
            )
            item.setToolTip(3, rec['references'].replace('; ', '\n'))

        set_rows(
            self.textures,
            result["textures"],
            [
                ("name", "Texture"),
                ("kind", "Container"),
                ("editable", "Layout supported"),
                ("metadata", "Metadata"),
            ],
        )

        raw = result["hex"]

        self.hex.setPlainText(
            "\n".join(
                f"{i:08X}  "
                + raw[i : i + 16].hex(" ")
                + "  "
                + "".join(chr(b) if 32 <= b < 127 else "." for b in raw[i : i + 16])
                for i in range(0, len(raw), 16)
            )
        )

        self.image.clear()
        self.explorer_image.setText(result["warning"] or "No supported textures in this asset")
        self.explorer_texture.clear()
        for texture in result["textures"]:
            if texture["editable"] and "reason" not in texture["metadata"]:
                info = texture["metadata"]
                self.explorer_texture.addItem(
                    f"{texture['name']} — {info.get('width', '?')} × {info.get('height', '?')} {info.get('format', '')}",
                    texture["name"],
                )
        self.explorer_texture.setEnabled(self.explorer_texture.count() > 0)
        if self.explorer_texture.count():
            self.explorer_image.setText("Loading texture preview…")
            # The inspection worker emits finished after its result callback.
            QTimer.singleShot(0, self.preview_explorer_texture)

        self.log(
            f"Inspected {self.asset_path.name}: {len(result['records'])} records, {len(result['textures'])} texture candidates. {result['warning']}"
        )

    def create_texture(self):

        layout = self.page(
            "Texture editor",
            "Export DDS, preserve dimensions/format/mips in your image editor, then import into a new container. Unsupported layouts stay raw-exportable.",
        )

        self.asset_label = QLabel("Open an archive asset or extracted file")

        layout.addWidget(self.asset_label)

        self.buttons(
            layout,
            [
                ("Open asset…", self.choose_asset),
                ("Export textures…", self.export_textures),
                ("Preview DDS…", self.preview_dds),
                ("Import edited DDS…", self.import_dds),
            ],
        )

        self.textures = table()

        self.textures.doubleClicked.connect(self.preview_texture)

        layout.addWidget(self.textures)

        self.image = TexturePreview("DDS previews appear here")

        self.image.setAlignment(Qt.AlignmentFlag.AlignCenter)

        scroll = QScrollArea()

        scroll.setWidgetResizable(True)

        scroll.setWidget(self.image)

        layout.addWidget(scroll)

    def export_textures(self):

        if not self.asset_path:
            return self.log("Open an asset first.")

        path = QFileDialog.getExistingDirectory(
            self, "Choose new texture export folder under output/", str(OUTPUT / "rips")
        )

        if path:
            from ..texture_tools.pipeline import export

            source = self.asset_path

            cdf = source.with_suffix(".cdf")

            self.run_job(
                "Export DDS and raw textures",
                lambda job: export(source, path, cdf if cdf.exists() else None),
            )

    def preview_dds(self):

        path, _ = QFileDialog.getOpenFileName(
            self, "Select DDS or PNG preview", str(OUTPUT), "Images (*.dds *.png)"
        )

        if not path:
            return

        def decode(job):

            from PIL import Image

            with Image.open(path) as image:
                if image.width * image.height > 32 * 1024 * 1024:
                    raise ValueError("Image exceeds interactive pixel limit")
                image.load()

                image.thumbnail((2048, 2048))

                rgba = image.convert("RGBA")

                return rgba.size, rgba.tobytes()

        def display(result):

            (w, h), raw = result

            image = QImage(raw, w, h, w * 4, QImage.Format.Format_RGBA8888).copy()

            self.image.setPixmap(QPixmap.fromImage(image))

        self.run_job("Decode image preview", decode, display)

    def preview_explorer_texture(self, index=None):
        selector = self.explorer_texture.currentData()
        if selector and self.asset_path:
            if self.active:
                QTimer.singleShot(20, self.preview_explorer_texture)
                return
            self.decode_texture_preview(selector, self.explorer_image)

    def preview_texture(self):

        rows = selected(self.textures)

        if not self.asset_path or len(rows) != 1:
            return

        self.decode_texture_preview(rows[0]["name"], self.image)

    def decode_texture_preview(self, selector, target):
        source = self.asset_path
        try: archive=self.preview_archive()
        except ValueError as error:return self.show_error(str(error))
        target.setText("Loading texture preview…")

        def decode(job):
            from .services import decode_texture_preview
            return decode_texture_preview(self.preview_file(source,archive), selector)

        def display(result):

            (w, h), raw = result

            image = QImage(raw, w, h, w * 4, QImage.Format.Format_RGBA8888).copy()

            if self.asset_path == source:
                target.setPixmap(QPixmap.fromImage(image))

        def decode_with_status(job):
            try:
                return decode(job)
            except Exception as error:
                return str(error)

        def display_with_status(result):
            if isinstance(result, str):
                target.setText("Preview unavailable: " + result)
                self.log("Preview unavailable: " + result)
            else:
                display(result)

        self.run_job("Preview selected texture", decode_with_status, display_with_status)

    def open_conference_logo(self, index):
        if self.active or index is None:
            return
        from ..roster.conference_assets import logo_record
        try:
            name = logo_record(index)
            archive = self.preview_archive()
            if archive is None:
                raise ValueError('Open a source JB folder first')
            matches = [e for e in archive.entries if e.get('name') == 'teamselectlogo.iff']
            if len(matches) != 1:
                raise ValueError('No unique teamselectlogo.iff bank in the selected preview source')
        except ValueError as error:
            return self.show_error(str(error))

        def inspect(job):
            result = inspect_asset(materialize(archive, matches[0]))
            if sum(row['name'] == name for row in result['textures']) != 1:
                raise ValueError(f'No unique {name} texture in the selected logo bank')
            return result

        def display(result):
            self.display_asset(result)
            self._scene_record_index = None
            self._shoe_preview_active = False
            self._jersey_preview_row = None
            for row in range(self.textures.model().rowCount()):
                if self.textures.model().index(row, 0).data(Qt.ItemDataRole.UserRole) == name:
                    self.textures.selectRow(row)
                    break
            self.explorer_texture.setCurrentIndex(self.explorer_texture.findData(name))
            self.navigate_to('Texture Editor')
            def preview_when_idle():
                if self.asset_path != result['path']:
                    return
                if self.active:
                    QTimer.singleShot(20, preview_when_idle)
                else:
                    self.decode_texture_preview(name, self.image)
            QTimer.singleShot(0, preview_when_idle)
        self.run_job('Open conference logo ' + name, inspect, display)

    def import_dds(self):

        rows = selected(self.textures)

        if not self.asset_path or len(rows) != 1:
            return self.log("Select one texture row first.")

        dds, _ = QFileDialog.getOpenFileName(
            self, "Edited DDS (dimensions, format and mip count may change)", str(OUTPUT), "DDS (*.dds)"
        )

        if not dds:
            return

        source = self.asset_path

        cdf = source.with_suffix(".cdf")

        if cdf.exists():
            output = QFileDialog.getExistingDirectory(
                self,
                "Choose new paired output folder under output/",
                str(OUTPUT / "temp"),
            )

        else:
            output, _ = QFileDialog.getSaveFileName(
                self,
                "Save new container under output/",
                str(OUTPUT / "temp" / source.name),
            )

        if output:
            from ..texture_tools.pipeline import import_texture

            self.run_job(
                "Validate and import texture",
                lambda job: import_texture(
                    source, rows[0]["name"], dds, output, cdf if cdf.exists() else None, dynamic=True
                ),
            )

    def create_roster(self):

        layout = self.page(
            "Roster / Legacy save editor",
            "Edit confirmed roster fields in roster files or the embedded roster in a Legacy-mode USERDATA save. Save a copy; unsupported Legacy-mode state is preserved.",
        )

        self.buttons(
            layout,
            [
                ("Open roster / Legacy save…", self.choose_roster),
                ("Load from JB", self.load_game_roster),
                ("Load from overrides", lambda: self.load_game_roster(True)),
                ("Undo", self.undo_roster),
                ("Redo", self.redo_roster),
                ("Save copy…", self.save_roster),
            ],
        )

        from .nba_roster import NBARosterPanel
        self.nba_roster=None
        self.nba_panel=NBARosterPanel(self);layout.addWidget(self.nba_panel,1);self.nba_panel.hide()
        self.ch_roster_panel=QWidget();layout.addWidget(self.ch_roster_panel,1)
        layout=QVBoxLayout(self.ch_roster_panel)
        from PySide6.QtWidgets import QMenu
        extra=QHBoxLayout()
        export_button=QPushButton('Export…');export_menu=QMenu(export_button)
        export_menu.addAction('Roster IFF…',self.export_game_roster)
        export_menu.addAction('Save data (USERDATA)…',self.export_roster_userdata)
        from .roster_bulk import export_csv,import_csv,compare_roster
        export_menu.addAction('Roster CSV…',lambda:export_csv(self))
        export_button.setMenu(export_menu);extra.addWidget(export_button);extra.addStretch()
        assets_button=QPushButton("Team assets…")
        assets_button.clicked.connect(lambda:self.navigation.setCurrentItem(self.navigation.findItems('Team Assets',Qt.MatchFlag.MatchExactly)[0]))
        extra.addWidget(assets_button)
        save_overrides=QPushButton('Save roster to overrides')
        def save_current_overrides():
            if not self.roster or self.active:return
            from .team_assets import save_payload_to_overrides
            save_payload_to_overrides(self,bytes(self.roster.data))
        save_overrides.clicked.connect(save_current_overrides);extra.addWidget(save_overrides)
        import_button=QPushButton('Import / compare…');import_menu=QMenu(import_button)
        import_menu.addAction('Edited CSV…',lambda:import_csv(self))
        import_menu.addAction('Compare another roster…',lambda:compare_roster(self))
        import_button.setMenu(import_menu);extra.addWidget(import_button)
        from .legacy_recruiting import open_recruiting_diagnostics
        recruiting_button=QPushButton('Recruiting diagnostics…')
        recruiting_button.clicked.connect(lambda:open_recruiting_diagnostics(self))
        extra.addWidget(recruiting_button)
        layout.addLayout(extra)

        self.roster_search = QLineEdit()

        self.roster_search.setPlaceholderText("Search current roster table")

        self.roster_search.textChanged.connect(lambda value: self.filter_roster(value))

        layout.addWidget(self.roster_search)
        self.player_school_filter=QComboBox();self.player_school_filter.addItem('All schools',None)
        self.player_school_filter.currentIndexChanged.connect(lambda _:self.roster_views['players'].model().choose_school(self.player_school_filter.currentData()) if self.roster_views['players'].model() else None)
        layout.addWidget(self.player_school_filter)

        self.roster_tabs = QTabWidget()

        self.roster_views = {}

        for name in ("players", "teams", "arenas", "coaches", "conferences", "uniforms"):
            view = table()

            self.roster_views[name] = view

            self.roster_tabs.addTab(view, "Schools" if name=='teams' else name.title())
        self.roster_views['schools']=self.roster_views['teams']

        # Keep category tabs outside the row-scrolling viewports.
        self.roster_tabs.tabBar().setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        from .player_details import PlayerDetails
        from .roster_panels import RecordDetails
        self.player_details=PlayerDetails(self)
        self.roster_detail_stack=QStackedWidget();self.roster_detail_stack.addWidget(self.player_details)
        self.record_panels={}
        for table_name in ('teams','arenas','coaches','conferences','uniforms'):
            panel=RecordDetails(self,table_name);self.record_panels[table_name]=panel;self.roster_detail_stack.addWidget(panel)
        splitter=QSplitter();splitter.addWidget(self.roster_tabs);splitter.addWidget(self.roster_detail_stack)
        splitter.setStretchFactor(0,3);splitter.setStretchFactor(1,2)
        layout.addWidget(splitter,1)
        self.roster_tabs.currentChanged.connect(lambda _:self.update_player_details())
        self.roster_views['players'].doubleClicked.connect(lambda _:self.edit_roster())

        self.roster_state = QLabel("No roster loaded")

        layout.addWidget(self.roster_state)

    def filter_roster(self, text):

        for view in self.roster_views.values():
            if view.model():
                view.model().setFilterFixedString(text)

    def update_player_details(self):
        if getattr(self,'_roster_refreshing',False):return
        view=self.roster_tabs.currentWidget()
        name=next((key for key,value in self.roster_views.items() if value is view),'players')
        rows=selected(view) if view and view.model() else []
        row=rows[0] if len(rows)==1 and self.roster else None
        panel=self.player_details if name=='players' else self.record_panels[name]
        self.roster_detail_stack.setCurrentWidget(panel)
        if name=='players':panel.show_player(row)
        else:panel.show_record(row)

    def choose_roster(self):

        path, _ = QFileDialog.getOpenFileName(
            self, "Open roster or Legacy-mode save", "", "Roster and save files (*.iff *.rost *.zip USERDATA* *USERDATA*);;All files (*)"
        )

        if path:
            from ..roster.editor_model import EditorModel

            self.run_job(
                "Load roster", lambda job: EditorModel.open(path), self.display_roster
            )

    def load_game_roster(self, from_overrides=False):
        if not self.archive:
            return self.log("Open a source JB folder first.")
        try:
            archive=self.preview_archive(use_overrides=bool(from_overrides))
            title=getattr(archive,'game_info',{}).get('TITLE','').casefold()
            roster_name='roster.iff' if title.startswith('nba 2k') or getattr(archive,'toc_layout',None)=='size64-hash-offset' else 'roster_english.iff'
            matches=[e for e in archive.entries if e['name'] and e['name'].casefold()==roster_name]
            if len(matches)!=1:
                raise ValueError("Roster identity is missing or ambiguous.")
            if from_overrides and matches[0]['index'] not in archive.replacements:
                raise ValueError("The selected overrides contain no roster_english.iff replacement.")
        except (ValueError,OSError) as error:
            return self.show_error(str(error))
        from ..roster.editor_model import EditorModel
        self.run_job(
            "Load overrides roster" if from_overrides else "Load source JB roster",
            lambda job: EditorModel.open(materialize(archive,matches[0])),
            self.display_roster,
        )

    def display_roster(self, model):
        diagnostics=getattr(self,'recruiting_diagnostics',None)
        if diagnostics is not None:diagnostics.close()
        from ..roster.nba import NBARosterModel
        if isinstance(model,NBARosterModel):
            self.nba_roster=model;self.roster=None
            self.ch_roster_panel.hide();self.nba_panel.show();self.nba_panel.set_model(model);self.refresh_catalog()
            return
        self.nba_roster=None;self.nba_panel.hide();self.ch_roster_panel.show()
        same_roster=self.roster is model
        context=getattr(self,'_jersey_preview_row',None)
        if context and context.get('preview_player_index') is not None:
            if not same_roster:
                self._jersey_preview_row={**context,'preview_player_index':None,'preview_number':None}
                for mesh in getattr(self,'scene_meshes',[]):
                    for batch in mesh['batches']:
                        for field in ('number_texture','number_uv','back_number_uv'):batch.pop(field,None)
            elif context.get('preview_number')!=model.rows['players'][context['preview_player_index']]['jersey_number']:
                QTimer.singleShot(0,self.reload_preview_source)
        keep={name:[r['index'] for r in selected(view)] if view.model() and self.roster is model else [] for name,view in self.roster_views.items() if name!='schools'}
        self._roster_refreshing=True
        self.roster = model
        self.refresh_catalog()
        school_filter=self.player_school_filter.currentData() if same_roster else None
        self.player_school_filter.blockSignals(True);self.player_school_filter.clear();self.player_school_filter.addItem('All schools',None)
        owners={}
        for school in model.rows.get('teams',[]):
            self.player_school_filter.addItem(school['school_name'],school['index'])
            for player in school['roster_slots']:
                if player is not None:owners.setdefault(player,[]).append(school['index'])
        self.player_school_filter.setCurrentIndex(max(0,self.player_school_filter.findData(school_filter)));self.player_school_filter.blockSignals(False)
        self.refresh_uniform_list()
        if hasattr(self,'scene_school'):
            previous=self.scene_school.currentData() if same_roster else None;self.scene_school.blockSignals(True);self.scene_school.clear();self.scene_school.addItem('Automatic school association',None)
            for school in model.rows.get('teams',[]):self.scene_school.addItem(school['school_name'],school['index'])
            self.scene_school.setCurrentIndex(max(0,self.scene_school.findData(previous)));self.scene_school.blockSignals(False)
        if getattr(self, "scene_meshes", None):
            self.select_scene_part()

        for name, view in self.roster_views.items():
            if name=='schools':continue
            rows = model.rows.get("teams" if name=="schools" else name, [])

            columns = (
                [
                    (key, key.replace("_", " ").title())
                    for key in rows[0]
                    if key != "row_offset"
                ]
                if rows
                else []
            )

            identity = 'display_name' if name=='players' else 'school_name' if name in ('teams','schools') else 'arena_name' if name=='arenas' else 'coach_name' if name=='coaches' else 'conference_name'
            columns.sort(key=lambda col: (0 if col[0]==identity else 1 if col[0]=='index' else 2))
            if name=='players':
                rows=[dict(row,school_indices=owners.get(row['index'],[]),school_name=' / '.join(model.rows['teams'][i]['school_name'] for i in owners.get(row['index'],[]))) for row in rows]
                columns=[('display_name','Player'),('school_name','School'),('jersey_number','Number'),('height_inches','Height'),('position_code','Position'),('scholarship_status','Scholarship'),('weight_lbs','Weight'),('hand_code','Hand')]
            elif name=='teams':
                conferences={r['index']:r['conference_name'] for r in model.rows.get('conferences',[])}
                rows=[dict(r,conference_name=conferences.get(r.get('conference_index'),'None')) for r in rows]
                columns=[('school_name','School'),('abbreviation','Abbreviation'),('conference_name','Conference'),('asset_id','Asset ID')]
            set_rows(view, rows, columns, self.roster_search.text())
            if name=='players':view.model().choose_school(school_filter)
            view.selectionModel().selectionChanged.connect(lambda *_:self.update_player_details())
            if len(keep.get(name,[]))==1:
                selected_index=keep[name][0]
                for i in range(view.model().rowCount()):
                    source=view.model().mapToSource(view.model().index(i,0))
                    if view.model().sourceModel().rows[source.row()]['index']==selected_index:view.selectRow(i);break
        self._roster_refreshing=False
        self.update_player_details()

        warnings=len(model.validate()['preserved_source_string_issues'])
        self.roster_state.setText(
            f"{len(model.rows['players']):,} players • {len(model.edits)} unsaved edits"
            +(f' • {warnings} unchanged source string warnings' if warnings else '')
            +(' • Legacy save: only the embedded roster is editable; other mode data is preserved' if model.source.kind=='legacy-save' else '')
        )

    def pick_rgba(self, value, parent):
        rgba = bytes.fromhex(value.removeprefix('#'))
        picker = QColorDialog(QColor(*rgba), parent)
        picker.setWindowTitle('Choose palette RGB color')
        picker.setOptions(QColorDialog.ColorDialogOption.DontUseNativeDialog |
                          QColorDialog.ColorDialogOption.ShowAlphaChannel)
        for control in picker.findChildren(QPushButton):
            if 'screen' in control.text().casefold():control.hide()
        if picker.exec() != QDialog.DialogCode.Accepted:return None
        color = picker.currentColor()
        return f'#{color.red():02X}{color.green():02X}{color.blue():02X}{color.alpha():02X}'




    def move_school(self):
        if not self.roster or self.active:return
        view=self.roster_tabs.currentWidget()
        if view not in (self.roster_views['teams'],self.roster_views['schools']):return self.log('Select a school in Teams or Edit Schools.')
        rows=selected(view)
        if len(rows)!=1:return self.log('Select exactly one school.')
        row=rows[0];conferences=self.roster.rows.get('conferences',[])
        dialog=QDialog(self);dialog.setWindowTitle('Conference realignment')
        form=QFormLayout(dialog);choices=QComboBox()
        for conf in conferences:choices.addItem(str(conf['index'])+': '+conf['conference_name'],conf['index'])
        choices.setCurrentIndex(max(0,choices.findData(row.get('conference_index'))))
        form.addRow('Destination conference',choices)
        buttons=QDialogButtonBox(QDialogButtonBox.StandardButton.Ok|QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(dialog.accept);buttons.rejected.connect(dialog.reject);form.addRow(buttons)
        if dialog.exec()!=QDialog.DialogCode.Accepted:return
        try:
            self.roster.move_team_to_conference(row['index'],choices.currentData())
            self.display_roster(self.roster)
        except ValueError as error:QMessageBox.warning(self,'School move blocked',str(error))


    def show_team_palette(self, team_index=None):
        if not self.roster:return self.log('Load a roster first.')
        if team_index is None or isinstance(team_index,bool):
            rows=selected(self.roster_views['teams'])
            if len(rows)!=1:return self.log('Select one school.')
            team_index=rows[0]['index']
        self.navigate_to('Roster Editor');self.roster_tabs.setCurrentWidget(self.roster_views['teams']);self.roster_search.clear()
        view=self.roster_views['teams'];proxy=view.model()
        for i in range(proxy.rowCount()):
            source=proxy.mapToSource(proxy.index(i,0))
            if proxy.sourceModel().rows[source.row()]['index']==team_index:view.selectRow(i);break
        panel=self.record_panels['teams'];panel.setCurrentWidget(panel.palette_view)



    def scene_team_palette(self):
        import re
        if not self.roster or not hasattr(self, 'scene_source'):
            return self.log("Load the game roster in Roster Editor, then open a stadium scene.")
        match = re.fullmatch(r's(\d+)', self.scene_source.stem, re.IGNORECASE)
        teams = [t for t in self.roster.rows['teams'] if match and t['asset_id'] == int(match[1])]
        if len(teams) != 1:
            return self.log("Stadium asset ID has no unique team match in the loaded roster.")
        self.show_team_palette(teams[0]['index'])

    def research_roster(self):
        if not self.roster:
            return self.log("Load a roster first.")
        from ..roster.research import analyze
        from ..core.reports import save_json
        import uuid
        path = OUTPUT / 'reports' / ('roster_layout_'+uuid.uuid4().hex+'.json')
        def research(job):
            report = analyze(self.roster)
            save_json(path,report)
            return {'report':str(path),'semantic_mapping_complete':False}
        self.run_job('Profile roster fields and unresolved regions',research)

    def edit_roster(self):
        self.update_player_details()
        panel=self.roster_detail_stack.currentWidget()
        if panel:panel.setCurrentIndex(0)

    def undo_roster(self):
        if self.nba_roster and not self.active:
            self.nba_roster.undo();self.nba_panel.populate();return

        if self.roster and not self.active:

            def undo(job):

                self.roster.undo()

                return self.roster

            self.run_job("Undo roster edit", undo, self.display_roster)

    def redo_roster(self):
        if self.nba_roster and not self.active:
            self.nba_roster.redo();self.nba_panel.populate();return

        if self.roster and not self.active:

            def redo(job):

                self.roster.redo()

                return self.roster

            self.run_job("Redo roster edit", redo, self.display_roster)

    def export_game_roster(self):
        if not self.roster or self.active:return
        if self.roster.source.kind=='standard-iff':
            template=self.roster.source.original
        elif self.archive:
            entries=[entry for entry in self.archive.entries if entry['name']=='roster_english.iff']
            if len(entries)!=1:return self.show_error('The loaded JB has no unique roster_english.iff.')
            template=self.archive.read(entries[0])
        else:
            path,_=QFileDialog.getOpenFileName(self,'Choose a roster IFF template','','Roster IFF (*.iff)')
            if not path:return
            try:template=Path(path).read_bytes()
            except OSError as error:return self.show_error(str(error))
        output,_=QFileDialog.getSaveFileName(self,'Export edited roster IFF',str(OUTPUT/'rosters'/'roster_english.iff'),'Roster IFF (*.iff)')
        if not output:return
        from ..roster.workflow import export_game_roster
        self.run_job('Export roster IFF',lambda job:export_game_roster(self.roster,template,output))

    def export_roster_userdata(self):
        if not self.roster or self.active:return
        output,_=QFileDialog.getSaveFileName(self,'Export decrypted save data',str(OUTPUT/'rosters'/'USERDATA'),'All files (*)')
        if not output:return
        from ..roster.workflow import export_userdata
        self.run_job('Export decrypted USERDATA',lambda job:export_userdata(self.roster,output))

    def save_roster(self):
        if self.nba_roster:return self.nba_panel.save()

        if not self.roster:
            return

        filename={'save-zip':'roster_edited.zip','userdata':'USERDATA','legacy-save':'USERDATA_legacy_edited','raw-rost':'roster_edited.rost','tool-wrapper':'roster_edited.rost'}.get(self.roster.source.kind,'roster_english.iff')
        output, _ = QFileDialog.getSaveFileName(
            self,
            "Save roster copy under output/",
            str(OUTPUT / "rosters" / filename),
        )

        if output:
            from ..roster.workflow import save_model

            self.run_job(
                "Save and reparse roster copy",
                lambda job: save_model(self.roster, output),
            )

    def prepare_court_template(self):
        source,_=QFileDialog.getOpenFileName(self,'Select full court template ZIP','','Court template (*.zip)')
        if not source:return
        from ..modding.court_template import prepare
        import uuid
        output=OUTPUT/'templates'/('single_surface_court_'+uuid.uuid4().hex[:8])
        def completed(result):
            self.model_details.setPlainText(json.dumps(result,indent=2))
            QMessageBox.information(self,'Court template ready',
                'Prepared floor and two texture overrides:\n'+result['floor']+'\n\nCopy the prepared folder into your overrides. Gameplay compatibility still requires your manual check.')
        self.run_job('Prepare single-texture court',lambda job:prepare(source,output,job),completed,cancellable=True)

    def create_models(self):
        layout = self.page(
            "Models / Courts • 3D preview",
            "Select a SCNE record in Explorer, then Preview scene. Left-drag: orbit; right-drag: look around; middle-drag or Shift-drag: pan. WASD: move; Q/E: down/up; Shift: faster; Ctrl: slower; wheel: zoom; F: fit. Material textures load automatically. Use cutaway to see inside; game shader effects are not reproduced.",
        )
        page_layout=layout
        controls=QWidget()
        layout=QVBoxLayout(controls)
        layout.setContentsMargins(4,4,4,4)
        controls_scroll=QScrollArea()
        controls_scroll.setWidgetResizable(True)
        controls_scroll.setWidget(controls)
        controls_scroll.setMinimumHeight(70)
        preview=QWidget()
        preview_layout=QVBoxLayout(preview)
        preview_layout.setContentsMargins(0,0,0,0)
        self.scene_splitter=QSplitter(Qt.Orientation.Vertical)
        self.scene_splitter.setHandleWidth(9)
        self.scene_splitter.setChildrenCollapsible(False)
        self.scene_splitter.setToolTip('Drag the divider to resize the preview and controls')
        self.scene_splitter.addWidget(controls_scroll)
        self.scene_splitter.addWidget(preview)
        self.scene_splitter.setStretchFactor(0,0)
        self.scene_splitter.setStretchFactor(1,1)
        page_layout.addWidget(self.scene_splitter,1)
        self.buttons(layout, [("Preview selected SCNE", self.inspect_scene), ("Prepare single-texture court…", self.prepare_court_template)])
        from PySide6.QtWidgets import QMenu
        uniform_mesh_button=QPushButton('Uniform meshes…')
        uniform_mesh_menu=QMenu(uniform_mesh_button)
        uniform_mesh_menu.addAction('Export all editable uniform models',lambda:self.uniform_mesh_export(False))
        uniform_mesh_menu.addAction('Prepare experimental modern fit',lambda:self.uniform_mesh_export(True))
        uniform_mesh_menu.addAction('Reimport edited uniform models…',self.uniform_mesh_import)
        uniform_mesh_button.setMenu(uniform_mesh_menu)
        layout.addWidget(uniform_mesh_button)
        self.scene_school=QComboBox();self.scene_school.addItem('Automatic school association',None)
        self.scene_school.currentIndexChanged.connect(lambda _:self.select_scene_part() if getattr(self,'scene_meshes',None) else None)
        layout.addWidget(self.scene_school)
        self.jersey_shape_controls=QWidget();shape_form=QFormLayout(self.jersey_shape_controls)
        self.jersey_neck=QComboBox()
        from ..roster.schema import JERSEY_SHAPES
        for value,label in JERSEY_SHAPES.items():self.jersey_neck.addItem(label,value)
        self.jersey_build=QComboBox();self.jersey_shorts=QComboBox()
        for box in (self.jersey_build,self.jersey_shorts):
            for value,label in [('thin','Thin'),('reg','Regular'),('fat','Fat')]:box.addItem(label,value)
        self.jersey_parts=QComboBox();self.jersey_parts.addItems(['Top + shorts','Top only','Shorts only'])
        for label,box in [('Neck',self.jersey_neck),('Jersey build',self.jersey_build),('Shorts cut',self.jersey_shorts),('Render',self.jersey_parts)]:
            shape_form.addRow(label,box);box.activated.connect(self.refresh_jersey_preview)
        layout.addWidget(self.jersey_shape_controls);self.jersey_shape_controls.hide();self._jersey_preview_row=None
        self.scene_complete = QCheckBox("Include all SCNE sections (arena and court)")
        self.scene_complete.setChecked(True)
        layout.addWidget(self.scene_complete)
        self.scene_cutaway = QCheckBox("Cutaway: hide roof and light-effect meshes")
        self.scene_cutaway.setChecked(True)
        self.scene_cutaway.toggled.connect(self.select_scene_part)
        layout.addWidget(self.scene_cutaway)
        self.scene_three_point = QCheckBox('Alignment guide: 3-point lines')
        self.scene_border = QCheckBox('Alignment guide: out-of-bounds borders')
        self.scene_key_center = QCheckBox('Alignment guide: key and center circle')
        for box in (self.scene_three_point, self.scene_border, self.scene_key_center):
            box.setChecked(False)
            box.toggled.connect(self.select_scene_part)
            layout.addWidget(box)
        self.scene_parts = QComboBox()
        self.scene_parts.activated.connect(self.select_scene_part)
        layout.addWidget(self.scene_parts)
        self.scene_textures = QComboBox()
        self.scene_textures.activated.connect(self.select_scene_texture)
        layout.addWidget(self.scene_textures)
        from .scene_view import SceneView
        self.scene_view = SceneView()
        self.scene_view.setMinimumSize(240,120)
        self.scene_view.setSizePolicy(QSizePolicy.Policy.Expanding,QSizePolicy.Policy.Expanding)
        preview_layout.addWidget(self.scene_view, 1)
        camera_speed = QDoubleSpinBox()
        camera_speed.setRange(.05, 10.)
        camera_speed.setValue(1.)
        camera_speed.setPrefix('Camera movement speed: ')
        camera_speed.valueChanged.connect(lambda value: setattr(self.scene_view, 'movement_speed', value))
        preview_layout.addWidget(camera_speed)
        self.buttons(preview_layout, [("Fit camera", self.scene_view.fit_camera), ("Linked roster palette…", self.scene_team_palette)])
        self.model_details = QPlainTextEdit()
        self.model_details.setReadOnly(True)
        self.model_details.setMaximumHeight(120)
        preview_layout.addWidget(self.model_details)
        self.scene_meshes = []
        self.scene_base_images = {}
        self.scene_uniform_images = {}
        self.scene_asset_tabs = QTabWidget()
        layout.addWidget(self.scene_asset_tabs)
        uniform_page = QWidget();uniform_layout = QVBoxLayout(uniform_page)
        shoe_page = QWidget();shoe_layout = QVBoxLayout(shoe_page)
        stadium_page = QWidget();stadium_layout = QVBoxLayout(stadium_page)
        self.scene_asset_tabs.addTab(uniform_page, 'Jerseys')
        self.scene_asset_tabs.addTab(shoe_page, 'Shoes')
        self.scene_asset_tabs.addTab(stadium_page, 'Stadiums / Floors')
        self.scene_uniforms = QComboBox()
        self.scene_uniforms.setEditable(False)
        self.scene_uniforms.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        self.scene_uniforms.activated.connect(self.select_scene_uniform)
        uniform_layout.addWidget(self.scene_uniforms)
        self.buttons(uniform_layout, [('Preview selected jersey', self.select_scene_uniform)])
        self.refresh_uniform_list()
        self.scene_shoes=QComboBox()
        self.scene_shoes.setEditable(False)
        shoe_layout.addWidget(self.scene_shoes)
        self.buttons(shoe_layout,[('Preview selected shoes',self.preview_shoes)])
        self.refresh_shoe_list()
        self.scene_stadiums = QComboBox()
        self.scene_stadiums.setEditable(False)
        self.scene_stadiums.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        stadium_layout.addWidget(self.scene_stadiums)
        self.scene_stadium_mode = QComboBox()
        self.scene_stadium_mode.addItems(['Arena and floor', 'Floor only', 'Arena only'])
        stadium_layout.addWidget(self.scene_stadium_mode)
        self.buttons(stadium_layout, [('Preview selected stadium / floor', self.preview_stadium)])
        self.refresh_stadium_list()
        self.scene_palette_state = QLabel('No roster associated; embedded material textures only')
        preview_layout.addWidget(self.scene_palette_state)
        layout.addStretch(1)
        self.scene_splitter.setSizes([220,650])

    def edit_roster_shoes(self):
        self.update_player_details();panel=self.roster_detail_stack.currentWidget()
        if hasattr(panel,'shoes'):panel.setCurrentWidget(panel.shoes)

    def preview_assigned_shoes(self):
        if self.active or not self.archive or not self.roster:return self.log('Load a JB folder and its roster first.')
        view=self.roster_tabs.currentWidget()
        if view not in (self.roster_views['players'],self.roster_views['teams'],self.roster_views['schools']):return self.log('Select one player or school.')
        rows=selected(view)
        if len(rows)!=1:return self.log('Select exactly one player or school.')
        choice,ok=QInputDialog.getItem(self,'Assigned shoes','Uniform side',['Home','Away'],0,False)
        if not ok:return
        name=rows[0].get('home_shoe_texture' if choice=='Home' else 'away_shoe_texture')
        entry=next((e for e in self.archive.entries if name and e['name']==name),None)
        if entry is None:return self.log('Assigned shoe package is missing or the shoe fields are unsupported.')
        self.scene_shoes.setCurrentIndex(self.scene_shoes.findData(entry['index']))
        self.preview_shoes()

    def preview_origin_label(self, entry):
        if not self.preview_overrides.isChecked():return ''
        if getattr(self, '_preview_origin_error', False):return ' [Overrides unavailable]'
        return ' [Override]' if entry['index'] in getattr(self, '_preview_replacement_indices', set()) else ' [JB fallback]'

    def refresh_preview_lists(self):
        self._preview_origin_error = False
        try:archive = self.preview_archive()
        except (ValueError,OSError):
            self._preview_origin_error = True
            archive = None
        self._preview_replacement_indices = set(getattr(archive, 'replacements', {}))
        if self.preview_overrides.isChecked():
            self.preview_source_info.setText('Overrides unavailable' if self._preview_origin_error else
                                            str(len(self._preview_replacement_indices)) + (' live archive overrides' if getattr(archive,'live',None) else ' prepared overrides — select folder again for live files'))
            self.preview_source_info.setToolTip(self.mod_path.text())
        else:
            self.preview_source_info.setText('Original JB assets')
            self.preview_source_info.setToolTip('')
        self.refresh_uniform_list();self.refresh_shoe_list();self.refresh_stadium_list()
        if self.archive and archive is not None:self.refresh_catalog(archive)

    def refresh_stadium_list(self):
        import re
        if not hasattr(self, 'scene_stadiums'):return
        current = self.scene_stadiums.currentData()
        self.scene_stadiums.clear()
        self.scene_stadiums.addItem('Choose a stadium from the loaded JB / overrides', None)
        teams = {}
        if self.roster:
            for row in self.roster.rows['teams']:
                teams.setdefault(row['asset_id'], []).append(row['school_name'])
        if self.archive:
            for entry in sorted(self.archive.entries, key=lambda e:e['name'] or ''):
                match = re.fullmatch(r'[sf](\d+)\.iff', entry['name'] or '', re.IGNORECASE)
                if not match:continue
                names = teams.get(int(match[1]), [])
                label = (names[0] + ' — ') if len(names) == 1 else ''
                self.scene_stadiums.addItem(label + entry['name'] + self.preview_origin_label(entry), entry['index'])
        self.scene_stadiums.setCurrentIndex(max(0, self.scene_stadiums.findData(current)))

    def preview_stadium(self):
        if self.active or not self.archive:return
        index = self.scene_stadiums.currentData()
        if index is None:return self.log('Choose a stadium package first.')
        try:archive = self.preview_archive()
        except ValueError as error:return self.show_error(str(error))
        from .services import inspect_stadium_preview
        entry = next(e for e in archive.entries if e['index'] == index)
        mode = self.scene_stadium_mode.currentIndex()
        def display(value):
            source, result = value
            self._direct_stadium_active = True
            self._jersey_preview_row = None
            self._shoe_preview_active = False
            self._scene_record_index = None
            self.jersey_shape_controls.hide()
            self.scene_parts.clear();self.scene_textures.clear()
            self.scene_view.set_image(None)
            self.navigate_to('Models / Courts')
            self.show_scene_preview(result, source)
        self.run_job('Preview stadium geometry and textures',
                     lambda job:inspect_stadium_preview(archive, entry, mode, job), display, cancellable=True)

    def refresh_shoe_list(self):
        import re
        current = self.scene_shoes.currentData()
        self.scene_shoes.clear()
        self.scene_shoes.addItem('Choose shoes from the loaded JB / overrides',None)
        if not self.archive:return
        from ..roster.shoes import BRANDS,COLORS
        for entry in sorted(self.archive.entries,key=lambda e:e['name'] or ''):
            name=entry['name'] or ''
            match=re.fullmatch(r'shoe_(\d+)(?:_(\d{2}))?\.iff',name,re.I)
            if not match:continue
            family=int(match[1]);color=match[2]
            brand=0 if color is None else {1:1,2:2,3:3,5:4}.get(family//100)
            label=BRANDS.get(brand,'Shoe')+' — '+COLORS.get(int(color) if color else family,'Color '+str(color))+' — '+name
            self.scene_shoes.addItem(label + self.preview_origin_label(entry),entry['index'])
        self.scene_shoes.setCurrentIndex(max(0, self.scene_shoes.findData(current)))

    def preview_shoes(self):
        if self.active or not self.archive:return
        index=self.scene_shoes.currentData()
        if index is None:return self.log('Choose a shoe texture package first.')
        from .services import inspect_shoe_preview
        try: archive=self.preview_archive()
        except ValueError as error:return self.show_error(str(error))
        entry=self.archive.entries[index]
        def display(value):
            self._direct_stadium_active=False
            self._shoe_preview_active=True;self._scene_record_index=None
            source,result=value
            self._jersey_preview_row=None;self.jersey_shape_controls.hide()
            self.navigate_to('Models / Courts')
            self.scene_view.set_meshes([]);self.scene_view.set_image(None)
            self.scene_parts.clear();self.scene_textures.clear()
            self.show_scene_preview(result,source)
        self.run_job('Preview shoe geometry and artwork',lambda job:inspect_shoe_preview(archive,entry,job),display,cancellable=True)

    def uniform_mesh_export(self, modern=False):
        if self.active or not self.archive:return
        import uuid
        from ..modding.uniform_mesh import export_archive
        try:archive=self.preview_archive()
        except ValueError as error:return self.show_error(str(error))
        output=OUTPUT/'uniform-models'/uuid.uuid4().hex[:10]
        def display(result):
            self.model_details.setPlainText(str(output)+'\n'+result['warning'])
            QMessageBox.information(self,'Uniform models exported',str(output)+'\n\n'+result['warning'])
        self.run_job('Prepare uniform mesh collection',lambda job:export_archive(archive,output,modern,job),display,cancellable=True)

    def uniform_mesh_import(self):
        if self.active:return
        import uuid
        folder=QFileDialog.getExistingDirectory(self,'Select exported collection containing originals and models')
        if not folder:return
        from ..modding.uniform_mesh import import_folder
        output=OUTPUT/'uniform-imports'/uuid.uuid4().hex[:10]
        def display(result):
            self.model_details.setPlainText(str(output)+'\n'+result['warning'])
            QMessageBox.information(self,'Uniform overrides prepared',str(output)+'\n\n'+result['warning'])
        self.run_job('Reimport edited uniform models',lambda job:import_folder(folder,output,job),display,cancellable=True)

    def refresh_uniform_list(self):
        import re
        selected_id = self.scene_uniforms.currentData()
        self.scene_uniforms.clear()
        self.scene_uniforms.addItem('Choose a uniform from the loaded JB / overrides', None)
        teams = {}
        if self.roster:
            for team in self.roster.rows['teams']:
                teams.setdefault(team['asset_id'], []).append(team['school_name'])
        linked_names = {}
        if self.roster:
            from ..roster.uniforms import asset_name
            for row in self.roster.rows.get('uniforms', []):
                try:name=asset_name(row)
                except ValueError:continue
                linked_names.setdefault(name,set()).update(teams.get(row['team_asset_id'],[]))
        if self.archive:
            for entry in sorted(self.archive.entries, key=lambda e:e['name'] or ''):
                match=re.fullmatch(r'u([haxyz])(\d+)\.iff',entry['name'] or '',re.IGNORECASE)
                if not match:continue
                names=sorted(linked_names.get(entry['name'],teams.get(int(match[2]),[])))
                label=(names[0]+' - ') if len(names)==1 else ''
                label += {'h':'Home','a':'Away','x':'Alternate 1','y':'Alternate 2','z':'Alternate 3'}[match[1].lower()]+' - '+entry['name']
                self.scene_uniforms.addItem(label + self.preview_origin_label(entry),entry['index'])
        self.scene_uniforms.setCurrentIndex(max(0,self.scene_uniforms.findData(selected_id)))

    def choose_scene_uniform_file(self):
        path,_=QFileDialog.getOpenFileName(self,'Select uniform IFF','','Uniform containers (*.iff);;All files (*)')
        if path:self.load_scene_uniform(Path(path))

    def select_scene_uniform(self, index=None):
        entry_index=self.scene_uniforms.currentData()
        if entry_index is None or not self.archive:return
        entry=self.archive.entries[entry_index]
        import re
        match = re.fullmatch(r'u([haxyz])(\d+)\.iff', entry['name'] or '', re.IGNORECASE)
        if not match:return self.log('Choose a uniform package first.')
        uniform = {'variant_code': 'haxyz'.index(match[1].lower()), 'uniform_asset_id': int(match[2])}
        if self._jersey_preview_row:
            uniform.update({key:self._jersey_preview_row.get(key) for key in ('preview_number','preview_player_index','preview_name')})
        self.preview_jersey(uniform, self.jersey_neck.currentData(), self.jersey_build.currentData(),
                           self.jersey_shorts.currentData(), self.jersey_parts.currentIndex())


    def load_scene_uniform(self, source, entry=None):
        if source is not None and self._jersey_preview_row:
            self.preview_jersey({'preview_path':str(source)},self.jersey_neck.currentData(),self.jersey_build.currentData(),self.jersey_shorts.currentData(),self.jersey_parts.currentIndex())
            return
        if not any(m.get('uniform_surface') for m in self.scene_meshes):
            return self.log('Preview a cloth jersey or shorts scene first.')
        from .services import inspect_uniform_preview
        try: archive=self.preview_archive()
        except ValueError as error:return self.show_error(str(error))
        def work(job):
            path=materialize(archive,entry) if entry is not None else self.preview_file(source,archive)
            return inspect_uniform_preview(path,job)
        def display(images):
            self.scene_uniform_images={role:QImage(raw,w,h,w*4,QImage.Format.Format_RGBA8888).copy()
                                       for role,((w,h),raw) in images.items()}
            material_images=dict(self.scene_base_images)
            material_images.update({'__uniform_'+role:image for role,image in self.scene_uniform_images.items()})
            self.scene_view.set_material_images(material_images)
            self.scene_textures.setCurrentIndex(0)
            self.scene_view.automatic=True
            self.scene_view.set_image(None)
            self.select_scene_part()
            self.log('Uniform preview loaded: '+(entry['name'] if entry is not None else source.name)+'. Authored uniform RGB is shown opaque; runtime material effects and player name/number overlays are not composited.')
        self.run_job('Load uniform preview textures',work,display)

    def inspect_scene(self):
        if not self.asset_path:
            return self.log("Open a stadium IFF in Explorer first.")
        items = self.nested.selectedItems()
        if items and items[0].text(1) == "SCNE":
            index = int(items[0].text(2))
        elif self.asset_path.suffix.lower() == '.scne':
            index = 0
        else:
            return self.log("Select a SCNE record in the Explorer nested list.")
        source = self.asset_path
        self._scene_record_name=items[0].text(0) if items and items[0].text(1)=='SCNE' else None
        try: archive=self.preview_archive()
        except ValueError as error:return self.show_error(str(error))
        record_name=self._scene_record_name
        self._direct_stadium_active=False
        self._scene_record_index=index;self._shoe_preview_active=False
        self._jersey_preview_row=None;self.jersey_shape_controls.hide()
        self.navigate_to('Models / Courts')
        self.scene_meshes = []
        self.scene_view.set_meshes([])
        self.scene_view.set_material_images({})
        self.scene_view.set_image(None)
        self.scene_parts.clear()
        self.scene_textures.clear()
        self.model_details.setPlainText("Loading scene…")
        from .services import inspect_scene_with_game_layers
        include_all = self.scene_complete.isChecked()
        def load(job):
            path=self.preview_file(source,archive)
            return path,inspect_scene_with_game_layers(path,index,archive,include_all,job,record_name=record_name)
        self.run_job('Decode scene geometry and textures',load,lambda value:self.show_scene_preview(value[1],value[0]),cancellable=True)

    def preview_jersey(self,uniform,neck,build,shorts,parts=0):
        if self.active or not self.archive:return
        from .services import inspect_jersey_preview
        try:archive=self.preview_archive()
        except ValueError as error:return self.show_error(str(error))
        uniform=dict(uniform)
        uniform.setdefault('preview_number',23)
        uniform.setdefault('preview_name','Reborn')
        if uniform.get('preview_player_index') is not None and self.roster:
            index=uniform['preview_player_index']
            if not 0<=index<len(self.roster.rows['players']):return self.show_error('Preview player no longer exists in the loaded roster')
            uniform['preview_number']=self.roster.rows['players'][index]['jersey_number']
        if uniform.get('preview_path'):
            try:uniform['preview_path']=str(self.preview_file(Path(uniform['preview_path']),archive))
            except (ValueError,OSError) as error:return self.show_error(str(error))
        def display(value):
            source,result=value;self._jersey_preview_row=dict(uniform)
            self._direct_stadium_active=False
            self._shoe_preview_active=False;self._scene_record_index=None
            self.scene_parts.clear();self.scene_textures.clear()
            self.jersey_neck.setCurrentIndex(self.jersey_neck.findData(neck));self.jersey_build.setCurrentIndex(self.jersey_build.findData(build));self.jersey_shorts.setCurrentIndex(self.jersey_shorts.findData(shorts));self.jersey_parts.setCurrentIndex(parts)
            self.navigate_to('Models / Courts');self.show_scene_preview(result,source);self.jersey_shape_controls.show()
        self.run_job('Preview jersey and shorts',lambda job:inspect_jersey_preview(archive,uniform,neck,build,shorts,parts,job),display,cancellable=True)

    def refresh_jersey_preview(self,*_):
        if self._jersey_preview_row:self.preview_jersey(self._jersey_preview_row,self.jersey_neck.currentData(),self.jersey_build.currentData(),self.jersey_shorts.currentData(),self.jersey_parts.currentIndex())

    def show_scene_preview(self,result,source):
        self.scene_source = source
        self.scene_meshes = result['meshes']
        from ..formats.scene_palette import COURT_PALETTE_ROUTES
        layers = {b.get('reference_slot')
                  for m in self.scene_meshes if m.get('game_floor_layer') for b in m.get('batches', [])}
        for box, slots in ((self.scene_three_point, {18}), (self.scene_border, {4}), (self.scene_key_center, {2, 10, 20})):
            box.setEnabled(bool(slots & layers))
            box.setToolTip('Fixed stock court alignment guide, raised 1 game unit. '
                           'Independent of roster palettes and floor artwork.')
        self.scene_parts.addItem('All supported parts', -1)
        for i, mesh in enumerate(self.scene_meshes):
            self.scene_parts.addItem(mesh['name'], i)
        self.scene_textures.addItem('Automatic material textures', '__automatic__')
        self.scene_textures.addItem('Untextured', None)
        for name in result['textures']:
            self.scene_textures.addItem(name, name)
        images = {}
        for name, ((w,h), raw) in result['images'].items():
            images[name] = QImage(raw,w,h,w*4,QImage.Format.Format_RGBA8888).copy()
        self.scene_base_images = images
        self.scene_uniform_images = {}
        self.scene_view.automatic = True
        self.scene_view.set_material_images(images)
        self.select_scene_part()
        self.model_details.setPlainText(
            f"{len(self.scene_meshes)} supported parts; {sum(len(m['vertices'])//3 for m in self.scene_meshes)} triangles. {len(result['images'])} material textures loaded; use dropdown for overrides.\n"
            + '\n'.join(result['warnings'])
        )

    def select_scene_part(self, index=None):
        part = self.scene_parts.currentData()
        meshes = self.scene_meshes if part == -1 else [self.scene_meshes[part]] if part is not None else []
        if part not in (-1, None) and meshes and meshes[0].get('court_surface'):
            meshes = meshes + [m for m in self.scene_meshes if m.get('game_floor_layer')]
        if part == -1 and self.scene_cutaway.isChecked():
            meshes = [m for m in meshes if not m.get('hidden_by_default')]
        from ..formats.scene_palette import associate_palette, floor_layers
        import re
        match = re.fullmatch(r's(\d+)', self.scene_source.stem, re.IGNORECASE) if hasattr(self, 'scene_source') else None
        teams = [team for team in self.roster.rows['teams'] if match and team['asset_id'] == int(match[1])] if self.roster else []
        school=self.scene_school.currentData()
        if self.roster and school is not None:teams=[self.roster.rows['teams'][school]]
        colors = teams[0]['palette_colors'] if len(teams) == 1 else None
        meshes = associate_palette(meshes, colors)
        meshes = floor_layers(meshes, self.scene_three_point.isChecked(), self.scene_border.isChecked(), self.scene_key_center.isChecked())
        if self.scene_uniform_images:
            meshes = [{**mesh,'batches':[{**batch,'texture':'__uniform_'+mesh['uniform_surface'], 'palette_tint':None}
                                        for batch in mesh['batches']]}
                      if mesh.get('uniform_surface') in self.scene_uniform_images else mesh for mesh in meshes]
        if colors is not None:
            count = sum(batch['palette_tint'] is not None for mesh in meshes for batch in mesh['batches'])
            self.scene_palette_state.setText(f"Associated roster: {self.roster.source.source_path or 'current JB folder roster'}; {teams[0]['school_name']}; {count} court color bindings. Authored arena color/lightmap masks enabled; runtime effects remain under research.")
        else:
            self.scene_palette_state.setText('No unique roster/team association; embedded material textures only. Use Associate roster to select a matching roster.')
        self.scene_view.set_meshes(meshes, fit=not isinstance(index, bool))

    def select_scene_texture(self, index=None):
        name = self.scene_textures.currentData()
        self.scene_view.automatic = name == '__automatic__'
        self.scene_view.set_image(None)
        if name is None or name == '__automatic__':
            return
        if name in self.scene_base_images:
            self.scene_view.set_image(self.scene_base_images[name]);return
        from .services import decode_texture_preview
        def display(result):
            (w, h), raw = result
            self.scene_view.set_image(QImage(raw, w, h, w*4, QImage.Format.Format_RGBA8888).copy())
        self.run_job('Decode scene texture', lambda job: decode_texture_preview(self.scene_source, name), display)

    def create_builder(self):

        layout = self.page(
            "Mod builder",
            "Select an overrides folder in Explorer. Build JB copy checks compatibility and writes a separate JB folder.",
        )

        form = QFormLayout()

        self.mod_path = QLineEdit(str(OUTPUT / "builds" / "my_mod"))
        self.mod_path.editingFinished.connect(lambda:self.reload_preview_source() if self.preview_overrides.isChecked() else None)

        self.build_path = QLineEdit(str(OUTPUT / "builds" / "my_build"))

        form.addRow("Mod workspace", self.mod_path)

        form.addRow("New JB output", self.build_path)

        browse=QPushButton('Choose JB output folder…')
        browse.clicked.connect(self.choose_build_output)
        form.addRow('',browse)

        layout.addLayout(form)

        self.buttons(
            layout,
            [
                ("Export mod patch…", self.export_mod_patch),
                ("Import mod patch…", self.import_mod_patch),
                ("Build JB copy", lambda: self.build_game(False)),
            ],
        )

        self.build_details = QPlainTextEdit()

        self.build_details.setReadOnly(True)

        layout.addWidget(self.build_details)

    def choose_build_output(self):
        path=QFileDialog.getExistingDirectory(self,'Choose an empty JB output folder (any drive)',self.build_path.text())
        if path:self.build_path.setText(path)

    def stage_replacements(self):

        if not self.source:
            return self.log("Open a game first.")

        path = QFileDialog.getExistingDirectory(
            self, "Overrides folder (includes subfolders and DDS textures)", str(OUTPUT)
        )

        if path:
            mod = Path(self.mod_path.text())

            self.run_job(
                "Load overrides folder and check compatibility",
                lambda job: stage_folder(self.source, Path(path), mod, job),
                lambda result: self.builder_completed(result, "staging"),
                cancellable=True,
            )

    def export_mod_patch(self):

        if not self.source:
            return self.log("Open a game first.")

        output, _ = QFileDialog.getSaveFileName(
            self,
            "Export source-bound patch under output/",
            str(OUTPUT / "builds" / "my_mod.chpatch"),
            "CHoops patch (*.chpatch)",
        )

        if output:
            from ..modding.patch_package import export_patch

            source, mod = self.source, Path(self.mod_path.text())

            self.run_job(
                "Export mod differences",
                lambda job: export_patch(source, mod, Path(output)),
            )

    def import_mod_patch(self):

        if not self.source:
            return self.log("Open a game first.")

        package, _ = QFileDialog.getOpenFileName(
            self,
            "Import source-bound mod patch",
            str(OUTPUT),
            "CHoops patch (*.chpatch)",
        )

        if package:
            from ..modding.patch_package import import_patch

            source, mod = self.source, Path(self.mod_path.text())

            self.run_job(
                "Check and load mod patch",
                lambda job: import_patch(source, Path(package), mod),
            )

    def build_game(self, dry_run):

        if not self.source:
            return self.log("Open a game first.")

        from ..archive.build_copy import build

        mod, output = self.mod_path.text(), self.build_path.text()

        self.run_job(
            "Preflight mod" if dry_run else "Build separate JB copy",
            lambda job: build(self.source, mod, output, dry_run=dry_run, job=job),
            lambda result: self.builder_completed(result, "preflight" if dry_run else "build"),
            cancellable=True,
        )

    def builder_completed(self, result, operation):
        from .build_summary import summary
        self.build_details.setPlainText(summary(result))
        for warning in result.get('warnings',[]):self.log('Alternate fallback: '+warning)
        if result.get("status") == "cancelled" or operation == "preflight":
            return
        if operation == "staging":
            self.mod_path.setText(str(result['mod']))
            self.preview_mod=result.get('mod')
            already_selected = self.preview_overrides.isChecked()
            self.preview_overrides.setChecked(True)
            self.refresh_preview_lists()
            if already_selected:QTimer.singleShot(0, self.reload_preview_source)
            title = "DDS prioritization complete"
            message = "Overrides are ready. DDS prioritization is complete.\n\n"
            message += f"Prepared archives: {result.get('staged', 0)}\nWorkspace: {result.get('mod', '')}"
            if result.get('workspace_changed'):
                message += '\nA new workspace was selected automatically; the existing folder was preserved.'
            unapplied = len(result.get("unapplied_overrides", []))
            if unapplied:
                message += f"\n\n{unapplied} overrides could not be applied. Review the details before building."
            else:
                message += "\n\nYou can now build the JB folder." if result.get('build_supported',True) else "\n\nPreviews are ready. JB rebuilding is not supported for this SDAT source yet."
        else:
            title = "JB build complete"
            message = f"The JB folder was built successfully.\n\nOutput: {result.get('output', '')}"
        QMessageBox.information(self, title, message)

    def create_research(self):

        layout = self.page(
            "Research • raw inspection",
            "First 4 KiB of the selected asset. Unknown audio, CDAN and roster fields remain read-only; no codecs or geometry writers are inferred.",
        )

        self.hex = QPlainTextEdit()

        self.hex.setReadOnly(True)

        self.hex.setStyleSheet("font-family: Consolas, monospace;")

        layout.addWidget(self.hex)

    def create_diagnostics(self):

        layout = self.page(
            "Diagnostics",
            "Check built-in DDS import/export using generated textures. Game files remain unchanged.",
        )

        from ..texture_tools.external_converters import status, test_tools

        self.buttons(
            layout,
            [
                (
                    "Texture conversion status",
                    lambda: self.run_job("Check built-in texture conversion", lambda job: status()),
                ),
                (
                    "Test texture conversion",
                    lambda: self.run_job(
                        "Run built-in texture round trip", lambda job: test_tools()
                    ),
                ),
            ],
        )

        layout.addStretch()

    def closeEvent(self, event):

        if self.active:
            self.show_error(
                "A task is running. Cancel extraction or wait for completion before closing."
            )

            event.ignore()

            return

        self.settings.setValue("geometry", self.saveGeometry())

        super().closeEvent(event)


def main(argv=None):

    parser = argparse.ArgumentParser(description="CHoops native Qt studio")

    parser.add_argument(
        "--smoke",
        action="store_true",
        help="Launch a real Qt window then close automatically",
    )

    parser.add_argument("--game", type=Path)

    parser.add_argument(
        "--verify-game",
        action="store_true",
        help="Run private packaged GUI fixture smoke",
    )

    args = parser.parse_args(argv)

    app = QApplication.instance() or QApplication(sys.argv[:1])

    app.setStyle("Fusion")

    window = Window()

    window.showMaximized()

    if args.game:
        window.open_game(args.game)

    if args.verify_game:
        if not args.game:
            parser.error("--verify-game requires --game")

        state = {"step": 0, "failed": False}

        started = time.monotonic()

        from ..core.reports import save_json

        def fail(text):

            state["failed"] = True

            window.log(text)

            save_json(
                OUTPUT / "reports" / "packaged_gui_smoke.json",
                {"status": "failed", "reason": text},
            )

            window.active = None

            app.exit(1)

        # Suppress modal dialogs during automated smoke, retaining factual errors.

        window.show_error = fail

        def verify():

            if state["failed"]:
                return

            if time.monotonic() - started > 90:
                fail("GUI smoke timed out")

                return

            if window.active:
                QTimer.singleShot(100, verify)

                return

            try:
                if state["step"] == 0:
                    if not window.archive:
                        raise ValueError("Archive did not load")

                    window.search.setText("ua000.iff")

                    window.explorer.selectRow(0)

                    window.inspect_selected()

                elif state["step"] == 1:
                    if window.nested.topLevelItemCount() == 0:
                        raise ValueError("No nested IFF records")

                    window.navigation.setCurrentItem(window.navigation.topLevelItem(1))

                    window.textures.selectRow(0)

                    window.preview_texture()

                elif state["step"] == 2:
                    if window.image.pixmap().isNull():
                        raise ValueError("Texture preview did not decode")

                    window.load_game_roster()

                elif state["step"] == 3:
                    if not window.roster or len(window.roster.rows["players"]) != 5685:
                        raise ValueError("Roster table did not load")

                    window.roster_search.setText("Smith")

                    count = window.roster_views["players"].model().rowCount()

                    window.navigation.setCurrentItem(window.navigation.topLevelItem(0))

                    window.search.clear()

                    snapshot = OUTPUT / "reports" / "actual_explorer.png"

                    snapshot.parent.mkdir(parents=True, exist_ok=True)

                    window.grab().save(str(snapshot))

                    entry = next(
                        e for e in window.archive.entries if e["name"] == "uh000.iff"
                    )

                    import uuid

                    destination = OUTPUT / "temp" / ("gui_export_" + uuid.uuid4().hex)

                    window.run_job(
                        "Harmless packaged export",
                        lambda job: extract(window.archive, [entry], destination, job),
                    )

                    state["filtered_players"] = count

                else:
                    save_json(
                        OUTPUT / "reports" / "packaged_gui_smoke.json",
                        {
                            "status": "passed",
                            "entries": len(window.archive.entries),
                            "preview_decoded": True,
                            "players": len(window.roster.rows["players"]),
                            "search_rows": state["filtered_players"],
                            "harmless_export": True,
                        },
                    )

                    window.close()

                    app.quit()

                    return

                state["step"] += 1

            except Exception as error:  # noqa: BLE001 - smoke records all failures
                fail(str(error))

                return

            QTimer.singleShot(100, verify)

        QTimer.singleShot(100, verify)

    elif args.smoke:

        def finish():

            if window.active:
                QTimer.singleShot(100, finish)

            else:
                window.close()

                app.quit()

        QTimer.singleShot(800, finish)

    return app.exec()
