"""Contract-gated NBA11 to CH owned-motion component translation.

Missing authoring/flag semantics require explicit per-header research assertions.
No default values, unrelated CH template or executable/bank installation is used.
"""

import hashlib
import math
import struct

from ..formats.embedded_motion import NativeELF
from ..formats.motion_bind import canonical_channels, verify_canonical_bind
from ..formats.motion_events import inspect_events, transcode_events
from ..formats.motion_frames import (
    layout,
    nba11_key_ticks,
    resample_nba11_frames,
    resample_nba11_root,
)
from .target_motion import MAX_IMAGE, relocate_target_image


def _contract(header, address, contract):
    if not isinstance(contract, dict) or contract.get("schema") != 1:
        raise ValueError("Donor header requires a schema-1 metadata contract")
    if (
        contract.get("source_header_address") != address
        or contract.get("source_header_sha256") != hashlib.sha256(header).hexdigest()
    ):
        raise ValueError("Metadata contract is not bound to this donor header")
    high, state = contract.get("target_mode_high16"), contract.get("target_state_bits")
    if (
        type(high) is not int
        or not 0 <= high <= 0xFFFF
        or type(state) is not int
        or not 0 <= state <= 0xFFFFFFFF
    ):
        raise ValueError("Explicit target mode/state words are required")
    source_mode = struct.unpack_from(">I", header, 20)[0]
    # Native cyclic-phase, mirror and root-stride fields have corresponding positions.
    if (high ^ (source_mode >> 16)) & 0xD000:
        raise ValueError(
            "Contract changes confirmed cyclic-phase/mirror/root-stride fields"
        )
    velocity = contract.get("authored_planar")
    if (
        not isinstance(velocity, (list, tuple))
        or len(velocity) != 3
        or any(
            type(x) not in (float, int)
            or abs(x) > 3.4028234663852886e38
            or not math.isfinite(x)
            for x in velocity
        )
        or velocity[0] < 0
    ):
        raise ValueError("Explicit finite authored planar speed/X/Z are required")
    try:
        encoded = struct.pack(">3f", *velocity)
    except (OverflowError, struct.error) as error:
        raise ValueError("Planar metadata exceeds float32") from error
    evidence = contract.get("evidence")
    if not isinstance(evidence, dict) or any(
        not isinstance(evidence.get(k), str)
        or not evidence[k].strip()
        or len(evidence[k]) > 2048
        for k in ("mode", "state", "planar")
    ):
        raise ValueError(
            "Each unresolved metadata group needs bounded research evidence"
        )
    return high, state, encoded


def translate_donor_motion(
    donor, target, address, metadata_contract, event_contract, *, budget=MAX_IMAGE
):
    """Return a relative CH component, never an installable bank or EBOOT.

    The explicit contract is a caller research assertion, not automatically proven
    by the serializer. Unknown auxiliary/reference layouts remain rejected.
    """
    if type(budget) is not int or not 64 <= budget <= MAX_IMAGE:
        raise ValueError("Donor component budget must be 64 bytes..16 MiB")
    if type(address) is not int or address < 0 or address % 4:
        raise ValueError("Donor header must be aligned")
    bind = verify_canonical_bind(donor, target)
    elf = NativeELF(donor)
    source = elf.read(address, 56)
    channels = canonical_channels(source, "nba-2k11")
    flags, mode = struct.unpack_from(">2I", source, 16)
    if mode & 0x8000:
        raise ValueError("Unpacked donor pose translation is not established")
    if not isinstance(metadata_contract, dict):
        raise ValueError("Explicit donor metadata contract required")
    if (
        metadata_contract.get("source_sha256") != hashlib.sha256(donor).hexdigest()
        or metadata_contract.get("target_sha256") != hashlib.sha256(target).hexdigest()
    ):
        raise ValueError(
            "Metadata contract source/target executable fingerprint changed"
        )
    high, state, planar = _contract(source, address, metadata_contract)
    keys, rate = mode & 0x7FFF, flags >> 24
    scale, duration = struct.unpack_from(">2f", source, 28)
    if (
        not keys
        or not rate
        or not math.isfinite(scale)
        or scale <= 0
        or not math.isfinite(duration)
        or duration < 0
    ):
        raise ValueError("Invalid donor timing metadata")
    timing, poses, root, events, auxiliary = struct.unpack_from(">5I", source, 36)
    if struct.unpack_from(">I", source, 4)[0] or flags & 63 or auxiliary:
        raise ValueError(
            "Donor auxiliary/reference dependencies need established extents"
        )
    if not all((timing, poses, root, events)):
        raise ValueError("Resolved donor timing/pose/root/event tracks are required")
    deltas = elf.read(timing, keys)
    ticks = nba11_key_ticks(deltas)
    frames = ticks[-1] + 1
    if keys > 1 and not math.isclose(
        ticks[-1], duration * rate * scale, rel_tol=2e-6, abs_tol=0.002
    ):
        raise ValueError("Donor duration and authored ticks disagree")
    _, source_size = layout(channels["rotations"], channels["translations"], keys)
    _, target_size = layout(channels["rotations"], channels["translations"], frames)
    root_stride = 6 if mode & 0x80000000 else 8
    # Reject growth before allocating expanded tracks; include alignment overhead.
    root_at = (64 + target_size + 15) & ~15
    event_at = (root_at + frames * root_stride + 15) & ~15
    if event_at + 4 > budget:
        raise ValueError("Expanded donor component exceeds byte budget")
    event_bytes, event_report = transcode_events(
        inspect_events(donor, "nba-2k11", events, native=True), event_contract
    )
    if event_at + len(event_bytes) > budget:
        raise ValueError("Expanded donor events exceed byte budget")
    packed, resampling = resample_nba11_frames(
        elf.read(poses, source_size),
        deltas,
        channels["rotations"],
        channels["translations"],
    )
    roots = resample_nba11_root(
        elf.read(root, keys * root_stride), deltas, has_heading=root_stride == 8
    )
    if len(packed) != target_size or len(roots) != frames * root_stride:
        raise ValueError("Converted tracks disagree with target header extents")
    header = bytearray(64)
    struct.pack_into(
        ">4I", header, 0, 0, channels["rotation_mask"], 0, channels["translation_mask"]
    )
    struct.pack_into(">3I", header, 16, flags, high << 16 | frames, state)
    header[28:36] = source[28:36]
    header[36:48] = planar
    output = bytearray(header)
    extents = []
    for field, role, data in (
        (0x30, "poses", packed),
        (0x34, "root", roots),
        (0x38, "events", event_bytes),
    ):
        at = (len(output) + 15) & ~15
        if at + len(data) > budget:
            raise ValueError("Aligned donor component exceeds byte budget")
        output.extend(bytes(at - len(output)))
        output.extend(data)
        struct.pack_into(">i", output, field, at - field + 1)
        extents.append(dict(role=role, offset=at, bytes=len(data)))
    # Exercise both transitions plus the complete target extent validator.
    native = relocate_target_image(output, [0], 0x20000000, source_state="relative")
    if relocate_target_image(native, [0], 0x20000000, source_state="native") != output:
        raise ValueError("Donor target relocation roundtrip failed")
    return bytes(output), dict(
        schema=1,
        pointer_state="relative",
        header_offsets=[0],
        bytes=len(output),
        extents=extents,
        source_header_address=address,
        source_header_sha256=hashlib.sha256(source).hexdigest(),
        source_identifier=struct.unpack_from(">I", source)[0],
        metadata_provenance="explicit-per-header-caller-research-assertions",
        metadata_automatically_established=False,
        metadata_assertions=dict(
            target_mode_high16=high,
            target_state_bits=state,
            authored_planar_float32=list(struct.unpack(">3f", planar)),
            evidence={
                k: metadata_contract["evidence"][k] for k in ("mode", "state", "planar")
            },
        ),
        target_frame_count=frames,
        source_key_count=keys,
        original_rate_time_scale_duration_retained=True,
        channels=channels,
        bind=bind,
        events=event_report,
        resampling=resampling,
        native_loader_installed=False,
        gameplay_ready=False,
    )
