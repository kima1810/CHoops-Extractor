# PR #30 compatibility review

Reviewed merged master `fd9eae5d43f0dec436411661dcf99c52f326e562`
(PR head `0254006`) against v1.16, v1.17, v1.18 and v1.19.
All four release tags remain ancestors of the merge. The merge adds changes to
three archive modules and five documentation files; it does not replace the
v1.19 codebase with an older branch. No dependency, workflow or packaging change.

## Retained behavior and evidence

| Area | Preservation checks |
| --- | --- |
| Overrides and caching | Existing nested/manifest imports, parallel preparation, cache invalidation and source/override preview tests remain in the full suite. New named/numeric folder cases verify DDS wins over raw TXTR, including the spelling alias. |
| Growing assets and audio | Append/repack, streaming verification, opaque header gaps, queued song imports and manually chosen destinations remain covered. New raw BIN cases verify exact payload length/content, zero storage padding, immutable source and rejection of new BIN additions. |
| NBA support | Existing 2K9 research/schema, 2K14 SDAT authentication, extended formats, ZLIB, NBA roster and split-header tests remain covered. Authenticated 2K14 building stays blocked. |
| Roster and previews | Existing side panels, appearance, ratings/bulk/CSV/comparison, source selection, jersey preview and court-guide tests remain covered. No editor or renderer code changed in PR #30. |
| v1.19 compatibility fixes | Existing manifest/CDF cubemap face-preservation and named-container diagnostic regressions remain covered. |

## Added input compatibility

- A direct numeric child of the selected override root resolves through that
  source archive's TOC index. Complete IFF files and nested artwork can use it.
  Numeric indices depend on the matching source TOC; they are not portable
  identities across different games or reordered archives. Named/hash folders
  remain preferable when sharing overrides.
- Legacy `icon_tatoo` record folders resolve to `icon_tattoo`.
- Existing raw `.bin` entries can be replaced without passing through an IFF
  parser, including relocation. This does not enable arbitrary new BIN assets.

Nine new synthetic regression cases exercise these contracts. The original merge
passed isolated portable verification: **602 passed, 10 skipped, 2 deselected**.
Skips include offscreen OpenGL and the absent optional native texture converter;
they are not rendering/runtime passes. Final follow-up verification is recorded
in TEST_REPORT.md and the follow-up PR.

No regression was found in the reviewed changes. This is source/structural
verification, not gameplay certification. No RPCS3, EBOOT writes or real/testing
JB copies. Synthetic archive outputs contain generated test bytes only.
Open PR #31 (Legacy saves) and PR #32 (scorebug editing) are separate work and
are not included in this review or silently merged.
