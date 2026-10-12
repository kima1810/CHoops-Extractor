"""Verified court material-to-roster bindings; preview-only color uniforms."""
# Runtime court initializer matches material IDs to team RGBA getter callbacks.
COURT_PALETTE_ROUTES = {1723127071: 2, 2136856199: 11, 2310823066: 18, 1460891455: 20, 4239636421: 3, 2218775043: 4, 1472182641: 9, 3117775956: 10, 2324736937: 19, 2264534394: 12, 536042688: 13, 308774085: 7, 2339296639: 8, 2792207522: 5, 581636477: 6, 2745515914: 5, 984378928: 6, 265342201: 14, 1889944695: 14, 2600458314: 18, 1961998694: 20, 3935644869: 11, 2643598419: 2}


def palette_tint(material_hash, colors):
    slot = COURT_PALETTE_ROUTES.get(material_hash)
    if slot is None or colors is None:
        return None
    value = colors[slot].removeprefix('#')
    rgba = bytes.fromhex(value)
    if len(rgba) != 4:
        raise ValueError('Palette colors require four RGBA bytes')
    # The runtime skips the custom court color when all RGB bytes are 0xBE.
    if rgba[:3] == b'\xbe\xbe\xbe':
        return None
    def linear(channel):
        c = channel/255.
        return c/12.92 if c <= .04045 else ((c+.055)/1.055)**2.4
    return tuple(linear(c) for c in rgba[:3]) + (rgba[3]/255.,)


def associate_palette(meshes, colors):
    """Return new batches so edits and roster changes cannot leave stale tints."""
    return [{**mesh, 'batches': [{**batch, 'palette_tint':
        palette_tint(batch.get('material_hash'), colors) if batch.get('supports_diffuse_color') else None} for batch in mesh.get('batches', [{'first':0, 'count':len(mesh.get('vertices', [])), 'texture':None}])]}
        for mesh in meshes]
