"""
SQLite Database Schema for Solana Meme Research Lab.
Stores tokens, snapshots, security checks, feature entries, scores, paper positions, and decision ledger.
"""

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS tokens (
    address TEXT PRIMARY KEY,
    symbol TEXT NOT NULL,
    name TEXT NOT NULL,
    pair_address TEXT,
    dex TEXT DEFAULT 'raydium',
    created_at TIMESTAMP,
    discovered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    initial_liquidity_usd REAL DEFAULT 0.0,
    initial_price_usd REAL DEFAULT 0.0,
    status TEXT DEFAULT 'DISCOVERED',
    quarantine_until TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS token_snapshots (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    token_address TEXT NOT NULL,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    price_usd REAL DEFAULT 0.0,
    liquidity_usd REAL DEFAULT 0.0,
    volume_5m_usd REAL DEFAULT 0.0,
    volume_1m_usd REAL DEFAULT 0.0,
    volume_24h_usd REAL DEFAULT 0.0,
    buys_5m INTEGER DEFAULT 0,
    sells_5m INTEGER DEFAULT 0,
    trade_count_5m INTEGER DEFAULT 0,
    market_cap_usd REAL,
    holders_count INTEGER,
    top10_holders_pct REAL,
    creator_balance_pct REAL,
    data_sources TEXT,
    data_quality_score REAL DEFAULT 100.0,
    missing_fields TEXT,
    FOREIGN KEY(token_address) REFERENCES tokens(address)
);

CREATE TABLE IF NOT EXISTS security_checks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    token_address TEXT NOT NULL,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_mintable BOOLEAN DEFAULT 0,
    is_freezable BOOLEAN DEFAULT 0,
    is_mutable BOOLEAN DEFAULT 1,
    transfer_fee_bps INTEGER DEFAULT 0,
    top10_holders_pct REAL DEFAULT 0.0,
    creator_balance_pct REAL DEFAULT 0.0,
    single_holder_max_pct REAL DEFAULT 0.0,
    is_liquidity_locked BOOLEAN DEFAULT 0,
    is_hard_reject BOOLEAN DEFAULT 0,
    hard_reject_reasons TEXT,
    soft_security_score REAL DEFAULT 100.0,
    explanations TEXT,
    FOREIGN KEY(token_address) REFERENCES tokens(address)
);

CREATE TABLE IF NOT EXISTS scores (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    token_address TEXT NOT NULL,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    total_score REAL DEFAULT 0.0,
    security_score REAL DEFAULT 0.0,
    liquidity_score REAL DEFAULT 0.0,
    wallet_score REAL DEFAULT 0.0,
    market_score REAL DEFAULT 0.0,
    momentum_score REAL DEFAULT 0.0,
    data_quality_score REAL DEFAULT 100.0,
    status TEXT DEFAULT 'WATCH',
    decision_reason TEXT,
    breakdown TEXT,
    explanations TEXT,
    FOREIGN KEY(token_address) REFERENCES tokens(address)
);

CREATE TABLE IF NOT EXISTS decision_ledger (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    token_address TEXT NOT NULL,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    action TEXT NOT NULL,
    status TEXT NOT NULL,
    total_score REAL DEFAULT 0.0,
    security_score REAL DEFAULT 0.0,
    liquidity_score REAL DEFAULT 0.0,
    momentum_score REAL DEFAULT 0.0,
    wallet_score REAL DEFAULT 0.0,
    data_quality_score REAL DEFAULT 100.0,
    primary_reason TEXT,
    reasons TEXT,
    features_version TEXT DEFAULT 'v1.0',
    data_sources TEXT,
    FOREIGN KEY(token_address) REFERENCES tokens(address)
);

CREATE TABLE IF NOT EXISTS paper_positions (
    position_id TEXT PRIMARY KEY,
    token_address TEXT NOT NULL,
    symbol TEXT NOT NULL,
    entry_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    entry_price_usd REAL NOT NULL,
    amount_usd REAL DEFAULT 2.0,
    tokens_amount REAL NOT NULL,
    estimated_slippage_pct REAL DEFAULT 1.0,
    estimated_price_impact_pct REAL DEFAULT 0.5,
    network_fee_usd REAL DEFAULT 0.005,
    priority_fee_usd REAL DEFAULT 0.005,
    dex_fee_usd REAL DEFAULT 0.005,
    total_entry_cost_usd REAL DEFAULT 2.015,
    current_price_usd REAL DEFAULT 0.0,
    highest_price_usd REAL DEFAULT 0.0,
    stop_loss_price_usd REAL DEFAULT 0.0,
    take_profit_price_usd REAL DEFAULT 0.0,
    is_open BOOLEAN DEFAULT 1,
    exit_timestamp TIMESTAMP,
    exit_price_usd REAL,
    exit_reason TEXT,
    gross_pnl_usd REAL DEFAULT 0.0,
    net_pnl_usd REAL DEFAULT 0.0,
    net_roi_pct REAL DEFAULT 0.0,
    initial_discovery_price_usd REAL DEFAULT 0.0,
    price_growth_at_entry_pct REAL DEFAULT 0.0,
    score_at_entry REAL DEFAULT 0.0,
    score_at_t0 REAL,
    score_at_t5 REAL,
    max_gain_from_t0_pct REAL DEFAULT 0.0,
    max_gain_from_entry_pct REAL DEFAULT 0.0,
    max_drawdown_pct REAL DEFAULT 0.0,
    holding_time_seconds REAL DEFAULT 0.0,
    FOREIGN KEY(token_address) REFERENCES tokens(address)
);

CREATE TABLE IF NOT EXISTS features (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    token_address TEXT NOT NULL,
    feature_name TEXT NOT NULL,
    feature_value REAL,
    feature_str_value TEXT,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    source TEXT,
    calculation_version TEXT DEFAULT 'v1.0',
    FOREIGN KEY(token_address) REFERENCES tokens(address)
);

CREATE TABLE IF NOT EXISTS scan_cycles (
    cycle_id TEXT PRIMARY KEY,
    started_at TIMESTAMP NOT NULL,
    completed_at TIMESTAMP,
    duration_sec REAL DEFAULT 0.0,
    tokens_discovered INTEGER DEFAULT 0,
    tokens_analyzed INTEGER DEFAULT 0,
    error TEXT
);

CREATE INDEX IF NOT EXISTS idx_snapshots_token_time ON token_snapshots(token_address, timestamp);
CREATE INDEX IF NOT EXISTS idx_scores_token_time ON scores(token_address, timestamp);
CREATE INDEX IF NOT EXISTS idx_ledger_token_time ON decision_ledger(token_address, timestamp);
CREATE INDEX IF NOT EXISTS idx_features_token_time ON features(token_address, timestamp);
CREATE INDEX IF NOT EXISTS idx_cycles_time ON scan_cycles(started_at);
"""
