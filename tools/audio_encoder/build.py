"""Build the LGPL ATRAC3 helper from pinned upstream sources using Zig."""
from pathlib import Path
import argparse
import subprocess
import importlib.util
import sys

REVISION='cb170709f836cb43dc0312455188c791159d81dc'
SOURCES=('env.cpp','transient_detector.cpp','transient_spectral_upsampler.cpp',
         'atrac3denc.cpp','atrac/at3/atrac3.cpp','atrac/at3/atrac3_bitstream.cpp',
         'atrac/atrac_scale.cpp','atrac/atrac_enc_cache.cpp','atrac/atrac_psy_common.cpp',
         'atrac/at1/atrac1.cpp','atrac/at3p/at3p_tables.cpp',
         'lib/mdct/mdct.cpp','lib/bs_encode/encode.cpp','lib/bitstream/bitstream.cpp','qmf/qmf.cpp')


def build(source):
    root=Path(__file__).resolve().parents[2];src=Path(source).resolve()/'src'
    if sys.platform=='darwin':
        cc=['xcrun','clang'];cxx=['xcrun','clang++']
    else:
        zig=Path(importlib.util.find_spec('ziglang').origin).parent/('zig.exe' if sys.platform=='win32' else 'zig')
        cc=[str(zig),'cc'];cxx=[str(zig),'c++']
    out=root/'choops_py/audio_tools/bin';out.mkdir(parents=True,exist_ok=True)
    work=root/'output/temp/atrac_encoder_compile';work.mkdir(parents=True,exist_ok=True)
    target=['-target','x86_64-windows-gnu'] if sys.platform=='win32' else []
    include=['-I'+str(src),'-I'+str(src/'lib'),'-I'+str(src/'lib/fft/kissfft_impl')]
    objects=[]
    for relative in ('lib/fft/kissfft_impl/kiss_fft.c','lib/fft/kissfft_impl/tools/kiss_fftr.c'):
        obj=work/(Path(relative).stem+'.o');objects.append(str(obj))
        subprocess.run([*cc,*target,'-O2','-Dkiss_fft_scalar=float',*include,'-c',str(src/relative),'-o',str(obj)],check=True)
    output=out/('choops_atrac3_encoder.exe' if sys.platform=='win32' else 'choops_atrac3_encoder')
    subprocess.run([*cxx,*target,'-std=c++17','-O2','-ffile-prefix-map='+str(root)+'=choops',*include,
                    str(Path(__file__).with_name('encoder.cpp')),*[str(src/p) for p in SOURCES],*objects,
                    *(['-municode'] if sys.platform=='win32' else []),'-o',str(output)],check=True)
    print(output)


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('source',help='AtracDEnc source directory at '+REVISION)
    build(parser.parse_args().source)
