# Solana Meme Research Lab — Project Audit (PROJECT_AUDIT.md)

## 1. Executive Summary & Found Assets

A comprehensive audit was performed across all workspace artifacts, reference repositories, academic datasets, and API configuration files.

| Asset / Repository | Type | Primary Role & Value | Reusability in Lab |
| :--- | :--- | :--- | :--- |
| **SolRPDS-main** | Academic Dataset (CODASPY 2025, Alhaidari et al.) | 3.69B historical Solana transactions (2021–2024), 62k+ liquidity pools, labeled rug pulls vs benign pools | **ML Training & Validation**: Ground truth labels, liquidity removal patterns, historical temporal analysis. |
| **memecoin.watch-main** | Architecture & Algorithm Spec | Multi-factor early warning, volume acceleration Heat formula, sequential buy pressure, bundle detection | **Momentum & Cluster Engine**: Heat metric, buy sequences, price-step increments, early warning scoring. |
| **solana-rugchecker-main** | TypeScript On-Chain Checker (degenfrends) | Modular security checks: Mint/Freeze authority, mutable metadata, holder concentration distribution, LP lock status | **Security Engine Spec**: Modular check design (Hard Rejects vs Soft Risk Scores). Do not use static score as truth. |
| **memebot3-main** | Full-scale Python Research & Trading Architecture | Feature Store (Parquet), Decision Ledger, Execution Simulator, Exit Models, Retrain/Walk-Forward ML loop | **Architecture Blueprint**: Pipeline structure (Discovery → Quarantine → Security → Momentum → Score → Paper Simulation → Decision Ledger). |
| **helios.dev-analitic.env** | Env Configuration | Helius RPC & DAS API configuration | **On-Chain Provider**: Token metadata, account parsing, transaction logs, DAS API. |
| **birdeye.env** | Env Configuration | Birdeye DeFi API configuration | **Market & Historical Provider**: OHLCV, volume, price, trader statistics. |
| **dex.txt** | OpenAPI Reference | DexScreener OpenAPI documentation | **Cross-Check & Discovery Provider**: Public REST API (60 req/min), pair discovery, market stats. |
| **юпитер.txt** | API Reference | Jupiter Quote & Price API documentation | **Execution Simulator (Optional)**: Realistic slippage, price impact, quote routing without real swaps. |

---

## 2. Deep-Dive Audit of Reference Repositories

### 2.1 SolRPDS (Solana Rug Pull Dataset)
- **Files**: `dataset/CSV/` and `dataset/json/` covering 2021, 2022, 2023, and Jan 2024–Nov 2024.
- **Key Columns**:
  - `LIQUIDITY_POOL_ADDRESS`, `MINT`
  - `TOTAL_ADDED_LIQUIDITY`, `TOTAL_REMOVED_LIQUIDITY`
  - `NUM_LIQUIDITY_ADDS`, `NUM_LIQUIDITY_REMOVES`
  - `ADD_TO_REMOVE_RATIO`
  - `LAST_POOL_ACTIVITY_TIMESTAMP`, `FIRST_POOL_ACTIVITY_TIMESTAMP`, `LAST_SWAP_TIMESTAMP`
  - `INACTIVITY_STATUS`
- **Critical Look-Ahead Bias Rule**: Historical dataset features represent aggregated lifecycles. For real-time inference at time $T$ (e.g., $T \in \{1\text{m}, 3\text{m}, 5\text{m}, 10\text{m}, 15\text{m}\}$), the model must strictly consume cumulative metrics computed **up to $T$ only**.
- **Usage**: Benchmark dataset for training classification models ($P(\text{rug} \mid \text{data}_{\le T})$) and measuring false negative rates.

### 2.2 solana-rugchecker (degenfrends)
- **Components**: `MetadataChecker`, `HoldersChecker`, `LiquidityChecker`, `MarketdataChecker`, `WebsiteChecker`.
- **Strengths**:
  - Token authority inspection (`isMintable`, `isFreezable`, `isMutable`).
  - Top holders percentage breakdown and individual holder threshold scoring ($>10\%$, $>7\%$, $>5\%$, $>3\%$, $>2\%$, $>1\%$).
- **Weaknesses**:
  - Outdated hardcoded scoring weights that are vulnerable to adversarial obfuscation (e.g. splitting balances across dozens of sybil wallets).
- **Adaptation**: Extract granular raw metrics into our `SecurityAnalyzer` and split into **Hard Reject** (e.g. freeze authority enabled, honeypot transfer fee, critical dev drain) and **Soft Risk Score** (0–100).

### 2.3 memecoin.watch (Raydium Scanner Concept)
- **Key Algorithms**:
  - **Volume Heat Formula**: $\text{Heat} = \frac{\text{Volume}_{1\text{m}}}{\text{Volume}_{5\text{m}}} \times 100\%$ (Cold: $<33\%$, Building: $33\text{--}48\%$, Hot: $48\text{--}99\%$, Peak/Exhaustion: $100\%$).
  - **Buy Sequence & Buy/Sell Ratio**: Ratio of buy volume to sell volume ($>1.2\times$ baseline, $>80\times$ extreme early spike) and consecutive buy count.
  - **Price Step Analysis**: Detecting minimum discrete upward increments (e.g., $\ge 0.2\%$ step increments).
  - **Early Warning Filters**: Flagging new wallet age ($<24\text{h}$ funding) and bundle transactions.

### 2.4 memebot3 (mudanzasalegre)
- **Best Architectural Patterns to Adopt**:
  1. **Dual Storage Tier**: Lightweight operational database (SQLite / PostgreSQL) for state + Parquet Feature Store for analytical time series.
  2. **Decision Ledger**: Every candidate token evaluation logs an immutable audit trail with timestamp, raw features, score components, decision (`PASS`, `WATCH`, `REJECT`), and detailed rejection reasons.
  3. **Realistic Paper Execution Engine**: Simulates entry with realistic DEX fees ($0.25\%$), Solana base + priority fees, and dynamic slippage / price impact curves.
  4. **Configurable Exit Models**: Trailing stops, hard stops (15%, 20%, 25%, 30%), partial take-profit ladders, and emergency liquidity exit.
  5. **Walk-Forward Validation**: Time-aware train/test splits that prevent leakage and model degradation.

---

## 3. API Infrastructure & Cost Control Matrix

| Provider | Purpose | Authentication | Rate Limits & Cost Management | Fallback / Cross-Check |
| :--- | :--- | :--- | :--- | :--- |
| **Helius** | Primary on-chain RPC, DAS API, parsed transactions, account balances | API Key via `HELIUS_API_KEY` (configured in env) | Adaptive rate limiter (token bucket), batch RPC requests, caching account data with TTL. | Public Solana RPC / DexScreener |
| **DexScreener** | Market discovery, newly created pairs, volume/liquidity cross-check | **Free Public REST API** (no key required) | Max 60 req/min. Caching with 15–30s TTL. Batch requests by token addresses (`/tokens/v1/solana/{addresses}`). | Birdeye |
| **Birdeye** | Granular market overview, token security overview, OHLCV historical feeds | API Key via `BIRDEYE_API_KEY` (configured in env) | Caching, deduplication queue, request throttling. | DexScreener |
| **Jupiter** | Quote simulation, realistic route analysis, slippage & price impact probing | Public / Optional API key | Optional execution check. If unavailable, use mathematical constant-product AMM impact model. | Internal AMM Cost Model |

> [!IMPORTANT]
> **Zero Secrets Policy**: All API keys and secrets are loaded strictly from environment files. No secrets are printed in logs, UI, artifacts, or source code.

---

## 4. Component Build Strategy: What to Reuse vs What to Write from Scratch

- **Reused Concepts & Data**:
  - SolRPDS historical raw dataset for ML training.
  - Security attribute checklists from rugchecker.
  - Momentum Heat and sequential buy formulas from memecoin.watch.
  - Decision ledger schema and paper simulation parameters from memebot3.
- **Written From Scratch (Clean Custom Architecture)**:
  - Unified asynchronous Provider Adapter layer (`DataProvider`, `MarketDataProvider`, `OnChainProvider`, `SecurityProvider`, `QuoteProvider`).
  - Liquidity time-series differential engine ($\Delta L$, velocity, acceleration, withdrawal ratio).
  - Time-indexed feature store without look-ahead bias.
  - Configurable multi-window quarantine evaluator ($3\text{m}, 5\text{m}, 7\text{m}, 10\text{m}, 15\text{m}$).
  - Paper trading execution engine with realistic fees and impact curves.
  - Research agent analytical interfaces.

---

## 5. Phase 1 Architecture Plan

1. **Workspace Setup**: Target root directory `solana-meme-research-lab/`.
2. **Provider Adapters**:
   - `HeliusAdapter` (RPC + DAS + RateLimiter + Cache)
   - `DexScreenerAdapter` (Discovery + Pairs + Batching)
   - `BirdeyeAdapter` (Market Data + Security fallback)
   - `JupiterAdapter` (Quote Probing / Slippage estimation)
3. **Core Analysis Engines**:
   - `SecurityAnalyzer`: Hard reject rules + soft risk score ($0\text{--}100$).
   - `LiquidityAnalyzer`: Liquidity snapshots, velocity, withdrawal ratios across $1\text{m}, 3\text{m}, 5\text{m}, 10\text{m}, 15\text{m}$.
   - `MomentumAnalyzer`: Heat index, buy pressure, sequential orders, trade size distributions.
   - `WalletAnalyzer`: Creator share, top-10 concentration, funding age, bundle heuristics.
   - `ScoreEngine`: Weighted composite scoring with modular configurations.
4. **Simulation & Ledger**:
   - `ExecutionSimulator`: Cost model, slippage, priority fee, DEX fee.
   - `PaperPortfolio`: $\$100$ initial capital, $\$2$ fixed position size, max 50 concurrent positions.
   - `DecisionLedger`: Structured JSON/SQLite ledger for full traceability of all decisions.
5. **SolRPDS ML Pipeline**:
   - Time-aware feature extractor for $T \in \{1\text{m}, 3\text{m}, 5\text{m}, 10\text{m}, 15\text{m}\}$.
   - Baseline models: Logistic Regression, Random Forest, LightGBM/XGBoost.
   - Evaluation metrics: Precision, Recall, PR-AUC, ROC-AUC, Calibration, False Negative Rate.
