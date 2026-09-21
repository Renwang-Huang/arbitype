"""Run the canonical :mod:`arbitype` CLI through the legacy module path."""

from arbitype.cli import main


if __name__ == "__main__":
    raise SystemExit(main())
