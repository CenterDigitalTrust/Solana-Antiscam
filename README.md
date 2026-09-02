# PATROL: Autonomous Data Monitoring & Analysis

PATROL (Digital Trust Center) is an autonomous, non-financial analytical daemon and interactive real-time dashboard. The system continuously scans decentralized data networks (DexScreener, Birdeye, Helius RPC), filters high-velocity streams through strict risk-management and behavioral parameters, and outputs the resulting signal feed to a secure Next.js frontend.

> **Note**: This system operates purely as an analytical research framework. It does not possess wallet signers, does not execute real swaps, and relies strictly on virtualized paper models.

---

## High-Level Architecture (Mermaid)

`mermaid
flowchart TD
    %% Define Styles
    classDef frontend fill:#1a1a1a,stroke:#333,stroke-width:2px,color:#fff;
    classDef backend fill:#252526,stroke:#4CAF50,stroke-width:2px,color:#fff;
    classDef db fill:#003b5c,stroke:#00a3e0,stroke-width:2px,color:#fff;
    classDef external fill:#4a4a4a,stroke:#666,stroke-width:2px,color:#fff;
    
    %% External Data Providers
    subgraph External Sources
        direction LR
        A[DexScreener API]:::external
        B[Birdeye API]:::external
        C[Helius RPC]:::external
    end

    %% Python Daemon (Backend)
    subgraph Azure Container / Python Daemon
        direction TB
        D((Collector<br/>Engine)):::backend
        E[Quarantine<br/>Manager]:::backend
        F[Scoring Engine &<br/>Feature Extractor]:::backend
        G[Simulation / Paper Trading]:::backend
        
        D -->|New Pairs| E
        E -->|Time Elapsed| F
        F -->|Passed Audit| G
    end

    %% Database (Supabase)
    subgraph Supabase Cloud
        direction TB
        H[(tokens)]:::db
        I[(daily_stats)]:::db
        J[(decision_ledger)]:::db
    end

    %% Frontend (Next.js)
    subgraph Azure Static Web Apps / Next.js
        direction TB
        K[React Client<br/>Dashboard]:::frontend
        L[Live Quaratine<br/>Feed]:::frontend
        M[Growth Leaders<br/>Cards]:::frontend
        
        K --- L
        K --- M
    end

    %% Connections
    External Sources -->|Raw Market Data| D
    G -->|Update Status & Prices| H
    G -->|Update PnL / Counters| I
    G -->|Audit Log| J
    
    H -->|Realtime Sub| K
    I -->|Realtime Sub| K
`

---

## Repository Structure

`	ext
PATROL/
├── site/                     # Next.js 14 Frontend (React, Tailwind, Supabase JS)
│   ├── src/components/       # UI Components (GrowthTable, StatsBar, etc.)
│   └── src/app/              # Next.js App Router (i18n, Pages, Layouts)
│
├── collectors/               # API Adapters for external sources
├── database/                 # Supabase Python SDK Client & Schema Defs
├── scoring/                  # Trust-scoring and filtering engine (0-100 logic)
├── quarantine/               # Delay buffers for initial screening
├── simulation/               # Virtual paper trading engine
└── main.py                   # Main Daemon Entrypoint
`

---

## Deployment Strategy

1. **GitHub Repository**: The entire mono-repo (Frontend + Backend) resides on GitHub.
2. **Azure Static Web Apps (SWA)**: Connected directly to the site/ folder in this GitHub repository. Automatically builds the Next.js app and provisions the edge network and CDN when code is pushed to main.
3. **Supabase**: Managed PostgreSQL database providing Realtime channels for the Next.js frontend, preventing the need for an intermediate WebSocket server.
4. **Azure VMs / Container Instances**: The Python daemon runs 24/7 as a background worker, pushing updates directly to Supabase via secure service-role keys.

---

## Development

`ash
# Start the Python analytical daemon (demo mode)
python simulate_market.py

# Or start the real paper daemon
python main.py --daemon

# Start the Next.js frontend
cd site
npm install
npm run dev
`
