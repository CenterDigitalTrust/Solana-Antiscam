# Solana Meme Research Lab

A modular research, analytics, and paper trading simulation framework for early-stage Solana memecoins.

> [!IMPORTANT]
> **RESEARCH & SIMULATION ONLY**: This system does NOT contain wallet signers, private keys, seed phrases, or real trade execution capabilities. All trades are purely virtual paper simulations.

---

## Quick Start CLI

```bash
# 1. Check Provider Capabilities & Connectivity
python -m app.healthcheck

# 2. Discover Newly Active Solana Meme Tokens
python -m app.discovery

# 3. Run Real-Time Analysis & Score Pipeline
python -m app.scan --limit 10

# 4. View Virtual Paper Portfolio Status
python -m app.paper

# 5. Run All Unit Tests
python -m tests.run_all_tests
```

---

## Core Architecture

```
solana-meme-research-lab/
├── app/                 # CLI entrypoints (healthcheck, discovery, scan, paper)
├── collectors/          # Robust API adapters (Helius, DexScreener, Birdeye, Jupiter)
├── core/                # Models, Rate Limiter, TTL Cache, HTTP Client
├── database/            # SQLite operational DB & schema
├── discovery/           # Token discovery & quarantine registration
├── analyzers/           # Security, Liquidity, Momentum, and Wallet analyzers
├── scoring/             # Explainable Score Engine (0-100)
├── quarantine/          # Configurable quarantine windows (3m, 5m, 7m, 10m, 15m)
├── simulation/          # Fee Model, Execution Simulator ($2 slot), Paper Portfolio
├── features/            # Feature Store according to FEATURE_CATALOG.md
├── ledger/              # Immutable Decision Ledger
├── scripts/             # Healthcheck and SolRPDS importer
└── tests/               # Unit tests (rate limiters, fee models, analyzers, ledger)
```
