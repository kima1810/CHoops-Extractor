"""One TXTR model for raw, wrapped, IFF and CDF subfiles."""
from dataclasses import dataclass
from .binary import Binary
from .tool_wrapper import unwrap,wrap
from ..texture_tools.gtf import descriptor_info,make
from ..core.errors import ToolError
@dataclass
class TXTR:
    blocks: list
    wrapper_type: int | None = None
    @classmethod
    def from_bytes(cls,data):
        if data[:4]==b'2kTl':
            typ,blocks=unwrap(data)
            if typ!=1:raise ToolError('invalid_txtr_wrapper','Wrapper type must be TXTR (1)')
            return cls(blocks,typ)
        return cls([data])
    def serialize(self):
        return wrap(self.wrapper_type,self.blocks) if self.wrapper_type is not None else self.blocks[0] if len(self.blocks)==1 else wrap(1,self.blocks)
    def info(self):
        if not 1<=len(self.blocks)<=2:raise ToolError('unsupported_txtr_layout','TXTR requires one inline block or two split blocks')
        b=Binary(self.blocks[0]);descriptor=b.slice(0x58,24);info=descriptor_info(descriptor)
        if len(self.blocks)==1:
            offset=b.relative(0xa4)
            if offset<0xb0:raise ToolError('invalid_txtr_pointer','Inline image overlaps header')
            b.slice(offset,info['image_size'])
        else:
            offset=0;Binary(self.blocks[1]).slice(0,info['image_size'])
        return dict(info,wrapper_status='2kTl' if self.wrapper_type is not None else 'raw',block_sizes=[len(x) for x in self.blocks],payload_block=len(self.blocks)-1,payload_offset=offset)
    def image(self):
        info=self.info();return self.blocks[info['payload_block']][info['payload_offset']:info['payload_offset']+info['image_size']]
    def gtf(self):return make(self.blocks[0][0x58:0x70],self.image())
    def replace_image(self,image):
        info=self.info()
        if len(image)!=info['image_size']:raise ToolError('payload_size_mismatch','Replacement must retain image byte count')
        blocks=list(self.blocks);index=info['payload_block'];out=bytearray(blocks[index]);start=info['payload_offset'];out[start:start+len(image)]=image;blocks[index]=bytes(out)
        result=TXTR(blocks,self.wrapper_type);result.info();return result

def inspect(data):return TXTR.from_bytes(data).info()
