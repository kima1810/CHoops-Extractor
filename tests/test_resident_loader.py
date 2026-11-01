import struct
from concurrent.futures import ThreadPoolExecutor
from threading import Event

import pytest
from test_donor_header import inputs, translated
from test_target_motion import fixture

from choops_py.research.resident_loader import ResidentLoaderModel
from choops_py.research.target_motion import prepare_target_image


class Memory:
    def __init__(self):
        self.blocks = {}
        self.calls = []
        self.next = 0x21000000
        self.bad_read = False
        self.bad_free = False
        self.null = False
        self.epoch = 1

    def allocate(self, size, alignment, tag0, tag1):
        self.calls.append(("allocate", size, alignment, tag0, tag1))
        if self.null:
            return 0
        base = self.next
        self.next += 0x10000
        self.blocks[base] = bytes(size)
        return base

    def release(self, base):
        self.calls.append(("free", base))
        self.blocks.pop(base)
        if self.bad_free:
            raise RuntimeError("Free completed then reported failure")

    def write(self, base, data):
        self.blocks[base] = data

    def read(self, base, size):
        return bytes(size) if self.bad_read else self.blocks[base][:size]

    def model(self, **kwargs):
        return ResidentLoaderModel(
            self.allocate,
            self.release,
            self.write,
            self.read,
            owner_identity=lambda: (0x40004000, self.epoch),
            **kwargs,
        )


def image():
    return prepare_target_image(fixture(), [0x10000])[0]


def test_donor_component_is_relocated_before_local_publication_and_freed_after_last_reader(
    tmp_path,
):
    donor, target, address = inputs(tmp_path)
    data, r = translated(donor, target, address)
    memory = Memory()
    loader = memory.model()
    handle = loader.load(data, r["header_offsets"])
    assert memory.calls == [("allocate", len(data), 16, 0, 0)]
    first, second = loader.lease(handle), loader.lease(handle)
    assert first.__enter__() == second.__enter__() == (0x21000000,)
    loader.close()
    assert not any(c[0] == "free" for c in memory.calls)
    with pytest.raises(ValueError, match="readers"):
        with loader.lease(handle):
            pass
    first.__exit__(None, None, None)
    assert memory.blocks
    second.__exit__(None, None, None)
    assert not memory.blocks and loader.stats()["reserved_payload_bytes"] == 0
    assert (
        loader.stats()["released_allocations"] == 1
        and not loader.stats()["native_loader_installed"]
    )
    loader.close()
    with pytest.raises(ValueError, match="closed"):
        loader.load(data, [0])


def test_active_reader_prevents_concurrent_retirement_free():
    memory = Memory()
    loader = memory.model()
    handle = loader.load(image(), [0])
    entered, leave = Event(), Event()

    def worker():
        with loader.lease(handle):
            entered.set()
            assert leave.wait(5)

    with ThreadPoolExecutor(max_workers=1) as pool:
        future = pool.submit(worker)
        assert entered.wait(5)
        loader.retire(handle)
        assert not any(c[0] == "free" for c in memory.calls)
        leave.set()
        future.result(timeout=5)
    assert sum(c[0] == "free" for c in memory.calls) == 1
    assert loader.stats()["banks"] == []


def test_bad_image_and_budget_fail_before_allocation():
    memory = Memory()
    loader = memory.model(budget=64)
    with pytest.raises(ValueError):
        loader.load(bytes(64), [0])
    with pytest.raises(ValueError, match="budget"):
        loader.load(image(), [0])
    assert memory.calls == []


def test_null_allocation_does_not_publish_or_free():
    memory = Memory()
    memory.null = True
    loader = memory.model()
    with pytest.raises(MemoryError):
        loader.load(image(), [0])
    assert (
        loader.stats()["banks"] == [] and loader.stats()["reserved_payload_bytes"] == 0
    )
    assert len(memory.calls) == 1


def test_failed_readback_rolls_back_unpublished_allocation_once():
    memory = Memory()
    memory.bad_read = True
    loader = memory.model()
    with pytest.raises(ValueError, match="readback"):
        loader.load(image(), [0])
    assert loader.stats()["banks"] == [] and not memory.blocks
    assert sum(c[0] == "free" for c in memory.calls) == 1


def test_uncertain_free_is_quarantined_without_retry_or_budget_reuse():
    memory = Memory()
    memory.bad_free = True
    data = image()
    loader = memory.model(budget=len(data))
    handle = loader.load(data, [0])
    with pytest.raises(RuntimeError, match="reported failure"):
        loader.retire(handle)
    assert loader.stats()["banks"][0]["state"] == "quarantined"
    assert loader.stats()["reserved_payload_bytes"] == len(data)
    with pytest.raises(ValueError, match="budget"):
        loader.load(data, [0])
    with pytest.raises(RuntimeError, match="quarantined"):
        loader.close()
    assert sum(c[0] == "free" for c in memory.calls) == 1


def test_overlapping_allocator_result_never_frees_an_existing_live_bank():
    memory = Memory()
    loader = memory.model()
    data = image()
    loader.load(data, [0])
    memory.next = 0x21000000
    with pytest.raises(ValueError, match="overlapping"):
        loader.load(data, [0])
    assert not any(c[0] == "free" for c in memory.calls)
    assert [b["state"] for b in loader.stats()["banks"]] == [
        "quarantined",
        "quarantined",
    ]


def test_allocator_callback_reentry_is_rejected_before_mutating_loader_state():
    memory = Memory()
    loader = memory.model()
    original = loader._write

    def reenter(base, data):
        with pytest.raises(ValueError, match="reenter"):
            loader.close()
        original(base, data)

    loader._write = reenter
    handle = loader.load(image(), [0])
    loader.retire(handle)
    assert loader.stats()["reserved_payload_bytes"] == 0


def test_nonbyte_image_and_unbounded_offset_iterator_fail_before_conversion_or_callbacks():
    memory = Memory()
    loader = memory.model()
    with pytest.raises(ValueError, match="bounded image"):
        loader.load(2**40, [0])
    with pytest.raises(ValueError, match="bounded image"):
        loader.load(image(), iter([0]))
    assert memory.calls == []


@pytest.mark.parametrize("operation", ["lease", "retire"])
def test_heap_generation_reuse_quarantines_instead_of_reading_or_freeing(operation):
    memory = Memory()
    loader = memory.model()
    handle = loader.load(image(), [0])
    memory.epoch += 1
    with pytest.raises(RuntimeError, match="owner/generation"):
        if operation == "lease":
            with loader.lease(handle):
                raise AssertionError("Must not publish stale pointers")
        else:
            loader.retire(handle)
    assert loader.stats()["banks"][0]["state"] == "quarantined"
    assert not any(c[0] == "free" for c in memory.calls)


def test_owner_rebinding_during_allocation_never_publishes_or_frees_ambiguous_pointer():
    memory = Memory()
    loader = memory.model()
    original = loader._allocate

    def change(*args):
        result = original(*args)
        memory.epoch += 1
        return result

    loader._allocate = change
    with pytest.raises(RuntimeError, match="owner/generation"):
        loader.load(image(), [0])
    assert loader.stats()["banks"][0]["state"] == "quarantined"
    assert not any(c[0] == "free" for c in memory.calls)


def test_owner_change_during_readback_blocks_publication_without_freeing_new_heap():
    memory = Memory()
    loader = memory.model()
    read = loader._read

    def change(*args):
        result = read(*args)
        memory.epoch += 1
        return result

    loader._read = change
    with pytest.raises(RuntimeError, match="owner/generation"):
        loader.load(image(), [0])
    assert loader.stats()["banks"][0]["state"] == "quarantined"
    assert not any(c[0] == "free" for c in memory.calls)


def test_unknown_extra_dependency_is_rejected_before_allocation():
    data = bytearray(image())
    event_delta = struct.unpack_from(">i", data, 0x38)[0]
    struct.pack_into(">i", data, 0x3C, event_delta - 4)
    memory = Memory()
    loader = memory.model()
    with pytest.raises(ValueError, match="auxiliary dependency"):
        loader.load(data, [0])
    assert memory.calls == []
