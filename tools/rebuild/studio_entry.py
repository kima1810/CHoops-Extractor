"""Standalone entrypoint; spawn workers dispatch before any GUI imports."""
import multiprocessing
import sys


def run():
    if sys.argv[1:2]==['--render-smoke']:
        from choops_py.studio.render_smoke import main as render_smoke
        return render_smoke()
    if sys.argv[1:2]==['--audio-codec-smoke']:
        from choops_py.audio_tools.codec_smoke import main as audio_codec_smoke
        return audio_codec_smoke()
    if sys.argv[1:2]==['--cli']:
        from choops_py.cli import main as cli_main
        return cli_main(sys.argv[2:])
    from choops_py.studio import main
    return main()


if __name__=='__main__':
    multiprocessing.freeze_support()
    raise SystemExit(run())
