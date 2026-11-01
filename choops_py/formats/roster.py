from ..archive.manifests import digest
from .tool_wrapper import unwrap
def inspect(data):
    wrapped=data[:4]==b'2kTl';blocks=unwrap(data)[1] if wrapped else [data]
    return dict(mode='experimental read-only',size=len(data),sha256=digest(data),wrapped=wrapped,block_sizes=[len(b) for b in blocks],prefix_hex=data[:64].hex(),semantic_decode='blocked: roster fields and compression variants require validation')
def compare(a,b):
    spans=[];start=None
    for i in range(max(len(a),len(b))):
        different=i>=len(a) or i>=len(b) or a[i]!=b[i]
        if different and start is None:start=i
        if not different and start is not None:spans.append([start,i]);start=None
    if start is not None:spans.append([start,max(len(a),len(b))])
    return dict(base=inspect(a),custom=inspect(b),changed_ranges=spans)
