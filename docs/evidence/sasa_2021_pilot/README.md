# SASA 2021 — official KAP PDF pilot, not empirical graduation

**Evidence:** KAP disclosure [1004314](https://www.kap.org.tr/tr/Bildirim/1004314), SASA Polyester Sanayi A.Ş. consolidated 31 December 2021 report. Original Turkish auditor PDF: `SASA SPK 31.12.2021.pdf`, 79 pages, SHA-256 `605a4a1f8fcd9c2dfa381849cc3d53fde3bde8aacc1813831d8017da84b74b97`. English convenience translation: `ENGLISH-SASA SPK 31.12.2021.pdf`, SHA-256 `417df4da711991f0eb55a8f2e7d4f760e521e18c0b388dc5c46a5f3fc5ff9cc7`. KAP generated disclosure PDF: `1004314.pdf`, SHA-256 `943a9b0ba40c1082a9ddb3cea42e516c1ce0ed0d136da52e70b7fd28a17b4bcc`. PDFs remain user-held, not committed to GitHub. This record logs a **single source document**, not 2021–2025 coverage.

- Fiscal reporting period ended **2021-12-31**; KAP public notice publication timestamp **2022-02-25 07:26:37**, timezone needs verification. The independent auditor signed **2022-02-24**; neither date is the fiscal period-end.
- Original reporting currency is **1,000 Turkish lira per unit**. Amount `X` in the PDF means `X × 1000 TRY`. Do not mix a later IAS 29/TAS 29 restatement with the originally available 2021 version.
- The Turkish consolidated financial statements and English translation both give an unqualified audit opinion and matching primary totals.

## Source-observed values, all amounts 1,000 TRY

| Field | 2021 value | Turkish PDF locator | Use |
|---|---:|---|---|
| Total assets | 22,194,163 | p9 balance sheet | candidate `total_assets` |
| Cash and equivalents | 2,170,396 | p9; Note 3 p33 | not all assumed interest-bearing |
| Term deposits | 1,239,597 | Note 3 p33 | subset of cash, do not add twice |
| Short financial investments | 3,132 | p9; Note 4 p33 | same Eximbank blocked deposits |
| Short financial borrowings | 3,206,990 | Note 4 p34 | includes leases 52,754 |
| Long financial borrowings | 8,791,882 | Note 4 p34 | includes leases 119,442 |
| Aggregate financial borrowings | **11,998,872** | Note 4 p34 | includes bank, convertibles, leases |
| Bank loans including accruals | 9,004,412 | Note 4(a) p34 | aggregate subset |
| Convertible bond liability | 2,822,264 | Note 4(c) pp36–37 | aggregate subset; 3.25% coupon |
| Lease liabilities | 172,196 | Note 4(b) p35 | aggregate subset |
| Total revenue | **14,644,953** | p10 income statement; Note 18 p53 | candidate `total_revenue` |
| Finance income, **not all interest** | 1,189,517 | p10; Note 23 p57 | includes FX income |
| Interest income | **20,567** | Note 23 p57 | not complete noncompliant-revenue definition |
| FX-related finance income | 1,165,282 | Note 23 p57 | requires separate classification |
| Interest subsidy within other operating income | 32,077 | Note 20 p55 | pending Sharia classification |
| Total finance expenses | 4,920,603 | p10; Note 24 p57 | not all interest expense |
| Loan interest expense | 388,062 | Note 24 p57 | reported |
| Convertible interest expense | 57,029 | Note 24 p57 | reported |
| Total interest expense | 445,091 | p12 cash flow adjustments | reconciles previous two |
| Paid-in share capital | 1,120,000 | p9; Note 17 p50 | book capital, not shares-unit basis |
| Nominal shares, each 0.01 TRY | 112,000,000,000 shares | Note 17 p50 | not price/split-adjusted |
| Equity | 4,162,627 | p9 | reported |
| Net profit | 697,435 | p10 | reported |
| Operating cash flow | 805,636 | p12 | reported |

**Reconciliations:** 3,206,990 + 8,791,882 = **11,998,872** = 9,004,412 + 2,822,264 + 172,196. Interest 388,062 + 57,029 = **445,091**.

**Descriptive ratios only:** borrowings/assets with lease 54.063%; excluding leases 53.287%; interest income/revenue 0.140%; interest plus interest subsidy/revenue 0.359% (**sensitivity scenario, not reviewed noncompliant-revenue accounting**). No compliance/eligibility verdict follows.

## Gaps and import gates

1. **Historical XK100 membership unknown.** SASA is a technical extraction example, not an attested member of the research universe.
2. **Interest-bearing assets unknown as a complete taxonomy:** term deposits and other financial investments need review.
3. **Noncompliant revenue unknown:** explicit interest revenue 20,567 and subsidy 32,077 must not be conflated or hardcoded into the field without standards review.
4. **Bank + convertible bond + IFRS 16 lease treatment must be approved.** Total liabilities, trade payables and all finance FX movements are not automatically interest-bearing debt.
5. **Activity and other criteria attestations unknown.** Do not set `activity_pass` or `other_criteria_pass` to `true` from this report.
6. **Shares and actions:** capital is in 1,000 TRY; 112bn 1-kurus shares must be reconciled with price/share/corporate-action convention before `shares.csv`.
7. Publication timing, timezone, any amended disclosures, cross-version inflation restatements, and source preservation require curator review.
8. A single report has no bearing on 2021–2025 company-session coverage.

`source_facts_PENDING_REVIEW.csv` has the exact intake ledger columns and three **non-approvable** candidate rows (`review_status=pending_human_review`). This is intentional: `ieai.intake.compile_facts` must refuse to promote these rows until all mandatory definitions and independent review are completed.

**Status: PDF_SOURCE_VERIFIED_LOCALLY / PILOT_FACT_EXTRACTION / ACADEMIC_COVERAGE_NOT_READY**.
