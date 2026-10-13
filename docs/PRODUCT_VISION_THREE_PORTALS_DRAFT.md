# IEAI-Sharia-Radar — Proposed Product Vision and Academic Scope (DRAFT)

**Source:** owner's 2026-10-14 requirements and screenshots of a previous prototype. **Status: SPEC_FOR_REVIEW — not a claim that the capabilities already exist.** This draft must NOT silently change the locked `config/protocol.json` research experiment or portray historical screenshots as empirical evidence.

## Owner scope decision — CONFIRMED 2026-10-14

**Binding project scope direction, not a university protocol amendment:**

1. **Academic thesis deliverable takes priority and must retain the university-declared pair:** `BIST 100 (XU100)` **versus** `BIST Katılım 100 (XK100)`, with effective-date historical compositions and point-in-time market/financial inputs as covered by the existing `2021-10-01 — 2025-12-31` research protocol. This is a comparison of **stock-index universes and resulting investable strategies**, not an assertion that either index consists of 100 individual *banks*.
2. **A separate sectoral/institutional study is accepted as a second workstream:** participation banks/financial institutions versus conventional banks/financial institutions. This separate workstream is **not** part of required university thesis deliverables and must not delay, rewrite, contaminate or replace the academic XLS/benchmark/backtest results unless a later university-approved scope change is explicitly issued.
3. **Portal roadmap includes both comparative contexts** with explicit tabs for `Market Index Comparison` and `Financial Institution Comparison`. Investor public screen presents both current/dated 100-constituent lists with labels by **membership**, while eligibility/compliance is a second independent variable. A stock may belong to **both** indexes. Bank-only panels use the **actual number** of qualifying institutions, never fabricate two 100-bank panels.
4. **Academic hypothesis wording:** investigate whether historically verified Sharia-screened equity selection / the IEAI adaptive strategy can sustain competitive or higher **risk-adjusted return and smaller drawdowns** than the broad-market BIST 100 and suitable baselines. Academic report must show outcomes honestly even if results do not establish outperformance. Results on share prices **cannot alone prove causal superior accounting profitability of financial institutions**.
5. **Deliverables tied to the university pair:** dated index constituent panel and overlap, auditable rule-defined eligibility, market/financial data and publication availability audit, as-of 2021-2025 portfolios, total-return benchmark against XU100 and XK100, validated experiment comparing adaptive ML vs static/rule baselines, costs and risk-adjusted performance, Turkish CAPM/FF3/FF5 when sourced, robustness and defensible financial conclusions. Other proposals (live private-bank alerts, bidding, personalized trade signals) belong to product phases, **not academic graduation dependencies**.
6. **No current runtime or frozen research protocol modification is authorized by this product-scope clarification alone.** Keep `config/protocol.json`, existing `ieai` screening and holdout settings, and existing sample gates as-is pending precise academic requirement checks. If the signed university thesis document explicitly defines a different time span, benchmark type, comparison operator or cohort, request and reconcile it before code changes.
7. **Legal and epistemic honesty** applies to both workstreams: no claim that Sharia rules guarantee profits/lower risk, no "safe buy" promise, no internally inferred rule breach from external price data alone, no fabricated 2019-2026 graphs or live tick feed.

**Priority:** complete the academic XU100/XK100 requirements first; build reusable product infrastructure in parallel if it does not interfere. Bank/institutional comparative analytics are an independent later work package.

---

## Executive intent

Build one evidence-led system with two clearly separated modes:

1. **Academic / Research Laboratory**: point-in-time, reproducible, as-published Turkish equity/index and institution study; explicit hypotheses, held-out 2025 period, genuine accounting evidence and independent benchmark comparison. **No automatic proof of desired hypothesis**.
2. **Operational / Three Role-Based Portals**: live licensed BIST stock monitoring and investor analytics; institutional Sharia oversight (exception and remediation workflow); internal bank/participation institution compliance and risk surveillance using duly authorized internal feeds. Three roles share governed indicators and historical evidence but need strictly separate access permissions and workflows.

Long-term role of IEAI standards association is **independent issuer of standards** and role of MAIUMAS, subject to later agreements, is **implementation of technical products**. The current `research_30` model is not certified IEAI-CPS or complete TKBB rule implementation.

## Population semantics (ACADEMIC PAIR CONFIRMED; BANK SUBSTUDY SEPARATE)

- **XK100** is 100 shares of participation-screened **public companies across many sectors**; **NOT 100 participation banks or 100 participation financial institutions**. See official BIST: https://www.borsaistanbul.com/en/indices/bist-stock-indices/participation.
- **XU100** is the broad-market benchmark of 100 shares and can **overlap** XK100. It is NOT 100 conventional banks, nor necessarily 100 non-compliant stocks.
- **Comparative study A (equity strategy)**: historically effective XK100 constituents/eligible cohort vs XU100 *as benchmark*, and ideally an explicitly constructed non-overlapping matched comparison group. Adjust overlap, sector, market cap and survivorship biases; do not present index vs index as 100 matched Islamic versus conventional **institutions**.
- **Comparative study B (bank-specific)**: participation banks vs actually identifiable conventional banks/finance institutions, with comparable legal forms and risk/accounting measures; population and available listed entities may be much smaller than 100+100. This can become a separate hypothesis/sector study, not merged without a protocol amendment.
- Existing base academic study: **2021-10-01 to 2025-12-31**. It cannot validate 2019–2026 charts without source-specific historical reconstruction and appropriate frozen validation. Preserve actual contemporaneous membership/timestamp and no lookahead.
- Open question: does owner's “100 participation / 100 conventional institutions” mean **two market indices** or **two banking-institution sectors**? Do not alter empirical populations until confirmed.

## Hypotheses and objective evaluation

- **H0**: no statistically supported positive relationship / difference in risk-adjusted profitability attributable to the selected, clearly defined Sharia eligibility/compliance strategy compared to proper baselines.
- **H1**: compliance-based/investment-selection strategy is associated with higher risk-adjusted performance and/or lower downside risk, contingent on evidence. **Do not commit to proving it**.
- Equities: total returns net transaction costs, CAGR, Max Drawdown, downside volatility, Sharpe/Sortino, turnover, liquidity, BIST100 and XK100 benchmark, CAPM and Turkey-local FF3/FF5, and transparent false-positive trade-off. Numeric `alpha` means estimated factor-adjusted abnormal intercept with uncertainty, **not simply the green area between nominal wealth curves**.
- Banks/financial institutions: ROA, ROE, cost-income, financing quality / credit losses and asset risk, capital adequacy, provisions and revenue terminology harmonized to each accounting model; distinguish accounting profitability from stock returns and isolate bank-only sector effects.
- Statistical identification: control sector, size, balance-sheet structure, time effects, cohort overlap, market regimes, inflation / nominal TRY, portfolio self-financing, point-in-time financial availability, changes in compliance and survivorship. Selection bias and non-random adherence mean simple comparisons establish **association**, not causality.
- Academic uncertainty, factor sensitivity and failure to reject H0 are valid publishable findings; never tune the held-out 2025 period to yield preferred results.

## Operational three-portal requirements (PROPOSED, NOT YET BUILT)

### Investor / Trader
- Two continuously refreshed tables: XK100 constituents and XU100 constituents, 100 rows **each when supported by licensed official provider**, with overlap flagged. Identity via symbol/ISIN and effective constituent date. BIST100 constituents are NOT all automatically non-compliant.
- Columns: issuer, instrument, sector, index membership, price, % change, best bid/ask, turnover, market volume, monetary Sharia accounts, eligibility rule-set version, audit/reference source link, last underlying data timestamp, last verified compliance timestamp, risk score with calibration horizon and uncertainty; quote timestamps vs financial statement timestamps differentiated.
- Status: `eligible_as_of`, `ineligible_as_of`, `pending_review`, `insufficient_data`, `no_current_attestation`, `rulebook_not_applicable`; never blanket "100% pure", “haram” or guaranteed safe.
- Reason-for-exclusion drilldown: standard version and specific clause, financial inputs, number/unit, report publication time, applicability date, reviewer or automated heuristic, source evidence.
- Risk and buy/sell watchlist **only as legally appropriate analytics**: signal timestamp, prediction horizon, event probability, confidence/calibration, slippage/liquidity and falsifiable outcome; no guaranteed profit or promised “safe trades”. Personalized recommendations / direct order routing must receive separate Turkish SPK regulatory analysis and appropriate permissions, not assumed legal.

### Sharia Supervisory Board
- Event and standards-based change detection, evidence-linked case records, active/inactive standards, institutional portfolios and product mandates, alert delivery, acknowledgment / inquiry / correction / escalation / close, reviewer signature, immutable audit trail.
- Source-driven time semantics: new public KAP/KAFIF information can trigger near-real-time **publication event alerts**; this does NOT mean full financial compliance is continuously observed between filings.
- Institution-specific Sharia contract violations require permitted integrations to actual transaction / contract / accounting systems. Public market prices do not reveal private bank contracts.

### Internal Bank / Financial Institution Compliance
- Privileged per-institution data feeds: orders (when authorized), actual financing contracts, treasury, GL, risk limits, product approvals, internal transactions and exceptions.
- Detect rule violations using explicit versioned standard logic and input traceability; flags need classification (`rule_breach_confirmed`, `potential_anomaly`, `information_gap`, `market_behavior_warning`).
- Herding warnings: statistical co-movement/flow concentration indicator with tested false-positive rates; not per se Sharia breach, illegal manipulation or actual trader coordination. Requires suitable licensed trade/order flow depth and validated model.
- Tenant isolation, per-institution access boundaries, strong authentication, auditable override/review, encrypted transport/storage and data residency/legal requirements assessed by contract.

## Proposed top-level dashboard

1. **Market radar**: two index tables side by side or tabs, filters and red/amber/green statuses, overlapping constituents, status explanation link. Auto refresh only when licensed subscription delivers actual market data.
2. **Issuer/instrument detail**: entity, security code timeline, financial statement archive, capital events, original vs restated versions, eligibility timeline, debts/interest assets/revenue, rule decisions, change log, risk probabilities, sources.
3. **Model laboratory**: date as-of switch, historical strategy versus correct benchmarks, out-of-sample test, turnover/costs, backtest accounting, model uncertainty and factor alpha. Audit clear no future-data leakage.
4. **Compliance events**: queue, severity, candidate vs confirmed, rule ID, source timestamp and full alert lifecycle; investor sees only information permitted for the public.
5. **Institution private workspace**: internal connectors, violations, responsible reviewers, deadlines, remediation, user access logs.
6. **Research outputs**: provenance, missing data, revision lineage, hypotheses/robustness, versioned downloadable reports.
7. **Operations**: source latency, ingestion success, staleness, license entitlements, model drift, inactive/insufficiently-covered instruments; real events rather than scripted terminal theater.

Proposed page states: `historical_as_of`, `licensed_live`, `delayed`, `stale`, `offline_demo`. All numerical data and alerts carry transparent origin, observation time, receipt time, last rule review. Never mix these state types.

## Feasibility and legal gates

- Market streaming/level-2/order book typically requires a BIST-licensed vendor and appropriate distribution and **non-display / algorithmic analytics** entitlements; initial MKK/KAP developer VYK API subscription is NOT equivalent to BIST real-time market data. Official BIST: https://www.borsaistanbul.com/en/data/data-dissemination and https://www.borsaistanbul.com/en/data/data-dissemination/borsa-istanbul-data-distribution-agreement.
- Order-flow/transaction analytics are data-provider tier dependent; BIST already describes 1-second order/volume/order cancel analytics: https://www.borsaistanbul.com/en/equity-market-data-analytics. Do not assert identical coverage/latency to all instruments.
- Turkish SPK distinguishes financial information/general recommendations from individualized investment advice; certain services require authorized entities and suitability review. Legal review before buy/sell order-level personalization: https://spk.gov.tr/data/61e496a11b41c60d1404d6b2/Yat%C4%B1r%C4%B1m%20Hizmetleri%20ve%20Kurulu%C5%9Flar%C4%B1%20Rehberi%20%28i-SPK.37.8%29%2010%2003%202026.pdf
- Sharia judgments should be connected to a governing standard and subject to competent committee review; statistical anomaly signals are not fatwas or disciplinary judgments.
- Prior user screenshots from previous Streamlit prototype contain `Katılım_93`, `BIST_72`, 2019–2026 curves, green “ethical alpha” shading, ~88.5% success claims, live terminal theater and dynamic bids. They serve as **desired visual/interaction references only**. No reproducible original market data or calibrated model outputs for those specific claims has been validated in the current repo. Do not hardcode them.

## Architecture direction

- Keep existing Python research engine, immutable research protocol and audited intake pipeline.
- Proposed front end: Next.js (RTL, Turkish, English, Arabic) for institutional user experience, not mandated as a replacement for Streamlit laboratory overnight.
- API services: source ingest, issuer/security identity & dated index membership, standards versioning & review, screening, scoring/model serving, signal/alert generation, institutional cases, investor UI, export/audit, access controls.
- Data storage separates **raw legal source bytes with SHA256**, normalized point-in-time financial/security records, market tick stream, versioned decisions, ML predictions/performance, private tenant transaction documents and public UI caches.
- No "guaranteed accurate" or "100% halal" representations. Avoid making investment execution dependent on unreviewed data or unsupervised Sharia verdicts.

## Delivery milestones / exit gates

1. **Scientific design frozen:** choose sample semantics, overlap policy, explicit H0/H1 and accounting metrics; accept contemporaneous XK100 constituents and validate historical BIST sources.
2. **Real 2021–2025 panel audited:** KAP archive 2021/H1 and FY acquired so far; 2021/Q1/Q3 and 2022–2025 period statements pending, revised/exceptions/capital event/FF3/FF5 missing. `coverage.py` must genuinely pass all research data gates.
3. **Empirical evaluation:** preregister scoring and comparisons, training/calibration/frozen final 2025, falsifiable source-linked academic results, robust statistical testing.
4. **Public investor radar beta:** live / delayed vendor contracts, 2×100 instrument tables, rule-versioned explanations, minimal quote timeline and portfolio analytics with no unauthorized personalized advice.
5. **Institutional oversight beta:** event-driven alerts from public disclosures, review and escalation, private institution connectors only under lawful access.
6. **Advanced surveillance:** independently validated market herding/abuse proxy, latency & reliability SLAs, licensed order-stream integration; internal bank Sharia rule engine with human review and deployment controls.

**Resolved by owner (2026-10-14):** University thesis must remain the BIST100 vs BIST Katılım100 index-based study; participation-vs-conventional financial institutions are a separately scoped future study. University document/rulebook and data-graduation gates remain independently subject to review.
