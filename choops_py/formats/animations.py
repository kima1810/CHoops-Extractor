"""Lossless motion-record discovery; no speculative skeletal track decoder."""
from .standard_iff import StandardIFF
from .standard_iff_writer import record_blocks

MOCAP_TYPE = 0x60900D71


def inspect_animations(raw):
    iff = StandardIFF(raw)
    records = []
    for record in iff.records:
        if record['type_hash'] != MOCAP_TYPE:
            continue
        if record['type'] != 'SingleMoCap':
            raise ValueError('Motion record hash and embedded type name disagree')
        blocks = record_blocks(iff, record)
        records.append({'index': record['index'], 'name': record['name'],
                        'type': 'SingleMoCap', 'blocks': [
                            {'index': block[0], 'decoded_bytes': len(block[3])} for block in blocks]})
    return {'mode': 'read-only', 'records': records,
            'skeletal_tracks_decoded': False,
            'note': 'Raw decoded record blocks are extractable. Bone identities, packed tracks and timing remain under research.'}
