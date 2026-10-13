# Verified user-supplied FinancialTable.zip — 2021 KAP annual export

**Reviewed:** 2026-10-13. **Scope:** User-uploaded `FinancialTable.zip`, 575 member files. **Original archive SHA-256:** `e6798fe4f673eb835d97325f405ec0cb168f20d9a6d33283622cc4fdf26e8f98`. Neither raw archive nor user-provided issuer data is committed to Git.

## Important result

The actual KAP Financial Statements `2021 + Yıllık` archive has now been obtained and inspected successfully. It contains **575** `.xls`-named files, internally **HTML** Excel exports, all labeled `Yıl: 2021`, `Periyot: 4`, `Bildirim Tipi: FR`. Filing IDs and release times are included per document, e.g. `SASA_1004314_2021_4.xls` reports `Gönderim Tarihi:25.02.2022 07:26:37`; independent SASA PDF and public notice agree. Metadata formatting checks passed for **575/575**, but that **does not independently authenticate every report** or certify 2021–2025 coverage.

- **538** unique **symbol strings** across 575 files; **37** extra records with repeated strings. These are not a count of distinct public companies or historical index members. Some symbols are composites of multiple tickers, others correspond to multiple filings or consolidation regimes.
- **320** consolidated (`Konsolide`), **255** nonconsolidated (`Konsolide Olmayan`).
- **437** source documents use `TL` (multiplier 1); **137** use `1.000 TL` (multiplier 1000); **1** uses `1.000.000 TL` (multiplier 1,000,000; THYAO). Original monetary unit MUST travel with each raw amount and be normalized exactly once.
- Source time headers: **574** reports published in **2022**, **one** in **2023** (BRKO `1139491`, `18.04.2023 00:07:27`). Publication header timezone remains unverified. A 2020 comparative column in a 2022 published report is **not 2020 point-in-time available data**.
- First balance-sheet taxonomy templates: **476** general corporate, **39** finance, **40** banks, **10** insurance, **8** holding, **2** participation banks. Specialized templates require dedicated taxonomy columns including local/foreign currency components.

## Automated source-hashed pilot account candidates

The offline reader `python -m ieai.kap_bulk_html` produces a source catalog and **unreviewed** general-sector candidate rows. It NEVER marks financial facts as fit for research or maps Sharia debt by convenience. From the user-supplied archive:

| Exact Turkish label / candidate | Reports |
|---|---:|
| `TOPLAM VARLIKLAR` — total assets | 476 |
| `TOPLAM KAYNAKLAR` — balance-sheet sources | 476 |
| `TOPLAM ÖZKAYNAKLAR` — equity | 476 |
| `Nakit ve Nakit Benzerleri` — cash and equivalents | 476 |
| `Kısa Vadeli Borçlanmalar` — *one* current borrowing line | 407 |
| `Uzun Vadeli Borçlanmalar` — *one* long borrowing line | 418 |
| `Hasılat` — operating sales (general income-statement template) | 320 |

**Total:** **3,049** raw source-to-account candidates. For the **476** general balance sheets with both top-line figures, `total_assets == total_sources` for all 476, zero numeric mismatches. This only tests arithmetic of extracted values.

**SASA reference:** 2021 assets `22,194,163`, revenue `14,644,953`, cash `2,170,396`, equity `4,162,627` as reported **in 1,000 TRY**; balances match the separately reviewed Turkish audit report. The HTML shows `Kısa Vadeli Borçlanmalar = 1,768,787` in a *specific sub-line*: do **not** assume this replaces the separately published total short financial borrowings of `3,206,990` which includes current portions of long-term borrowings and leases. IFRS16 leasing, convertibles and financial income require human-accounting and approved-Sharia interpretation.

## Reproduce without KAP API access

Place your legally acquired original KAP `FinancialTable.zip` in a private local folder, then:

```sh
python -m ieai.kap_bulk_html --archive "/local/FinancialTable.zip" --output-dir "/local/new-kap-2021-audit"
```

Outputs: `filing_catalog.csv`, `account_candidates.csv`, `source_audit.json`. The command only reads supplied files, checks paths and ZIP uncompressed-size limits, confirms reporting metadata, preserves individual file SHA256 and detects balance-sheet source mismatches. Does **not** fetch or download anything automatically. All outputs remain `UNREVIEWED_CANDIDATE_NOT_FOR_EMPIRICAL_SCREENING`; archive's original contents and the standalone publication date cannot be certified by these tests alone.

## Required before empirical study completion

1. Read the 2021/03, /06, /09 exports and years 2022–2025, plus **the 2021-10-01 opening-knowledge financial information published before that date**. This year-end export alone was largely disclosed in 2022 and cannot backfill earlier 2021 decisions.
2. Establish historical XK100 membership snapshots, changes and security-code continuity from official index data, separate from raw filing issuers.
3. Validate releases/corrections via original KAP disclosure pages, authenticate publication time zone and preserve original plus amended reports.
4. Independently review statement type (consolidated/non-consolidated), currency, temporal periods, sector-specific taxonomy, financing leases, related instruments, interest-bearing assets and noncompliant revenue according to a versioned screening standard. Use notes and PDF attachments as required.
5. Validate capital changes, lot/stock split-adjustment and share-unit compatibility; collect Turkey-specific FF3 and FF5 factors separately.
6. Confirm original KAP data retention/redistribution rights; do not present unreviewed source candidates as official IEAI endorsements or screened data.

**State:** `2021_ANNUAL_FINANCIAL_EXPORT_ACQUIRED_AND_CATALOGUED` / `RAW_ACCOUNT_CANDIDATES_EXTRACTED` / `RESEARCH_PANEL_NOT_READY`.

See [KAP_FINANCIAL_REVIEW_PIPELINE.md](KAP_FINANCIAL_REVIEW_PIPELINE.md), [KAP_FINANCIAL_REPORT_ANNOUNCEMENT_DATES.md](KAP_FINANCIAL_REPORT_ANNOUNCEMENT_DATES.md), and [DATA_CONTRACT.md](DATA_CONTRACT.md).
