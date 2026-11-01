"""Confirmed canonical 21-bone CH2K8/NBA11 binding compatibility.

The native parent/rest tables and default channel routes are equal. Retargeting
for this specific rig is identity in bone space, plus packed quaternion selector
translation. This does not describe arbitrary skins or other skeleton families.
"""

from __future__ import annotations

import math
import struct

from .embedded_motion import NativeELF
from .motion_frames import transcode_frames

BONES = (
    "root",
    "r_hip",
    "r_femur",
    "r_knee",
    "r_ankle",
    "l_hip",
    "l_femur",
    "l_knee",
    "l_ankle",
    "thorax",
    "l_clavicle",
    "l_shoulder",
    "l_humerus",
    "l_elbow",
    "l_hand",
    "head",
    "r_clavicle",
    "r_shoulder",
    "r_humerus",
    "r_elbow",
    "r_hand",
)
RIGS = {
    "college-hoops-2k8": dict(parents=0x1000A0C0, rest=0x10009F70, routing=0x10000100),
    "nba-2k11": dict(parents=0xA1CBB8, rest=0xA1CC10, routing=0x9D8D88),
}
PARENTS = (0, 0, 1, 2, 3, 0, 5, 6, 7, 0, 9, 10, 11, 12, 13, 9, 9, 16, 17, 18, 19)


def read_canonical_rig(raw, profile):
    if profile not in RIGS:
        raise ValueError("Canonical motion bind profile is not established")
    elf = NativeELF(raw)
    layout = RIGS[profile]
    parent_bytes = elf.read(layout["parents"], 21 * 4)
    rest_bytes = elf.read(layout["rest"], 21 * 16)
    route_bytes = elf.read(layout["routing"], 21 * 3)
    parents = struct.unpack(">21I", parent_bytes)
    rest = list(struct.iter_unpack(">4f", rest_bytes))
    if parents[0] != 0 or any(not 0 <= p < i for i, p in enumerate(parents[1:], 1)):
        raise ValueError("Canonical rig hierarchy is not the established ordered tree")
    if parents != PARENTS:
        raise ValueError("Canonical rig parent assignments changed")
    if any(
        not all(math.isfinite(v) and abs(v) < 10000 for v in row) or row[3] != 0
        for row in rest
    ):
        raise ValueError("Canonical rest translations are invalid")
    if route_bytes != bytes(v for i in range(21) for v in (0, i, i)):
        raise ValueError("Canonical default channel routing changed")
    return dict(
        profile=profile,
        parents=parents,
        parent_bytes=parent_bytes,
        rest_bytes=rest_bytes,
        route_bytes=route_bytes,
    )


def verify_canonical_bind(donor, target):
    source = read_canonical_rig(donor, "nba-2k11")
    destination = read_canonical_rig(target, "college-hoops-2k8")
    for field in ("parent_bytes", "rest_bytes", "route_bytes"):
        if source[field] != destination[field]:
            raise ValueError(
                "Canonical rigs differ in " + field + "; identity retarget blocked"
            )
    return dict(
        mode="canonical-21-identity",
        bind_equivalent=True,
        bone_count=21,
        parent_table_equal=True,
        rest_translations_equal=True,
        channel_routing_equal=True,
        bone_map=list(range(21)),
        bones=list(BONES),
        gameplay_ready=False,
        scope="observed-canonical-motion-rig-only",
    )


def canonical_channels(header, profile):
    """Return declared source bone/channel identities; no missing track invention."""
    if profile not in RIGS or len(header) < (
        64 if profile == "college-hoops-2k8" else 56
    ):
        raise ValueError("Canonical motion header is truncated or unsupported")
    flags = struct.unpack_from(">I", header, 0x10)[0]
    rotations, translations, bones = (
        (flags >> 12) & 63,
        (flags >> 6) & 63,
        (flags >> 18) & 63,
    )
    rotation_at = 4 if profile == "college-hoops-2k8" else 8
    rmask = struct.unpack_from(">I", header, rotation_at)[0]
    tmask = struct.unpack_from(">I", header, 12)[0]
    if bones != 21 or rmask != 0x1DF7DD or tmask >> 21:
        raise ValueError("Motion does not use the confirmed canonical 21-bone family")
    if rotations != rmask.bit_count() or translations != tmask.bit_count():
        raise ValueError("Motion channel counts disagree with bone masks")
    if profile == "college-hoops-2k8" and any(
        struct.unpack_from(">I", header, at)[0] for at in (0, 8)
    ):
        raise ValueError("CH extended rotation/translation mask is not established")
    return dict(
        rotations=rotations,
        translations=translations,
        declared_bones=bones,
        rotation_mask=rmask,
        translation_mask=tmask,
        rotation_bones=[i for i in range(21) if rmask >> i & 1],
        translation_bones=[i for i in range(21) if tmask >> i & 1],
    )


def retarget_canonical_frames(raw, header, frames, donor, target):
    proof = verify_canonical_bind(donor, target)
    channels = canonical_channels(header, "nba-2k11")
    if struct.unpack_from(">I", header, 0x14)[0] & 0x8000:
        raise ValueError("NBA11 unpacked pose mode needs its separate native decoder")
    output = transcode_frames(
        raw,
        channels["rotations"],
        channels["translations"],
        frames,
        "nba-2k11",
        "college-hoops-2k8",
    )
    return output, dict(
        **proof,
        **channels,
        frames=frames,
        missing_translations="retain-native-absent-channel-behavior",
        packed_selector_translated=True,
    )
