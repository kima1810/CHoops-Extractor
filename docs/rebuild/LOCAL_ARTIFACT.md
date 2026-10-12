# Development artifact

The Windows development artifact is built with `tools/rebuild/package_windows.ps1` into `dist/CHoops-Studio/`. Packaging smoke tests launch an actual Qt window. The standalone entry point also supports `--cli --help`.

Before delivery, extract the ZIP to a clean directory containing spaces and run CLI, GUI and authorized read-only input checks. Record build-specific sizes and checksums with the generated artifact rather than embedding machine-specific build records in documentation.

Game assets and converter binaries are excluded from the development ZIP. Converter redistribution and complete binary notices remain acceptance gates. A development artifact is not a published `v1.0beta` release.
