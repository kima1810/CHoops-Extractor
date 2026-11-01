# Arena shader colour and alpha routing

The stadium SCNE contains embedded Cg programs; it is unnecessary to modify EBOOT
or load a complete game to inspect these shader families. The sampled source
programs establish these operations (RGBA multiplication, not guessed school
colours):

| SCNE shader hash | Embedded fragment program | Static preview |
|---|---|---|
| 0x9BF5D4AE | BasePrelitPixelShader | Diffuse × vertex RGBA |
| 0x9BF5D4AE | BaseLightmapPixelShader | Diffuse × vertex RGBA × lightmap RGBA |
| 0xAD91D4DE | GlowSignsPixelShader | RGB = diffuse RGB × vertex RGB × (1 + diffuse alpha); alpha = vertex alpha |
| 0xB3DC3294 | LightFlarePixelShader | RGB = diffuse RGB × vertex RGB; alpha = diffuse alpha |

Float4 COLOR declarations (usage 3) are preserved including HDR values. The
second signed-normalized TEXCOORD channel (usage 9) supplies lightmap coordinates;
base UVs are not reused when the second declaration is present. For the verified
prelit family, sampler 0xAB0D0064 is a lightmap, **not a normal map**. Other shader
families do not acquire that role merely by having the same sampler hash.
Material CPU offsets still select DiffuseColor; confirmed court palette uniforms
continue to follow loaded roster/selected school state. Prelit materials do not
receive a second artificial directional-light multiplier.

Source/selected overrides supply SCNE and all sampled texture records through the
same snapshot. Single archives remain usable. Tests verify declared attribute
bounds and actual rendered lightmap/colour/alpha pixels. Hidden read-only S256
inspection rendered 119 supported parts and 180 lightmapped batches without
shader errors. No RPCS3 or testing JB was involved.

This is static preview support. Reflection/environment lighting, full fake-bump
lighting, screen-space AO, dynamic arena illumination, cloth and every runtime
palette mode are not reproduced. Palette slots 24–26 must not be assigned to
seating from colour similarity: Edit Schools also includes cheerleader colours.
Unproved channel-to-roster links remain unassigned. Complete GPU/game shader
emulation and full roster reverse engineering are not claimed.

## Floor alignment guides

The optional 3-point and out-of-bounds guides are for positioning one-texture
court artwork only. They copy the verified line draw coordinates from the fixed
stock S256 floor, raised by 1 game unit. Guide depth bias is ordered above the existing coplanar floor passes.
The guide shader is flat amber and
independent of roster palettes, floor layout, texture overrides and lighting.
The floor itself keeps every original draw and its confirmed material/palette
behavior. Toggling guides never removes actual court markings. No bounds-based
apron geometry is invented; without the stock reference guides are unavailable.
These controls change no SCNE, roster or build data and retain the camera.

Reference guide width uses the central 10% of the authored strip UV: U across both 3-point and boundary strips. This thins guides without moving their centerlines or modifying floor geometry.

The separate key/center-circle toggle adds authored S256 routes 20 (Key Line),
2 (Key Circle Outer) and 10 (Center Circle). Filled paint route 19 is excluded.
Curved strips use V as their cross-line UV axis; straight key strips use U. The
central 10% clipping and +1-unit height match the existing guide treatment. This
changes reference overlays only and does not simulate a new runtime floor shader.
