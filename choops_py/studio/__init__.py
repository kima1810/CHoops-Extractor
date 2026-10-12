"""Native CHoops desktop application."""


def main(argv=None):
    from .app import main as run

    return run(argv)
