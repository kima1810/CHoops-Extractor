# LGPL audio helper

The standalone Windows app uses a small FFmpeg command-line helper for WAV and
ATRAC3 conversion plus the existing AtracDEnc-based ATRAC3 encoder helper. The
FFmpeg build is deliberately restricted to the formats used by the audio
workflow and disables GPL/nonfree components and autodetection.

On Windows, install MSYS2 and the MINGW64 toolchain packages
`mingw-w64-x86_64-toolchain`, `make`, `git`, `pkgconf` and `diffutils`. Then, from an MSYS2 MINGW64 shell at the repository
root, run:

```bash
bash tools/audio_codec/build_ffmpeg.sh
```

Build the encoder separately with `python tools/dev/setup.py --audio-encoder`.
The package script requires both helpers and includes their pinned source
archives, license texts and build scripts under `THIRD-PARTY-SOURCES`.

The build fetches FFmpeg 9.0.2 at commit
`946fcce07b6dcd0331c8cc609192aeff5e1924f8`. The compiled helper is written to
the ignored `choops_py/audio_tools/bin/` directory. The executable's build
configuration is checked to ensure GPL and nonfree options are absent.
