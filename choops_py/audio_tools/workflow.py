"""Audio discovery, WAV export and archive-only replacement preparation."""
import io
import json
import shutil
import uuid
from pathlib import Path
from PIL import Image
from ..archive.hash_names import replacement_hash
from ..archive.manifests import OUTPUT,safe_output,safe_name,write_bytes,digest
from ..formats.standard_iff import StandardIFF
from ..formats.standard_iff_writer import record_blocks,replace_records_expanding
from ..formats.compression import decode
from ..formats.tool_wrapper import unwrap,wrap
from ..formats import audio
from ..core.reports import save_json
from .banks import StreamBank
from .codec import export_wav,encode_wav

MUSIC_BANKS=('cribmusic','femusic','drillmusic','hlmusic','loadm')


def names():
    data=json.loads(Path(__file__).with_name('soundtrack_names.json').read_text(encoding='utf8'))
    return {row['index']:row for row in data['tracks']}


def entry_for(archive,name):
    matches=[e for e in archive.entries if e['hash']==replacement_hash(name)]
    if len(matches)!=1:raise ValueError('Audio archive is missing or ambiguous: '+name)
    return matches[0]


def _parts(iff,rec,decoded):
    result=[]
    for index,start,end in iff.spans(rec):
        if index not in decoded:
            block=iff.blocks[index];decoded[index]=decode(iff.raw[block['start']:block['start']+block['size']],block['logical_size'])
        result.append(decoded[index][start:end])
    return result


def catalog(archive,job=None):
    source=archive.read(entry_for(archive,'global.iff'));iff=StandardIFF(source);decoded={};rows=[];known=names()
    for rec in iff.records:
        if rec['type']!='AUSB' or rec['name'] not in MUSIC_BANKS:continue
        if job:job.check();job.progress(0,1,'Reading audio bank '+rec['name'])
        parts=_parts(iff,rec,decoded)
        if len(parts)!=1:raise ValueError('Unsupported multiblock AUSB metadata')
        # Bound the table first, then resolve its embedded stream filename.
        provisional=StreamBank(parts[0],0xffffffff);entry=entry_for(archive,provisional.filename)
        bank=StreamBank(parts[0],entry['size'])
        for i in range(bank.count):
            row=dict(bank.info(i),kind='stream',metadata_archive='global.iff',bank=rec['name'],data_archive=bank.filename,
                     data_hash=entry['hash'],start=bank.offsets[i],end=bank.offsets[i+1],
                     title=f'{rec["name"]} stream {i}',artist='',category='Other audio',cover_record=None)
            if rec['name']=='cribmusic' and i in known:row.update(known[i])
            row['asset_key']=rec['name']+':'+str(i);rows.append(row)
    return dict(tracks=rows,soundtrack_count=sum(r['category']=='Soundtrack' for r in rows),fight_song_count=sum(r['category']=='Fight song' for r in rows))


def _stream(archive,row):
    entry=entry_for(archive,row['data_archive'])
    return archive.read({**entry,'offset':entry['offset']+row['start'],'size':row['end']-row['start']})


def export_track(archive,row,output,job=None):
    out=safe_output(output,[archive.path]);out.parent.mkdir(parents=True,exist_ok=True)
    if out.exists() or out.with_suffix('.audio.json').exists():raise ValueError('Choose a new WAV output filename')
    temporary=out.with_name('.'+out.name+'.'+uuid.uuid4().hex+'.wav')
    try:
        result=export_wav(_stream(archive,row),row['channels'],row['sample_rate'],temporary,row['samples'],job)
        temporary.replace(out)
    finally:
        if temporary.exists():temporary.unlink()
    report=dict(result,output=str(out),bank=row['bank'],index=row['index'],title=row['title'],artist=row['artist'],source_unchanged=True)
    save_json(out.with_suffix('.audio.json'),report);return report


def export_tracks(archive,rows,output,job=None):
    out=safe_output(output,[archive.path])
    if out.exists():raise ValueError('Choose a new audio export folder')
    if not rows:raise ValueError('Choose at least one audio track to export')
    work=safe_output(out.parent/('.audio_export_'+uuid.uuid4().hex),[archive.path])
    work.mkdir(parents=True);manifest=[]
    try:
        seen=set()
        for i,row in enumerate(rows):
            if job:job.check();job.progress(i,len(rows),'Exporting '+row['title'])
            key=(row['bank'],row['index'])
            if key in seen:raise ValueError('Duplicate audio export target')
            seen.add(key)
            filename=safe_name(row['bank'])+f'_{row["index"]:03d}_'+safe_name(row['artist']+' - '+row['title'])+'.wav'
            report=export_track(archive,row,work/filename,job)
            report['output']=str(out/filename)
            save_json((work/filename).with_suffix('.audio.json'),report)
            manifest.append(dict(bank=row['bank'],index=row['index'],file=filename,title=row['title'],artist=row['artist'],sha256=digest((work/filename).read_bytes())))
        save_json(work/'audio_manifest.json',dict(schema=1,tracks=manifest))
        if job:job.check()
        work.rename(out)
    except BaseException:
        if work.exists():shutil.rmtree(work)
        raise
    return dict(output=str(out),exported=len(manifest),format='PCM16 WAV',manifest=str(out/'audio_manifest.json'))


def replace_tracks(archive,replacements,output,job=None):
    """Write global.iff plus each affected .bin; no JB folder is built."""
    if not replacements:raise ValueError('Choose at least one audio replacement')
    out=safe_output(output,[archive.path,*[p for _,p in replacements]])
    if out.exists():raise ValueError('Choose a new audio replacement output folder')
    work=out.parent/('.audio_mod_'+uuid.uuid4().hex);work.mkdir(parents=True)
    original=archive.read(entry_for(archive,'global.iff'));iff=StandardIFF(original);decoded={};groups={};details=[]
    try:
        seen=set()
        for row,path in replacements:
            key=(row['bank'],row['index'])
            if key in seen:raise ValueError('Duplicate audio replacement target')
            seen.add(key)
            if row['bank'] not in MUSIC_BANKS:raise ValueError('Unknown music bank')
            found=[r for r in iff.records if r['name']==row['bank'] and r['type']=='AUSB']
            if len(found)!=1:raise ValueError('AUSB metadata record is missing or ambiguous')
            rec=found[0];parts=_parts(iff,rec,decoded)
            if row['bank'] not in groups:
                bank=StreamBank(parts[0],0xffffffff);entry=entry_for(archive,bank.filename);data=archive.read(entry)
                groups[row['bank']]=dict(rec=rec,bank=StreamBank(parts[0],len(data)),data=data,entry=entry,changes={})
            group=groups[row['bank']];layout=group['bank'].info(row['index'])
            if job:job.check();job.progress(0,1,'Converting '+row['title'])
            encoded,samples=encode_wav(path,layout['channels'],layout['sample_rate'],job,
                                       target_samples=layout['samples'])
            group['changes'][row['index']]=(encoded,samples)
            details.append(dict(bank=row['bank'],index=row['index'],samples=samples,seconds=samples/layout['sample_rate'],encoded_bytes=len(encoded)))
        changes={}
        for group in groups.values():
            metadata,data=group['bank'].replace(group['data'],group['changes']);changes[group['rec']['index']]=[metadata]
            write_bytes(work/group['bank'].filename,data)
        rebuilt=replace_records_expanding(iff,changes);write_bytes(work/'global.iff',rebuilt)
        report=dict(output=str(out),replacements=details,files=['global.iff',*[g['bank'].filename for g in groups.values()]],
                    other_streams_preserved=True,source_unchanged=True,jb_built=False,gameplay_verified=False)
        save_json(work/'audio_replacement_report.json',report)
        if job:job.check()
        work.rename(out);return report
    except BaseException:
        if work.exists() and work.resolve().is_relative_to(OUTPUT.resolve()):shutil.rmtree(work)
        raise


def import_wav_folder(archive,folder,output,job=None):
    folder=Path(folder).resolve();document=json.loads((folder/'audio_manifest.json').read_text(encoding='utf8'))
    if document.get('schema')!=1:raise ValueError('Unsupported audio manifest')
    tracks={(r['bank'],r['index']):r for r in catalog(archive,job)['tracks']};replacements=[]
    for item in document['tracks']:
        relative=Path(item['file']);path=(folder/relative).resolve()
        if relative.is_absolute() or not path.is_relative_to(folder):raise ValueError('Audio manifest path leaves the selected folder')
        if not path.is_file():continue
        if item.get('sha256')==digest(path.read_bytes()):continue
        key=(item['bank'],item['index'])
        if key not in tracks:raise ValueError('Audio manifest target does not exist in the loaded JB')
        replacements.append((tracks[key],path))
    return replace_tracks(archive,replacements,output,job)


def read_audo(path):
    path=Path(path);raw=path.read_bytes()
    if path.suffix.lower()=='.block0':
        companion=path.with_suffix('.block1')
        if not companion.is_file():raise ValueError('The AUDO payload .block1 file is missing')
        return [raw,companion.read_bytes()],None
    return audio.parts_from_bytes(raw),unwrap(raw)[0] if raw[:4]==b'2kTl' else None


def export_audo(source,output,job=None):
    parts,_=read_audo(source);metadata=audio.info(parts);out=safe_output(output,[source]);out.parent.mkdir(parents=True,exist_ok=True)
    if out.exists():raise ValueError('Choose a new WAV output filename')
    split=audio.parts_from_bytes(parts[0]) if len(parts)==1 else parts
    temporary=out.with_name('.'+out.name+'.'+uuid.uuid4().hex+'.wav')
    try:
        result=export_wav(split[1][:metadata['encoded_bytes']],metadata['channels'],metadata['sample_rate'],temporary,metadata['samples'],job)
        temporary.replace(out)
    finally:
        if temporary.exists():temporary.unlink()
    return dict(result,output=str(out))


def replace_audo(source,wav,output,job=None):
    parts,typ=read_audo(source);metadata=audio.info(parts)
    encoded,samples=encode_wav(wav,metadata['channels'],metadata['sample_rate'],job)
    result=audio.replace(parts,encoded,samples);out=safe_output(output,[source,wav])
    write_bytes(out,wrap(typ,result) if typ is not None else b''.join(result))
    return dict(output=str(out),**audio.info(result),source_unchanged=True)


def export_cover(archive,record,output):
    from ..formats.txtr import TXTR
    from ..texture_tools.builtin_converter import to_dds
    iff=StandardIFF(archive.read(entry_for(archive,'jukebox.iff')))
    rec=next((r for r in iff.records if r['name']==record and r['type']=='TXTR'),None)
    if rec is None:raise ValueError('Jukebox artwork record does not exist')
    texture=TXTR([p[3] for p in record_blocks(iff,rec)]);out=safe_output(output,[archive.path])
    write_bytes(out,to_dds(texture.gtf()));return dict(output=str(out),record=record,**texture.info())


def replace_cover(archive,record,image,output,job=None):
    from ..texture_tools.override_import import apply_dds
    iff=StandardIFF(archive.read(entry_for(archive,'jukebox.iff')))
    rec=next((r for r in iff.records if r['name']==record and r['type']=='TXTR'),None)
    if rec is None:raise ValueError('Jukebox artwork record does not exist')
    source=Path(image)
    if source.suffix.lower()=='.dds':data=source.read_bytes()
    else:
        with Image.open(source) as opened:
            buffer=io.BytesIO();opened.convert('RGBA').save(buffer,format='DDS');data=buffer.getvalue()
    parts=[p[3] for p in record_blocks(iff,rec)];changed,info=apply_dds(parts,'TXTR',record,data,job,preserve_layout=True)
    out=safe_output(output,[archive.path,image]);write_bytes(out,replace_records_expanding(iff,{rec['index']:changed}))
    return dict(output=str(out),record=record,**info,other_records_preserved=True,source_unchanged=True)
