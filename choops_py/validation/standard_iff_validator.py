from ..formats.standard_iff import StandardIFF,decompress
def validate(data):
    iff=StandardIFF(data)
    for block in iff.blocks:decompress(data[block['start']:block['start']+block['size']],block['logical_size'])
    return dict(valid=True,scope='structural and block decompression; console behavior unverified',**iff.manifest())
