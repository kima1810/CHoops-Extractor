import struct

import pytest

from choops_py.research.motion_auxiliary import inspect_selector_curve


def test_signed_ticks_selector_ids_and_exact_bits_are_kept_without_portability_claims():
    raw = struct.pack(">4I", 0x10FFFFFF, 0x18000000, 0x19000000, 0x10000258)
    before = raw
    r = inspect_selector_curve(raw, duration=1, time_scale=2)
    assert [(x["tick"], x["selector"]) for x in r["knots"]] == [
        (-1, 16),
        (0, 24),
        (0, 25),
        (600, 16),
    ]
    assert r["declared_last_query_tick"] == 600 and r["equal_tick_pairs"] == 1
    assert (
        not r["selector_semantics_established"]
        and not r["cross_game_translation_allowed"]
    )
    assert raw == before


@pytest.mark.parametrize(
    "raw,duration,scale",
    [
        (bytes(4), 1, 1),
        (bytes(9), 1, 1),
        (struct.pack(">2I", 1, 0), 0, 1),
        (bytes(8), 1, 1),
        (bytes(8), float("nan"), 1),
        (bytes(8), 0, 0),
    ],
)
def test_unknown_bounds_padding_or_timing_cannot_be_treated_as_a_complete_curve(
    raw, duration, scale
):
    with pytest.raises(ValueError):
        inspect_selector_curve(raw, duration=duration, time_scale=scale)


def test_huge_timing_integer_is_rejected_without_float_overflow():
    with pytest.raises(ValueError, match="timing"):
        inspect_selector_curve(bytes(8), duration=2**2048)
