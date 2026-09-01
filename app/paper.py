"""
Paper Portfolio Simulation CLI for Solana Meme Research Lab.
Displays portfolio stats, open/closed positions, fees, and net ROI.
"""

from __future__ import annotations

from database.db import Database
from simulation.portfolio import PaperPortfolio


def main():
    db = Database()
    portfolio = PaperPortfolio(db=db)
    summary = portfolio.get_summary()

    print("\n" + "=" * 80)
    print("SOLANA MEME RESEARCH LAB — PAPER SIMULATION PORTFOLIO")
    print("=" * 80)
    print(f"Starting Capital:     ${summary['starting_capital_usd']:.2f}")
    print(f"Available Cash:       ${summary['available_cash_usd']:.2f}")
    print(f"Position Slot Size:   $2.00 (Fixed research size)")
    print(f"Max Capacity:         50 simultaneous positions")
    print(f"Open Positions:       {summary['open_positions_count']}")
    print(f"Closed Positions:     {summary['closed_positions_count']}")
    print(f"Closed Net P&L:       ${summary['total_closed_net_pnl_usd']:.4f}")
    print(f"Win Rate:             {summary['win_rate_pct']:.1f}% ({summary['wins_count']}W / {summary['losses_count']}L)")
    print("=" * 80)

    if portfolio.open_positions:
        print("\n[+] ACTIVE VIRTUAL POSITIONS ($2 Fixed Slot):")
        fmt = "{:<8} | {:<12} | {:<12} | {:<14} | {:<10} | {:<10}"
        print(fmt.format("SYMBOL", "ENTRY PRICE", "PEAK PRICE", "TRAIL STOP (-25%)", "SLIPPAGE", "IMPACT"))
        print("-" * 76)
        for pos in portfolio.open_positions.values():
            print(fmt.format(
                pos.symbol[:8],
                f"${pos.entry_price_usd:.6f}",
                f"${pos.highest_price_usd:.6f}",
                f"${pos.stop_loss_price_usd:.6f}",
                f"{pos.estimated_slippage_pct:.1f}%",
                f"{pos.estimated_price_impact_pct:.2f}%",
            ))
        print("-" * 76 + "\n")


if __name__ == "__main__":
    main()
