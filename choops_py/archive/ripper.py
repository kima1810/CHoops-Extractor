from pathlib import Path
from .usrdir_reader import Archive
from .manifests import safe_output,write_bytes,report,safe_name,digest
from ..formats.standard_iff import StandardIFF
from ..formats.cdf_backed_iff import CDFPair
def rip(source,output,index=None,file=None,iff_only=False,raw_iff=False,types=(),strict=False,log_output=None):
    out=safe_output(output,[source]);a=Archive(source);entries=a.entries
    if index is not None:entries=[e for e in entries if e['index']==index]
    if file:entries=[e for e in entries if e['name'] and e['name'].lower()==file.lower()]
    if not entries:raise ValueError("No matching archive entries")
    results=[];emitted=set()
    for e in entries:
        data=a.read(e);magic=data[:4];name=safe_name(e['name'] or f"hash_{e['hash']:08x}")
        if not e['name']:name+= '.iff' if magic in (bytes.fromhex('ff3bef94'),bytes.fromhex('f0985030')) else '.bin'
        if name not in emitted:write_bytes(out/name,data,[source]);emitted.add(name)
        row=dict(e,output=name,sha256=digest(data));results.append(row)
        if magic==bytes.fromhex('f0985030') or (not iff_only and not raw_iff):
            try:
                if magic==bytes.fromhex('ff3bef94'):StandardIFF(data).dump(out/(name+'.subfiles'),types)
                elif magic==bytes.fromhex('f0985030'):
                    partner=name[:-4]+'.cdf';matches=[x for x in a.entries if x['name']==partner]
                    if len(matches)!=1:raise ValueError("Paired CDF unresolved; raw metadata preserved")
                    cdf=a.read(matches[0])
                    if partner not in emitted:write_bytes(out/partner,cdf,[source]);emitted.add(partner)
                    pair=CDFPair(data,cdf)
                    if not iff_only and not raw_iff:pair.dump(out/(name+'.pair'))
            except ValueError as error:
                row['extraction_error']=str(error)
                if strict:
                    report(out/'rip_report.json',results,[source]);raise
    log=Path(log_output) if log_output else out/'rip_report.json'
    if log_output and not log.is_absolute():log=out/log
    report(log,results,[source]);return results
