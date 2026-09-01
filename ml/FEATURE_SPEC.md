# Feature Specification & Missing Value Policy (SolRPDS ML)

## 1. Unit of Observation
- **Observation Unit**: $\text{Pool}_i$ evaluated at time horizon $T \in \{1\text{m}, 3\text{m}, 5\text{m}, 10\text{m}, 15\text{m}\}$ from first valid pool activity timestamp $T_0$.
- **Sample Representation**: $(\mathbf{x}_{i, T}, y_i)$, where $\mathbf{x}_{i, T}$ is strictly computed using only on-chain observations at $t \le T_0 + T$, and $y_i \in \{0, 1\}$ is the ground truth outcome ($1 = \text{Rug/Inactive}, 0 = \text{Benign/Active}$).

---

## 2. Feature Definitions & Formulas

| Feature Name | Mathematical Formula | Data Source | Lookahead Safe? | Missing Value Policy |
| :--- | :--- | :---: | :---: | :--- |
| `liquidity_initial_usd` | $L_0 = \text{TOTAL\_ADDED\_LIQUIDITY} \times \text{fraction}_{\le T}$ | SolRPDS LP event | YES ($\le T_0 + T$) | `NULL` if uninitialized |
| `liquidity_added_T` | $L_{\text{add}}(T) = \sum_{t \le T_0 + T} \text{AddAmount}_t$ | SolRPDS LP Adds | YES ($\le T_0 + T$) | $0.0$ if no adds |
| `liquidity_removed_T` | $L_{\text{rem}}(T) = \sum_{t \le T_0 + T} \text{RemoveAmount}_t$ | SolRPDS LP Removes | YES ($\le T_0 + T$) | $0.0$ if no removes |
| `net_liquidity_T` | $L_{\text{net}}(T) = L_{\text{add}}(T) - L_{\text{rem}}(T)$ | SolRPDS LP diff | YES ($\le T_0 + T$) | $0.0$ if drained |
| `withdrawal_ratio_T` | $\frac{L_{\text{rem}}(T)}{L_{\text{add}}(T)}$ if $L_{\text{add}}(T) > 0$ else `NULL` | Derived | YES ($\le T_0 + T$) | `NULL` (never substitute $0.0$ if $L_{\text{add}}=0$) |
| `liquidity_velocity_T` | $\frac{L_{\text{net}}(T) - L_0}{T}$ (USD per minute) | Derived | YES ($\le T_0 + T$) | `NULL` if $T=0$ |
| `add_remove_count_ratio_T` | $\frac{N_{\text{adds}}(T)}{N_{\text{removes}}(T) + 1}$ | SolRPDS event count | YES ($\le T_0 + T$) | $N_{\text{adds}}$ if removes=0 |
| `pool_inactivity_indicator_T` | $\mathbb{I}\left(\Delta t_{\text{last\_swap}} > T\right)$ | SolRPDS swap events | YES ($\le T_0 + T$) | $1.0$ if no swaps observed |
| `transaction_count_T` | $N_{\text{adds}}(T) + N_{\text{removes}}(T)$ | SolRPDS event count | YES ($\le T_0 + T$) | $0$ |
| `data_quality_score` | $100.0 - \sum \text{Penalties}_{\text{missing}}$ | Feature Store | YES ($\le T_0 + T$) | $[0, 100]$ |

---

## 3. Strict Missing Data & Division-by-Zero Rules
1. **`DATA_UNAVAILABLE != 0`**: When a metric cannot be measured, it is stored as `NULL` / `np.nan` and processed via explicit median/indicator imputation fitted **ONLY on the TRAIN set**.
2. **Withdrawal Ratio Safety**:
   $$\text{withdrawal\_ratio} = \begin{cases} \frac{L_{\text{rem}}}{L_{\text{add}}} & \text{if } L_{\text{add}} > 0 \\ \text{NULL} & \text{if } L_{\text{add}} = 0 \end{cases}$$
3. **Scaler & Imputer Leakage Prevention**:
   ```python
   imputer.fit(X_train)
   scaler.fit(X_train_imputed)

   X_train_scaled = scaler.transform(imputer.transform(X_train))
   X_val_scaled = scaler.transform(imputer.transform(X_val))
   X_test_scaled = scaler.transform(imputer.transform(X_test))
   ```
