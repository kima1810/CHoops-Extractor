"""Experimental, bounded edits of authored PS3 HUD geometry and text anchors.

No runtime bindings, events, font resources or executable bytes are rewritten.
"""
import argparse
import json
import math
import struct
from pathlib import Path

from ..formats.binary import Binary
from ..formats.tool_wrapper import unwrap,wrap


def edit_scene(parts, profile):
    if not isinstance(profile,dict) or set(profile)-{'parts','text','disable_text'}:
        raise ValueError('Profile requires parts/text keys; select one scene profile object')
    if type(profile.get('disable_text',False)) is not bool:raise ValueError('disable_text must be boolean')
    if len(parts)!=2:
        raise ValueError('HUD editing requires a split header/vertex SCNE')
    if any(isinstance(v,list) for v in profile.get('parts',{}).values()):
        result=list(parts);reports=[]
        for name,operations in profile.get('parts',{}).items():
            for operation in operations if isinstance(operations,list) else [operations]:
                if not isinstance(operation,dict):raise ValueError('HUD part operations must be objects')
                result,rows=edit_scene(result,{'parts':{name:operation}});reports.extend(rows)
        result,rows=edit_scene(result,{'text':profile.get('text',{}),'disable_text':profile.get('disable_text',False)});reports.extend(rows)
        return result,reports
    original=bytes(parts[0]);b=Binary(original);out=[bytearray(p) for p in parts]
    table=b.relative(0x48);count=b.u32(0x44)
    if count>4096:raise ValueError('HUD part count exceeds limit')
    b.slice(table,count*176)
    meshes={}
    for i in range(count):
        off=table+i*176;name=b.utf16(b.relative(off),'be')
        if name in meshes:raise ValueError('Ambiguous HUD part '+name)
        meshes[name]=off
    reports=[]
    for name,change in profile.get('parts',{}).items():
        if name not in meshes:raise ValueError('Unknown HUD part '+name)
        off=meshes[name];descriptor=b.relative(off+0x88)
        if b.u32(off+0x84)!=1:raise ValueError('HUD editor supports one vertex stream')
        n=b.u32(descriptor+16);stride=b.u32(descriptor+32);start=b.u32(descriptor+40)-1
        if not 1<=n<=250000 or stride not in (32,36):raise ValueError('Unsupported HUD stream')
        Binary(parts[1]).slice(start,n*stride)
        for other_name,other in meshes.items():
            if other_name==name:continue
            if b.u32(other+0x84)!=1:raise ValueError('Cannot exclude shared HUD streams')
            d=b.relative(other+0x88);other_start=b.u32(d+40)-1
            other_end=other_start+b.u32(d+16)*b.u32(d+32)
            if start<other_end and other_start<start+n*stride:raise ValueError('HUD vertex stream aliases another part')
        decl=b.relative(off+0x9c);attributes={}
        declarations=b.u32(off+0x94)
        if not 1<=declarations<=16:raise ValueError('Unsupported HUD declaration count')
        for j in range(declarations):
            code=b.slice(decl+j*64+8,8)
            if code[:1]==b'\x20' and code[2:4]==bytes(2):attributes[code[4:]]=code[1]
        if attributes.get(bytes.fromhex('02030000'))!=0:raise ValueError('HUD position must be float3 at zero')
        rgba=attributes.get(bytes.fromhex('02040300'))
        uv=attributes.get(bytes.fromhex('03020800'))
        if rgba is None or rgba+16>stride:raise ValueError('HUD color must be float4')
        selected=change.get('vertex_range',[0,n])
        if not isinstance(selected,(list,tuple)) or len(selected)!=2 or any(type(v) is not int for v in selected) or not 0<=selected[0]<selected[1]<=n:
            raise ValueError('Invalid HUD vertex range')
        first,last=selected
        old=[struct.unpack_from('>3f',parts[1],start+j*stride) for j in range(first,last)]
        if not all(math.isfinite(v) for point in old for v in point):raise ValueError('Non-finite HUD position')
        lo=[min(v[k] for v in old) for k in range(2)];hi=[max(v[k] for v in old) for k in range(2)]
        bounds=change.get('bounds')
        if bounds is not None and (len(bounds)!=4 or not all(math.isfinite(v) for v in bounds) or bounds[0]>=bounds[2] or bounds[1]>=bounds[3] or min(hi[k]-lo[k] for k in range(2))<=0):
            raise ValueError('Invalid HUD rectangle')
        if change.get('rectify_uv') and (bounds is None or uv is None or uv+4>stride):raise ValueError('Rectified HUD requires half2 UV and bounds')
        z_offset=change.get('z_offset',0.)
        if not math.isfinite(z_offset) or abs(z_offset)>100:raise ValueError('Invalid HUD depth offset')
        scale=change.get('rgb_scale',1.)
        if not math.isfinite(scale) or not 0<=scale<=1:raise ValueError('HUD color multiplier must be 0..1')
        alpha=change.get('alpha')
        if alpha is not None and (not math.isfinite(alpha) or not 0<=alpha<=1):raise ValueError('HUD alpha must be 0..1')
        rgb=change.get('rgb')
        if rgb is not None and (len(rgb)!=3 or not all(math.isfinite(v) and 0<=v<=1 for v in rgb)):
            raise ValueError('HUD RGB must contain three values in 0..1')
        # Normalize each horizontal edge independently, avoiding the stock shear.
        single_quad=change.get('single_quad',False)
        if single_quad:
            if first!=0 or last!=n or not change.get('rectify_uv') or n%4 or b.u32(off+0xa4)!=0x20000010:raise ValueError('Single quad requires independent restart strips')
            expected=[]
            for k in range(n//4):
                if k:expected.append(65535)
                expected.extend(range(k*4,k*4+4))
            index_count=b.u32(off+0xa8);index_at=b.u32(off+0xac)-1
            actual=struct.unpack('>'+str(index_count)+'H',Binary(parts[1]).slice(index_at,index_count*2))
            if tuple(expected)!=actual:raise ValueError('Unsupported HUD strip topology')
        rows={round(p[1],3) for p in old}
        row_ranges={y:(min(p[0] for p in old if round(p[1],3)==y),max(p[0] for p in old if round(p[1],3)==y)) for y in rows}
        for j,point in enumerate(old):
            at=start+(first+j)*stride
            if bounds is not None:
                x0,y0,x1,y1=bounds
                if change.get('rectify_uv') or change.get('straighten'):
                    left,right=row_ranges[round(point[1],3)]
                    if single_quad and j<4:
                        edge=[p[0] for p in old[:4] if round(p[1],3)==round(point[1],3)]
                        left,right=min(edge),max(edge)
                    if right<=left:raise ValueError('Degenerate HUD horizontal edge')
                    u=(point[0]-left)/(right-left);v=1-(point[1]-lo[1])/(hi[1]-lo[1])
                    x=x0+u*(x1-x0);y=y1-v*(y1-y0)
                    if change.get('rectify_uv'):struct.pack_into('>2e',out[1],at+uv,u,v)
                else:
                    x=x0+(point[0]-lo[0])/(hi[0]-lo[0])*(x1-x0);y=y0+(point[1]-lo[1])/(hi[1]-lo[1])*(y1-y0)
                struct.pack_into('>2f',out[1],at,x,y)
            if z_offset:struct.pack_into('>f',out[1],at+8,point[2]+z_offset)
            color=struct.unpack_from('>4f',parts[1],at+rgba)
            if not all(math.isfinite(v) for v in color):raise ValueError('Non-finite HUD vertex color')
            struct.pack_into('>4f',out[1],at+rgba,*(v*scale for v in (rgb if rgb is not None else color[:3])),0. if change.get('hide') or (single_quad and j>=4) else (color[3] if alpha is None else alpha))
        if bounds is not None or z_offset:
            all_points=[struct.unpack_from('>3f',out[1],start+j*stride) for j in range(n)]
            lower=[min(p[k] for p in all_points) for k in range(3)]
            upper=[max(p[k] for p in all_points) for k in range(3)]
            struct.pack_into('>3f',out[0],off+0x30,*((a+c)/2 for a,c in zip(lower,upper)))
            struct.pack_into('>f',out[0],off+0x10,math.sqrt(sum((a-c)**2 for a,c in zip(lower,upper)))/2)
        reports.append(dict(part=name,vertices=last-first,vertex_range=[first,last],bounds=bounds,hidden=bool(change.get('hide')),rgb_scale=scale))
    text_count=b.u32(0x4c);texts=b.relative(0x50) if text_count else 0
    if text_count>4096:raise ValueError('HUD text count exceeds limit')
    b.slice(texts,text_count*144)
    for name,position in profile.get('text',{}).items():
        options=position if isinstance(position,dict) else {'position':position}
        if set(options)-{'position','scale','marker_offset'}:raise ValueError('Unsupported HUD text option')
        xy=options.get('position',[]);text_scale=options.get('scale',1.)
        if not math.isfinite(text_scale) or not 0.25<=text_scale<=4:raise ValueError('Invalid HUD text scale')
        if len(xy)!=2 or not all(math.isfinite(v) for v in xy):raise ValueError('Invalid HUD text position')
        matches=[texts+i*144 for i in range(text_count) if b.utf16(b.relative(texts+i*144+64),'be')==name]
        if len(matches)!=1:raise ValueError('Unknown/ambiguous HUD text '+name)
        at=matches[0];xyz=b.slice(at+48,12)
        offset=options.get('marker_offset',[0.,0.,0.])
        if len(offset)!=3 or not all(math.isfinite(v) for v in offset):raise ValueError('Invalid HUD marker offset')
        expected_world=tuple(v+d for v,d in zip(struct.unpack('>3f',xyz),offset))
        if b.slice(at+96,12)!=xyz:raise ValueError('HUD text matrix copies differ')
        marker=[];encoded=name.encode('utf-16-be')+bytes(2)
        for field in range(32,len(original)-4,4):
            dest=field+struct.unpack_from('>i',original,field)[0]-1
            if 0<=dest<=len(original)-len(encoded) and original[dest:dest+len(encoded)]==encoded and original[field-16:field-4]==xyz and all(abs(v-w)<1e-4 for v,w in zip(struct.unpack_from('>3f',original,field-32),expected_world)):marker.append(field)
        if len(marker)!=1:raise ValueError('Missing/ambiguous matching HUD marker '+name)
        for field in (at+48,at+96,marker[0]-16):struct.pack_into('>2f',out[0],field,*xy)
        struct.pack_into('>2f',out[0],marker[0]-32,xy[0]+offset[0],xy[1]+offset[1])
        if text_scale!=1:
            # The text's authored 4x4 basis; translation, marker vectors, resource
            # pointers and the separate cached translation remain untouched here.
            basis=[at+r*16+c*4 for r in range(3) for c in range(3)]
            values=[struct.unpack_from('>f',original,p)[0] for p in basis]
            if not all(math.isfinite(v) for v in values):raise ValueError('Non-finite HUD text basis')
            for field,value in zip(basis,values):struct.pack_into('>f',out[0],field,value*text_scale)
        reports.append(dict(text=name,position=xy,matching_marker=True))
    if profile.get('disable_text'):
        # Native HUD dispatchers check this count before their label loop. Keep
        # all record/property/bone bytes rather than relocating or deleting them.
        struct.pack_into('>I',out[0],0x4c,0)
        reports.append(dict(disabled_text_records=text_count))
    result=list(map(bytes,out))
    if list(map(len,result))!=list(map(len,parts)):raise ValueError('HUD edit changed block sizes')
    return result,reports


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('scene',type=Path);parser.add_argument('profile',type=Path);parser.add_argument('output',type=Path)
    args=parser.parse_args();kind,parts=unwrap(args.scene.read_bytes())
    if kind!=2:raise ValueError('Select a SCNE wrapper')
    result,report=edit_scene(parts,json.loads(args.profile.read_text(encoding='utf8')))
    from ..archive.manifests import write_bytes
    if args.output.exists():raise ValueError('Choose a new SCNE output file')
    write_bytes(args.output,wrap(2,result),[args.scene,args.profile])
    print(json.dumps(report,indent=2))


if __name__=='__main__':main()
