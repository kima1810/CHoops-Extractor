"""Offline ownership model for a future native allocator binding.

Callbacks are synchronous, bound to the same allocator object for allocate/free.
There is no installed native hook, real process access or game publication here.
"""

import struct
from contextlib import contextmanager
from threading import RLock

from .target_motion import MAX_IMAGE, relocate_target_image


class ResidentLoaderModel:
    """Validate, allocate, relocate, read back, then publish to a local registry.

    Allocation callback shape follows CH 0x843404: (size, alignment, tag0, tag1),
    with its object bound by the caller. Release follows CH 0x8434B8(pointer).
    Native reader acquisition/retirement must still be hooked before deployment.
    """

    def __init__(
        self, allocate, release, write, read, *, owner_identity, budget=MAX_IMAGE
    ):
        if type(budget) is not int or not 64 <= budget <= MAX_IMAGE:
            raise ValueError("Resident payload budget must be 64 bytes..16 MiB")
        self._allocate, self._release = allocate, release
        self._write, self._read = write, read
        self._owner_identity = owner_identity
        self._budget, self._reserved = budget, 0
        self._banks, self._next = {}, 1
        self._closed = False
        self._callback_active = False
        self._released = 0
        self._lock = RLock()

    def _callback(self, function, *args):
        if self._callback_active:
            raise ValueError("Allocator callbacks must not reenter the loader model")
        self._callback_active = True
        try:
            return function(*args)
        finally:
            self._callback_active = False

    def _check_reentry(self):
        if self._callback_active:
            raise ValueError("Allocator callbacks must not reenter the loader model")

    def _owner(self):
        identity = self._callback(self._owner_identity)
        if (
            not isinstance(identity, tuple)
            or len(identity) != 2
            or any(type(x) is not int for x in identity)
            or not 0 < identity[0] < 1 << 32
            or not 0 <= identity[1] < 1 << 64
        ):
            raise ValueError("Supply an immutable heap address/generation identity")
        return identity

    def _check_owner(self, bank):
        try:
            if self._owner() == bank["owner"]:
                return
        except BaseException:
            bank["state"] = "quarantined"
            raise
        for affected in self._banks.values():
            if affected["owner"] == bank["owner"]:
                affected["state"] = "quarantined"
        raise RuntimeError(
            "Allocator heap owner/generation changed; allocations quarantined"
        )

    def _drop(self, bank):
        # An uncertain free is quarantined permanently: automatic retry could
        # double-free if the callback freed memory and then raised an error.
        try:
            self._check_owner(bank)
            self._callback(self._release, bank["base"])
        except BaseException:
            bank["state"] = "quarantined"
            raise
        bank["state"] = "released"
        self._reserved -= bank["bytes"]
        self._banks.pop(bank["handle"])
        self._released += 1

    def load(self, image, header_offsets):
        if (
            not isinstance(image, (bytes, bytearray))
            or not 64 <= len(image) <= MAX_IMAGE
            or not isinstance(header_offsets, (list, tuple))
            or not 1 <= len(header_offsets) <= 4096
        ):
            raise ValueError("Choose bounded image bytes and header offsets")
        image, offsets = bytes(image), tuple(header_offsets)
        # Validate all known extents before making any allocation callback.
        relocate_target_image(image, offsets, 0x20000000, source_state="relative")
        for offset in offsets:
            if (
                struct.unpack_from(">I", image, offset + 16)[0] & 63
                or struct.unpack_from(">I", image, offset + 60)[0]
            ):
                raise ValueError(
                    "Unknown auxiliary dependency extents cannot be published"
                )
        with self._lock:
            self._check_reentry()
            if self._closed:
                raise ValueError("Resident loader model is closed")
            if len(self._banks) >= 4096 or self._reserved + len(image) > self._budget:
                raise ValueError("Resident payload budget exhausted")
            owner = self._owner()
            base = self._callback(self._allocate, len(image), 16, 0, 0)
            if base == 0:
                raise MemoryError("Native allocation callback returned null")
            handle = self._next
            self._next += 1
            bank = dict(
                owner=owner,
                handle=handle,
                base=base,
                bytes=len(image),
                readers=0,
                state="allocated",
                offsets=offsets,
            )
            self._banks[handle] = bank
            self._reserved += len(image)
            invalid = (
                type(base) is not int
                or base < 0x10000
                or base % 16
                or base + len(image) > 1 << 32
            )
            overlaps = (
                []
                if invalid
                else [
                    b
                    for b in self._banks.values()
                    if b is not bank
                    and type(b["base"]) is int
                    and base < b["base"] + b["bytes"]
                    and b["base"] < base + len(image)
                ]
            )
            if invalid or overlaps:
                # An allocator overlap may already have damaged an older bank.
                # Stop new leases to every affected allocation; never free an
                # ambiguous shared pointer automatically.
                for affected in [bank, *overlaps]:
                    affected["state"] = "quarantined"
                raise ValueError(
                    "Allocator returned invalid or overlapping native memory"
                )
            self._check_owner(bank)
            try:
                native = relocate_target_image(
                    image, offsets, base, source_state="relative"
                )
                self._callback(self._write, base, native)
                if self._callback(self._read, base, len(native)) != native:
                    raise ValueError("Resident image readback mismatch")
                self._check_owner(bank)
            except BaseException:
                if bank["state"] != "quarantined":
                    self._drop(bank)
                raise
            bank["state"] = "published"
            return handle

    @contextmanager
    def lease(self, handle):
        with self._lock:
            self._check_reentry()
            bank = self._banks.get(handle)
            if bank is None:
                raise ValueError("Unknown or released resident handle")
            if self._closed or bank["state"] != "published":
                raise ValueError("Resident bank is not accepting readers")
            self._check_owner(bank)
            bank["readers"] += 1
            pointers = tuple(bank["base"] + offset for offset in bank["offsets"])
        try:
            yield pointers
        finally:
            with self._lock:
                bank["readers"] -= 1
                if bank["readers"] == 0 and bank["state"] == "draining":
                    self._drop(bank)

    def retire(self, handle):
        with self._lock:
            self._check_reentry()
            bank = self._banks.get(handle)
            if bank is None:
                raise ValueError("Unknown or released resident handle")
            if bank["state"] == "published":
                bank["state"] = "draining"
            if bank["state"] == "draining" and not bank["readers"]:
                self._drop(bank)

    def close(self):
        with self._lock:
            self._check_reentry()
            self._closed = True
            failures = []
            for handle in tuple(self._banks):
                try:
                    self.retire(handle)
                except Exception as error:
                    failures.append(error)
            if failures or any(
                b["state"] == "quarantined" for b in self._banks.values()
            ):
                raise RuntimeError(
                    "Resident releases failed; allocations quarantined"
                ) from (failures[0] if failures else None)

    def stats(self):
        with self._lock:
            return dict(
                payload_budget=self._budget,
                reserved_payload_bytes=self._reserved,
                banks=[dict(v) for v in self._banks.values()],
                released_allocations=self._released,
                registry="offline-model-only",
                native_loader_installed=False,
                total_process_memory_bounded=False,
                gameplay_ready=False,
            )
