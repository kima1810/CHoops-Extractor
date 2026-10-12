"""Standalone entrypoint includes the same public CLI as the source package."""
import sys
if sys.argv[1:2]==['--audio-codec-smoke']:
    from choops_py.audio_tools.codec_smoke import main as audio_codec_smoke
    raise SystemExit(audio_codec_smoke())
from choops_py.studio import main
from choops_py.cli import main as cli_main
if sys.argv[1:2]==['--cli']:
    raise SystemExit(cli_main(sys.argv[2:]))
raise SystemExit(main())
