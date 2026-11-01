"""Synthetic policy checks; these do not execute native recruiting."""

from collections import Counter
from dataclasses import replace
from unittest.mock import patch

import pytest

from choops_py.research.transfer_portal import (
    Priority,
    SchoolCandidate,
    assign_priority,
    native_preference_profile,
    rank_schools,
    transfer_label,
)


@pytest.mark.parametrize("code,year", [(4, "FR"), (5, "SO"), (6, "JR"), (7, "SR")])
def test_transfer_class_and_historical_redshirt_labels(code, year):
    assert transfer_label(code, redshirt_used=False) == f"TR {year}"
    assert transfer_label(code, redshirt_used=True) == f"TR {year} (RS)"


@pytest.mark.parametrize("code", [0, 1, 2, 3, 8, 15, True, 5.0])
def test_noncollege_class_rejected(code):
    with pytest.raises(ValueError):
        transfer_label(code, redshirt_used=False)


def test_label_does_not_treat_transfer_sitout_enum_as_redshirt_history():
    with pytest.raises(ValueError):
        transfer_label(5, redshirt_used=2)


def test_priority_repeatable_and_independent_of_iteration_order():
    seed = bytes(range(32))
    expected = {
        str(p): assign_priority(seed, "2030-offseason", str(p)) for p in range(300)
    }
    actual = {
        str(p): assign_priority(seed, "2030-offseason", str(p))
        for p in reversed(range(300))
    }
    assert actual == expected
    assert set(actual.values()) == set(Priority)
    assert any(
        assign_priority(seed, "2031-offseason", p) != v for p, v in expected.items()
    )
    assert any(
        assign_priority(bytes(32), "2030-offseason", p) != v
        for p, v in expected.items()
    )


def test_priority_has_no_school_or_display_name_input_and_balanced_smoke_sample():
    counts = Counter(assign_priority(bytes(32), "2030", str(p)) for p in range(6000))
    assert all(1700 < count < 2300 for count in counts.values())

    # Length framing separates identities that would collide by concatenation.
    class Digest:
        def digest(self):
            return bytes(32)

    with patch(
        "choops_py.research.transfer_portal.sha256", return_value=Digest()
    ) as digest:
        assign_priority(bytes(32), "ab", "c")
        first = digest.call_args.args[0]
        assign_priority(bytes(32), "a", "bc")
        assert digest.call_args.args[0] != first


def test_priority_rejects_255_before_modulo():
    class Digest:
        def digest(self):
            return bytes([255, 2]) + bytes(30)

    with patch("choops_py.research.transfer_portal.sha256", return_value=Digest()):
        assert assign_priority(bytes(32), "2030", "player") is Priority.TEAM_RANKING


@pytest.mark.parametrize(
    "seed,season,player",
    [(b"short", "2030", "x"), (bytes(32), "", "x"), (bytes(32), "2030", "x" * 129)],
)
def test_priority_rejects_missing_stable_inputs(seed, season, player):
    with pytest.raises(ValueError):
        assign_priority(seed, season, player)


CANDIDATES = (
    SchoolCandidate("minutes", 32, 1000, 50, 1),
    SchoolCandidate("hometown", 15, 10, None, 1),
    SchoolCandidate("ranking", 5, 500, 1, 1),
)


@pytest.mark.parametrize(
    "priority,winner",
    [
        (Priority.PLAYING_TIME, "minutes"),
        (Priority.HOMETOWN, "hometown"),
        (Priority.TEAM_RANKING, "ranking"),
    ],
)
def test_each_primary_motivation_controls_interest(priority, winner):
    result = rank_schools(priority, 12, CANDIDATES, source_school_id="source")
    assert result[0].school_id == winner
    assert result == rank_schools(
        priority, 12, tuple(reversed(CANDIDATES)), source_school_id="source"
    )
    assert {r.school_id: r.minutes_gain for r in result} == {
        "minutes": 20,
        "hometown": 3,
        "ranking": -7,
    }


def test_capacity_eligibility_and_source_excluded_without_changing_inputs():
    blocked = (
        replace(CANDIDATES[0], school_id="source"),
        replace(CANDIDATES[0], school_id="full", scholarship_spots=0),
        replace(CANDIDATES[0], school_id="ineligible", eligible=False),
    )
    assert (
        rank_schools(Priority.PLAYING_TIME, 12, blocked, source_school_id="source")
        == ()
    )
    assert blocked[0].projected_minutes == 32


def test_duplicate_id_rejected_even_for_excluded_school():
    with pytest.raises(ValueError, match="duplicate"):
        rank_schools(
            Priority.HOMETOWN,
            12,
            (CANDIDATES[0], CANDIDATES[0]),
            source_school_id="minutes",
        )


@pytest.mark.parametrize(
    "changes",
    [
        {"projected_minutes": float("nan")},
        {"projected_minutes": 41},
        {"projected_minutes": True},
        {"hometown_distance_km": -1},
        {"hometown_distance_km": float("inf")},
        {"hometown_distance_km": 10**1000},
        {"team_rank": 0},
        {"team_rank": True},
        {"scholarship_spots": -1},
        {"eligible": 1},
    ],
)
def test_invalid_metrics_rejected(changes):
    with pytest.raises(ValueError):
        replace(CANDIDATES[0], **changes)


def test_native_code_or_unbounded_candidate_iterator_not_accepted():
    with pytest.raises(ValueError):
        rank_schools("playing_time", 12, CANDIDATES, source_school_id="source")
    with pytest.raises(ValueError):
        rank_schools(Priority.HOMETOWN, 12, iter(CANDIDATES), source_school_id="source")


def test_native_profiles_preserve_rank_vs_motivation_distinction():
    first = native_preference_profile(0)
    assert first["feeling_wanted"] == (0, 1.0)
    assert first["playing_time"][0] == 4
    assert first["playing_time"][1] == pytest.approx(0.2)
    # Native index four is not "playing time" priority.
    assert native_preference_profile(4)["playing_time"][0] != 0


def test_all_initialized_native_profiles_and_three_requested_categories_exist():
    profiles = [native_preference_profile(i) for i in range(96)]
    rows = [tuple(rank for rank, _ in p.values()) for p in profiles]
    assert len(set(rows)) == 96
    assert rows[0] == (0, 1, 2, 3, 4)
    assert rows[-1] == (3, 4, 2, 1, 0)
    assert all(sorted(row) == list(range(5)) and row[0] != 4 for row in rows)
    for name in ("hometown_proximity", "playing_time", "big_program"):
        assert sum(p[name][0] == 0 for p in profiles) == 18
    assert sum(p["feeling_wanted"][0] == 0 for p in profiles) == 24
    assert "team_ranking" not in profiles[0]


@pytest.mark.parametrize("index", [-1, 96, 127, True, 4.0])
def test_uninitialized_or_invalid_native_profile_rejected(index):
    with pytest.raises(ValueError):
        native_preference_profile(index)
