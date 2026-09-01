# SolRPDS Dataset Schema & Ground Truth Validation

## 1. Overview & Provenance
- **Dataset Name**: SolRPDS (Solana Rug Pull Dataset, derived from 3.69 Billion on-chain transactions)
- **Reference**: *Alhaidari, A., Kalal, B., Palanisamy, B. and Sural, S., 2025. SolRPDS: A Dataset for Analyzing Rug Pulls in Solana Decentralized Finance. In Proceedings of the Fifteenth ACM Conference on Data and Application Security and Privacy (CODASPY '25), pp. 293-298.*
- **License**: Creative Commons Attribution 4.0 International (CC BY 4.0)

---

## 2. Quantitative Summary
- **Total Files**: 4 CSV files (`2021.csv`, `2022.csv`, `2023.csv`, `Jan_2024-Nov_2024.csv`)
- **Total Records**: 116,308 records
- **Unique Liquidity Pools**: 63,521 pools
- **Unique Token Mints**: 33,358 mints
- **Temporal Range**: 2021-02-14 21:09:21 UTC to 2024-11-01 00:00:00 UTC (3.75 years of Solana DeFi history)

---

## 3. Ground Truth Definition & Class Balance
- **Ground Truth Field**: `INACTIVITY_STATUS`
- **Class Labeling**:
  - `Inactive` $\rightarrow$ **RUG / DRAINED POOL ($y = 1$)**: 22,555 records (**19.39%**)
  - `Active` $\rightarrow$ **BENIGN / ACTIVE POOL ($y = 0$)**: 93,749 records (**80.61%**)
  - `Missing / Null`: 4 records (0.003%, sanitized during load)
- **Class Imbalance Ratio**: $1 : 4.16$ (Rug to Benign)

### Breakdown by Year:
| File | Records | Active (Benign) | Inactive (Rug) | Rug Rate (%) |
| :--- | :---: | :---: | :---: | :---: |
| `2021.csv` | 1,703 | 1,612 | 90 | 5.29% |
| `2022.csv` | 3,695 | 3,199 | 495 | 13.40% |
| `2023.csv` | 15,477 | 12,580 | 2,896 | 18.71% |
| `Jan_2024-Nov_2024.csv` | 95,433 | 76,358 | 19,074 | 19.99% |
| **Total** | **116,308** | **93,749** | **22,555** | **19.39%** |

---

## 4. Fields Specification & Missing Value Counts

| Field Name | Type | Description | Missing Count | Policy |
| :--- | :---: | :--- | :---: | :--- |
| `LIQUIDITY_POOL_ADDRESS` | `string` | Base58 Solana AMM Pool Account Address | 0 | Required key |
| `MINT` | `string` | Base58 SPL Token Mint Address | 4 | Drop if missing |
| `TOTAL_ADDED_LIQUIDITY` | `float` | Cumulative liquidity deposited into pool | 4 | NULL if missing |
| `TOTAL_REMOVED_LIQUIDITY` | `float` | Cumulative liquidity withdrawn/drained from pool | 4 | NULL if missing |
| `NUM_LIQUIDITY_ADDS` | `int` | Number of LP mint/deposit operations | 4 | 0 if missing |
| `NUM_LIQUIDITY_REMOVES` | `int` | Number of LP burn/withdrawal operations | 4 | 0 if missing |
| `ADD_TO_REMOVE_RATIO` | `float` | Ratio of added to removed liquidity | 4 | NULL if removed=0 |
| `FIRST_POOL_ACTIVITY_TIMESTAMP` | `timestamp` | Pool creation timestamp ($T_0$) | 4 | Required for lookahead filter |
| `LAST_POOL_ACTIVITY_TIMESTAMP` | `timestamp` | Timestamp of last LP addition/removal | 4 | Validated $\ge T_0$ |
| `LAST_SWAP_TIMESTAMP` | `timestamp` | Timestamp of last swap transaction | 623 | NULL if no swaps |
| `LAST_SWAP_TX_ID` | `string` | Transaction signature of final swap | 623 | NULL if no swaps |
| `INACTIVITY_STATUS` | `string` | Ground truth label (`Active` / `Inactive`) | 4 | Required label |
