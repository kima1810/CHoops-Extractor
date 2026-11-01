"""Read-only indexed uniform-font decoding and runtime number composition."""

import struct
import math
from PIL import Image


def atlas(texture):
    """The font's trailing ARGB palette is used by the CPU copy path.

    Its GPU remap forces all channels to ONE, so ordinary TXTR previews cannot
    decode these indexed glyphs. Do not generalize this discriminator to L8 art.
    """
    info = texture.info()
    if info['format'] != 'L8' or not info['linear'] or info['cubemap'] or info['remap'] != 0x5500:
        raise ValueError('Expected a supported indexed uniform font atlas')
    data = texture.blocks[info['payload_block']]
    start = info['payload_offset']
    palette_start = (start + info['image_size'] + 3) & ~3
    if palette_start + 1024 > len(data):
        raise ValueError('Indexed font palette is missing or truncated')
    width, height = info['width'], info['height']
    indices = data[start:start + width * height]
    if len(indices) != width * height:
        raise ValueError('Indexed font base image is truncated')
    palette = [bytes((r, g, b, a)) for a, r, g, b in struct.iter_unpack('>4B', data[palette_start:palette_start + 1024])]
    return Image.frombytes('RGBA', (width, height), b''.join(palette[index] for index in indices))


def number_metrics(data, image_width):
    if len(data) < 40:
        raise ValueError('Number glyph metrics are truncated')
    metrics = list(struct.iter_unpack('>2H', data[:40]))
    for x, width in metrics:
        if not width or x + ((width + 3) & ~3) > image_width:
            raise ValueError('Number glyph metric extends outside the atlas')
    return metrics


def number_image(image, metrics, number, size=(256, 128)):
    """Reproduce 0x4E7C8C's width alignment, spacing and 100 -> 00 sentinel."""
    if type(number) is not int or not 0 <= number <= 100:
        raise ValueError('Jersey number must be 0–99 or 100 for 00')
    digits = [0, 0] if number == 100 else [number // 10, number % 10] if number >= 10 else [number]
    if len(metrics) != 10:
        raise ValueError('Ten number glyph metrics are required')
    if len(size) != 2 or not all(type(x) is int and 0 < x <= 4096 for x in size):
        raise ValueError('Invalid number template dimensions')
    image = image.convert('RGBA')
    width, height = size
    if image.height > height:
        raise ValueError('Number glyphs exceed template height')
    background = (*image.getpixel((0, 0))[:3], 0)
    result = Image.new('RGBA', size, background)
    left = (width - sum(metrics[digit][1] for digit in digits)) // 2
    for digit in digits:
        x, glyph_width = metrics[digit]
        copy_width = (glyph_width + 3) & ~3
        if x + copy_width > image.width or left < 0 or left + copy_width > width:
            raise ValueError('Number glyphs exceed template bounds')
        # Copy pixels, including transparent palette entries, as the game does.
        result.paste(image.crop((x, 0, x + copy_width, image.height)), (left, 0))
        left += (glyph_width + 5) & ~3
    return result


def number_uv(data, offset=0x1c):
    """Front/back number transforms set by 0x4DCD5C."""
    if offset not in (0x1c,0x2c,0x3c) or len(data)<offset+16:
        raise ValueError('Uniform number placement record is truncated')
    x,y,width,height=struct.unpack_from('>4f',data,offset)
    if not all(math.isfinite(v) for v in (x,y,width,height)) or width<=0 or height<=0:
        raise ValueError('Invalid uniform number placement')
    return (1/width,1/height,.5-x/width,.5-y/height)


def name_metrics(data, image_width):
    """0x520740 maps apostrophe/hyphen to 0/1 and A–Z (either case) to 2–27."""
    if len(data) < 112:
        raise ValueError('Surname glyph metrics are truncated')
    metrics = list(struct.iter_unpack('>2H', data[:112]))
    if any(not width or x + ((width + 3) & ~3) > image_width for x, width in metrics):
        raise ValueError('Surname glyph metric extends outside the atlas')
    return metrics


def name_image(image, metrics, text='Reborn', size=(256, 32)):
    """Compose the CPU surname strip with 0x520898's aligned spacing."""
    if not isinstance(text, str) or not 1 <= len(text) <= 64 or len(metrics) != 28:
        raise ValueError('Invalid surname preview text or metrics')
    if len(size) != 2 or not all(type(x) is int and 0 < x <= 4096 for x in size):
        raise ValueError('Invalid surname template dimensions')
    indices = []
    for char in text:
        if char == "'": indices.append(0)
        elif char in ('-', ' '): indices.append(1)
        elif 'A' <= char <= 'Z': indices.append(ord(char)-ord('A')+2)
        elif 'a' <= char <= 'z': indices.append(ord(char)-ord('a')+2)
        else: raise ValueError('Unsupported surname glyph: '+char)
    width, height = size
    if image.height > height:
        raise ValueError('Surname glyphs exceed template height')
    def extent(spacing):
        return sum((metrics[i][1]+spacing+3)&~3 for i in indices)-spacing
    spacing = max(1, 25 - extent(0)//len(indices))
    total = extent(spacing)
    if total > width-10:
        # The runtime starts from 25 and reduces spacing for a maximum of
        # three iterations. Refuse an impossible strip rather than crop it.
        if len(indices) <= 2:
            raise ValueError('Surname glyphs exceed template bounds')
        spacing = 25
        for _ in range(3):
            total = extent(spacing)
            if total <= width-10: break
            spacing -= (total-(width-10)+len(indices)-2)//(len(indices)-2)
        total = extent(spacing)
    left = int((width-total)/2)
    result = Image.new('RGBA', size, (*image.getpixel((0,0))[:3],0))
    for char,index in zip(text,indices):
        x,glyph_width=metrics[index];copy_width=(glyph_width+3)&~3
        if left<0 or left+copy_width>width or x+copy_width>image.width:
            raise ValueError('Surname glyphs exceed template bounds')
        if char != ' ':
            result.paste(image.crop((x,0,x+copy_width,image.height)),(left,0))
        left += (glyph_width+spacing+3)&~3
    return result


def name_placement(data):
    """Authored polar name transform from UnAD +08..18 (0x4DCD5C)."""
    if len(data)<28:
        raise ValueError('Surname placement record is truncated')
    x,y,radius,angular_width,radial_scale=struct.unpack_from('>5f',data,8)
    if not all(math.isfinite(v) for v in (x,y,radius,angular_width,radial_scale)) or min(radius,angular_width,radial_scale)<=0:
        raise ValueError('Invalid surname placement')
    return (x,y,radius,angular_width),radial_scale
