"""
Unified CLI Entrypoint for Solana Meme Research Lab.
"""

from __future__ import annotations

import argparse
import sys

from app.discovery import main as run_discovery
from app.healthcheck import print_table, run_healthcheck
from app.paper import main as run_paper
from app.scan import print_scan_table, run_pipeline


def main():
    parser = argparse.ArgumentParser(
        prog="solana-meme-research-lab",
        description="Solana Meme Research Lab — Analytics, Feature Store, and Paper Trading Simulator",
    )
    subparsers = parser.add_subparsers(dest="command", help="Available subcommands")

    # healthcheck command
    subparsers.add_parser("healthcheck", help="Run provider capability and connectivity check")

    # discovery command
    subparsers.add_parser("discovery", help="Discover newly active Solana meme tokens")

    # scan command
    scan_parser = subparsers.add_parser("scan", help="Run complete scan and analysis pipeline")
    scan_parser.add_argument("--limit", type=int, default=10, help="Number of candidate tokens to scan")

    # paper command
    subparsers.add_parser("paper", help="View paper simulation portfolio status")

    args = parser.parse_args()

    if args.command == "healthcheck":
        results = run_healthcheck()
        print_table(results)
    elif args.command == "discovery":
        run_discovery()
    elif args.command == "scan":
        results = run_pipeline(limit=args.limit)
        print_scan_table(results)
    elif args.command == "paper":
        run_paper()
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
