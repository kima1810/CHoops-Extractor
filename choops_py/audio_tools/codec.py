"""ATRAC3 decoding and encoding with open-source codec components."""
import math
import os
import shutil
import struct
import subprocess
import sys
import time
import uuid
import wave
from pathlib import Path
from ..archive.manifests import OUTPUT

FRAME_SAMPLES=1024
BYTES_PER_CHANNEL=152
GAME_DELAY=2048
ENCODER_DELAY=1162


def ffmpeg_path():
    name='choops_ffmpeg.exe' if os.name=='nt' else 'choops_ffmpeg'
    bundled=Path(__file__).parent/'bin'/name
    if bundled.is_file():return bundled
    if getattr(sys,'frozen',False):raise ValueError('The bundled LGPL audio helper is missing; reinstall the application package')
    found=shutil.which(name) or shutil.which('ffmpeg')
    if found:return Path(found)
    raise ValueError('The LGPL audio helper is missing; run tools/audio_codec/build_ffmpeg.sh (MSYS2 MINGW64 on Windows, bash on macOS)')


def _run_ffmpeg(args,work,job,label,timeout=1800):
    log_path=work/'ffmpeg.log'
    with log_path.open('wb') as log:
        process=subprocess.Popen([str(ffmpeg_path()),'-nostdin','-hide_banner','-loglevel','error','-y',*map(str,args)],
                                 stdin=subprocess.DEVNULL,stdout=log,stderr=log,
                                 creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
        try:
            deadline=time.monotonic()+timeout
            while process.poll() is None:
                if job:job.check()
                if time.monotonic()>deadline:raise ValueError('Audio conversion timed out')
                time.sleep(.1)
        finally:
            if process.poll() is None:process.kill();process.wait()
    if process.returncode:
        raise ValueError(label+' failed: '+log_path.read_text(errors='replace')[-500:])


def atrac_riff(data,channels,rate):
    if channels not in (1,2) or not 8000<=rate<=192000:raise ValueError('Unsupported ATRAC3 channel/rate configuration')
    align=BYTES_PER_CHANNEL*channels
    if not data or len(data)%align:raise ValueError('ATRAC3 stream ends inside a frame')
    extra=struct.pack('<HIHHHH',1,1024,0,0,1,0)
    fmt=struct.pack('<HHIIHHH',0x270,channels,rate,align*rate//1024,align,0,14)+extra
    body=b'WAVEfmt '+struct.pack('<I',len(fmt))+fmt+b'data'+struct.pack('<I',len(data))+data
    return b'RIFF'+struct.pack('<I',len(body))+body


def export_wav(data,channels,rate,output,samples=None,job=None):
    if channels not in (1,2) or not 8000<=rate<=192000:raise ValueError('Unsupported ATRAC3 channel/rate configuration')
    work=OUTPUT/'temp'/('audio_decode_'+uuid.uuid4().hex);work.mkdir(parents=True)
    raw_path=work/'decoded.s16le';input_path=work/'input.wav';written=0;skip=GAME_DELAY
    try:
        input_path.write_bytes(atrac_riff(data,channels,rate))
        _run_ffmpeg(['-i',input_path,'-map','0:a:0','-vn','-acodec','pcm_s16le','-f','s16le','-ac',channels,'-ar',rate,raw_path],work,job,'ATRAC3 decode')
        frame_bytes=channels*2;raw_size=raw_path.stat().st_size
        if raw_size%frame_bytes:raise ValueError('Decoded PCM ended inside a sample frame')
        available=raw_size//frame_bytes-skip
        count=available if samples is None else min(available,samples)
        if count<=0:raise ValueError('Audio stream has no samples after decoder priming')
        if samples is not None and available<samples:raise ValueError('Decoded audio is shorter than its declared sample range')
        with raw_path.open('rb') as raw,wave.open(str(output),'wb') as target:
            target.setnchannels(channels);target.setsampwidth(2);target.setframerate(rate)
            raw.seek(skip*frame_bytes);remaining=count*frame_bytes
            while remaining:
                if job:job.check()
                block=raw.read(min(1024*1024,remaining))
                if not block:break
                target.writeframesraw(block);written+=len(block)//frame_bytes;remaining-=len(block)
        if written!=count:raise ValueError('Decoded audio ended before the requested sample range')
        return dict(channels=channels,sample_rate=rate,samples=written,seconds=written/rate,format='PCM16 WAV')
    finally:
        if work.resolve().is_relative_to((OUTPUT/'temp').resolve()):shutil.rmtree(work)


def encoder_path():
    path=Path(__file__).parent/'bin'/('choops_atrac3_encoder.exe' if os.name=='nt' else 'choops_atrac3_encoder')
    if not path.is_file():raise ValueError('ATRAC encoder is missing; build it with tools/audio_encoder/build.py or use a desktop release')
    return path


def encode_wav(source,channels,rate,job=None,target_samples=None):
    if channels not in (1,2) or not 8000<=rate<=192000:raise ValueError('Unsupported ATRAC3 channel/rate configuration')
    source=Path(source).resolve()
    try:
        with source.open('rb') as audio:
            header=audio.read(12)
        if len(header)!=12 or header[:4] not in (b'RIFF',b'RF64') or header[8:]!=b'WAVE':
            raise ValueError('Replacement audio must be a RIFF or RF64 WAV file')
    except OSError as exc:
        raise ValueError('Replacement WAV could not be opened') from exc
    work=OUTPUT/'temp'/('audio_encode_'+uuid.uuid4().hex);work.mkdir(parents=True)
    pcm_path=work/'input.f32';converted=work/'converted.f32';encoded=work/'output.at3';samples=0
    try:
        _run_ffmpeg(['-i',source,'-map','0:a:0','-vn','-acodec','pcm_f32le','-f','f32le','-ac',channels,'-ar',rate,converted],work,job,'WAV conversion')
        converted_size=converted.stat().st_size
        if converted_size%(4*channels):raise ValueError('Converted WAV ended inside a sample frame')
        input_samples=converted_size//(4*channels)
        if not input_samples:raise ValueError('WAV contains no audio samples')
        if input_samples>rate*1800:raise ValueError('A replacement track may not exceed 30 minutes')
        if target_samples is not None and (target_samples<=0 or target_samples>rate*1800):
            raise ValueError('Target audio length is outside the supported range')
        samples=input_samples if target_samples is None else target_samples
        with pcm_path.open('wb') as pcm,converted.open('rb') as src:
            pcm.write(b'\0'*((GAME_DELAY-ENCODER_DELAY)*channels*4))
            remaining=samples*channels*4
            while remaining:
                if job:job.check()
                block=src.read(min(1024*1024,remaining))
                if block:
                    pcm.write(block);remaining-=len(block)
                else:
                    silence=min(1024*1024,remaining)
                    pcm.write(b'\0'*silence);remaining-=silence
        if job:job.progress(0,1,'Encoding ATRAC3 replacement');job.check()
        with (work/'encoder.log').open('wb') as log:
            process=subprocess.Popen([str(encoder_path()),str(pcm_path),str(encoded),str(channels)],stdout=log,stderr=log,
                                     creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
            try:
                deadline=time.monotonic()+1800
                while process.poll() is None:
                    if job:job.check()
                    if time.monotonic()>deadline:raise ValueError('ATRAC encoding timed out')
                    time.sleep(.1)
            finally:
                if process.poll() is None:process.kill();process.wait()
        if process.returncode:raise ValueError('ATRAC encoder failed: '+(work/'encoder.log').read_text(errors='replace')[-500:])
        data=encoded.read_bytes();align=BYTES_PER_CHANNEL*channels
        if len(data)%align or len(data)//align*1024-GAME_DELAY<samples:raise ValueError('Encoded replacement has an invalid sample extent')
        export_wav(data,channels,rate,work/'validated.wav',samples,job)
        return data,samples
    finally:
        if work.resolve().is_relative_to((OUTPUT/'temp').resolve()):shutil.rmtree(work)


def playback_samples(encoded_size,channels,rate,stored=None):
    align=BYTES_PER_CHANNEL*channels
    if not encoded_size or encoded_size%align:raise ValueError('Audio byte count is not frame-aligned')
    physical=encoded_size//align*1024-GAME_DELAY
    if physical<=0:raise ValueError('Audio stream is too short')
    if stored is not None and math.isfinite(stored):
        target=round(stored)
        if 0<target<=physical and physical-target<=8192:return target
    return physical
