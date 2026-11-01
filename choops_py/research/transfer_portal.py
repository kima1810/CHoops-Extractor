"""Offline transfer-recruiting policy; no native records or saves are written.

Inputs are explicit caller-supplied projections, not decoded game fields.
A native recruiting adapter and persistence contract remain unimplemented.
"""

from dataclasses import dataclass
from enum import Enum
from hashlib import sha256
from itertools import permutations
from math import isfinite
from struct import pack, unpack


class Priority(str, Enum):
    PLAYING_TIME = "playing_time"
    HOMETOWN = "hometown"
    TEAM_RANKING = "team_ranking"


def _identity(value: str, name: str) -> bytes:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be a nonempty identity")
    encoded = value.encode("utf8")
    if len(encoded) > 128:
        raise ValueError(f"{name} exceeds 128 encoded bytes")
    return encoded


def _number(value: float, name: str, maximum: float | None = None) -> None:
    if type(value) not in (int, float) or not 0 <= value <= 1e9:
        raise ValueError(f"{name} must be a bounded nonnegative number")
    if not isfinite(value) or (maximum is not None and value > maximum):
        raise ValueError(f"invalid {name}")


def transfer_label(class_code: int, *, redshirt_used: bool) -> str:
    """Format established college class codes, without changing eligibility.

    redshirt_used is historical eligibility usage, not transfer sit-out status.
    The caller must supply the class appropriate to this offseason's phase.
    """
    if type(class_code) is not int or class_code not in (4, 5, 6, 7):
        raise ValueError("a transfer requires a college FR/SO/JR/SR class code")
    if type(redshirt_used) is not bool:
        raise ValueError("redshirt_used must be a boolean")
    return (
        "TR "
        + ("FR", "SO", "JR", "SR")[class_code - 4]
        + (" (RS)" if redshirt_used else "")
    )


def assign_priority(seed: bytes, season_id: str, player_id: str) -> Priority:
    """Uniform three-way pseudorandom draw, stable for seed/season/player.

    The integration must retain the seed and stable identities across save/reload.
    Rejection sampling avoids modulo bias. No native PRNG state is touched.
    """
    if not isinstance(seed, bytes) or len(seed) != 32:
        raise ValueError("seed must be exactly 32 bytes")
    season = _identity(season_id, "season_id")
    player = _identity(player_id, "player_id")
    digest = sha256(
        b"choops-transfer-priority-v1\0"
        + seed
        + len(season).to_bytes(2, "big")
        + season
        + len(player).to_bytes(2, "big")
        + player
    ).digest()
    for counter in range(256):
        for byte in digest:
            if byte < 255:
                return tuple(Priority)[byte % 3]
        digest = sha256(digest + counter.to_bytes(2, "big")).digest()
    raise ValueError("could not draw a priority")


@dataclass(frozen=True)
class SchoolCandidate:
    school_id: str
    projected_minutes: float
    hometown_distance_km: float
    team_rank: int | None
    scholarship_spots: int
    eligible: bool = True

    def __post_init__(self) -> None:
        _identity(self.school_id, "school_id")
        _number(self.projected_minutes, "projected_minutes", 40)
        _number(self.hometown_distance_km, "hometown_distance_km")
        if self.team_rank is not None and (
            type(self.team_rank) is not int or not 1 <= self.team_rank <= 1_000_000
        ):
            raise ValueError("team_rank must be positive or None for unranked")
        if (
            type(self.scholarship_spots) is not int
            or not 0 <= self.scholarship_spots <= 100
        ):
            raise ValueError("invalid scholarship_spots")
        if type(self.eligible) is not bool:
            raise ValueError("eligible must be a boolean")


@dataclass(frozen=True)
class SchoolInterest:
    school_id: str
    priority: Priority
    minutes_gain: float
    hometown_distance_km: float
    team_rank: int | None


def rank_schools(
    priority: Priority,
    current_minutes: float,
    candidates: tuple[SchoolCandidate, ...],
    *,
    source_school_id: str,
) -> tuple[SchoolInterest, ...]:
    """Order eligible destinations by one priority, without committing a player.

    Playing-time priority sorts by projected minutes gained over the source.
    Hometown priority sorts by distance, ranking priority by lower numeric rank;
    unranked schools follow ranked schools. Ties use stable school identity.
    Values are explanatory metrics, not native interest percentages or promises.
    """
    if not isinstance(priority, Priority):
        raise ValueError("priority must be a Priority")
    _number(current_minutes, "current_minutes", 40)
    _identity(source_school_id, "source_school_id")
    if not isinstance(candidates, tuple) or len(candidates) > 4096:
        raise ValueError("candidates must be a bounded tuple")
    identities = set()
    result = []
    for candidate in candidates:
        if not isinstance(candidate, SchoolCandidate):
            raise ValueError("invalid candidate")
        if candidate.school_id in identities:
            raise ValueError("duplicate school identity")
        identities.add(candidate.school_id)
        if (
            candidate.school_id == source_school_id
            or not candidate.eligible
            or candidate.scholarship_spots == 0
        ):
            continue
        result.append(
            SchoolInterest(
                candidate.school_id,
                priority,
                candidate.projected_minutes - current_minutes,
                candidate.hometown_distance_km,
                candidate.team_rank,
            )
        )
    if priority is Priority.PLAYING_TIME:
        result.sort(key=lambda row: (-row.minutes_gain, row.school_id))
    elif priority is Priority.HOMETOWN:
        result.sort(key=lambda row: (row.hometown_distance_km, row.school_id))
    else:
        result.sort(
            key=lambda row: (row.team_rank is None, row.team_rank or 0, row.school_id)
        )
    return tuple(result)


NATIVE_MOTIVATIONS = (
    "feeling_wanted",
    "hometown_proximity",
    "coaching",
    "big_program",
    "playing_time",
)
# CH initializer 0x75B6C0 emits lexicographic permutations, first column 0..3.
# It does not emit the 24 permutations beginning with rank 4.
_NATIVE_PROFILES = tuple(row for row in permutations(range(5)) if row[0] != 4)
_NATIVE_WEIGHTS = tuple(
    unpack(">f", pack(">f", value))[0] for value in (1, 0.8, 0.6, 0.4, 0.2)
)


def native_preference_profile(index: int) -> dict[str, tuple[int, float]]:
    """Inspect CH's established 96 native profiles, without writing a recruit.

    Return motivation -> (rank, native float32 weight), with rank zero strongest.
    Native big-program preference is not equated to current team poll ranking.
    Source is the seven-bit recruit +0x40 >>7 field, not a direct motivation enum.
    """
    if type(index) is not int or not 0 <= index < len(_NATIVE_PROFILES):
        raise ValueError(
            "native preference index is outside the 96 initialized profiles"
        )
    return {
        name: (rank, _NATIVE_WEIGHTS[rank])
        for name, rank in zip(NATIVE_MOTIVATIONS, _NATIVE_PROFILES[index], strict=True)
    }
