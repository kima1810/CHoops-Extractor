"""NBA roster side-panel editing using the researched per-game backend."""
from pathlib import Path
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QWidget,QVBoxLayout,QHBoxLayout,QLabel,QLineEdit,QComboBox,
                               QSplitter,QTableWidget,QTableWidgetItem,QHeaderView,QFileDialog,QPushButton,QStyledItemDelegate,QSpinBox,QDoubleSpinBox)


class NBAFieldDelegate(QStyledItemDelegate):
    def createEditor(self,parent,option,index):
        field=index.data(Qt.ItemDataRole.UserRole)
        if field in ('position_code','secondary_position_code'):
            editor=QComboBox(parent)
            for label in ('PG','SG','SF','PF','C')+(('None',) if field=='secondary_position_code' else ()):editor.addItem(label)
            return editor
        if field in ('jersey_number','face_id'):
            editor=QSpinBox(parent);editor.setRange(0,100 if field=='jersey_number' else 65535);return editor
        if field in ('height_inches','weight_pounds'):
            editor=QDoubleSpinBox(parent);editor.setDecimals(2);editor.setRange(36 if field=='height_inches' else 80,100 if field=='height_inches' else 450);return editor
        return super().createEditor(parent,option,index)

    def setEditorData(self,editor,index):
        value=index.data(Qt.ItemDataRole.EditRole)
        if isinstance(editor,QComboBox):editor.setCurrentIndex(int(index.data(Qt.ItemDataRole.UserRole+1)));return
        if isinstance(editor,(QSpinBox,QDoubleSpinBox)):editor.setValue(float(value) if isinstance(editor,QDoubleSpinBox) else int(value));return
        super().setEditorData(editor,index)

    def setModelData(self,editor,model,index):
        if isinstance(editor,QComboBox):model.setData(index,str(editor.currentIndex()),Qt.ItemDataRole.EditRole);return
        if isinstance(editor,(QSpinBox,QDoubleSpinBox)):model.setData(index,str(editor.value()),Qt.ItemDataRole.EditRole);return
        super().setModelData(editor,model,index)


class NBARosterPanel(QWidget):
    def __init__(self,app):
        super().__init__();self.app=app;self.model=None;self.refreshing=False
        layout=QVBoxLayout(self)
        self.title=QLabel();layout.addWidget(self.title)
        tools=QHBoxLayout();self.category=QComboBox();self.category.addItems(['Players','Teams','Arenas'])
        self.category.currentIndexChanged.connect(self.populate);tools.addWidget(self.category)
        self.teams=QComboBox();self.teams.currentIndexChanged.connect(self.populate);tools.addWidget(self.teams)
        self.search=QLineEdit();self.search.setPlaceholderText('Search NBA roster');self.search.textChanged.connect(self.populate);tools.addWidget(self.search)
        export=QPushButton('Export USERDATA…');export.clicked.connect(self.export_userdata);tools.addWidget(export)
        layout.addLayout(tools)
        splitter=QSplitter();self.records=QTableWidget();self.records.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.records.setSelectionMode(QTableWidget.SelectionMode.SingleSelection);self.records.itemSelectionChanged.connect(self.details)
        self.fields=QTableWidget(0,2);self.fields.setHorizontalHeaderLabels(['Field','Value (double-click to edit)'])
        self.fields.setItemDelegate(NBAFieldDelegate(self.fields));self.fields.itemChanged.connect(self.changed)
        splitter.addWidget(self.records);splitter.addWidget(self.fields);splitter.setStretchFactor(0,3);splitter.setStretchFactor(1,2)
        layout.addWidget(splitter,1)
        self.status=QLabel();self.status.setWordWrap(True);layout.addWidget(self.status)

    def set_model(self,model):
        self.model=model;self.refreshing=True
        self.teams.clear();self.teams.addItem('All NBA teams',None)
        for team in model.rows['teams']:self.teams.addItem(team['city']+' '+team['team_name'],team['index'])
        self.refreshing=False;self.populate()

    def populate(self,*_):
        if self.refreshing or self.model is None:return
        self.refreshing=True
        table=self.category.currentText().lower();self.current_table=table
        columns={'players':['display_name','jersey_number','height_inches','weight_pounds','face_id'],
                 'teams':['city','team_name','abbreviation'], 'arenas':['arena_name','city','stadium_asset']}[table]
        rows=self.model.rows[table];team=self.teams.currentData();term=self.search.text().casefold()
        allowed=set(self.model.rows['teams'][team]['roster_slots']) if table=='players' and team is not None else None
        self.visible=[r for r in rows if (allowed is None or r['index'] in allowed) and term in ' '.join(str(r.get(f,'')) for f in columns).casefold()]
        self.records.clear();self.records.setColumnCount(len(columns));self.records.setHorizontalHeaderLabels([f.replace('_',' ').title() for f in columns]);self.records.setRowCount(len(self.visible))
        for i,row in enumerate(self.visible):
            for j,field in enumerate(columns):
                value=row.get(field,'')
                if field=='jersey_number' and value==100:value='00'
                item=QTableWidgetItem(str(value));item.setFlags(item.flags()&~Qt.ItemFlag.ItemIsEditable);self.records.setItem(i,j,item)
        self.records.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        self.title.setText(self.model.profile['title']+' roster — detected from payload, '+self.model.source.kind)
        self.status.setText(str(len(self.model.edits))+' unsaved edits. Confirmed names, measurements, jersey numbers and face IDs are editable. Team membership and asset links are read-only. Ratings, appearance bits, save encryption and text-heap growth remain unconfirmed. Shared text edits are blocked. Gameplay is unverified.')
        self.refreshing=False
        if self.visible:self.records.selectRow(0)
        else:self.fields.setRowCount(0)

    def details(self):
        if self.refreshing or not self.records.selectedItems():return
        row=self.visible[self.records.currentRow()];self.selected_index=row['index'];self.refreshing=True
        fields=[k for k in row if k not in ('row_offset','display_name')];self.fields.setRowCount(len(fields))
        for i,field in enumerate(fields):
            label=QTableWidgetItem(field.replace('_',' ').title());label.setFlags(label.flags()&~Qt.ItemFlag.ItemIsEditable);self.fields.setItem(i,0,label)
            value=QTableWidgetItem(str(row[field]));value.setData(Qt.ItemDataRole.UserRole,field)
            if field in ('position_code','secondary_position_code'):
                value.setData(Qt.ItemDataRole.UserRole+1,row[field]);value.setText({0:'PG',1:'SG',2:'SF',3:'PF',4:'C',5:'None'}.get(row[field],str(row[field])))
            if field not in self.model.editable(self.current_table):value.setFlags(value.flags()&~Qt.ItemFlag.ItemIsEditable)
            self.fields.setItem(i,1,value)
        self.fields.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch);self.refreshing=False

    def changed(self,item):
        if self.refreshing or item.column()!=1:return
        field=item.data(Qt.ItemDataRole.UserRole)
        try:
            value=item.text()
            if field in ('position_code','secondary_position_code'):
                value={'PG':0,'SG':1,'SF':2,'PF':3,'C':4,'None':5}.get(value,value)
            self.model.edit(self.current_table,self.selected_index,field,value)
            index=self.selected_index;self.populate()
            for i,row in enumerate(self.visible):
                if row['index']==index:self.records.selectRow(i);break
        except (ValueError,RuntimeError) as error:
            self.app.show_error(str(error));self.details()

    def save(self):
        if not self.model or self.app.active:return
        path,_=QFileDialog.getSaveFileName(self,'Save NBA roster copy',str(Path('output/rosters')/(Path(self.model.source.source_path).name or 'roster.iff')))
        if path:
            from ..roster.workflow import save_model
            self.app.run_job('Save NBA roster copy',lambda job:save_model(self.model,path))

    def export_userdata(self):
        if not self.model or self.app.active:return
        path,_=QFileDialog.getSaveFileName(self,'Export decrypted NBA payload','output/rosters/USERDATA')
        if path:
            from ..roster.workflow import export_userdata
            self.app.run_job('Export NBA USERDATA',lambda job:export_userdata(self.model,path))
