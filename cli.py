#!/usr/bin/env python3
"""Command-line interface for mirror operations."""

from __future__ import annotations

import argparse
from typing import Sequence

import mirror_sync
import update_pat


class CLIApplication:
    """Dispatch subcommands for mirror sync and PAT rotation."""

    def __init__(self) -> None:
        self.parser = self._build_parser()

    def _build_parser(self) -> argparse.ArgumentParser:
        parser = argparse.ArgumentParser(
            prog="mirror-sync",
            description="Sync GitHub org repos to Gitea mirrors and manage mirror PAT.",
        )
        subparsers = parser.add_subparsers(dest="command")

        sync_parser = subparsers.add_parser("sync", help="Sync missing repos from GitHub to Gitea")
        sync_parser.set_defaults(handler=self._handle_sync)

        update_parser = subparsers.add_parser(
            "update-pat",
            help="Rotate GitHub PAT for mirrored repos",
        )
        update_parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Preview repos that would be updated without making changes",
        )
        update_parser.set_defaults(handler=self._handle_update_pat)

        # Backward-compatible default: no subcommand behaves like "sync".
        parser.set_defaults(handler=self._handle_sync)

        return parser

    def _handle_sync(self, _args: argparse.Namespace) -> int:
        mirror_sync.main()
        return 0

    def _handle_update_pat(self, args: argparse.Namespace) -> int:
        update_pat.main(dry_run=args.dry_run)
        return 0

    def run(self, argv: Sequence[str] | None = None) -> int:
        args = self.parser.parse_args(argv)
        return int(args.handler(args))


def main(argv: Sequence[str] | None = None) -> int:
    app = CLIApplication()
    return app.run(argv)
