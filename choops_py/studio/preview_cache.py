"""Bounded immutable RGBA cache shared by the JB and override preview sources."""
from collections import OrderedDict
from threading import RLock


class ImageCache:
    def __init__(self, limit=64*1024*1024):
        self.limit=limit
        self.items: OrderedDict[object, tuple[tuple[int, int], bytes]] = OrderedDict()
        self.bytes=0
        self.lock=RLock()

    def get(self, key, decode):
        with self.lock:
            if key in self.items:
                self.items.move_to_end(key)
                return self.items[key]
        result=decode()
        size=len(result[1])
        if size>self.limit:return result
        with self.lock:
            previous=self.items.pop(key,None)
            if previous is not None:self.bytes-=len(previous[1])
            while self.items and self.bytes+size>self.limit:
                _,removed=self.items.popitem(last=False)
                self.bytes-=len(removed[1])
            self.items[key]=result
            self.bytes+=size
        return result


images=ImageCache()
