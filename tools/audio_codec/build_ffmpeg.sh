#!/usr/bin/env bash
set -euo pipefail

# Build the narrow, LGPL-only FFmpeg CLI used by the standalone Audio workspace.
# Run from an MSYS2 MINGW64 shell with mingw-w64-x86_64-toolchain, make, git,
# pkgconf and diffutils installed. No external codec libraries are autodetected.

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd -W)"
VERSION='n9.0.2'
REVISION='946fcce07b6dcd0331c8cc609192aeff5e1924f8'
VENDOR="$ROOT/.private/vendor/ffmpeg-$VERSION"
BIN="$ROOT/choops_py/audio_tools/bin/choops_ffmpeg.exe"

mkdir -p "$(dirname "$VENDOR")" "$(dirname "$BIN")"
if [[ ! -d "$VENDOR/.git" ]]; then
    git clone --filter=blob:none --no-checkout https://github.com/FFmpeg/FFmpeg.git "$VENDOR"
fi
if ! actual="$(git -C "$VENDOR" rev-parse "$VERSION^{commit}" 2>/dev/null)"; then
    git -C "$VENDOR" fetch --depth 1 origin "$VERSION"
    actual="$(git -C "$VENDOR" rev-parse FETCH_HEAD)"
fi
[[ "$actual" == "$REVISION" ]] || { echo "Unexpected FFmpeg revision: $actual" >&2; exit 1; }
git -C "$VENDOR" checkout --detach "$REVISION"

BUILD="$ROOT/output/temp/ffmpeg-build-$VERSION"
mkdir -p "$BUILD"
cd "$BUILD"
"$VENDOR/configure" \
    --prefix="$BUILD/install" \
    --arch=x86_64 \
    --target-os=mingw32 \
    --cc=gcc \
    --cxx=g++ \
    --pkg-config=pkg-config \
    --pkg-config-flags=--static \
    --extra-ldflags='-static -static-libgcc -static-libstdc++' \
    --disable-debug \
    --disable-doc \
    --disable-network \
    --disable-autodetect \
    --disable-gpl \
    --disable-nonfree \
    --disable-programs \
    --enable-ffmpeg \
    --disable-ffplay \
    --disable-ffprobe \
    --disable-everything \
    --enable-static \
    --disable-shared \
    --disable-x86asm \
    --enable-swresample \
    --enable-protocol=file,pipe \
    --enable-demuxer=wav \
    --enable-muxer=pcm_s16le,pcm_f32le \
    --enable-decoder=atrac3,pcm_u8,pcm_s8,pcm_u16le,pcm_u16be,pcm_s16le,pcm_s16be,pcm_s24le,pcm_s24be,pcm_s32le,pcm_s32be,pcm_f32le,pcm_f32be,pcm_f64le,pcm_f64be \
    --enable-encoder=pcm_s16le,pcm_f32le \
    --enable-filter=aresample,aformat \
    --disable-parsers
make -j"${NUMBER_OF_PROCESSORS:-4}" ffmpeg.exe
cp ffmpeg.exe "$BIN"

buildconf="$($BIN -buildconf 2>&1)"
if grep -Eq -- '--enable-(gpl|nonfree)' <<<"$buildconf"; then
    echo 'Refusing to package an FFmpeg build with GPL or nonfree options.' >&2
    exit 1
fi
grep -q -- '--disable-gpl' <<<"$buildconf"
grep -q -- '--disable-nonfree' <<<"$buildconf"
"$BIN" -decoders 2>&1 | grep -q ' atrac3 '
filters="$("$BIN" -filters 2>&1)"
grep -q ' aresample ' <<<"$filters"
grep -q ' aformat ' <<<"$filters"
formats="$("$BIN" -formats 2>&1)"
grep -q ' wav ' <<<"$formats"
grep -q ' s16le ' <<<"$formats"
grep -q ' f32le ' <<<"$formats"

echo "Built $BIN from FFmpeg $VERSION ($REVISION), with GPL/nonfree disabled."
