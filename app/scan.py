"""
Scan & Analysis Pipeline for Solana Meme Research Lab.
Performs end-to-end token discovery, on-chain holder distribution, multi-factor analysis, scoring, ledger logging, and paper trading.
Displays:
1. RAW UNWEIGHTED ON-CHAIN METRICS TABLE (top10, creator age, creator share, mutable, transfer fee, lp lock, cluster score)
2. 6-FACTOR WEIGHTED SCORES & STATUS TABLE
"""

from __future__ import annotations

import argparse
import sys
from typing import Any, Dict, List, Optional

from analyzers.liquidity import LiquidityAnalyzer
from analyzers.momentum import MomentumAnalyzer
from analyzers.security import SecurityAnalyzer
from analyzers.wallet import WalletAnalyzer
from collectors.dexscreener import DexScreenerAdapter
from collectors.helius import HeliusAdapter
from config.settings import settings
from core.models import TokenInfo, TokenStatus, TradeAction, utc_now
from database.db import Database
from discovery.service import TokenDiscoveryService
from features.store import FeatureStore
from ledger.decision_ledger import DecisionLedger
from quarantine.manager import QuarantineManager
from scoring.engine import ScoreEngine
from simulation.execution_simulator import ExecutionSimulator
from simulation.portfolio import PaperPortfolio


def run_pipeline(limit: int = 10) -> Dict[str, Any]:
    db = Database()
    dex_adapter = DexScreenerAdapter()
    helius_adapter = HeliusAdapter()

    quarantine_mgr = QuarantineManager(default_quarantine_minutes=3.0)
    discovery_service = TokenDiscoveryService(
        market_provider=dex_adapter,
        db=db,
        quarantine_manager=quarantine_mgr,
    )

    sec_analyzer = SecurityAnalyzer(onchain_provider=helius_adapter)
    liq_analyzer = LiquidityAnalyzer()
    mom_analyzer = MomentumAnalyzer()
    wal_analyzer = WalletAnalyzer()
    score_engine = ScoreEngine()
    feature_store = FeatureStore(db=db)
    decision_ledger = DecisionLedger(db=db)
    portfolio = PaperPortfolio(db=db)

    print(f"[*] Discovering top active Solana tokens from DexScreener (limit={limit})...")
    discovered_tokens = discovery_service.discover_and_register(limit=limit)

    results = []
    raw_metrics_list = []
    data_unavailable_stats = {
        "liquidity_unavailable": 0,
        "price_unavailable": 0,
        "top10_holders_unavailable": 0,
        "creator_age_unavailable": 0,
        "total_scanned": len(discovered_tokens),
    }

    for token in discovered_tokens:
        # 1. Fetch market snapshot
        snapshot = dex_adapter.get_token_snapshot(token.address)
        if not snapshot:
            continue

        if snapshot.liquidity_usd is None:
            data_unavailable_stats["liquidity_unavailable"] += 1
        if snapshot.price_usd is None:
            data_unavailable_stats["price_unavailable"] += 1

        # 2. Fetch on-chain raw metrics from Helius RPC
        authorities = helius_adapter.get_token_authorities(token.address)
        decimals = authorities.get("decimals", 6)
        raw_supply = float(authorities.get("supply") or 0.0)
        ui_supply = (raw_supply / (10 ** decimals)) if raw_supply > (10 ** decimals) else raw_supply

        holders_data = helius_adapter.get_top_holders(
            token.address,
            total_supply=raw_supply,
            decimals=decimals,
        )
        creator_data = helius_adapter.get_creator_info(token.address)

        top10_pct = holders_data.get("top10_percentage")
        single_max_pct = holders_data.get("single_holder_max_percentage")
        creator_age_days = creator_data.get("creator_wallet_age_days")
        creator_age_hours = (creator_age_days * 24.0) if creator_age_days is not None else None

        if top10_pct is None:
            data_unavailable_stats["top10_holders_unavailable"] += 1
        if creator_age_days is None:
            data_unavailable_stats["creator_age_unavailable"] += 1

        # Enrich snapshot with resolved on-chain distribution metrics
        snapshot.top10_holders_pct = top10_pct
        snapshot.creator_balance_pct = single_max_pct
        snapshot.holders_count = len(holders_data.get("top_holders", []))

        db.save_snapshot(snapshot)
        history = db.get_snapshots(token.address, limit=10)

        # 3. Run Analyzers with enriched metrics
        security = sec_analyzer.analyze(token.address, snapshot=snapshot, authorities_override=authorities)
        db.save_security_check(security)

        liquidity = liq_analyzer.analyze(token.address, current_snapshot=snapshot, historical_snapshots=history)
        momentum = mom_analyzer.analyze(
            token.address,
            current_snapshot=snapshot,
            historical_snapshots=history,
            token_age_minutes=token.age_minutes(),
        )
        wallet = wal_analyzer.analyze(
            token.address,
            snapshot=snapshot,
            creator_age_hours=creator_age_hours,
        )

        # 4. Score Token across all 6 components
        score = score_engine.calculate_score(
            token=token,
            snapshot=snapshot,
            security=security,
            liquidity=liquidity,
            momentum=momentum,
            wallet=wallet,
        )
        db.save_score(score)

        # 5. Feature Store & Decision
        features = feature_store.extract_features(
            token=token,
            snapshot=snapshot,
            security=security,
            liquidity=liquidity,
            momentum=momentum,
            score=score,
            wallet=wallet,
        )
        feature_store.save_features(features)

        action = TradeAction.HOLD
        if score.status == TokenStatus.CANDIDATE:
            action = TradeAction.BUY
            if portfolio.can_open_position():
                portfolio.open_virtual_position(token, snapshot, venue=token.dex)
        elif score.status == TokenStatus.REJECT:
            action = TradeAction.REJECT

        decision_ledger.record_decision(
            token=token,
            snapshot=snapshot,
            security=security,
            score=score,
            action=action,
        )

        age_m = token.age_minutes()
        bp_pct = f"{momentum.buy_pressure_ratio*100:.0f}%"
        price_str = f"${snapshot.price_usd:.6f}" if (snapshot.price_usd is not None and snapshot.price_usd < 0.01) else (f"${snapshot.price_usd:.4f}" if snapshot.price_usd is not None else "DATA_UNAVAILABLE")
        liq_str = f"${snapshot.liquidity_usd:,.0f}" if snapshot.liquidity_usd is not None else "DATA_UNAVAILABLE"

        # Raw metrics record
        raw_row = {
            "token": token.symbol[:8],
            "address": token.address,
            "top10_holder_share_pct": f"{top10_pct:.2f}%" if top10_pct is not None else "DATA_UNAVAILABLE",
            "creator_wallet_age_days": f"{creator_age_days:.3f}d" if creator_age_days is not None else "DATA_UNAVAILABLE",
            "creator_share_pct": f"{single_max_pct:.2f}%" if single_max_pct is not None else "DATA_UNAVAILABLE",
            "mutable_metadata": "YES" if security.is_mutable else "NO",
            "transfer_fee_pct": f"{security.transfer_fee_bps/100:.2f}%",
            "lp_lock_status": "UNVERIFIED (0%)",
            "wallet_cluster_score": f"{wallet.cluster_risk_score:.1f}",
        }
        raw_metrics_list.append(raw_row)

        # Scored row
        scored_row = {
            "token": token.symbol[:8],
            "address": token.address,
            "age": f"{age_m:.1f}m" if age_m > 0 else "<1m",
            "price": price_str,
            "liquidity": liq_str,
            "volume": f"${snapshot.volume_5m_usd:,.0f}",
            "buys": snapshot.buys_5m,
            "sells": snapshot.sells_5m,
            "buy_pressure": bp_pct,
            "sec_score": round(security.soft_security_score, 1),
            "liq_score": round(liquidity.liquidity_score, 1),
            "wal_score": round(wallet.wallet_score, 1),
            "mkt_score": round(score.breakdown.get("market", 0.0), 1),
            "mom_score": round(momentum.momentum_score, 1),
            "dq_score": round(snapshot.data_quality_score, 1),
            "total_score": score.total_score,
            "status": score.status.value,
            "decision_reason": score.decision_reason,
            "score_breakdown": score.breakdown,
        }
        results.append(scored_row)

    return {
        "raw_metrics": raw_metrics_list,
        "results": results,
        "stats": data_unavailable_stats,
    }


def print_scan_table(data: Dict[str, Any]) -> None:
    raw_metrics = data["raw_metrics"]
    results = data["results"]
    stats = data["stats"]

    # 1. RAW UNWEIGHTED METRICS TABLE
    print("\n" + "=" * 160)
    print("1. RAW UNWEIGHTED ON-CHAIN METRICS (BEFORE SCORING WEIGHTS)")
    print("=" * 160)
    raw_fmt = "{:<8} | {:<22} | {:<24} | {:<18} | {:<16} | {:<16} | {:<16} | {:<20}"
    print(raw_fmt.format(
        "TOKEN", "TOP10_HOLDER_SHARE_%", "CREATOR_WALLET_AGE_DAYS", "CREATOR_SHARE_%", "MUTABLE_METADATA", "TRANSFER_FEE_%", "LP_LOCK_STATUS", "WALLET_CLUSTER_SCORE"
    ))
    print("-" * 160)
    for r in raw_metrics:
        print(raw_fmt.format(
            r["token"],
            r["top10_holder_share_pct"],
            r["creator_wallet_age_days"],
            r["creator_share_pct"],
            r["mutable_metadata"],
            r["transfer_fee_pct"],
            r["lp_lock_status"],
            r["wallet_cluster_score"],
        ))
    print("=" * 160)

    # 2. 6-COMPONENT WEIGHTED SCORE TABLE
    print("\n" + "=" * 160)
    print("2. 6-FACTOR WEIGHTED SCORES & STATUS TABLE")
    print("=" * 160)
    header_fmt = "{:<8} | {:<5} | {:<12} | {:<16} | {:<8} | {:<4} | {:<4} | {:<5} | {:<5} | {:<5} | {:<5} | {:<5} | {:<5} | {:<5} | {:<6} | {:<9}"
    print(header_fmt.format(
        "TOKEN", "AGE", "PRICE", "LIQUIDITY", "VOLUME", "BUYS", "SELL", "BUY_P", "SEC", "LIQ", "WAL", "MKT", "MOM", "DQ", "SCORE", "STATUS"
    ))
    print("-" * 160)
    for r in results:
        print(header_fmt.format(
            r["token"],
            r["age"],
            r["price"][:12],
            r["liquidity"][:16],
            r["volume"],
            r["buys"],
            r["sells"],
            r["buy_pressure"],
            r["sec_score"],
            r["liq_score"],
            r["wal_score"],
            r["mkt_score"],
            r["mom_score"],
            r["dq_score"],
            r["total_score"],
            r["status"],
        ))
    print("=" * 160)

    # 3. SUMMARY & VERIFICATION SAMPLES
    print("\n[*] PROVIDER DATA AVAILABILITY SUMMARY:")
    print(f"    - Total Candidates Scanned:          {stats['total_scanned']}")
    print(f"    - Liquidity DATA_UNAVAILABLE:        {stats['liquidity_unavailable']} / {stats['total_scanned']}")
    print(f"    - Top-10 Holders DATA_UNAVAILABLE:   {stats['top10_holders_unavailable']} / {stats['total_scanned']}")
    print(f"    - Creator Age DATA_UNAVAILABLE:      {stats['creator_age_unavailable']} / {stats['total_scanned']}")

    if results:
        print("\n[*] SAMPLE 6-COMPONENT SCORE BREAKDOWNS:")
        for r in results[:3]:
            b = r["score_breakdown"]
            calc_sum = (
                b['security'] * 0.25
                + b['liquidity'] * 0.20
                + b['wallet'] * 0.15
                + b['market'] * 0.15
                + b['momentum'] * 0.20
                + b['data_quality'] * 0.05
            )
            print(f"    Token: {r['token']} ({r['address'][:16]}...) | Status: {r['status']}")
            print(f"      SEC (25%): {b['security']:.1f} | LIQ (20%): {b['liquidity']:.1f} | WAL (15%): {b['wallet']:.1f} | MKT (15%): {b['market']:.1f} | MOM (20%): {b['momentum']:.1f} | DQ (5%): {b['data_quality']:.1f}")
            print(f"      Formula: 0.25*{b['security']:.1f} + 0.20*{b['liquidity']:.1f} + 0.15*{b['wallet']:.1f} + 0.15*{b['market']:.1f} + 0.20*{b['momentum']:.1f} + 0.05*{b['data_quality']:.1f} = {calc_sum:.1f} -> TOTAL_SCORE = {r['total_score']:.1f}")
            print(f"      Reason:  {r['decision_reason']}\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run Solana Meme Research Lab Scanner")
    parser.add_argument("--limit", type=int, default=10, help="Number of candidate tokens to scan")
    args = parser.parse_args()
    data = run_pipeline(limit=args.limit)
    print_scan_table(data)
