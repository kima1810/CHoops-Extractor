"""A source-bound, explicit batch of song replacements awaiting save."""
from pathlib import Path


class PendingSongs:
    def __init__(self):
        self.archive=None
        self.source_key=None
        self.items={}

    @staticmethod
    def identity(archive):
        if not hasattr(archive,'path') or not hasattr(archive,'parts'):return archive
        path=Path(archive.path).resolve();parts=[]
        for part in archive.parts:
            stat=(path/part['name']).stat()
            parts.append((part['name'],stat.st_size,stat.st_mtime_ns,stat.st_ino))
        return str(path).casefold(),tuple(parts)

    def add(self,archive,row,path):
        identity=self.identity(archive)
        if self.items and self.source_key!=identity:
            raise ValueError('Save or clear queued songs before changing the source JB')
        path=Path(path).resolve()
        with path.open('rb') as stream:header=stream.read(12)
        if len(header)!=12 or header[:4] not in (b'RIFF',b'RF64') or header[8:]!=b'WAVE' or path.stat().st_size<=12:
            raise ValueError('Choose a nonempty RIFF or RF64 WAV file')
        self.archive=archive
        self.source_key=identity
        self.items[(row['bank'],row['index'])]=(dict(row),path)

    def replacements(self,archive):
        if not self.items:raise ValueError('Queue at least one song before saving')
        if self.source_key!=self.identity(archive):
            raise ValueError('Queued songs belong to a different JB; return to that source or clear the queue')
        return list(self.items.values())

    def saved(self,archive,replacements):
        if self.source_key!=self.identity(archive):return
        for row,path in replacements:
            key=(row['bank'],row['index'])
            if self.items.get(key)==(row,path):self.items.pop(key)

    def clear(self):
        self.items.clear()
        self.archive=None
        self.source_key=None
