"""Roster table UI; all edits/saves go through EditorModel/workflow."""
import tkinter as tk
from tkinter import ttk,filedialog,messagebox
from pathlib import Path
from ..archive.manifests import OUTPUT,safe_output
from ..core.errors import ToolError
from .schema import EDITABLE
from .editor_model import EditorModel
from .workflow import export_model,save_model

class RosterEditor(ttk.Frame):
    def __init__(self,parent,app):
        super().__init__(parent);self.app=app;self.model=None;self.source=tk.StringVar();self.status=tk.StringVar(value='Open roster_english.iff, raw ROST, decrypted USERDATA or a save ZIP.')
        top=ttk.Frame(self);top.pack(fill='x');ttk.Entry(top,textvariable=self.source).pack(side='left',fill='x',expand=True);ttk.Button(top,text='Open Roster',command=self.open).pack(side='left')
        controls=ttk.Frame(self);controls.pack(fill='x')
        for label,callback in [('Validate Changes',self.validate),('Undo',self.undo),('Revert Unsaved',self.revert),('Save Copy',self.save),('Export JSON/CSV',self.export)]:ttk.Button(controls,text=label,command=callback).pack(side='left')
        ttk.Label(self,textvariable=self.status,wraplength=850).pack(fill='x')
        self.notebook=ttk.Notebook(self);self.notebook.pack(fill='both',expand=True);self.trees={};self.filters={}
        columns={'players':['index','first_name','last_name','jersey_number','height_inches','position'],'teams':['index','school_name','asset_id','arena_index','coach_index'],'arenas':['index','arena_name','arena_code'],'coaches':['index','coach_name','abbreviation']}
        for table,cols in columns.items():
            frame=ttk.Frame(self.notebook);self.notebook.add(frame,text=table.title());filter_var=tk.StringVar();self.filters[table]=filter_var
            ttk.Label(frame,text='Search/filter').pack(anchor='w');entry=ttk.Entry(frame,textvariable=filter_var);entry.pack(fill='x');entry.bind('<KeyRelease>',lambda e,t=table:self.refresh(t))
            box=ttk.Frame(frame);box.pack(fill='both',expand=True);tree=ttk.Treeview(box,columns=cols,show='headings',height=9);scroll=ttk.Scrollbar(box,orient='vertical',command=tree.yview);tree.configure(yscrollcommand=scroll.set);scroll.pack(side='right',fill='y');tree.pack(side='left',fill='both',expand=True)
            for col in cols:tree.heading(col,text=col.replace('_',' ').title());tree.column(col,width=80 if col=='index' else 130,stretch=True)
            self.trees[table]=tree;tree.bind('<<TreeviewSelect>>',lambda e,t=table:self.select(t))
        self.notebook.bind('<<NotebookTabChanged>>',lambda e:self.selected_tab())
        edit=ttk.LabelFrame(self,text='Edit selected player/team — confirmed fields only');edit.pack(fill='x');self.field=tk.StringVar();self.value=tk.StringVar();self.slot=tk.StringVar(value='1')
        self.field_box=ttk.Combobox(edit,textvariable=self.field,state='readonly',width=22);self.field_box.pack(side='left');self.field_box.bind('<<ComboboxSelected>>',lambda e:self.populate_value())
        ttk.Entry(edit,textvariable=self.value,width=28).pack(side='left');ttk.Label(edit,text='Roster slot (1–16)').pack(side='left');ttk.Spinbox(edit,from_=1,to=16,textvariable=self.slot,width=5).pack(side='left');ttk.Button(edit,text='Apply Edit',command=self.apply).pack(side='left')
        ttk.Label(self,text='Names: same UTF-16 byte length, unshared storage only. Position: 0 PG, 1 SG, 2 SF, 3 PF, 4 C. References use table indices. Skin tone, conference, prestige, unknown appearance bytes and long strings remain read-only.',wraplength=850).pack(fill='x')
        slots=ttk.LabelFrame(self,text='Selected team roster slots');slots.pack(fill='both');self.slots=ttk.Treeview(slots,columns=['slot','player_index','player_name'],show='headings',height=4)
        for col in self.slots['columns']:self.slots.heading(col,text=col.replace('_',' ').title())
        self.slots.pack(fill='both');self.slots.bind('<<TreeviewSelect>>',self.select_slot)
    def current_table(self):return ['players','teams','arenas','coaches'][self.notebook.index('current')]
    def selected_index(self,table):
        selection=self.trees[table].selection()
        if not selection:raise ToolError('no_row_selected','Select a row first')
        return int(selection[0])
    def open(self):
        if self.app.busy:return
        if self.model and self.model.edits and not messagebox.askyesno('Unsaved changes','Discard unsaved changes and open another roster?'):return
        file=filedialog.askopenfilename(title='Open roster source',filetypes=[('Roster sources','*.iff *.rost *.zip *USERDATA*'),('All files','*')])
        if not file:return
        self.source.set(file);self.app.preview.set(f'Load roster source: {file}')
        self.app.task(lambda:EditorModel.open(file),self.loaded)
    def loaded(self,model):
        self.model=model;result=model.validate();self.status.set(f"Loaded {model.source.kind}: {len(model.rows['players'])} players, {len(model.rows['teams'])} teams. Validation: {'passed' if result['valid'] else 'failed; saving blocked'}")
        for table in self.trees:self.refresh(table)
        self.selected_tab()
    def refresh(self,table):
        tree=self.trees[table];tree.delete(*tree.get_children())
        if not self.model:return
        term=self.filters[table].get().casefold()
        for row in self.model.rows[table]:
            if term and term not in ' '.join(str(v) for v in row.values()).casefold():continue
            tree.insert('', 'end',iid=str(row['index']),values=[row.get(col,'') for col in tree['columns']])
    def selected_tab(self):
        table=self.current_table();values=list(EDITABLE.get(table,()))
        self.field_box.configure(values=values);self.field.set(values[0] if values else 'Read-only');self.populate_value()
    def select(self,table):
        if not self.model:return
        if table==self.current_table():self.populate_value()
        if table=='teams':
            try:index=self.selected_index('teams')
            except ToolError:return
            self.slots.delete(*self.slots.get_children())
            for slot,player in enumerate(self.model.rows['teams'][index]['roster_slots']):
                name=self.model.rows['players'][player]['display_name'] if player is not None else 'Empty'
                self.slots.insert('','end',iid=str(slot),values=[slot+1,'' if player is None else player,name])
    def select_slot(self,event=None):
        choice=self.slots.selection()
        if choice:self.slot.set(str(int(choice[0])+1));self.field.set('roster_slots');self.populate_value()
    def populate_value(self):
        if not self.model:return
        table=self.current_table()
        try:
            index=self.selected_index(table);value=self.model.rows[table][index].get(self.field.get(),'')
            if self.field.get()=='roster_slots':value=value[int(self.slot.get())-1]
            self.value.set('' if value is None else str(value))
        except (ToolError,ValueError,IndexError):self.value.set('')
    def apply(self):
        if self.app.busy:return
        if not self.model:return
        try:
            table=self.current_table();index=self.selected_index(table);slot=int(self.slot.get())-1 if self.field.get()=='roster_slots' else None
            self.model.edit(table,index,self.field.get(),self.value.get(),slot)
            self.refresh(table);self.trees[table].selection_set(str(index));self.select(table);self.status.set(f'{len(self.model.edits)} unsaved edits; source unchanged.')
        except (ToolError,ValueError) as error:messagebox.showerror('Edit blocked',str(error))
    def validate(self):
        if self.app.busy:return
        if self.model:self.app.log(str(self.model.validate())+'\n');self.status.set('Changes valid' if self.model.validate()['valid'] else 'Validation failed; save blocked')
    def undo(self):
        if self.app.busy:return
        if self.model:self.model.undo();self.loaded(self.model)
    def revert(self):
        if self.app.busy:return
        if self.model and messagebox.askyesno('Revert unsaved','Discard all unsaved roster edits?'):self.model.revert();self.loaded(self.model)
    def save(self):
        if self.app.busy:return
        if not self.model:return
        original=Path(self.source.get());folder=OUTPUT/'rips';folder.mkdir(parents=True,exist_ok=True)
        file=filedialog.asksaveasfilename(title='Save edited roster copy',initialdir=str(folder),initialfile=original.name,defaultextension=original.suffix)
        if not file:return
        try:safe_output(file,[original,*self.app.protected_sources()])
        except ValueError as error:messagebox.showerror('Unsafe output',str(error));return
        self.app.preview.set(f'Save validated {self.model.source.kind} copy to {file}')
        if not messagebox.askokcancel('Save copy',self.app.preview.get()):return
        self.app.task(lambda:save_model(self.model,file),lambda result:self.status.set('Saved validated copy. Original roster remains unchanged.'))
    def export(self):
        if self.app.busy:return
        if not self.model:return
        folder=filedialog.askdirectory(title='Export review JSON/CSV',initialdir=str(OUTPUT/'reports'))
        if folder:
            try:safe_output(folder,[*self.app.protected_sources()])
            except ValueError as error:messagebox.showerror('Unsafe output',str(error));return
            self.app.task(lambda:export_model(self.model,folder),lambda result:self.status.set('Exported JSON/CSV for review.'))
