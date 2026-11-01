"""Authenticated, bounded read-only NPD v3/v4 SDAT (observed flags 0x0100003c).

Format reference: RPCS3 Crypto/unedat.cpp and key_vault.h. No emulator is used.
Unsupported compression/debug/other flag combinations are rejected.
"""
import hashlib
import hmac
import io
import struct
from collections import OrderedDict

SDAT_KEY = bytes.fromhex('0d655ef8e674a98ab8505cfa7d012933')
WRAP_KEY = bytes.fromhex('4ca9c14b01c95309969bec68aa0bc081')
WRAP_KEY_V3 = bytes.fromhex('be959ca8308defa2e5e180c63712a9ae')


class SDATReader(io.RawIOBase):
    def __init__(self, path):
        super().__init__()
        from Crypto.Cipher import AES
        from Crypto.Hash import CMAC
        self.stream = open(path, 'rb')
        try:
            header = self.stream.read(256)
            if len(header) != 256 or header[:4] != b'NPD\0':
                raise ValueError('Invalid SDAT header')
            version = struct.unpack_from('>I', header, 4)[0]
            flags, self.block_size, self.size = struct.unpack_from('>IIQ', header, 128)
            if version not in (3,4) or flags != 0x0100003c:
                raise ValueError('Unsupported SDAT version/flags; compressed/debug EDAT is not supported')
            self.wrap_key = WRAP_KEY_V3 if version == 3 else WRAP_KEY
            if not 16 <= self.block_size <= 1024*1024 or self.block_size % 16 or not self.size:
                raise ValueError('Invalid SDAT block size/length')
            self.blocks = (self.size+self.block_size-1)//self.block_size
            self.stream.seek(0, 2)
            expected = 256+self.blocks*32+((self.size+15)//16)*16
            if self.stream.tell() < expected:
                raise ValueError('Truncated SDAT payload')
            self.key = bytes(a ^ b for a, b in zip(header[96:112], SDAT_KEY))
            self.dev = header[96:108]
            self.iv = header[64:80]
            header_key = AES.new(self.wrap_key, AES.MODE_CBC, bytes(16)).decrypt(self.key)
            check = CMAC.new(header_key, ciphermod=AES)
            check.update(header[:160])
            if not hmac.compare_digest(check.digest(), header[160:176]):
                raise ValueError('SDAT header authentication failed')
            self.position = 0
            self.cache = OrderedDict()
        except BaseException:
            self.stream.close()
            raise

    def readable(self):
        return True

    def seekable(self):
        return True

    def tell(self):
        return self.position

    def seek(self, offset, whence=0):
        position = offset if whence == 0 else self.position+offset if whence == 1 else self.size+offset if whence == 2 else -1
        if position < 0:
            raise ValueError('Invalid SDAT seek')
        self.position = position
        return position

    def _block(self, index):
        if index in self.cache:
            self.cache.move_to_end(index)
            return self.cache[index]
        from Crypto.Cipher import AES
        count = min(self.block_size, self.size-index*self.block_size)
        self.stream.seek(256+index*(32+self.block_size))
        metadata = self.stream.read(32)
        data = self.stream.read((count+15)//16*16)
        if len(metadata) != 32 or len(data) != (count+15)//16*16:
            raise ValueError('Truncated SDAT block')
        cipher = AES.new(self.key, AES.MODE_ECB)
        key = cipher.encrypt(self.dev+struct.pack('>I', index))
        hashed = cipher.encrypt(key)
        key = AES.new(self.wrap_key, AES.MODE_CBC, bytes(16)).decrypt(key)
        hashed = AES.new(self.wrap_key, AES.MODE_CBC, bytes(16)).decrypt(hashed)
        expected = bytes(a ^ b for a, b in zip(metadata[:16], metadata[16:]))+metadata[16:20]
        if not hmac.compare_digest(hmac.new(hashed+bytes(4), data, hashlib.sha1).digest(), expected):
            raise ValueError('SDAT block authentication failed at '+str(index))
        decoded = AES.new(key, AES.MODE_CBC, self.iv).decrypt(data)[:count]
        self.cache[index] = decoded
        if len(self.cache) > 8:
            self.cache.popitem(last=False)
        return decoded

    def read(self, size=-1):
        if size is None or size < 0:
            size = self.size-self.position
        size = max(0, min(size, self.size-self.position))
        chunks = []
        while size:
            index, within = divmod(self.position, self.block_size)
            block = self._block(index)
            part = block[within:within+size]
            chunks.append(part)
            self.position += len(part)
            size -= len(part)
        return b''.join(chunks)

    def close(self):
        if hasattr(self, 'stream'):
            self.stream.close()
        super().close()
