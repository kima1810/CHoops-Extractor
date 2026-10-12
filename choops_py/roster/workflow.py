"""Roster detect/decode/export/save backend shared by CLI and GUI."""
import csv
import io
import json
from pathlib import Path
from ..archive.manifests import safe_output,write_bytes,digest
from ..core.reports import save_json
from ..core.errors import ToolError
from .editor_model import EditorModel
from .adapters import load,load_bytes

def detect(path):
    source=load(path);model=EditorModel(source)
    return {'source_type':source.kind,'source_size':len(source.original),'payload_size':len(source.payload),'validation':model.validate()}

def export_model(model,output):
    out=safe_output(output,[model.source.source_path.split('!')[0]] if model.source.source_path else []);out.mkdir(parents=True,exist_ok=True)
    save_json(out/'roster.json',model.document())
    for name,rows in model.rows.items():
        stream=io.StringIO(newline='');writer=csv.DictWriter(stream,fieldnames=list(rows[0]) if rows else [])
        writer.writeheader()
        for row in rows:writer.writerow({k:json.dumps(v) if isinstance(v,list) else v for k,v in row.items()})
        write_bytes(out/(name+'.csv'),stream.getvalue().encode('utf-8'))
    save_json(out/'edit_report.json',{'source_type':model.source.kind,'edits':model.edits,'validation':model.validate()})
    return {'output':str(out),'counts':{name:len(rows) for name,rows in model.rows.items()}}

def decode(path,output):return export_model(EditorModel.open(path),output)

def save_model(model,output):
    result=model.validate()
    if not result['valid']:raise ToolError('roster_validation_failed',str(result['issues'][:10]))
    data=model.source.encode(bytes(model.data));decoded=load_bytes(data)
    if decoded.kind!=model.source.kind or decoded.payload!=bytes(model.data):raise ToolError('roster_wrapper_validation_failed','Wrapper/payload round trip differs')
    out=safe_output(output,[model.source.source_path.split('!')[0]] if model.source.source_path else [])
    write_bytes(out,data,[model.source.source_path.split('!')[0]] if model.source.source_path else [])
    report={'status':'success','source_type':model.source.kind,'source_sha256':digest(model.source.original),'output_sha256':digest(data),'edits':model.edits,'validation':result,'unknown_bytes_preserved':True}
    save_json(out.with_suffix(out.suffix+'.edit_report.json'),report);return report


def export_game_roster(model,base_iff,output):
    """Wrap a community save's edited payload in the selected game's IFF."""
    validation=model.validate()
    if not validation['valid']:raise ToolError('roster_validation_failed',str(validation['issues'][:10]))
    source=load_bytes(base_iff)
    if source.kind!='standard-iff':raise ToolError('game_roster_iff_required','Choose the loaded JB roster_english.iff')
    encoded=source.encode(bytes(model.data))
    if load_bytes(encoded).payload!=bytes(model.data):raise ToolError('roster_wrapper_validation_failed','Game roster payload differs after export')
    inputs=[model.source.source_path.split('!')[0]] if model.source.source_path else []
    out=safe_output(output,inputs);write_bytes(out,encoded,inputs)
    report=dict(status='success',output=str(out),source_type=model.source.kind,output_type='standard-iff',validation=validation,
                output_sha256=digest(encoded),jb_built=False)
    save_json(out.with_suffix(out.suffix+'.edit_report.json'),report);return report

def save(path,patch,output):
    model=EditorModel.open(path);document=json.loads(Path(patch).read_text(encoding='utf-8'));model.apply_document(document);return save_model(model,output)
