# CapEx Transmission Engine
## Technical and Research Specification

**Version:** 1.0  
**Project Duration:** 7 days  
**Language:** Python 3.12+  
**Project Type:** Quantitative investment research system  
**Primary Universe:** NVDA, MU, VRT  
**Extended Drivers:** MSFT, META, GOOGL  
**Research Frequency:** Quarterly  
**Market Frequency:** Daily, aggregated where required  
**Initial Historical Window:** 2016-01-01 through latest available date  
**Primary Benchmark:** SPY  
**Status:** Implementation Ready

---

# 1. PURPOSE

The CapEx Transmission Engine is a quantitative research system that models how artificial-intelligence infrastructure spending propagates through the physical technology supply chain and into public-company fundamentals.

The system must connect:

\[
\text{Hyperscaler CapEx}
\rightarrow
\text{AI Infrastructure Demand}
\rightarrow
\text{Physical Constraints}
\rightarrow
\text{Supplier Fundamentals}
\rightarrow
\text{Earnings}
\rightarrow
\text{Market Expectations}
\rightarrow
\text{Investment Signal}
\]

The system must produce interpretable investment views rather than direct black-box price predictions.

The central research question is:

> Can changes in AI infrastructure capital expenditure and physical supply constraints explain future fundamental performance, and can differences between model-implied fundamentals and market expectations identify subsequent earnings revisions or relative equity returns?

---

# 2. DESIGN PRINCIPLES

The implementation must follow these principles.

### P-001: Economic hypothesis before model

Every predictive feature must have a documented economic rationale.

Features must not be included only because they improve backtest performance.

### P-002: Point-in-time correctness

A calculation for date \(t\) may use only information that would have been available on or before \(t\).

### P-003: Interpretability

Every investment signal must be decomposable into identifiable economic drivers.

### P-004: Falsifiability

Every active investment thesis must define conditions that would weaken or invalidate it.

### P-005: Out-of-sample evaluation

Final performance must use walk-forward evaluation.

Random train/test splitting is prohibited for time-dependent investment tests.

### P-006: Research integrity

The system must report negative, unstable, and statistically insignificant results.

Failed hypotheses must not be silently removed.

### P-007: Reproducibility

A clean installation must be able to reproduce processed datasets, model outputs, figures, and final results from documented commands.

---

# 3. NON-GOALS

Version 1 will NOT:

- execute real trades;
- connect to brokerage accounts;
- use intraday data;
- perform high-frequency trading;
- predict next-day stock direction;
- use deep neural networks for return prediction;
- scrape hundreds of alternative datasets;
- optimize a large equity universe;
- implement production cloud infrastructure;
- implement live streaming;
- implement an LLM investment agent;
- claim causal identification when only correlation is measured.

These features are outside the one-week scope.

---

# 4. RESEARCH UNIVERSE

## 4.1 Core companies

The system must fully model:

```text
NVDA
MU
VRT
```

### NVDA

Represents accelerator and compute infrastructure.

### MU

Represents memory and HBM exposure.

### VRT

Represents data-center power and cooling infrastructure.

---

# 5. ECONOMIC DRIVER UNIVERSE

The first-order demand indicators must include:

```text
MSFT_CAPEX
META_CAPEX
GOOGL_CAPEX
```

Define:

\[
AggregateCapEx_t
=
CapEx_{MSFT,t}
+
CapEx_{META,t}
+
CapEx_{GOOGL,t}
\]

Define year-over-year growth:

\[
CapExGrowth_t
=
\frac{AggregateCapEx_t}
{AggregateCapEx_{t-4}}
-1
\]

The system should preserve individual company CapEx series in addition to the aggregate.

---

# 6. CAUSAL GRAPH

The research graph must be stored as machine-readable data.

Required initial graph:

```text
AI DEMAND
   |
   v
HYPERSCALER CAPEX
   |
   +----------------+
   |                |
   v                v
COMPUTE DEMAND   DATA CENTER BUILDOUT
   |                |
   v                +----------+
GPU DEMAND                     |
   |                           |
   +----------+                |
   |          |                |
   v          v                v
NVDA       HBM DEMAND      POWER / COOLING
              |                |
              v                v
             MU               VRT
```

---

# 7. CAUSAL EDGE SCHEMA

Each edge must contain:

```json
{
  "edge_id": "CAPEX_TO_NVDA",
  "source": "aggregate_hyperscaler_capex_growth",
  "target": "nvda_revenue_growth",
  "direction": "positive",
  "expected_lag_quarters": [1, 2, 3],
  "economic_rationale": "Higher hyperscaler infrastructure spending should increase demand for accelerator infrastructure.",
  "status": "untested"
}
```

Valid `status` values:

```text
untested
supported
weak
rejected
unstable
```

---

# 8. INITIAL HYPOTHESES

The repository must contain `research/hypotheses.yaml`.

## H-001

Higher aggregate hyperscaler CapEx growth predicts higher subsequent NVDA revenue growth.

Expected sign:

\[
\beta > 0
\]

Test lags:

\[
k \in \{0,1,2,3,4\}
\]

---

## H-002

Higher aggregate hyperscaler CapEx growth predicts higher subsequent MU revenue growth.

Expected sign:

\[
\beta > 0
\]

---

## H-003

Higher aggregate hyperscaler CapEx growth predicts higher subsequent VRT revenue growth.

Expected sign:

\[
\beta > 0
\]

---

## H-004

The relationship between CapEx and downstream revenue varies across macroeconomic regimes.

---

## H-005

A positive difference between model-implied earnings and market expectations predicts positive subsequent earnings revisions.

---

## H-006

A positive expectation gap predicts positive subsequent excess returns.

---

## H-007

The predictive value of the expectation gap remains after controlling for price momentum.

---

## H-008

Constraint indicators improve earnings forecasts relative to a model using hyperscaler CapEx alone.

---

# 9. DATA ARCHITECTURE

Required directories:

```text
data/
    raw/
        fundamentals/
        macro/
        market/
        estimates/
        industry/

    interim/

    processed/

    metadata/
        data_dictionary.yaml
        sources.yaml
```

Raw files must never be manually edited.

All transformations must create new files.

---

# 10. COMMON OBSERVATION SCHEMA

Every time-dependent observation must contain:

```text
series_id
entity
observation_date
period_end_date
available_date
value
unit
frequency
source
retrieved_at
```

The critical field is:

```text
available_date
```

`available_date` means the earliest date on which the information could legitimately enter the model.

---

# 11. POINT-IN-TIME RULE

For a model evaluated at date \(T\):

```python
observation.available_date <= T
```

must be true for every observation used.

Any observation violating this condition must cause the backtest to fail.

---

# 12. FUNDAMENTAL DATA

Required quarterly fields for each core company:

```text
revenue
cost_of_revenue
gross_profit
operating_income
net_income
diluted_eps
operating_cash_flow
capital_expenditure
free_cash_flow
cash
total_debt
inventory
accounts_receivable
diluted_shares
```

Derived:

\[
GrossMargin
=
\frac{GrossProfit}{Revenue}
\]

\[
OperatingMargin
=
\frac{OperatingIncome}{Revenue}
\]

\[
FCF
=
OperatingCashFlow-CapEx
\]

\[
FCFMargin
=
\frac{FCF}{Revenue}
\]

---

# 13. MARKET DATA

Required daily fields:

```text
date
ticker
adjusted_close
volume
```

Derived:

### 1-month momentum

\[
MOM_{21}
=
\frac{P_t}{P_{t-21}}-1
\]

### 3-month momentum

\[
MOM_{63}
=
\frac{P_t}{P_{t-63}}-1
\]

### 6-month momentum

\[
MOM_{126}
=
\frac{P_t}{P_{t-126}}-1
\]

### Excess return

\[
ER_{i,t}
=
R_{i,t}-R_{SPY,t}
\]

---

# 14. MACRO DATA

Minimum required variables:

```text
FED_FUNDS
US_10Y
US_2Y
CPI
INDUSTRIAL_PRODUCTION
UNEMPLOYMENT
```

Optional:

```text
HIGH_YIELD_SPREAD
FINANCIAL_CONDITIONS
REAL_GDP
```

Every macro observation must preserve release availability information when feasible.

---

# 15. INDUSTRY / CONSTRAINT DATA

Version 1 must contain at least three industry indicators.

Preferred categories:

```text
semiconductor_sales
memory_pricing_proxy
data_center_investment_proxy
```

Optional:

```text
taiwan_semiconductor_exports
tsmc_monthly_revenue
electricity_demand
semiconductor_equipment_sales
```

Every industry series must document:

```text
name
source
frequency
units
economic_interpretation
known_limitations
```

---

# 16. DATA INGESTION INTERFACE

All data adapters must implement:

```python
class DataSource:
    def fetch(
        self,
        start_date,
        end_date,
        **kwargs
    ) -> pd.DataFrame:
        ...

    def validate(
        self,
        data: pd.DataFrame
    ) -> None:
        ...

    def save_raw(
        self,
        data: pd.DataFrame,
        path: str
    ) -> None:
        ...
```

---

# 17. DATA VALIDATION

Each ingestion job must check:

```text
duplicate observations
missing dates
unexpected null rate
invalid numeric values
non-monotonic dates
duplicate primary keys
impossible values
```

The job must produce a validation report.

Example:

```json
{
  "dataset": "nvda_income_statement",
  "rows": 42,
  "duplicate_rows": 0,
  "null_rate": 0.01,
  "validation_status": "PASS"
}
```

---

# 18. QUARTER ALIGNMENT

All fundamental research models operate on fiscal quarters.

Each record must contain:

```text
ticker
fiscal_year
fiscal_quarter
period_end
filing_date
available_date
```

No company observation may become available before its filing or reported publication date.

---

# 19. FEATURE STORE

Processed features must use:

```text
entity
as_of_date
feature_name
feature_value
source_series
lookback
```

Example:

```text
NVDA
2025-09-30
hyperscaler_capex_yoy
0.284
MSFT+META+GOOGL
4Q
```

---

# 20. FEATURE TRANSFORMATIONS

Supported transformations:

```text
level
quarter-over-quarter growth
year-over-year growth
rolling mean
rolling standard deviation
z-score
difference
percentage difference
lag
```

Z-score:

\[
z_{i,t}
=
\frac{x_{i,t}-\mu_{i,t}}
{\sigma_{i,t}}
\]

Rolling statistics must use historical observations only.

---

# 21. TRANSMISSION MODEL

Module:

```text
src/transmission/
```

Primary interface:

```python
fit_transmission(
    driver: pd.Series,
    target: pd.Series,
    max_lag: int = 4
) -> TransmissionResult
```

---

# 22. TRANSMISSION RESULT

```python
@dataclass
class TransmissionResult:
    driver: str
    target: str
    lag: int
    coefficient: float
    intercept: float
    r_squared: float
    adjusted_r_squared: float
    standard_error: float
    t_statistic: float
    p_value: float
    observations: int
```

---

# 23. LAG SELECTION

For each causal edge, estimate:

\[
Y_t
=
\alpha+\beta X_{t-k}+\epsilon_t
\]

for:

\[
k=0,1,2,3,4
\]

The system must report all five models.

It must not silently return only the best-performing lag.

The preferred lag may be selected using training data only.

---

# 24. MULTIVARIATE TRANSMISSION MODEL

The second-stage model must support:

\[
RevenueGrowth_{i,t+1}
=
\alpha
+
\beta_1CapExGrowth_t
+
\beta_2Industry_t
+
\beta_3Macro_t
+
\beta_4Momentum_t
+
\epsilon
\]

Required model types:

```text
OLS
Ridge
Lasso
```

Optional:

```text
Random Forest
Gradient Boosting
```

Tree models are secondary.

The primary reported model must remain interpretable.

---

# 25. MODEL EVALUATION

Required metrics:

```text
MAE
RMSE
R²
directional accuracy
```

For linear models also report:

```text
coefficients
standard errors
t-statistics
confidence intervals
```

---

# 26. CONSTRAINT MODEL

Module:

```text
src/transmission/constraints.py
```

A constraint is represented by:

```python
@dataclass
class Constraint:
    name: str
    series_id: str
    current_value: float
    normalized_score: float
    direction: str
    confidence: float
```

---

# 27. CONSTRAINT SCORE

Each constraint proxy must be standardized using only historical information.

\[
C_{j,t}
=
z(x_{j,t})
\]

The direction must be transformed so that:

\[
Higher\ C_{j,t}
=
Tighter\ Constraint
\]

The overall constraint score is:

\[
C_t
=
\max_j C_{j,t}
\]

The binding constraint is:

\[
j^*
=
\arg\max_j C_{j,t}
\]

The dashboard must show both the result and the underlying proxies.

---

# 28. EARNINGS MODEL

Module:

```text
src/earnings/
```

Required companies:

```text
NVDA
MU
VRT
```

Interface:

```python
forecast_company(
    ticker: str,
    as_of_date: date,
    horizon_quarters: int
) -> EarningsForecast
```

---

# 29. EARNINGS FORECAST SCHEMA

```python
@dataclass
class EarningsForecast:
    ticker: str
    as_of_date: date
    horizon: str

    revenue_estimate: float
    gross_margin_estimate: float
    operating_income_estimate: float
    eps_estimate: float

    consensus_revenue: float | None
    consensus_eps: float | None

    revenue_gap_pct: float | None
    eps_gap_pct: float | None

    confidence: float
```

---

# 30. COMPANY MODEL: NVDA

At minimum:

\[
Revenue
=
DataCenter
+
Gaming
+
Automotive
+
Other
\]

For Version 1, segment growth may be estimated using historical segment growth plus transmission variables.

Then:

\[
GrossProfit
=
Revenue\times GrossMargin
\]

\[
OperatingIncome
=
GrossProfit-OperatingExpenses
\]

\[
PretaxIncome
=
OperatingIncome+NetInterestIncome
\]

\[
NetIncome
=
PretaxIncome(1-TaxRate)
\]

\[
EPS
=
\frac{NetIncome}{DilutedShares}
\]

---

# 31. COMPANY MODEL: MU

Minimum model:

\[
Revenue
=
MemoryVolume
\times
EffectivePrice
\]

If direct volume data is unavailable, use historical revenue plus documented industry proxies.

Gross margin must be modeled separately because memory pricing can materially affect operating leverage.

---

# 32. COMPANY MODEL: VRT

Model revenue as a function of:

```text
historical revenue
hyperscaler CapEx
data-center investment proxy
historical growth
```

Margin assumptions must be explicit.

---

# 33. CONSENSUS

Consensus estimates should include, when available:

```text
revenue estimate
EPS estimate
number of analysts
revision history
estimate date
```

Every estimate must include an `available_date`.

If reliable historical point-in-time consensus is unavailable, historical consensus-based backtesting must be disabled rather than reconstructed using future information.

This is mandatory.

---

# 34. EARNINGS GAP

Define:

\[
EG^{EPS}_{i,t}
=
\frac{
EPS^{model}_{i,t}
-
EPS^{consensus}_{i,t}
}{
|EPS^{consensus}_{i,t}|+\epsilon
}
\]

with:

\[
\epsilon=10^{-6}
\]

Similarly:

\[
EG^{Revenue}_{i,t}
=
\frac{
Revenue^{model}_{i,t}
-
Revenue^{consensus}_{i,t}
}{
|Revenue^{consensus}_{i,t}|+\epsilon
}
\]

---

# 35. REVERSE DCF

Module:

```text
src/valuation/reverse_dcf.py
```

Purpose:

Infer the growth assumptions required to justify the observed market price.

---

# 36. REVERSE DCF INPUT

```python
@dataclass
class ReverseDCFInput:
    ticker: str
    valuation_date: date

    market_price: float
    diluted_shares: float
    cash: float
    debt: float

    base_revenue: float
    initial_fcf_margin: float

    discount_rate: float
    terminal_growth: float

    explicit_years: int = 5
```

---

# 37. REVERSE DCF PROCESS

For candidate revenue growth \(g\):

\[
Revenue_t
=
Revenue_0(1+g)^t
\]

Version 1 may hold FCF margin constant or allow convergence toward a terminal margin.

\[
FCF_t
=
Revenue_t\times FCFMargin_t
\]

Terminal value:

\[
TV
=
\frac{
FCF_{T+1}
}{
r-g_T
}
\]

Enterprise value:

\[
EV
=
\sum_{t=1}^{T}
\frac{FCF_t}{(1+r)^t}
+
\frac{TV}{(1+r)^T}
\]

Equity value:

\[
EquityValue
=
EV+Cash-Debt
\]

Share value:

\[
P
=
\frac{EquityValue}{DilutedShares}
\]

Solve for \(g\):

\[
P(g)=P_{market}
\]

---

# 38. SOLVER

Use a deterministic root-finding algorithm.

Preferred:

```text
Brent's method
```

Search range:

```text
-0.50 <= g <= 1.50
```

Tolerance:

```text
1e-6
```

If no valid solution exists, return:

```text
status = NO_SOLUTION
```

Do not extrapolate silently.

---

# 39. REVERSE DCF OUTPUT

```python
@dataclass
class ReverseDCFResult:
    ticker: str
    valuation_date: date

    market_price: float
    implied_revenue_cagr: float
    model_revenue_cagr: float

    expectation_gap_pp: float

    reconstructed_price: float
    solver_error: float
    status: str
```

Define:

\[
ExpectationGap^{DCF}
=
ModelCAGR
-
MarketImpliedCAGR
\]

---

# 40. SIGNAL ENGINE

Module:

```text
src/signals/
```

Required raw signals:

```text
eps_gap
revenue_gap
reverse_dcf_gap
capex_transmission_score
constraint_score
momentum_3m
momentum_6m
```

---

# 41. STANDARDIZATION

At each date:

\[
z(x_i)
=
\frac{x_i-\mu}{\sigma}
\]

If the cross-section is too small for meaningful cross-sectional normalization, use expanding historical normalization per security.

The selected method must be documented.

---

# 42. COMPOSITE EXPECTATION GAP

Initial specification:

\[
EG_i
=
0.40z(EPSGap_i)
+
0.30z(RevenueGap_i)
+
0.30z(ReverseDCFGap_i)
\]

These weights are baseline research assumptions.

They must NOT be described as statistically optimal.

A later model may estimate weights from training data.

---

# 43. STATISTICALLY ESTIMATED SIGNAL

Fit:

\[
R_{i,t+k}^{excess}
=
\alpha+
\beta^TX_{i,t}
+\epsilon
\]

where:

\[
X=
[
EPSGap,
RevenueGap,
DCFGap,
ConstraintScore,
Momentum
]
\]

Required estimators:

```text
OLS
Ridge
Lasso
```

---

# 44. SIGNAL EVALUATION

Required statistics:

### Pearson IC

\[
IC_t
=
Corr(Signal_{i,t},Return_{i,t+k})
\]

### Rank IC

\[
RankIC_t
=
Spearman(
Signal_{i,t},
Return_{i,t+k}
)
\]

Also report:

```text
mean IC
IC standard deviation
IC information ratio
hit rate
mean long return
mean short return
long-short spread
```

---

# 45. LOOK-AHEAD PROTECTION

The backtester must execute:

```python
assert feature.available_date <= rebalance_date
```

for every feature used.

Failure must stop the backtest.

No warning-only mode is allowed.

---

# 46. WALK-FORWARD EVALUATION

Required structure:

```text
Train              Test
2016-2019      ->   2020
2016-2020      ->   2021
2016-2021      ->   2022
2016-2022      ->   2023
2016-2023      ->   2024
2016-2024      ->   2025
```

Adjust based on actual available history.

No test period may influence:

```text
feature selection
model selection
hyperparameters
signal weights
lag selection
```

---

# 47. BASELINES

Every predictive model must be compared against:

### B-001

Historical mean.

### B-002

Previous-quarter growth.

### B-003

Momentum-only model.

### B-004

CapEx-only model.

The full model is valuable only if it improves on relevant simple baselines.

---

# 48. REGIME ENGINE

Module:

```text
src/regimes/
```

Version 1 uses two dimensions:

```text
growth
inflation
```

Growth direction may use industrial production or another documented growth proxy.

Inflation direction uses CPI trend.

---

# 49. REGIME DEFINITIONS

```text
REGIME_1 = Growth Up / Inflation Up
REGIME_2 = Growth Up / Inflation Down
REGIME_3 = Growth Down / Inflation Up
REGIME_4 = Growth Down / Inflation Down
```

Classification thresholds must use historical data only.

---

# 50. REGIME ANALYSIS

For each regime report:

```text
observations
mean signal
mean forward return
mean excess return
IC
rank IC
hit rate
```

The system must warn when a regime contains too few observations for useful inference.

---

# 51. PORTFOLIO ENGINE

Module:

```text
src/portfolio/
```

The portfolio is a research artifact.

It does not execute trades.

---

# 52. BASELINE PORTFOLIO

Rank companies by expectation-gap score.

Long:

```text
highest scores
```

Short:

```text
lowest scores
```

For the three-security MVP, the system may hold one long, one short, and leave one neutral.

---

# 53. OPTIMIZATION

Extended portfolio construction:

\[
\max_w
w^T\hat{\mu}
-
\lambda w^T\Sigma w
\]

Subject to:

\[
\sum_iw_i=0
\]

\[
\sum_i|w_i|\le2
\]

\[
|w_i|\le0.50
\]

Target market beta:

\[
|\beta_p|\le0.10
\]

If the small universe makes these constraints infeasible, the optimizer must report infeasibility instead of relaxing constraints silently.

---

# 54. TRANSACTION COSTS

Backtests must support:

```text
0 bps
5 bps
10 bps
25 bps
```

per transaction.

Default:

```text
10 bps
```

---

# 55. PORTFOLIO METRICS

Required:

\[
CAGR
\]

\[
AnnualizedVolatility
\]

\[
Sharpe
\]

\[
MaxDrawdown
\]

\[
Beta
\]

\[
Turnover
\]

\[
HitRate
\]

Also report:

```text
long contribution
short contribution
transaction cost drag
```

---

# 56. PERFORMANCE ATTRIBUTION

The system must estimate whether strategy returns can be explained by common exposures.

Minimum controls:

```text
market return
semiconductor/technology benchmark
momentum
```

Estimate:

\[
R_{portfolio,t}
=
\alpha
+
\beta_mR_{market,t}
+
\beta_sR_{sector,t}
+
\beta_{mom}MOM_t
+
\epsilon_t
\]

Report coefficients and residual alpha.

Do not describe raw portfolio return as investment alpha without this analysis.

---

# 57. FALSIFICATION ENGINE

Module:

```text
src/thesis/
```

Each investment thesis must use:

```python
@dataclass
class Thesis:
    ticker: str
    direction: str

    thesis: str

    supporting_drivers: list[str]
    contradicting_drivers: list[str]

    break_conditions: list["BreakCondition"]

    status: str
    confidence: float
```

---

# 58. BREAK CONDITION

```python
@dataclass
class BreakCondition:
    feature: str
    operator: str
    threshold: float
    duration: int
    description: str
```

Example:

```json
{
  "feature": "aggregate_capex_yoy",
  "operator": "<",
  "threshold": 0.10,
  "duration": 2,
  "description": "Hyperscaler CapEx growth remains below 10% for two consecutive quarters."
}
```

---

# 59. THESIS STATUS

Allowed:

```text
ACTIVE
WEAKENING
BROKEN
INSUFFICIENT_DATA
```

Rules must be deterministic.

---

# 60. CONFIDENCE

Confidence must NOT be presented as a literal probability that the trade succeeds.

It is a model evidence score.

Initial definition:

\[
Confidence
=
f(
ModelAgreement,
DataQuality,
HypothesisSupport,
ContradictingEvidence
)
\]

Output range:

```text
0-100
```

The UI must label it:

```text
Evidence Score
```

not:

```text
Probability of Success
```

---

# 61. DASHBOARD

Recommended framework:

```text
Streamlit
```

Use Streamlit because the goal is research presentation, not frontend engineering.

---

# 62. PAGE 1: SYSTEM MAP

Must show:

```text
Hyperscaler CapEx
      ↓
Compute Demand
      ↓
Physical Constraints
      ↓
Company Revenue
      ↓
Earnings
      ↓
Market Expectations
```

Required components:

```text
current CapEx growth
current estimated binding constraint
latest company signals
portfolio positions
latest expectation gaps
```

---

# 63. PAGE 2: COMPANY RESEARCH

Selector:

```text
NVDA
MU
VRT
```

Show:

```text
historical fundamentals
model revenue estimate
consensus revenue estimate
model EPS
consensus EPS
earnings gap
reverse-DCF implied growth
model growth
expectation gap
signal history
thesis
supporting evidence
contradicting evidence
break conditions
```

---

# 64. PAGE 3: CAUSAL GRAPH

Display every modeled edge.

Clicking an edge must show:

```text
economic rationale
expected direction
tested lags
coefficient
t-statistic
p-value
R²
out-of-sample performance
status
```

---

# 65. PAGE 4: BACKTEST

Required charts:

```text
cumulative return
drawdown
rolling Sharpe
signal IC
long vs short contribution
```

Required controls:

```text
transaction cost
forecast horizon
signal type
```

---

# 66. PAGE 5: REGIMES

Show:

```text
current regime
historical regime timeline
signal performance by regime
company behavior by regime
```

---

# 67. PAGE 6: MODEL AUDIT

This page is mandatory.

Show:

```text
failed hypotheses
weak hypotheses
data limitations
missing observations
model instability
largest historical prediction errors
```

This prevents the project from becoming a marketing dashboard.

---

# 68. CLI

Required commands:

```bash
python -m capex_engine ingest
python -m capex_engine validate
python -m capex_engine features
python -m capex_engine research
python -m capex_engine forecast
python -m capex_engine backtest
python -m capex_engine report
```

Complete pipeline:

```bash
python -m capex_engine run-all
```

---

# 69. CONFIGURATION

File:

```text
config/research.yaml
```

Example:

```yaml
start_date: "2016-01-01"
benchmark: "SPY"

core_universe:
  - NVDA
  - MU
  - VRT

capex_drivers:
  - MSFT
  - META
  - GOOGL

max_lag_quarters: 4

forecast_horizon_quarters: 1

transaction_cost_bps: 10

reverse_dcf:
  explicit_years: 5
  discount_rate: 0.10
  terminal_growth: 0.03

portfolio:
  gross_exposure: 2.0
  max_position: 0.50
  beta_limit: 0.10
```

No research parameter may exist only as an unexplained magic number inside Python code.

---

# 70. LOGGING

Every pipeline execution must log:

```text
timestamp
module
operation
input dataset
output dataset
rows processed
warnings
errors
runtime
```

---

# 71. DATA LINEAGE

Every generated model output must be traceable to source data.

Example:

```json
{
  "output": "nvda_eps_forecast_2026Q4",
  "generated_at": "...",
  "as_of_date": "...",
  "inputs": [
    "nvda_fundamentals",
    "aggregate_hyperscaler_capex",
    "semiconductor_sales"
  ],
  "model_version": "earnings_v1"
}
```

---

# 72. TESTS

Required test directories:

```text
tests/
    test_ingestion.py
    test_point_in_time.py
    test_features.py
    test_transmission.py
    test_reverse_dcf.py
    test_signals.py
    test_backtest.py
    test_portfolio.py
    test_thesis.py
```

---

# 73. CRITICAL TEST: LOOK-AHEAD

Create a synthetic observation:

```text
observation_date = 2024-03-31
available_date   = 2024-05-20
```

Run backtest at:

```text
2024-04-30
```

Expected:

```text
observation excluded
```

Any inclusion is a test failure.

---

# 74. CRITICAL TEST: REVERSE DCF

Given a known growth rate \(g\):

1. Generate a theoretical stock price.
2. Pass that price to the reverse DCF.
3. Solve for implied \(g\).

Acceptance:

\[
|g_{solved}-g_{true}|<10^{-5}
\]

---

# 75. CRITICAL TEST: SIGNAL

Synthetic:

```text
model EPS = 12
consensus EPS = 10
```

Expected:

\[
EPSGap=0.20
\]

---

# 76. CRITICAL TEST: PORTFOLIO

Every portfolio must satisfy:

\[
\left|\sum_iw_i\right|<10^{-6}
\]

when dollar neutrality is enabled.

---

# 77. CRITICAL TEST: WALK-FORWARD

Training observations must satisfy:

```text
training_date < test_period_start
```

Any violation fails the run.

---

# 78. RESEARCH OUTPUT

Generate:

```text
reports/final_research_report.md
```

automatically where possible.

Required sections:

```text
Executive Summary
Research Question
Economic Model
Data
Hypotheses
Methodology
Results
Expectation Gaps
Portfolio Results
Regime Analysis
Falsification
Failed Hypotheses
Limitations
Conclusion
Future Research
```

---

# 79. COMPANY RESEARCH OUTPUT

Generate one file per company:

```text
reports/NVDA.md
reports/MU.md
reports/VRT.md
```

Each must answer:

1. What does the company economically do?
2. Which variables should drive its fundamentals?
3. What does the model expect?
4. What does the market expect?
5. Why do they differ?
6. What evidence supports the model?
7. What evidence contradicts it?
8. What would invalidate the thesis?

---

# 80. README

The README must begin with the research question.

Do NOT begin with:

> This project uses Python, pandas, scikit-learn...

Begin with:

> AI infrastructure spending is rising rapidly, but a dollar of capital expenditure does not translate instantly or equally into revenue across the supply chain. This project tests whether the transmission from hyperscaler CapEx through compute, memory, power, and cooling can be modeled systematically, and whether deviations between model-implied fundamentals and market expectations contain investment information.

Then show the causal graph.

Technology comes later.

---

# 81. REPOSITORY STRUCTURE

Final structure:

```text
capex-transmission-engine/
│
├── README.md
├── SPEC.md
├── requirements.txt
├── pyproject.toml
├── .env.example
│
├── config/
│   ├── research.yaml
│   ├── companies.yaml
│   └── sources.yaml
│
├── data/
│   ├── raw/
│   ├── interim/
│   ├── processed/
│   └── metadata/
│
├── research/
│   ├── hypotheses.yaml
│   ├── causal_graph.yaml
│   ├── methodology.md
│   └── research_log.md
│
├── src/
│   └── capex_engine/
│       ├── __init__.py
│       ├── cli.py
│       │
│       ├── ingestion/
│       ├── validation/
│       ├── features/
│       ├── transmission/
│       ├── constraints/
│       ├── earnings/
│       ├── valuation/
│       ├── signals/
│       ├── regimes/
│       ├── portfolio/
│       ├── thesis/
│       ├── backtest/
│       └── reporting/
│
├── notebooks/
│   ├── 01_data_audit.ipynb
│   ├── 02_transmission.ipynb
│   ├── 03_earnings.ipynb
│   ├── 04_expectations.ipynb
│   └── 05_backtest.ipynb
│
├── dashboard/
│   └── app.py
│
├── reports/
│
└── tests/
```

---

# 82. DEPENDENCIES

Minimum:

```text
pandas
numpy
scipy
statsmodels
scikit-learn
pyyaml
requests
pyarrow
matplotlib
plotly
streamlit
pytest
```

Optional:

```text
cvxpy
networkx
```

Use `cvxpy` only if constrained portfolio optimization is implemented.

---

# 83. IMPLEMENTATION ORDER

Implementation must follow this order:

```text
1. schemas
2. ingestion
3. point-in-time data rules
4. validation
5. features
6. causal transmission tests
7. earnings models
8. reverse DCF
9. expectation-gap signal
10. walk-forward backtest
11. regime analysis
12. portfolio construction
13. falsification engine
14. dashboard
15. report
```

Do not build the dashboard before the research pipeline works.

---

# 84. DAY 1 ACCEPTANCE CRITERIA

By the end of Day 1:

- repository exists;
- environment installs successfully;
- `SPEC.md` exists;
- causal graph exists;
- hypotheses are machine-readable;
- data dictionary exists;
- three core companies are configured;
- three hyperscaler drivers are configured;
- at least one fundamental source works;
- at least one macro source works;
- raw data can be saved without manual modification;
- initial point-in-time schema exists;
- tests run.

---

# 85. DAY 2 ACCEPTANCE CRITERIA

By the end of Day 2:

- NVDA, MU, and VRT fundamental histories are available;
- MSFT, META, and GOOGL CapEx histories are available;
- market prices are available;
- macro series are available;
- at least three industry indicators are available;
- processed quarterly panel exists;
- missing-data report exists;
- every processed observation has `available_date`;
- no point-in-time violations exist.

---

# 86. DAY 3 ACCEPTANCE CRITERIA

By the end of Day 3:

- H-001 through H-004 have been tested;
- lag tables exist;
- regression diagnostics exist;
- baseline models exist;
- at least one constraint proxy works;
- causal graph edges contain empirical status;
- failed hypotheses remain visible.

---

# 87. DAY 4 ACCEPTANCE CRITERIA

By the end of Day 4:

- three company earnings models run;
- model revenue forecasts exist;
- model EPS forecasts exist;
- consensus comparison works where data permits;
- reverse DCF works for all three companies;
- expectation gaps are calculated;
- reverse DCF unit tests pass.

---

# 88. DAY 5 ACCEPTANCE CRITERIA

By the end of Day 5:

- signals are generated historically;
- walk-forward infrastructure works;
- H-005 through H-008 are tested where data permits;
- momentum baseline exists;
- CapEx-only baseline exists;
- IC and Rank IC are calculated;
- regime analysis works;
- look-ahead tests pass.

---

# 89. DAY 6 ACCEPTANCE CRITERIA

By the end of Day 6:

- long/short portfolio is generated;
- transaction costs are included;
- risk statistics exist;
- attribution exists;
- thesis objects exist;
- break conditions work;
- model limitations are documented;
- largest historical prediction failures are identified.

---

# 90. DAY 7 ACCEPTANCE CRITERIA

By the end of Day 7:

- dashboard works;
- README is complete;
- research report is complete;
- company reports exist;
- figures are publication quality;
- repository installs from scratch;
- tests pass;
- one command reproduces the research pipeline;
- no API keys exist in Git history;
- results can be explained without opening the source code.

---

# 91. DEFINITION OF DONE

Version 1 is complete only when a reviewer can answer all of the following from the repository:

### Economic reasoning

What economic relationship is being tested?

### Fundamental investing

Why should NVDA, MU, or VRT earnings differ from expectations?

### Quantitative research

Does the relationship survive out-of-sample testing?

### Market expectations

What assumptions appear to be embedded in current valuations?

### Risk

Could the observed return simply be market, sector, or momentum exposure?

### Falsification

What observation would demonstrate that the investment thesis is wrong?

### Research integrity

Which hypotheses failed?

If any of these cannot be answered, the project is incomplete.

---

# 92. MVP CUT LINE

If the seven-day deadline becomes binding, features must be cut in this order:

```text
CUT FIRST:
interactive causal graph

THEN:
portfolio optimizer

THEN:
advanced regime visualization

THEN:
automated report generation

THEN:
VRT detailed segment model
```

Never cut:

```text
point-in-time correctness
causal hypotheses
fundamental model
reverse DCF
expectation gap
walk-forward evaluation
baselines
falsification
limitations
```

Those are the project's core research contributions.

---

# 93. FINAL DEMO

The final demonstration must take less than five minutes.

### Minute 0-1

Explain:

> AI CapEx is observable at hyperscalers, but its economic impact must pass through a constrained physical supply chain before appearing in supplier earnings. I wanted to test whether that transmission could be modeled and whether the market systematically misestimated it.

### Minute 1-2

Show the causal graph.

Select one relationship.

Show:

```text
hypothesis
economic rationale
lag
coefficient
out-of-sample result
```

### Minute 2-3

Open MU or NVDA.

Show:

```text
model EPS
consensus EPS
reverse-DCF implied growth
model growth
expectation gap
```

Explain the disagreement.

### Minute 3-4

Show historical testing.

Show:

```text
IC
out-of-sample results
regime dependence
baseline comparison
```

### Minute 4-5

Show the thesis.

Show:

```text
supporting evidence
contradicting evidence
break conditions
largest model failure
```

Finish with what the system still does not understand.

---

# 94. INTERVIEW STANDARD

The project must allow the author to defend every major design choice.

The author must be able to answer:

> Why should CapEx lead revenue?

> Why did you choose this lag?

> Why should this relationship persist?

> What causes it to break?

> How did you prevent look-ahead bias?

> Why use this regression?

> Why not use a neural network?

> What does the coefficient mean economically?

> How sensitive is the DCF to the discount rate?

> Why is consensus wrong?

> What evidence would convince you that consensus is right?

> Is your portfolio actually generating alpha or loading on semiconductor momentum?

> What was your strongest hypothesis that failed?

> If you had another month, what would you test next?

If the implementation cannot support defensible answers to those questions, additional features should not be added.

---

# 95. PROJECT SUCCESS CRITERION

Success is NOT defined as:

```text
positive returns
high Sharpe ratio
high R²
significant p-values
beating SPY
```

Success is defined as building a reproducible research system that:

1. starts with explicit economic hypotheses;
2. converts those hypotheses into measurable relationships;
3. connects macro and industry information to company fundamentals;
4. compares independent estimates with market expectations;
5. evaluates those disagreements without future information;
6. determines whether observed relationships survive reasonable robustness tests;
7. identifies why the model works or fails;
8. states what evidence would invalidate its conclusions.

A rigorous null result satisfies the specification.

---

# 96. FINAL PROJECT DESCRIPTION

**CapEx Transmission Engine** is a systematic investment research platform that models how AI infrastructure spending propagates through compute, memory, power, and cooling supply chains. It combines point-in-time economic data, bottom-up company models, reverse-DCF market-implied expectations, causal transmission testing, and walk-forward signal evaluation to identify and investigate differences between fundamental estimates and market expectations.

The system is designed to answer:

\[
\boxed{
\text{What does the market believe, what does the economic system imply, and why are they different?}
}
\]