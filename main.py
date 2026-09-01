"""
Solana Meme Research Lab — Unified Command Line Interface & Paper Runner.
Supports:
  --scan       Run discovery, scoring, and market scan
  --paper      Run autonomous live paper trading engine ($100 bankroll, $2 slots)
  --status     Display portfolio status, cash, equity, win rate
  --positions  Display active virtual positions
  --report     Display ML and Paper performance reports
  --health     Run provider health checks
"""

from __future__ import annotations

import argparse
import os
import sys
import time
from datetime import datetime, timezone

from app.healthcheck import print_table as print_health_table, run_healthcheck
from app.scan import print_scan_table, run_pipeline
from runner.paper_runner import AutonomousPaperRunner


def print_banner() -> None:
    print("=" * 80)
    print("  SOLANA MEME RESEARCH LAB — AUTONOMOUS PAPER RESEARCH & SIMULATION")
    print("  NO REAL SWAPS | NO REAL MONEY | NO WALLET SIGNING | ZERO LOOKAHEAD")
    print("=" * 80 + "\n")


def cmd_status(runner: AutonomousPaperRunner) -> None:
    print_banner()
    if os.path.exists(runner.portfolio_txt_path):
        with open(runner.portfolio_txt_path, "r", encoding="utf-8") as fp:
            print(fp.read())
    else:
        runner.write_all_outputs()
        with open(runner.portfolio_txt_path, "r", encoding="utf-8") as fp:
            print(fp.read())


def cmd_positions(runner: AutonomousPaperRunner) -> None:
    print_banner()
    if os.path.exists(runner.positions_txt_path):
        with open(runner.positions_txt_path, "r", encoding="utf-8") as fp:
            print(fp.read())


def cmd_report() -> None:
    print_banner()
    report_path = "ML_RESEARCH_REPORT.md"
    if os.path.exists(report_path):
        with open(report_path, "r", encoding="utf-8") as fp:
            print(fp.read())
    else:
        print("[!] ML_RESEARCH_REPORT.md not found. Run ML benchmark first via `python -m ml.train`.")


def cmd_paper(runner: AutonomousPaperRunner, cycles: int = 1, interval_sec: float = 10.0) -> None:
    print_banner()
    print(f"[*] Starting Autonomous Paper Runner ({cycles} cycles, interval={interval_sec}s)...")
    print(f"    - Initial Capital:   $100.00")
    print(f"    - Available Cash:    ${runner.portfolio.available_cash_usd:.2f}")
    print(f"    - Active Positions:  {len(runner.portfolio.open_positions)} / 50")
    print(f"    - Position Slot:     $2.00 Fixed")
    print(f"    - Strategy Exits:    Trailing Stop (-25% from peak), Emergency Liq (<$1000)\n")

    for c in range(1, cycles + 1):
        print(f"--- [CYCLE {c} / {cycles}] {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')} ---")
        # 1. Discovery & Scoring
        results = runner.run_discovery_and_eval(limit=10)
        candidates = [r for r in results if r["status"] == "PAPER_BUY"]
        print(f"    Evaluated: {len(results)} tokens | New Buys: {len(candidates)}")

        # 2. Monitor Active Positions
        closed = runner.monitor_and_update_positions()
        if closed:
            print(f"    [!] Closed {len(closed)} position(s): {[p.symbol for p in closed]}")

        cmd_status(runner)

        if c < cycles:
            print(f"[*] Sleeping for {interval_sec}s...")
            time.sleep(interval_sec)

    print("\n[+] Paper Runner cycle completed. All results saved to runtime/results/.")


def main() -> None:
    import os
    parser = argparse.ArgumentParser(
        description="Solana Meme Research Lab CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--scan", action="store_true", help="Run token discovery and analysis scan")
    parser.add_argument("--paper", action="store_true", help="Run autonomous paper trading simulation")
    parser.add_argument("--daemon", action="store_true", help="Run continuous autonomous background daemon with hourly reports")
    parser.add_argument("--status", action="store_true", help="Show current paper portfolio status")
    parser.add_argument("--positions", action="store_true", help="Show active open virtual positions")
    parser.add_argument("--report", action="store_true", help="Show ML research benchmark report")
    parser.add_argument("--health", action="store_true", help="Run provider health checks")
    parser.add_argument("--limit", type=int, default=10, help="Candidate discovery limit (default: 10)")
    parser.add_argument("--cycles", type=int, default=1, help="Number of paper execution cycles (default: 1)")
    parser.add_argument("--interval", type=float, default=10.0, help="Polling interval in seconds (default: 10)")
    parser.add_argument("--report-interval", type=float, default=60.0, help="Hourly report interval in minutes (default: 60)")

    args = parser.parse_args()
    runner = AutonomousPaperRunner()

    if args.health:
        print_banner()
        results = run_healthcheck()
        print_health_table(results)
    elif args.scan:
        print_banner()
        data = run_pipeline(limit=args.limit)
        print_scan_table(data)
    elif args.status:
        cmd_status(runner)
    elif args.positions:
        cmd_positions(runner)
    elif args.report:
        cmd_report()
    elif args.paper:
        cmd_paper(runner, cycles=args.cycles, interval_sec=args.interval)
    elif args.daemon:
        print_banner()
        runner.run_daemon(
            interval_sec=args.interval,
            report_interval_min=args.report_interval,
            limit=args.limit,
        )
    else:
        # Default fallback to status + help
        print_banner()
        parser.print_help()


if __name__ == "__main__":
    main()
