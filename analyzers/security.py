"""
Security Analyzer for Solana Meme Research Lab.
Evaluates token security using on-chain authorities, token extensions, and holder distribution.
Separates critical HARD REJECT conditions from continuous SOFT SCORES (0-100) with explainable breakdown.
"""

from __future__ import annotations

from typing import Dict, List, Optional

from analyzers.base import BaseAnalyzer
from collectors.base import OnChainProvider
from core.models import HardRejectReason, SecurityCheckResult, TokenSnapshot, utc_now


class SecurityAnalyzer(BaseAnalyzer):
    def __init__(self, onchain_provider: Optional[OnChainProvider] = None):
        self.onchain_provider = onchain_provider

    @property
    def name(self) -> str:
        return "SecurityAnalyzer"

    def analyze(
        self,
        token_address: str,
        snapshot: Optional[TokenSnapshot] = None,
        authorities_override: Optional[dict] = None,
    ) -> SecurityCheckResult:
        auth_data = authorities_override or {}
        if not auth_data and self.onchain_provider:
            auth_data = self.onchain_provider.get_token_authorities(token_address)

        is_mintable = auth_data.get("is_mintable", False)
        is_freezable = auth_data.get("is_freezable", False)
        transfer_fee_bps = auth_data.get("transfer_fee_bps", 0)
        is_mutable = auth_data.get("is_mutable", True)

        top10_pct = snapshot.top10_holders_pct if snapshot else None
        creator_pct = snapshot.creator_balance_pct if snapshot else None
        single_max_pct = None

        if self.onchain_provider and top10_pct is None:
            try:
                top_holders_data = self.onchain_provider.get_top_holders(
                    token_address,
                    total_supply=float(auth_data.get("supply") or 0.0),
                    decimals=int(auth_data.get("decimals", 6)),
                )
                if top_holders_data.get("available"):
                    top10_pct = top_holders_data.get("top10_percentage")
                    single_max_pct = top_holders_data.get("single_holder_max_percentage")
            except Exception:
                pass

        hard_reject_reasons: List[str] = []
        explanations: List[str] = []
        breakdown: Dict[str, float] = {}

        score = 100.0
        breakdown["base"] = 100.0

        # === 1. HARD REJECT CHECKS ===
        if is_freezable:
            hard_reject_reasons.append(HardRejectReason.FREEZE_AUTHORITY_ENABLED.value)
            explanations.append("CRITICAL: Freeze authority is active (creator can blacklist wallets).")

        if transfer_fee_bps > 500:  # > 5% transfer fee
            hard_reject_reasons.append(HardRejectReason.TRANSFER_FEE_HONEYPOT.value)
            explanations.append(f"CRITICAL: Transfer fee tax detected ({transfer_fee_bps/100:.2f}%).")

        if snapshot and snapshot.liquidity_usd is not None and snapshot.liquidity_usd < 500.0 and snapshot.liquidity_usd > 0:
            hard_reject_reasons.append(HardRejectReason.INSUFFICIENT_LIQUIDITY.value)
            explanations.append(f"CRITICAL: Liquidity is below minimum safety threshold (${snapshot.liquidity_usd:.2f} < $500).")

        if single_max_pct is not None and single_max_pct >= 50.0:
            hard_reject_reasons.append(HardRejectReason.EXTREME_HOLDER_CONCENTRATION.value)
            explanations.append(f"CRITICAL: Single non-pool wallet holds {single_max_pct:.1f}% of supply.")

        # === 2. SOFT SCORE EVALUATION (0-100) ===
        # A. Mint authority penalty
        if is_mintable:
            score -= 35.0
            breakdown["mint_penalty"] = -35.0
            explanations.append("WARNING: Mint authority not revoked (-35).")
        else:
            breakdown["mint_penalty"] = 0.0
            explanations.append("+ Mint authority revoked (0 penalty).")

        # B. Mutable metadata penalty
        if is_mutable:
            score -= 10.0
            breakdown["mutable_penalty"] = -10.0
            explanations.append("NOTICE: Token metadata is mutable (-10).")
        else:
            breakdown["mutable_penalty"] = 0.0
            explanations.append("+ Token metadata is immutable (0 penalty).")

        # C. Token-2022 Transfer fee (mild tax < 5%)
        if 0 < transfer_fee_bps <= 500:
            fee_pen = (transfer_fee_bps / 100.0) * 5.0
            score -= fee_pen
            breakdown["transfer_fee_penalty"] = -fee_pen
            explanations.append(f"WARNING: Token transfer fee {transfer_fee_bps/100:.2f}% (-{fee_pen:.1f}).")
        else:
            breakdown["transfer_fee_penalty"] = 0.0

        # D. Holder Concentration & Distribution Differentiation
        if top10_pct is not None:
            if top10_pct > 80.0:
                pen = -35.0
            elif top10_pct > 65.0:
                pen = -25.0
            elif top10_pct > 50.0:
                pen = -15.0
            elif top10_pct > 35.0:
                pen = -5.0
            else:
                pen = 0.0
            score += pen
            breakdown["holder_concentration_penalty"] = pen
            explanations.append(f"Top 10 holders: {top10_pct:.1f}% ({pen:+.1f} penalty).")
        else:
            # Unverified holder distribution penalty
            score -= 20.0
            breakdown["holder_concentration_penalty"] = -20.0
            explanations.append("NOTICE: Top holders distribution unverified (-20).")

        # E. Single Whale / Creator Max Balance Impact
        whale_share = single_max_pct or creator_pct
        if whale_share is not None:
            if whale_share > 35.0:
                pen_whale = -25.0
            elif whale_share > 20.0:
                pen_whale = -15.0
            elif whale_share > 10.0:
                pen_whale = -5.0
            else:
                pen_whale = 0.0
            score += pen_whale
            breakdown["whale_concentration_penalty"] = pen_whale
            explanations.append(f"Largest single holder: {whale_share:.1f}% ({pen_whale:+.1f} penalty).")
        else:
            breakdown["whale_concentration_penalty"] = -5.0
            score -= 5.0

        # F. Liquidity Lock Status (Default assumption: unlocked if unknown)
        score -= 10.0
        breakdown["lp_lock_penalty"] = -10.0
        explanations.append("NOTICE: LP token lock unverified on-chain (-10).")

        soft_security_score = round(max(0.0, min(100.0, score)), 1)
        breakdown["final_score"] = soft_security_score
        is_hard_reject = len(hard_reject_reasons) > 0

        # Strict Security Gate (No optimistic fallback)
        has_verified_onchain_data = bool(auth_data) and (top10_pct is not None)
        if is_hard_reject:
            security_verified = False
            security_status = "SECURITY_BLOCKED"
            soft_security_score = None
        elif not has_verified_onchain_data:
            security_verified = False
            security_status = "SECURITY_UNVERIFIED"
            explanations.append("SECURITY_UNVERIFIED: On-chain authority or holder data unverified (Entry blocked).")
            soft_security_score = None
        elif is_mintable:
            security_verified = False
            security_status = "SECURITY_BLOCKED"
            explanations.append("SECURITY_BLOCKED: Mint authority active (Entry blocked).")
            soft_security_score = None
        else:
            security_verified = True
            security_status = "SECURITY_VERIFIED"
            explanations.append("SECURITY_VERIFIED: All security gates verified on-chain.")

        return SecurityCheckResult(
            token_address=token_address,
            timestamp=utc_now(),
            is_mintable=is_mintable,
            is_freezable=is_freezable,
            is_mutable=is_mutable,
            transfer_fee_bps=transfer_fee_bps,
            top10_holders_pct=top10_pct,
            creator_balance_pct=creator_pct,
            single_holder_max_pct=single_max_pct,
            is_liquidity_locked=False,
            is_hard_reject=is_hard_reject,
            hard_reject_reasons=hard_reject_reasons,
            soft_security_score=soft_security_score,
            security_verified=security_verified,
            security_status=security_status,
            score_breakdown=breakdown,
            explanations=explanations,
        )
