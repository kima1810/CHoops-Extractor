"""Compose static HUD artwork from the supplied game's FONT atlas and metrics.

This does not install fonts, rewrite the font bank, or change runtime text bindings.
The observed green atlas channel carries coverage. Kerning tables are not decoded.
"""
import io
import math
import struct

from PIL import Image

from ..formats.binary import Binary
from ..formats.txtr import TXTR
from ..texture_tools.builtin_converter import to_dds


def render_line(parts, text):
    """Return native-size white RGBA glyphs, using recorded advances/bearings."""
    if len(parts)!=2:raise ValueError('FONT requires header and atlas blocks')
    header=parts[0];b=Binary(header)
    first,last=b.u16(0),b.u16(2)
    if not 0<first<=last<=0xffff or last-first>4096:raise ValueError('Unsupported FONT character range')
    mapping=b.relative(8)
    if (b.u16(mapping),b.u16(mapping+2))!=(first,last):raise ValueError('FONT character maps disagree')
    glyphs=b.relative(mapping+4);b.slice(glyphs,(last-first+1)*96)
    atlas=Image.open(io.BytesIO(to_dds(TXTR([header[32:],parts[1]]).gtf()))).convert('RGB').getchannel('G')
    space=b.u32(12)
    if space>4096 or len(text)>4096:raise ValueError('FONT text exceeds artwork limit')
    pen=0;items=[]
    for char in text:
        if char==' ':pen+=space;continue
        code=ord(char)
        if not first<=code<=last:raise ValueError('Character absent from FONT')
        at=glyphs+(code-first)*96;advance=b.u32(at)
        corners=[struct.unpack_from('>4f',header,at+16+i*16) for i in range(4)]
        uv=struct.unpack_from('>4f',header,at+80)
        if not all(math.isfinite(v) for c in corners for v in c) or not all(math.isfinite(v) and 0<=v<=1 for v in uv):raise ValueError('Invalid FONT glyph metrics')
        x,y=corners[0][:2];u0,v0,u1,v1=uv
        if advance>4096 or u0>u1 or v0>v1 or abs(x)>4096 or abs(y)>4096:raise ValueError('Invalid FONT glyph bounds')
        crop=atlas.crop((round(u0*atlas.width),round(v0*atlas.height),round(u1*atlas.width),round(v1*atlas.height)))
        items.append((round(pen+x),round(y),crop));pen+=advance
    left=min([0]+[x for x,y,im in items]);top=min([0]+[y for x,y,im in items])
    right=max([pen]+[x+im.width for x,y,im in items]);bottom=max([1]+[y+im.height for x,y,im in items])
    if right-left>32768 or bottom-top>8192:raise ValueError('FONT artwork dimensions exceed limit')
    result=Image.new('RGBA',(max(1,right-left),bottom-top))
    for x,y,mask in items:
        glyph=Image.new('RGBA',mask.size,'white');glyph.putalpha(mask)
        result.alpha_composite(glyph,(x-left,y-top))
    return result
