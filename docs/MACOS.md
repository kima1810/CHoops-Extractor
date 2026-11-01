# macOS installation

Choose **macos-arm64** for Apple Silicon (M1 or newer), or **macos-x86_64** for
Intel. Requires macOS 13 or newer. Each ZIP contains a native `CHoops-Studio.app`,
documentation and the audio helpers' corresponding LGPL sources/notices.

1. Extract the complete ZIP using Archive Utility.
2. Move `CHoops-Studio.app` into Applications.
3. Open it. This release uses an ad-hoc signature and is not Apple-notarized.
   If Gatekeeper blocks this trusted download, use System Settings → Privacy &
   Security → Open Anyway after attempting to open it. Do not disable Gatekeeper.
4. Select your source JB and overrides through Explorer as on Windows. Game files
   are not included. Keep the source game separate from output/build destinations.

Caches, temporary conversions and reports are stored under
`~/Library/Application Support/CHoops Studio/output`, outside the app bundle.
Qt preferences remain in the normal macOS user preferences location.
Build destinations can still be selected manually. Use a writable local disk;
leave originals immutable. Retain the ZIP's source/license directory with the
distributed package. No Python installation or external DDS converter is required.

The CLI can be launched with:

```sh
/Applications/CHoops-Studio.app/Contents/MacOS/CHoops-Studio --cli --help
```

Native package checks cover Qt startup, CLI imports, synthetic audio conversion
and OpenGL rendering. These do not certify gameplay or every real asset. Existing
format restrictions (including NBA 2K14 SDAT writing) still apply. Use the matching
architecture package; the release does not require Rosetta. Linux remains a source
target. Apple Developer ID signing/notarization is not configured.
