"""Optional in-process acceleration; the Python codec remains portable."""
import ctypes
import os
from pathlib import Path
from functools import lru_cache
from ..core.errors import ToolError


@lru_cache(maxsize=1)
def library():
    if os.name!='nt':return None
    path=Path(__file__).with_name('_h7a.dll')
    if not path.is_file():return None
    try:lib=ctypes.CDLL(str(path))
    except OSError:return None
    if not hasattr(lib,'h7a_version'):return None
    lib.h7a_version.restype=ctypes.c_uint32
    if lib.h7a_version()!=2:return None
    lib.h7a_decode.argtypes=[ctypes.c_char_p,ctypes.c_size_t,ctypes.c_void_p,ctypes.c_size_t]
    lib.h7a_decode.restype=ctypes.c_size_t
    lib.h7a_encode.argtypes=[ctypes.c_char_p,ctypes.c_size_t,ctypes.c_uint32,ctypes.c_void_p,ctypes.c_size_t]
    lib.h7a_encode.restype=ctypes.c_size_t
    lib.h7a_game_compatible.argtypes=[ctypes.c_char_p,ctypes.c_size_t]
    lib.h7a_game_compatible.restype=ctypes.c_uint32
    return lib


def decode(raw,size):
    lib=library()
    if lib is None:return None
    out=ctypes.create_string_buffer(size)
    count=lib.h7a_decode(raw,len(raw),out,size)
    if count!=size:raise ToolError('invalid_h7a','Native decoder rejected invalid compressed data')
    return out.raw


def encode(data,shift):
    lib=library()
    if lib is None:return None
    capacity=len(data)+(len(data)+7)//8
    out=ctypes.create_string_buffer(capacity)
    count=lib.h7a_encode(data,len(data),shift,out,capacity)
    if count>capacity:raise ToolError('compression_verification_failed','Native encoder rejected input')
    return out.raw[:count]


def game_compatible(raw):
    lib=library()
    return None if lib is None else bool(lib.h7a_game_compatible(raw,len(raw)))
