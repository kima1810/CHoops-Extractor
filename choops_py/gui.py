"""Focused Tkinter workflows with one CLI/backend and background jobs."""
import json
import queue
import shlex
import subprocess
import sys
import threading
import tkinter as tk
from tkinter import ttk,filedialog,messagebox
from pathlib import Path
from .commands import COMMANDS,SPECS
from .cli import parser
from .archive.manifests import OUTPUT,safe_output
PANELS=[
    ('Project Setup',[]),
    ('Texture Tool Setup',['texture-tools-status','test-texture-tools','setup-texture-tools','configure-texture-tools']),
    ('Export Textures to DDS',['export-iff-textures','export-dds','export-cdf-textures']),
    ('Import Edited DDS',['replace-iff-texture','import-dds','replace-cdf-texture']),
    ('Uniform Texture Tools',['export-uniform-atlas-dds','import-uniform-atlas-dds']),
    ('Court / SCNE Textures',['export-court-textures','replace-court-texture','export-scne-textures','import-scne-texture']),
    ('Team Logo / CDF Textures',['export-teamselectlogo-dds','import-teamselectlogo-dds','export-cdf-textures','replace-cdf-texture']),
    ('Mod Staging',['import','list-overrides','validate-mod']),
    ('Build JB Folder',['build-copy']),
    ('Roster Editor',['roster-detect','roster-decode','roster-export-json','roster-validate','roster-save']),
    ('Validate Build',['validate-build']),
    ('Logs / Reports',[])]
COMMAND_REGISTRY={c:COMMANDS[c] for _,commands in PANELS for c in commands}
class App:
    def __init__(self,root):
        self.root=root;root.title('CHoops Extractor Reborn — Textures, Rosters and JB Builds');root.geometry('1250x1000')
        self.events=queue.Queue();self.busy=False;self.preview=tk.StringVar();self.command=tk.StringVar();self.options=tk.StringVar();self.fields={}
        self.paths={name:tk.StringVar(value=str(OUTPUT/folder) if folder else '') for name,folder in [('vanilla',None),('mod','builds/mods'),('build','builds/my_build'),('rip','rips'),('reports','reports'),('gtf2dds',None),('dds2gtf',None)]}
        navigation=ttk.Panedwindow(root,orient='horizontal');navigation.pack(fill='both',expand=True,padx=8,pady=8)
        self.panel_list=tk.Listbox(navigation,width=30,exportselection=False);navigation.add(self.panel_list,weight=0)
        for label,_ in PANELS:self.panel_list.insert('end',label)
        self.form=ttk.Frame(navigation);navigation.add(self.form,weight=1);self.panel_list.bind('<<ListboxSelect>>',self.select_panel)
        ttk.Label(root,textvariable=self.preview,wraplength=1200).pack(fill='x',padx=8)
        controls=ttk.Frame(root);controls.pack(fill='x');self.run_button=ttk.Button(controls,text='Preview and Run',command=self.run);self.run_button.pack(side='left');ttk.Button(controls,text='Save Logs',command=self.save_logs).pack(side='left');ttk.Button(controls,text='Open Report',command=self.open_report).pack(side='left')
        self.logs=tk.Text(root,height=9);self.logs.pack(fill='both',padx=8,pady=4);root.after(100,self.poll);self.panel_list.selection_set(0);self.select_panel();root.protocol('WM_DELETE_WINDOW',self.close)
    def protected_sources(self):return [self.paths['vanilla'].get()] if self.paths['vanilla'].get() else []
    def browse(self,var,directory=False,save=False):
        value=filedialog.askdirectory() if directory else filedialog.asksaveasfilename(initialdir=str(OUTPUT/'rips')) if save else filedialog.askopenfilename()
        if value:var.set(value)
    def select_panel(self,event=None):
        if self.busy:return
        for child in self.form.winfo_children():
            if child is getattr(self,'roster_editor',None):child.pack_forget()
            else:child.destroy()
        self.command.set('gui');self.fields={}
        index=self.panel_list.curselection()[0];label,commands=PANELS[index]
        ttk.Label(self.form,text=label,font=('Segoe UI',14,'bold')).pack(anchor='w',pady=6)
        if index==0:
            self.show_setup();self.run_button.configure(state='disabled');return
        if label=='Roster Editor':
            from .roster.gui_editor import RosterEditor
            if not hasattr(self,'roster_editor'):self.roster_editor=RosterEditor(self.form,self)
            self.roster_editor.pack(fill='both',expand=True);self.run_button.configure(state='disabled');return
        if label=='Logs / Reports':ttk.Label(self.form,text='Read reports and save job logs using the buttons below.').pack();self.run_button.configure(state='disabled');return
        self.run_button.configure(state='normal');self.command.set(commands[0]);combo=ttk.Combobox(self.form,textvariable=self.command,values=commands,state='readonly');combo.pack(fill='x');combo.bind('<<ComboboxSelected>>',lambda e:self.build_form())
        self.fields_frame=ttk.Frame(self.form);self.fields_frame.pack(fill='x');self.build_form()
        if label=='Texture Tool Setup':
            self.tool_status=ttk.Label(self.form,text='Checking bundled tools...',wraplength=850);self.tool_status.pack(fill='x')
            from .texture_tools.external_converters import status
            self.task(status,self.show_tool_status)
    def show_setup(self):
        rows=[('Select Vanilla JB Folder','vanilla',True),('Select Mod Folder','mod',True),('Select Output Build Folder','build',True),('Texture / Rip Output','rip',True),('Reports Folder','reports',True),('Fallback gtf2dds.exe Path','gtf2dds',False),('Fallback dds2gtf.exe Path','dds2gtf',False)]
        frame=ttk.Frame(self.form);frame.pack(fill='x')
        for i,(label,key,directory) in enumerate(rows):
            ttk.Label(frame,text=label).grid(row=i,column=0,sticky='w');ttk.Entry(frame,textvariable=self.paths[key],width=70).grid(row=i,column=1,sticky='ew');ttk.Button(frame,text='Browse',command=lambda k=key,d=directory:self.browse(self.paths[k],d)).grid(row=i,column=2)
        ttk.Label(self.form,text='Bundled tools/ converters are used first. Raw extraction works without converters. DDS export/import requires bundled converter tools. Builds always create a separate JB folder under output/builds/.',wraplength=850).pack(fill='x',pady=12)
    def build_form(self):
        for child in self.fields_frame.winfo_children():child.destroy()
        self.fields={};command=self.command.get();spec=COMMANDS[command]
        for i,field in enumerate(spec.fields):
            default=self.paths['vanilla'].get() if field=='source' else self.paths['mod'].get() if field=='mod' else self.paths['build'].get() if field=='modded' else ''
            if field=='output':
                folder=self.paths['build'].get() if command=='build-copy' else str(Path(self.paths['reports'].get())/command) if command=='validate-build' else str(Path(self.paths['rip'].get())/command)
                default=folder+('.iff' if spec.output_file else '')
            var=tk.StringVar(value=default);self.fields[field]=var
            label={'source':'Select Vanilla JB Folder','mod':'Select Mod Folder','output':'Select Output Build Folder'}.get(field,field.replace('_',' ').title()) if command=='build-copy' else field.replace('_',' ').title()
            ttk.Label(self.fields_frame,text=label).grid(row=i,column=0,sticky='w');ttk.Entry(self.fields_frame,textvariable=var,width=75).grid(row=i,column=1,sticky='ew')
            if field not in ('selector','value'):
                directory=field in ('source','mod','modded','edited') or field=='output' and not spec.output_file
                ttk.Button(self.fields_frame,text='Browse',command=lambda v=var,d=directory,save=field=='output' and spec.output_file:self.browse(v,d,save)).grid(row=i,column=2)
        default_options='--same-format-only' if 'import-format' in spec.options else '--same-size-only' if 'import-size' in spec.options else '--copy-from-old-sources' if 'copy-tools' in spec.options else '--overwrite' if command=='build-copy' else ''
        self.options.set(default_options);i=len(spec.fields);ttk.Label(self.fields_frame,text='Options').grid(row=i,column=0);ttk.Entry(self.fields_frame,textvariable=self.options,width=75).grid(row=i,column=1)
        if command=='build-copy':ttk.Button(self.fields_frame,text='Build JB Folder',command=self.run).grid(row=i+1,column=1,sticky='w')
        else:ttk.Label(self.fields_frame,text='For staging DDS: --iff ua000.iff --sub unif. Court selectors: floor/texture_0. All outputs must stay under output/.',wraplength=850).grid(row=i+1,column=0,columnspan=3)
    def show_tool_status(self,result):
        if not hasattr(self,'tool_status') or not self.tool_status.winfo_exists():return
        self.tool_status.configure(text='\n'.join([f"Bundled {name}: {'found' if result[name]['bundled_found'] else 'missing'}; {result[name]['reason']}" for name in ('gtf2dds','dds2gtf')]+[f"DDS export readiness: {result['export_dds_ready']}",f"DDS import readiness: {result['import_dds_ready']}",f"Test conversion result: {result['test_conversion_result']}"]))
    def args(self):
        command=self.command.get();args=[command]+[self.fields[field].get().strip() for field in COMMANDS[command].fields]
        args.extend(shlex.split(self.options.get()))
        if 'export' in COMMANDS[command].options and self.paths['gtf2dds'].get():args+=['--gtf2dds',self.paths['gtf2dds'].get()]
        if any(g in COMMANDS[command].options for g in ('import-format','import-size')) and self.paths['dds2gtf'].get():args+=['--dds2gtf',self.paths['dds2gtf'].get()]
        if command=='configure-texture-tools':
            for name in ('gtf2dds','dds2gtf'):
                if self.paths[name].get():args+=['--'+name,self.paths[name].get()]
        return args
    def run(self):
        if self.busy:return
        if not self.fields and self.command.get() not in COMMANDS:return
        try:
            args=self.args();parsed=parser().parse_args(args)
            if hasattr(parsed,'output'):safe_output(parsed.output,self.protected_sources())
            if parsed.command=='import':safe_output(parsed.mod,self.protected_sources())
        except (ValueError,SystemExit,KeyError) as error:messagebox.showerror('Invalid command',str(error));return
        argv=[sys.executable,'-u','-m','choops_py.cli',*args];self.preview.set(subprocess.list2cmdline(argv))
        if not messagebox.askokcancel('Run command',self.preview.get()):return
        def work():
            process=subprocess.Popen(argv,cwd=str(Path(__file__).resolve().parents[1]),stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,errors='replace',creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
            for line in process.stdout:self.events.put(('log',line))
            code=process.wait()
            if code:raise ToolError('command_failed',f'Exit code {code}; see live log for exact reason')
            return {'exit_code':code}
        from .core.errors import ToolError
        self.task(work,lambda result:self.log('Completed successfully.\n'))
    def task(self,function,callback=None):
        if self.busy:return
        self.busy=True;self.run_button.configure(state='disabled');self.panel_list.configure(state='disabled')
        def worker():
            try:result=function();self.events.put(('result',(callback,result)))
            except Exception as error:self.events.put(('error',str(error)))
            finally:self.events.put(('done',None))
        threading.Thread(target=worker,daemon=True).start()
    def poll(self):
        while not self.events.empty():
            kind,value=self.events.get()
            if kind=='log':self.log(value)
            elif kind=='result':
                callback,result=value
                if callback:callback(result)
            elif kind=='error':self.log('Error: '+value+'\n');messagebox.showerror('Operation blocked/failed',value)
            elif kind=='done':self.busy=False;self.run_button.configure(state='normal' if self.command.get() in COMMANDS else 'disabled');self.panel_list.configure(state='normal')
        self.root.after(100,self.poll)
    def log(self,text):self.logs.insert('end',text);self.logs.see('end')
    def save_logs(self):
        file=filedialog.asksaveasfilename(initialdir=self.paths['reports'].get(),defaultextension='.txt')
        if file:
            try:
                from .archive.manifests import write_bytes
                write_bytes(file,self.logs.get('1.0','end').encode(),self.protected_sources())
            except ValueError as error:messagebox.showerror('Unsafe output',str(error))
    def open_report(self):
        file=filedialog.askopenfilename(initialdir=self.paths['reports'].get())
        if file:
            with Path(file).open(encoding='utf-8',errors='replace') as stream:self.log(stream.read(2*1024*1024))
    def close(self):
        if self.busy:messagebox.showinfo('Job running','Wait for the job to finish before closing.');return
        if hasattr(self,'roster_editor') and self.roster_editor.model and self.roster_editor.model.edits:
            if not messagebox.askyesno('Unsaved roster edits','Close and discard unsaved edits?'):return
        self.root.destroy()
def launch():
    root=tk.Tk();App(root);root.mainloop()
