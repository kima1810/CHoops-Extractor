# Historical implementation summary

Historical development introduced the Python archive, container and modding services:

- Split archive indexing, CRC32 name resolution and raw extraction.
- Bounds-checked standard IFF, CDF, H7A, texture and tool-wrapper readers.
- Conservative container writers that preserve unrelated data and reject unsafe growth or aliases.
- Shared DDS/GTF conversion, generated converter tests and unsupported-layout reporting.
- Confirmed roster fields, wrapper preservation, reference validation and transactional edits.
- Separate JB builds with preflight, ownership checks and output validation.

The native rebuild adds Qt model/view browsing, supported image previews, safe roster forms, undo/redo, source-bound difference packages, folder staging, cancellation and exact untouched-byte checks. Current capabilities and remaining acceptance work are in [FEATURE_MATRIX.md](rebuild/FEATURE_MATRIX.md), [TEST_REPORT.md](TEST_REPORT.md) and [RISKS.md](rebuild/RISKS.md).

Historical observations are not proof for the current source revision. Reproduce checks with generated fixtures and legally supplied read-only inputs. Environment-specific paths, account-access details, session timestamps, machine configuration and fixture inventories are excluded from this summary.
