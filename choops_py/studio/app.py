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
        if role != Qt.ItemDataRole.DisplayRole:
            return None
        if key == "hash":
            return f"{value:08X}"
        if key == "name" and not value:
            hint=self.rows[index.row()].get("name_hint")
            if hint:return hint+f" [hash {self.rows[index.row()].get('hash',0):08X}]"
            return f"hash_{self.rows[index.row()].get('hash', 0):08x}"
        from ..roster.schema import ENUM_CHOICES
        if key in ENUM_CHOICES:
            return ENUM_CHOICES[key].get(value, f'Unknown ({value})')
        if isinstance(value, (list, dict)):
            labels = {'palette_colors':'colors; use Team palette',
                      'attribute_ratings':'ratings; use Player attributes',
                      'properties':'properties; use Player properties',
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


def set_rows(view, rows, columns, query=""):

    proxy = QSortFilterProxyModel(view)

    proxy.setSourceModel(Rows(rows, columns))
    proxy.setSortRole(Qt.ItemDataRole.UserRole)

    proxy.setFilterKeyColumn(-1)

    proxy.setFilterCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)

    proxy.setFilterFixedString(query)

    view.setModel(proxy)

    view.resizeColumnsToContents()
    for column in range(len(columns)):
        view.setColumnWidth(column, min(240, max(80, view.columnWidth(column))))
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

        self.setWindowTitle("CHoops Modding Studio • 1.0beta development")

        self.resize(1420, 900)

        self.settings = QSettings("CHoops", "ModdingStudio")

        self.pool = QThreadPool(self)

        self.pool.setMaxThreadCount(1)

        self.active = None

        self.archive = None

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

        layout = self.page(
            "Audio workspace",
            "Browse Licensed Music and Fight Songs from the selected JB. WAV exports and replacement folders are prepared under output/ for you to stage and build manually.",
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
                ("Replace selected from WAV…", self.audio_replace_selected),
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
        output = self.audio_output_path(
            "Choose a new replacement folder", Path("audio") / "song_edit"
        )
        if not output:
            return
        from ..audio_tools.workflow import replace_tracks

        self.run_job(
            "Prepare WAV replacement",
            lambda job: replace_tracks(archive, [(rows[0], Path(wav))], output, job),
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

        worker = Worker(function, JobContext())

        self.active = worker

        self.cancel.setEnabled(cancellable)

        self.progress.setRange(0, 0)

        self.statusBar().showMessage(label)

        self.log(label)

        worker.events.progress.connect(self.job_progress)

        worker.events.failed.connect(self.show_error)

        worker.events.result.connect(
            callback
            or (lambda result: self.log(json.dumps(result, default=str)[:8000]))
        )

        worker.events.finished.connect(self.job_finished)

        self.pool.start(worker)

    def job_progress(self, done, total, text):

        self.progress.setRange(0, total)

        self.progress.setValue(done)

        self.statusBar().showMessage(text)

    def job_finished(self):

        self.active = None

        self.cancel.setEnabled(False)

        self.progress.setRange(0, 100)

        self.progress.setValue(100)

        self.statusBar().showMessage("Ready")

    def log(self, text):

        self.logs.appendPlainText(str(text))

    def show_error(self, text):

        self.log(text)

        QMessageBox.warning(self, "Operation could not complete", text)

    def choose_game(self):

        path = QFileDialog.getExistingDirectory(
            self, "Select original JB game or USRDIR", self.settings.value("game", "")
        )

        if path:
            self.open_game(Path(path))

    def open_game(self, path):

        def loaded(archive):

            self.archive = archive
            self.audio_state.setText("Audio catalog has not been loaded for this JB.")
            for view in self.audio_tables.values():
                view.setModel(None)
            self.scene_uniform_images = {}
            # A newly selected JB folder must not inherit another source's roster.
            self.roster = None
            self.refresh_uniform_list()
            self.refresh_shoe_list()
            for view in self.roster_views.values():
                view.setModel(None)
            self.roster_state.setText('No roster loaded; load the current JB folder roster')
            self.scene_meshes = []
            self.scene_view.set_meshes([])
            self.scene_palette_state.setText("No roster associated; load the current JB folder roster")

            self.source = path

            self.settings.setValue("game", str(path))

            self.explorer_proxy = set_rows(
                self.explorer,
                archive.entries,
                [
                    ("name", "Asset"),
                    ("size", "Bytes"),
                    ("hash", "CRC32"),
                    ("index", "TOC index"),
                    ("offset", "Logical offset"),
                    ("size_derived", "Derived extent"),
                ],
                self.search.text(),
            )

            self.identity.setText(
                f"{len(archive.entries):,} entries • {len(archive.parts)} split parts • original source read-only"
            )

            self.log("Archive index loaded; payloads remain lazy.")

        self.run_job("Index JB folder", lambda job: Archive(path), loaded)

    def identify_asset_names(self, candidates=()):
        if isinstance(candidates,bool):candidates=()
        if self.active or not self.archive:return
        from ..archive.identity import recover,apply
        def display(result):
            apply(self.archive,result['identities'])
            self.explorer.model().sourceModel().layoutChanged.emit()
            self.refresh_uniform_list();self.refresh_shoe_list()
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

        self.explorer = table()

        self.explorer.doubleClicked.connect(self.inspect_selected)

        layout.addWidget(self.explorer)

        self.nested = QTreeWidget()

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

    def extract_selected(self, all_entries=False):

        if not self.archive:
            return self.log("Open a game first.")

        entries = list(self.archive.entries) if all_entries else selected(self.explorer)

        if not entries:
            return self.log("Select one or more rows to extract.")

        path = QFileDialog.getExistingDirectory(
            self, "Choose new output folder under output/", str(OUTPUT / "rips")
        )

        if path:
            self.run_job(
                "Extract raw assets",
                lambda job: extract(self.archive, entries, Path(path), job),
                cancellable=True,
            )

    def inspect_selected(self):

        entries = selected(self.explorer)

        if not entries:
            return

        entry = entries[0]

        self.run_job(
            "Read and inspect asset",
            lambda job: inspect_asset(materialize(self.archive, entry)),
            self.display_asset,
        )

    def choose_asset(self):

        path, _ = QFileDialog.getOpenFileName(
            self,
            "Open extracted IFF/TXTR/DDS",
            "",
            "Assets (*.iff *.txtr *.dds *.scne);;All files (*)",
        )

        if path and Path(path).name == "0A":
            self.open_game(Path(path))
        elif path:
            self.run_job(
                "Inspect extracted asset",
                lambda job: inspect_asset(Path(path)),
                self.display_asset,
            )

    def display_asset(self, result):

        self.asset_path = result["path"]

        self.asset_label.setText(self.asset_path.name)

        self.nested.clear()

        for rec in result["records"]:
            QTreeWidgetItem(
                self.nested,
                [rec.get("name", ""), rec.get("type", ""), str(rec["index"])],
            )

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
        target.setText("Loading texture preview…")

        def decode(job):
            from .services import decode_texture_preview
            return decode_texture_preview(source, selector)

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
            "Roster editor",
            "Confirmed player and team fields only. Save a copy, reopen it, then stage it for a separate JB build.",
        )

        self.buttons(
            layout,
            [
                ("Open roster…", self.choose_roster),
                ("Load game roster", self.load_game_roster),
                ("Edit selected…", self.edit_roster),
                ("Team palette…", self.show_team_palette),
                ("Add alternate to JB copy…", self.add_uniform_alternate),
                ("Give schools five jerseys…", self.fill_five_uniforms),
                ("Move school / convert to D1…", self.move_school),
                ("Enable alternates…", self.edit_alternate_availability),
                ("Preview assigned shoes…", self.preview_assigned_shoes),
                ("Edit shoes…", self.edit_roster_shoes),
                ("Give school independent assets…", self.declone_school_assets),
                ("Player attributes…", self.show_player_attributes),
                ("Player properties…", self.show_player_properties),
                ("Research layout…", self.research_roster),
                ("Undo", self.undo_roster),
                ("Redo", self.redo_roster),
                ("Save copy…", self.save_roster),
                ("Export game roster IFF…", self.export_game_roster),
            ],
        )

        self.roster_search = QLineEdit()

        self.roster_search.setPlaceholderText("Search current roster table")

        self.roster_search.textChanged.connect(lambda value: self.filter_roster(value))

        layout.addWidget(self.roster_search)

        self.roster_tabs = QTabWidget()

        self.roster_views = {}

        for name in ("players", "teams", "schools", "arenas", "coaches", "conferences", "uniforms"):
            view = table()

            self.roster_views[name] = view

            self.roster_tabs.addTab(view, "Edit Schools" if name=="schools" else name.title())

        # Keep category tabs outside the row-scrolling viewports.
        self.roster_tabs.tabBar().setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        layout.addWidget(self.roster_tabs, 1)

        self.roster_state = QLabel("No roster loaded")

        layout.addWidget(self.roster_state)

    def filter_roster(self, text):

        for view in self.roster_views.values():
            if view.model():
                view.model().setFilterFixedString(text)

    def choose_roster(self):

        path, _ = QFileDialog.getOpenFileName(
            self, "Open roster or decrypted USERDATA", "", "All supported files (*)"
        )

        if path:
            from ..roster.editor_model import EditorModel

            self.run_job(
                "Load roster", lambda job: EditorModel.open(path), self.display_roster
            )

    def load_game_roster(self):

        if not self.archive:
            return self.log("Open a game first.")

        matches = [e for e in self.archive.entries if e["name"] == "roster_english.iff"]

        if len(matches) != 1:
            return self.log("Roster identity is missing or ambiguous.")

        from ..roster.editor_model import EditorModel

        self.run_job(
            "Load current JB folder roster",
            lambda job: EditorModel.open(materialize(self.archive, matches[0])),
            self.display_roster,
        )

    def display_roster(self, model):

        self.roster = model
        self.refresh_uniform_list()
        if getattr(self, "scene_meshes", None):
            self.select_scene_part()

        for name, view in self.roster_views.items():
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
            set_rows(view, rows, columns, self.roster_search.text())

        warnings=len(model.validate()['preserved_source_string_issues'])
        self.roster_state.setText(
            f"{len(model.rows['players']):,} players • {len(model.edits)} unsaved edits"
            +(f' • {warnings} unchanged source string warnings' if warnings else '')
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

    def fill_five_uniforms(self):
        if self.active or not self.archive or not self.roster:return self.log('Load the current JB folder and roster first.')
        output,_=QFileDialog.getSaveFileName(self,'New JB folder with five jerseys per playable school',str(OUTPUT/'builds'/'five_uniforms'))
        if not output:return
        from ..modding.add_alternate import fill_five
        payload=bytes(self.roster.data)
        self.run_job('Build five-bank school uniforms',lambda job:fill_five(self.source,output,job,payload),
                     lambda report:self.log(json.dumps(report,indent=2)),cancellable=True)

    def declone_school_assets(self):
        if self.active or not self.roster or not self.archive:return self.log('Load the current JB folder and roster first.')
        view=self.roster_tabs.currentWidget()
        if view not in (self.roster_views['teams'],self.roster_views['schools']):return self.log('Select a school in Teams or Edit Schools.')
        rows=selected(view)
        if len(rows)!=1:return self.log('Select exactly one school.')
        asset,ok=QInputDialog.getInt(self,'Independent school assets','New stadium, uniform owner and menu-logo ID',1000,0,1023)
        if not ok:return
        output,_=QFileDialog.getSaveFileName(self,'New JB folder with independent school assets',str(OUTPUT/'builds'/'independent_school'))
        if not output:return
        from ..modding.declone import declone
        payload=bytes(self.roster.data)
        self.run_job('Copy independent school assets',lambda job:declone(self.source,rows[0]['index'],asset,output,job,payload),
                     lambda report:self.log(json.dumps(report,indent=2)),cancellable=True)

    def edit_alternate_availability(self):
        if not self.roster or self.active:return
        view=self.roster_tabs.currentWidget()
        if view not in (self.roster_views['teams'],self.roster_views['schools']):return self.log('Select a school in Teams or Edit Schools.')
        rows=selected(view)
        if len(rows)!=1:return self.log('Select exactly one school.')
        from ..roster.uniforms import disabled_uniforms
        row=rows[0];owner=row['uniform_owner_id']
        active={r['variant_code'] for r in self.roster.rows['uniforms'] if r['team_asset_id']==owner}
        dormant={a>>8&7 for a,_ in disabled_uniforms(bytes(self.roster.data)) if a>>22&1023==owner}
        dialog=QDialog(self);dialog.setWindowTitle('Alternate availability')
        form=QFormLayout(dialog);checks={}
        for variant in (2,3,4):
            box=QCheckBox('Alternate '+str(variant-1));box.setChecked(variant in active)
            box.setEnabled(variant in active or variant in dormant)
            if not box.isEnabled():box.setToolTip('Add this alternate and its assets to a JB copy first.')
            checks[variant]=box;form.addRow(box)
        buttons=QDialogButtonBox(QDialogButtonBox.StandardButton.Ok|QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(dialog.accept);buttons.rejected.connect(dialog.reject);form.addRow(buttons)
        if dialog.exec()!=QDialog.DialogCode.Accepted:return
        before=bytes(self.roster.data);history=list(self.roster.history);edits=list(self.roster.edits);redo=list(self.roster.redo_history)
        try:
            for variant,box in checks.items():
                if box.isEnabled():self.roster.set_alternate_enabled(row['index'],variant,box.isChecked())
            self.display_roster(self.roster)
        except ValueError as error:
            self.roster.data=bytearray(before);self.roster.history=history;self.roster.edits=edits;self.roster.redo_history=redo;self.roster.reload()
            QMessageBox.warning(self,'Alternate edit blocked',str(error))

    def move_school(self):
        if not self.roster or self.active:return
        view=self.roster_tabs.currentWidget()
        if view not in (self.roster_views['teams'],self.roster_views['schools']):return self.log('Select a school in Teams or Edit Schools.')
        rows=selected(view)
        if len(rows)!=1:return self.log('Select exactly one school.')
        row=rows[0];conferences=self.roster.rows.get('conferences',[])
        dialog=QDialog(self);dialog.setWindowTitle('Conference membership / optional D1 conversion')
        form=QFormLayout(dialog);choices=QComboBox()
        for conf in conferences:choices.addItem(str(conf['index'])+': '+conf['conference_name'],conf['index'])
        choices.setCurrentIndex(max(0,choices.findData(row.get('conference_index'))))
        convert=QCheckBox('Convert this slot to Current D1 classification')
        convert.setChecked(False)
        form.addRow('Destination conference',choices);form.addRow(convert)
        buttons=QDialogButtonBox(QDialogButtonBox.StandardButton.Ok|QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(dialog.accept);buttons.rejected.connect(dialog.reject);form.addRow(buttons)
        if dialog.exec()!=QDialog.DialogCode.Accepted:return
        try:
            self.roster.move_team_to_conference(row['index'],choices.currentData(),make_d1=convert.isChecked())
            self.display_roster(self.roster)
        except ValueError as error:QMessageBox.warning(self,'School move blocked',str(error))

    def add_uniform_alternate(self):
        if self.active or not self.roster or not self.archive:
            return self.log('Load the current JB folder and roster first.')
        if self.roster_tabs.currentWidget() is not self.roster_views['uniforms']:
            return self.log('Select the template record in the Uniforms roster tab.')
        rows=selected(self.roster_views['uniforms'])
        if len(rows)!=1:return self.log('Select exactly one uniform template.')
        row=rows[0]
        occupied={r['variant_code'] for r in self.roster.rows['uniforms'] if r['team_asset_id']==row['team_asset_id']}
        available=[v for v in (2,3,4) if v not in occupied]
        if not available:return self.log('This team already uses all three supported alternate banks.')
        from ..roster.uniforms import VARIANT_NAMES
        label,ok=QInputDialog.getItem(self,'New alternate bank','Choose an unused bank',[VARIANT_NAMES[v] for v in available],0,False)
        if not ok:return
        variant=next(v for v in available if VARIANT_NAMES[v]==label)
        asset,ok=QInputDialog.getInt(self,'New alternate asset','Asset selector (0–1023)',row['uniform_asset_id'],0,1023)
        if not ok:return
        output,_=QFileDialog.getSaveFileName(self,'New copied JB folder path',str(OUTPUT/'builds'/'new_alternate'))
        if not output:return
        from ..modding.add_alternate import add
        payload=bytes(self.roster.data)
        self.run_job('Build copied JB with new alternate',
                     lambda job:add(self.source,row['index'],asset,variant,output,job,payload),
                     lambda report:self.log(json.dumps(report,indent=2)),cancellable=True)

    def show_team_palette(self, team_index=None):
        if not self.roster:
            return self.log("Load a roster first.")
        if team_index is None or isinstance(team_index, bool):
            view=self.roster_views['schools'] if self.roster_tabs.currentWidget() is self.roster_views.get('schools') else self.roster_views['teams']
            rows = selected(view)
            if len(rows) != 1:
                return self.log("Select one team in the Teams tab.")
            team_index = rows[0]['index']
        from ..roster.research import palette_rows
        team = self.roster.rows['teams'][team_index]
        dialog = QDialog(self)
        dialog.setWindowTitle(f"{team['school_name']} • asset {team['asset_id']} • team palette")
        dialog.resize(760, 700)
        layout = QVBoxLayout(dialog)
        layout.addWidget(QLabel("22 Edit Schools captions are verified. Other slot roles remain provisional; court material bindings are supported."))
        view = QTreeWidget()
        view.setHeaderLabels(['Palette slot','RGBA','Edit Schools control','Caption / provisional role'])
        layout.addWidget(view)
        def refresh():
            view.clear()
            for row in palette_rows(self.roster, team_index):
                item = QTreeWidgetItem(view,[str(row['slot']),row['rgba'],str(row['school_control']) if row['school_control'] is not None else 'Not in color callback list',row['role']])
                color = bytes.fromhex(row['rgba'][1:])
                item.setBackground(1,QColor(*color))
        def edit():
            items = view.selectedItems()
            if not items:
                return
            slot = int(items[0].text(0))
            value = self.pick_rgba(items[0].text(1), dialog)
            if value is not None:
                try:
                    self.roster.edit('teams',team_index,'palette_colors',value,slot)
                    refresh()
                    self.display_roster(self.roster)
                except ValueError as error:
                    QMessageBox.warning(dialog,'Palette edit blocked',str(error))
        button = QPushButton('Pick selected color…');button.clicked.connect(edit);layout.addWidget(button)
        view.itemDoubleClicked.connect(lambda *_: edit())
        refresh();dialog.exec()

    def show_player_properties(self):
        if not self.roster:return
        rows=selected(self.roster_views['players'])
        if len(rows)!=1:return self.log("Select one player in the Players tab.")
        from ..roster.schema import TENDENCY_NAMES
        row=rows[0];dialog=QDialog(self);dialog.resize(650,650)
        dialog.setWindowTitle('Player properties • executable-backed storage')
        layout=QVBoxLayout(dialog)
        layout.addWidget(QLabel('Confirmed choices use readable labels; unresolved appearance enums retain their raw codes.'))
        view=QTreeWidget();view.setHeaderLabels(['Property','Value'])
        from ..roster.schema import PROPERTY_CHOICES
        for name,value in row['properties'].items():QTreeWidgetItem(view,[name,PROPERTY_CHOICES.get(name,{}).get(value,str(value))])
        for name,value in zip(TENDENCY_NAMES,row['shot_tendencies']):QTreeWidgetItem(view,[name+' tendency',str(value)])
        layout.addWidget(view);dialog.exec()

    def show_player_attributes(self):
        if not self.roster or self.active:
            return
        rows = selected(self.roster_views['players'])
        if len(rows)!=1:
            return self.log("Select one player in the Players tab.")
        from ..roster.schema import RATING_HINTS,RATING_OFFSET
        from ..formats.binary import Binary
        player_index=rows[0]['index']
        dialog=QDialog(self);dialog.resize(780,700)
        dialog.setWindowTitle('Player attributes • executable and UI metadata verified')
        layout=QVBoxLayout(dialog)
        layout.addWidget(QLabel('30 named attributes; edits use the game setter encoding (rating × 100).'))
        view=QTreeWidget();view.setHeaderLabels(['Channel','Row offset','Rating','Stored u16','Attribute'])
        layout.addWidget(view)
        def refresh():
            view.clear();row=self.roster.rows['players'][player_index];binary=Binary(self.roster.data)
            for i,value in enumerate(row['attribute_ratings']):
                offset=RATING_OFFSET+i*2
                QTreeWidgetItem(view,[str(i),hex(offset),str(value),str(binary.u16(row['row_offset']+offset)),RATING_HINTS.get(i,'Unassigned attribute')])
        def edit():
            items=view.selectedItems()
            if not items:return
            channel=int(items[0].text(0))
            value,ok=QInputDialog.getInt(dialog,'Edit attribute channel','Rating',int(items[0].text(2)),35,99)
            if ok:
                try:
                    self.roster.edit('players',player_index,'attribute_ratings',value,channel)
                    self.display_roster(self.roster);refresh()
                except ValueError as error:QMessageBox.warning(dialog,'Rating edit blocked',str(error))
        button=QPushButton('Edit selected channel…');button.clicked.connect(edit);layout.addWidget(button)
        refresh();dialog.exec()

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

        if not self.roster or self.active:
            return

        view = self.roster_tabs.currentWidget()
        name = next(key for key,value in self.roster_views.items() if value is view)
        name = 'teams' if name == 'schools' else name

        rows = selected(view)

        if len(rows) != 1:
            return self.log("Select exactly one roster row.")


        from ..roster.schema import EDITABLE, POSITIONS, REFERENCES, ENUM_CHOICES

        row = rows[0]

        dialog = QDialog(self)

        dialog.setWindowTitle(f"Edit {name} record {row['index']}")

        form = QFormLayout(dialog)

        field = QComboBox()
        field.setObjectName("rosterField")

        field.addItems(EDITABLE[name])

        value = QLineEdit()

        slot = QComboBox()

        slot.addItems([str(i) for i in range(16)])

        choices = QComboBox()
        choices.setObjectName("rosterValue")

        choices.setEditable(False)

        rgb_button = QPushButton('Choose RGB color…')
        def pick_color():
            chosen = self.pick_rgba(value.text(), dialog)
            if chosen is not None:value.setText(chosen)
        rgb_button.clicked.connect(pick_color)

        def changed(key):
            rgb_button.setVisible(key == 'palette_colors')
            reference = key == "roster_slots" or key in REFERENCES
            menu = reference or key == "position_code" or key in ENUM_CHOICES
            value.setVisible(not menu)
            choices.setVisible(menu)
            needed = 31 if key == 'palette_colors' else 30 if key == 'attribute_ratings' else 4 if key=='shot_tendencies' else 16
            if slot.count() != needed:
                slot.blockSignals(True)
                slot.clear()
                slot.addItems([str(i) for i in range(needed)])
                slot.blockSignals(False)
            slot.setVisible(key in ('roster_slots','palette_colors','attribute_ratings','shot_tendencies'))
            choices.clear()
            if key in ENUM_CHOICES:
                from ..roster.shoes import FIELDS,choices as shoe_choices
                options=shoe_choices(key,row['shoe_brand_code']) if key in FIELDS.get(name,{}) else ENUM_CHOICES[key]
                for code,label in options.items():choices.addItem(label,code)
                choices.setCurrentIndex(choices.findData(row[key]))
            elif key == "position_code":
                for code, label in POSITIONS.items():
                    choices.addItem(label, code)
                choices.setCurrentIndex(choices.findData(row[key]))
            elif reference:
                target = "players" if key == "roster_slots" else REFERENCES[key][1]
                choices.addItem("None", None)
                for candidate in self.roster.rows[target]:
                    label = (
                        candidate.get("display_name")
                        or candidate.get("school_name")
                        or candidate.get("arena_name")
                        or candidate.get("coach_name")
                        or ""
                    )
                    choices.addItem(
                        f"{candidate['index']}: {label}", candidate["index"]
                    )
                current = (
                    row[key][int(slot.currentText())]
                    if key == "roster_slots"
                    else row[key]
                )
                choices.setCurrentIndex(max(0, choices.findData(current)))
            else:
                value.setText(str(row[key][int(slot.currentText())]) if key in ('palette_colors','attribute_ratings','shot_tendencies') else str(row.get(key, "")))

        slot.currentTextChanged.connect(lambda value: changed(field.currentText()))
        form.addRow("Field (see palette dialog for verified captions)", field)

        form.addRow("Value", value)
        form.addRow(rgb_button)

        form.addRow("Reference", choices)

        form.addRow("Roster / palette slot", slot)

        field.currentTextChanged.connect(changed)

        changed(field.currentText())

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )

        buttons.accepted.connect(dialog.accept)

        buttons.rejected.connect(dialog.reject)

        form.addRow(buttons)

        if dialog.exec() == QDialog.DialogCode.Accepted:
            key = field.currentText()

            new = (
                choices.currentData()
                if key == "roster_slots" or key in REFERENCES or key == "position_code" or key in ENUM_CHOICES
                else value.text()
            )

            def edit(job):

                self.roster.edit(
                    name,
                    row["index"],
                    key,
                    new,
                    int(slot.currentText()) if key in ("roster_slots", "palette_colors", "attribute_ratings", "shot_tendencies") else None,
                )

                return self.roster

            self.run_job("Apply validated roster edit", edit, self.display_roster)

    def undo_roster(self):

        if self.roster and not self.active:

            def undo(job):

                self.roster.undo()

                return self.roster

            self.run_job("Undo roster edit", undo, self.display_roster)

    def redo_roster(self):

        if self.roster and not self.active:

            def redo(job):

                self.roster.redo()

                return self.roster

            self.run_job("Redo roster edit", redo, self.display_roster)

    def export_game_roster(self):
        if not self.roster or self.active:return
        if not self.archive:return self.log('Open the destination JB folder first.')
        entries=[entry for entry in self.archive.entries if entry['name']=='roster_english.iff']
        if len(entries)!=1:return self.log('The loaded JB has no unique roster_english.iff.')
        output,_=QFileDialog.getSaveFileName(self,'Export edited roster for manual JB staging',str(OUTPUT/'rosters'/'roster_english.iff'),'Game roster (*.iff)')
        if not output:return
        from ..roster.workflow import export_game_roster
        self.run_job('Export game roster IFF',lambda job:export_game_roster(self.roster,self.archive.read(entries[0]),output))

    def save_roster(self):

        if not self.roster:
            return

        filename={'save-zip':'roster_edited.zip','userdata':'USERDATA','raw-rost':'roster_edited.rost','tool-wrapper':'roster_edited.rost'}.get(self.roster.source.kind,'roster_english.iff')
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
        self.buttons(layout, [("Preview selected SCNE", self.inspect_scene), ("Prepare single-texture court…", self.prepare_court_template)])
        self.scene_complete = QCheckBox("Include all SCNE sections (arena and court)")
        self.scene_complete.setChecked(True)
        layout.addWidget(self.scene_complete)
        self.scene_cutaway = QCheckBox("Cutaway: hide roof and light-effect meshes")
        self.scene_cutaway.setChecked(True)
        self.scene_cutaway.toggled.connect(self.select_scene_part)
        layout.addWidget(self.scene_cutaway)
        self.scene_parts = QComboBox()
        self.scene_parts.activated.connect(self.select_scene_part)
        layout.addWidget(self.scene_parts)
        self.scene_textures = QComboBox()
        self.scene_textures.activated.connect(self.select_scene_texture)
        layout.addWidget(self.scene_textures)
        from .scene_view import SceneView
        self.scene_view = SceneView()
        layout.addWidget(self.scene_view, 1)
        camera_speed = QDoubleSpinBox()
        camera_speed.setRange(.05, 10.)
        camera_speed.setValue(1.)
        camera_speed.setPrefix('Camera movement speed: ')
        camera_speed.valueChanged.connect(lambda value: setattr(self.scene_view, 'movement_speed', value))
        layout.addWidget(camera_speed)
        self.buttons(layout, [("Fit camera", self.scene_view.fit_camera), ("Linked roster palette…", self.scene_team_palette)])
        self.model_details = QPlainTextEdit()
        self.model_details.setReadOnly(True)
        self.model_details.setMaximumHeight(120)
        layout.addWidget(self.model_details)
        self.scene_meshes = []
        self.scene_base_images = {}
        self.scene_uniform_images = {}
        self.scene_uniforms = QComboBox()
        self.scene_uniforms.setEditable(True)
        self.scene_uniforms.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        self.scene_uniforms.completer().setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        self.scene_uniforms.completer().setFilterMode(Qt.MatchFlag.MatchContains)
        self.scene_uniforms.activated.connect(self.select_scene_uniform)
        layout.addWidget(self.scene_uniforms)
        self.buttons(layout, [('Open uniform IFF…', self.choose_scene_uniform_file)])
        self.refresh_uniform_list()
        self.scene_shoes=QComboBox()
        self.scene_shoes.setEditable(True);self.scene_shoes.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        self.scene_shoes.completer().setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        self.scene_shoes.completer().setFilterMode(Qt.MatchFlag.MatchContains)
        layout.addWidget(self.scene_shoes)
        self.buttons(layout,[('Preview selected shoes',self.preview_shoes)])
        self.refresh_shoe_list()
        self.scene_palette_state = QLabel('No roster associated; embedded material textures only')
        layout.addWidget(self.scene_palette_state)

    def edit_roster_shoes(self):
        if not self.roster or self.active:return
        view=self.roster_tabs.currentWidget()
        table=next(key for key,value in self.roster_views.items() if value is view)
        table='teams' if table=='schools' else table
        rows=selected(view)
        if table not in ('players','teams') or len(rows)!=1:return self.log('Select one player or school to edit shoes.')
        from ..roster.shoes import FIELDS,BRANDS,choices,texture_name
        row=rows[0];dialog=QDialog(self);dialog.setWindowTitle('Player shoes' if table=='players' else 'School shoe defaults')
        form=QFormLayout(dialog);widgets={}
        labels=('Brand','Style / artwork ID','Home color','Away color')
        for key,label in zip(FIELDS[table],labels):
            box=QComboBox();box.setObjectName(key);widgets[key]=box;form.addRow(label,box)
        brand=widgets['shoe_brand_code']
        for code,label in BRANDS.items():brand.addItem(label,code)
        brand.setCurrentIndex(max(0,brand.findData(row['shoe_brand_code'])))
        description=QLabel();form.addRow(description)
        def show_paths():
            values={key:widget.currentData() for key,widget in widgets.items()}
            if any(value is None for value in values.values()):return
            home=texture_name(values['shoe_brand_code'],values['shoe_style_code'],values['home_shoe_color_code'])
            away=texture_name(values['shoe_brand_code'],values['shoe_style_code'],values['away_shoe_color_code'])
            description.setText(f'Home: {home}\nAway: {away}'+('\nSchool defaults change independently of existing player assignments.' if table=='teams' else ''))
        def refill():
            for key,box in widgets.items():
                if key=='shoe_brand_code':continue
                current=box.currentData();current=row[key] if current is None else current
                box.blockSignals(True);box.clear()
                for code,label in choices(key,brand.currentData()).items():box.addItem(label,code)
                box.setCurrentIndex(max(0,box.findData(current)));box.blockSignals(False)
            show_paths()
        brand.currentIndexChanged.connect(refill)
        for key,box in widgets.items():
            if key!='shoe_brand_code':box.currentIndexChanged.connect(show_paths)
        refill()
        buttons=QDialogButtonBox(QDialogButtonBox.StandardButton.Ok|QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(dialog.accept);buttons.rejected.connect(dialog.reject);form.addRow(buttons)
        if dialog.exec()!=QDialog.DialogCode.Accepted:return
        values={key:box.currentData() for key,box in widgets.items()}
        def work(job):
            self.roster.edit_shoes(table,row['index'],**values)
            return self.roster
        self.run_job('Apply shoe assignment',work,self.display_roster)

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

    def refresh_shoe_list(self):
        import re
        self.scene_shoes.clear()
        self.scene_shoes.addItem('Choose shoe artwork from the loaded JB folder',None)
        if not self.archive:return
        from ..roster.shoes import BRANDS,COLORS
        for entry in sorted(self.archive.entries,key=lambda e:e['name'] or ''):
            name=entry['name'] or ''
            match=re.fullmatch(r'shoe_(\d+)(?:_(\d{2}))?\.iff',name,re.I)
            if not match:continue
            family=int(match[1]);color=match[2]
            brand=0 if color is None else {1:1,2:2,3:3,5:4}.get(family//100)
            label=BRANDS.get(brand,'Shoe')+' — '+COLORS.get(int(color) if color else family,'Color '+str(color))+' — '+name
            self.scene_shoes.addItem(label,entry['index'])

    def preview_shoes(self):
        if self.active or not self.archive:return
        index=self.scene_shoes.currentData()
        if index is None:return self.log('Choose a shoe texture package first.')
        from .services import inspect_shoe_preview
        def display(value):
            source,result=value
            self.navigate_to('Models / Courts')
            self.scene_view.set_meshes([]);self.scene_view.set_image(None)
            self.scene_parts.clear();self.scene_textures.clear()
            self.show_scene_preview(result,source)
        self.run_job('Preview shoe geometry and artwork',lambda job:inspect_shoe_preview(self.archive,self.archive.entries[index],job),display,cancellable=True)

    def refresh_uniform_list(self):
        import re
        selected_id = self.scene_uniforms.currentData()
        self.scene_uniforms.clear()
        self.scene_uniforms.addItem('Choose a uniform from the loaded JB folder', None)
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
                self.scene_uniforms.addItem(label,entry['index'])
        self.scene_uniforms.setCurrentIndex(max(0,self.scene_uniforms.findData(selected_id)))

    def choose_scene_uniform_file(self):
        path,_=QFileDialog.getOpenFileName(self,'Select uniform IFF','','Uniform containers (*.iff);;All files (*)')
        if path:self.load_scene_uniform(Path(path))

    def select_scene_uniform(self, index=None):
        entry_index=self.scene_uniforms.currentData()
        if entry_index is None or not self.archive:return
        entry=self.archive.entries[entry_index]
        self.load_scene_uniform(None,entry)

    def load_scene_uniform(self, source, entry=None):
        if not any(m.get('uniform_surface') for m in self.scene_meshes):
            return self.log('Preview a cloth jersey or shorts scene first.')
        from .services import inspect_uniform_preview
        def work(job):
            path=materialize(self.archive,entry) if entry is not None else source
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
        self.navigate_to('Models / Courts')
        self.scene_meshes = []
        self.scene_view.set_meshes([])
        self.scene_view.set_material_images({})
        self.scene_view.set_image(None)
        self.scene_parts.clear()
        self.scene_textures.clear()
        self.model_details.setPlainText("Loading scene…")
        from .services import inspect_scene_preview
        include_all = self.scene_complete.isChecked()
        self.run_job('Decode scene geometry and textures', lambda job: inspect_scene_preview(source, index, include_all, job), lambda result:self.show_scene_preview(result,source), cancellable=True)

    def show_scene_preview(self,result,source):
        self.scene_source = source
        self.scene_meshes = result['meshes']
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
        if part == -1 and self.scene_cutaway.isChecked():
            meshes = [m for m in meshes if not m.get('hidden_by_default')]
        from ..formats.scene_palette import associate_palette
        import re
        match = re.fullmatch(r's(\d+)', self.scene_source.stem, re.IGNORECASE) if hasattr(self, 'scene_source') else None
        teams = [team for team in self.roster.rows['teams'] if match and team['asset_id'] == int(match[1])] if self.roster else []
        colors = teams[0]['palette_colors'] if len(teams) == 1 else None
        meshes = associate_palette(meshes, colors)
        if self.scene_uniform_images:
            meshes = [{**mesh,'batches':[{**batch,'texture':'__uniform_'+mesh['uniform_surface'], 'palette_tint':None}
                                        for batch in mesh['batches']]}
                      if mesh.get('uniform_surface') in self.scene_uniform_images else mesh for mesh in meshes]
        if colors is not None:
            count = sum(batch['palette_tint'] is not None for mesh in meshes for batch in mesh['batches'])
            self.scene_palette_state.setText(f"Associated roster: {self.roster.source.source_path or 'current JB folder roster'}; {teams[0]['school_name']}; {count} court color bindings. Arena shader masks are unresolved.")
        else:
            self.scene_palette_state.setText('No unique roster/team association; embedded material textures only. Use Associate roster to select a matching roster.')
        self.scene_view.set_meshes(meshes)

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
            "Scan nested overrides, import SCNEs first and apply DDS textures with priority over TXTRs. Dry run checks the resulting archives; build writes a separate JB copy.",
        )

        form = QFormLayout()

        self.mod_path = QLineEdit(str(OUTPUT / "builds" / "my_mod"))

        self.build_path = QLineEdit(str(OUTPUT / "builds" / "my_build"))

        form.addRow("Mod workspace", self.mod_path)

        form.addRow("New JB output", self.build_path)

        layout.addLayout(form)

        self.buttons(
            layout,
            [
                ("Stage replacement folder…", self.stage_replacements),
                ("Export mod patch…", self.export_mod_patch),
                ("Import mod patch…", self.import_mod_patch),
                ("Dry run", lambda: self.build_game(True)),
                ("Build JB copy", lambda: self.build_game(False)),
            ],
        )

        self.build_details = QPlainTextEdit()

        self.build_details.setReadOnly(True)

        layout.addWidget(self.build_details)

    def stage_replacements(self):

        if not self.source:
            return self.log("Open a game first.")

        path = QFileDialog.getExistingDirectory(
            self, "Overrides folder (includes subfolders and DDS textures)", str(OUTPUT)
        )

        if path:
            mod = Path(self.mod_path.text())

            self.run_job(
                "Stage and preflight replacement folder",
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
                "Validate and stage mod patch",
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
        self.build_details.setPlainText(json.dumps(result, indent=2))
        if result.get("status") == "cancelled" or operation == "preflight":
            return
        if operation == "staging":
            title = "DDS prioritization complete"
            message = "Override staging and DDS prioritization are complete.\n\n"
            message += f"Staged archives: {result.get('staged', 0)}\nWorkspace: {result.get('mod', '')}"
            unapplied = len(result.get("unapplied_overrides", []))
            if unapplied:
                message += f"\n\n{unapplied} overrides could not be applied. Review the details before building."
            else:
                message += "\n\nYou can now build the JB folder."
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
