# Feature Catalog — Solana Meme Research Lab (FEATURE_CATALOG.md)

This catalog defines the standard feature schema used across all analyzers, feature stores, and ML training pipelines.

| Feature Name | Category | Definition & Formula | Source Provider | Real-time? | Historical? | Look-Ahead Risk | Priority |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `mint_authority_disabled` | Security | Boolean: 1 if mint authority is null/revoked, 0 otherwise | Helius / On-chain | Yes | Yes | None | **P0 (Hard Reject)** |
| `freeze_authority_disabled` | Security | Boolean: 1 if freeze authority is null/revoked, 0 otherwise | Helius / On-chain | Yes | Yes | None | **P0 (Hard Reject)** |
| `is_metadata_mutable` | Security | Boolean: 1 if token metadata can be changed by creator, 0 otherwise | Helius / Metaplex | Yes | Yes | None | **P1 (Soft Risk)** |
| `transfer_fee_basis_points` | Security | Integer: Token-2022 transfer fee tax (bps). >0 indicates tax/honeypot | Helius / On-chain | Yes | Yes | None | **P0 (Hard Reject)** |
| `creator_balance_pct` | Wallet / Security | % of total token supply held by creator/dev wallet | Helius / Birdeye | Yes | Yes | None | **P0 (Hard/Soft)** |
| `top10_holders_pct` | Wallet / Security | Cumulative % of supply held by top 10 non-pool holders | Helius / Birdeye | Yes | Yes | None | **P0 (Soft Risk)** |
| `single_holder_max_pct` | Wallet / Security | Maximum % of supply held by any single non-pool wallet | Helius / Birdeye | Yes | Yes | None | **P0 (Hard/Soft)** |
| `creator_funded_age_hours` | Wallet | Age (in hours) of creator wallet since first incoming transaction | Helius / On-chain | Yes | Yes | None | **P1 (Soft Risk)** |
| `early_buyers_cluster_risk` | Wallet | Probabilistic score (0-100) of coordinated funding / sybil clusters | Helius / Internal | Yes | Yes | High if future tx used; strictly $\le T$ | **P1 (Soft Risk)** |
| `liquidity_usd` | Liquidity | Current total liquidity in USD pool | DexScreener / Birdeye | Yes | Yes | None | **P0** |
| `liquidity_velocity_5m` | Liquidity | $\frac{\text{Liq}(T) - \text{Liq}(T-5\text{m})}{5}$ ($/min rate of liquidity change) | Snapshots / SolRPDS | Yes | Yes | Critical: compute strictly at $T$ | **P0** |
| `liquidity_acceleration_5m` | Liquidity | Second derivative of liquidity curve $\frac{d^2 L}{dt^2}$ | Snapshots / SolRPDS | Yes | Yes | Critical: compute strictly at $T$ | **P1** |
| `liquidity_withdrawal_ratio` | Liquidity | Cumulative removed liquidity / Cumulative added liquidity | SolRPDS / Helius | Yes | Yes | Critical: cumulative strictly $\le T$ | **P0** |
| `inactivity_period_minutes` | Liquidity | Time elapsed since last pool swap / activity | SolRPDS / DexScreener | Yes | Yes | None | **P1** |
| `heat_1m_5m` | Momentum | $\frac{\text{Volume}_{1\text{m}}}{\text{Volume}_{5\text{m}}} \times 100\%$ (Volume acceleration) | DexScreener / Birdeye | Yes | Yes | None | **P0** |
| `volume_5m_usd` | Momentum | Trading volume in last 5 minutes (USD) | DexScreener / Birdeye | Yes | Yes | None | **P0** |
| `buy_sell_ratio_5m` | Momentum | Ratio of buy volume to sell volume over last 5 minutes | DexScreener / Birdeye | Yes | Yes | None | **P0** |
| `buy_pressure_index` | Momentum | Weighted index of consecutive buys + transaction count | memecoin.watch / Calc | Yes | Yes | None | **P1** |
| `price_change_5m_pct` | Momentum | Percentage price change over 5-minute window | DexScreener / Birdeye | Yes | Yes | None | **P0** |
| `price_step_count` | Momentum | Count of discrete upward price steps ($\ge 0.2\%$) | Birdeye / Calc | Yes | Yes | None | **P1** |
| `large_swap_count_5m` | Momentum | Count of single buy trades $> 3$ SOL ($>\$500$) | Helius / DexScreener | Yes | Yes | None | **P1** |
| `volume_to_liquidity_ratio` | Market | $\frac{\text{Volume}_{5\text{m}}}{\text{Liquidity}_{\text{usd}}}$ | DexScreener / Calc | Yes | Yes | None | **P0** |
| `market_cap_to_liquidity` | Market | $\frac{\text{FDV}}{\text{Liquidity}_{\text{usd}}}$ | DexScreener / Calc | Yes | Yes | None | **P1** |
| `data_quality_score` | Data Quality | 0–100 score reflecting completeness of fields (no missing essential metrics) | Internal Engine | Yes | Yes | None | **P0** |
| `security_composite_score` | Score | $0\text{--}100$ aggregated security assessment | SecurityAnalyzer | Yes | Yes | None | **P0** |
| `momentum_composite_score`| Score | $0\text{--}100$ aggregated momentum assessment | MomentumAnalyzer | Yes | Yes | None | **P0** |
| `composite_research_score`| Score | Configurable weighted sum: $0.25 S + 0.20 L + 0.15 W + 0.15 M + 0.20 Mo + 0.05 Q$ | ScoreEngine | Yes | Yes | None | **P0** |

---

## Look-Ahead Bias Prevention Rules

1. **Temporal Horizon Pinning ($T$)**: Every feature computation receives an explicit timestamp parameter $T$. All database queries and rolling metrics are strictly filtered with `WHERE timestamp <= :T`.
2. **Snapshot-Based Time Series**: Liquidity and price trajectories are recorded as immutable snapshots: $(t_0, t_1, t_2, \dots)$. Interpolation or future reference is strictly prohibited during replay/backtesting.
3. **Quarantine Window Partitioning**: Evaluation at $T = 1\text{m}, 3\text{m}, 5\text{m}, 10\text{m}, 15\text{m}$ utilizes strictly the information horizon $[0, T]$.
