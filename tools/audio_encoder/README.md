# ATRAC3 encoder development helper

This helper supplies ATRAC3 encoding for the audio backend and standalone
Windows package. It does not enable song-name editing or modify EBOOT.

The frontend is in `encoder.cpp`. It builds against AtracDEnc revision
`cb170709f836cb43dc0312455188c791159d81dc`:
https://github.com/dcherednik/atracdenc

Install the Python `ziglang` package, clone that upstream repository and check
out the pinned revision, then run from this repository:

```powershell
python tools/audio_encoder/build.py PATH_TO_ATRACDENC
```

The generated executable goes into `choops_py/audio_tools/bin`, which is ignored
by Git. The upstream encoder and this frontend use LGPL 2.1 or later; see
`LICENSE.txt`. Distributing a compiled helper requires the corresponding source
and applicable license notices. Game audio and other game assets are not included.

The paired LGPL FFmpeg helper handles WAV conversion and ATRAC3 decoding. The
Windows app includes both helpers with corresponding source archives and notices.
Game playback validation has not been performed.
