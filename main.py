#!/usr/bin/env python3
"""Package entrypoint for the mirror CLI."""

from cli import main as cli_main


if __name__ == "__main__":
    raise SystemExit(cli_main())
