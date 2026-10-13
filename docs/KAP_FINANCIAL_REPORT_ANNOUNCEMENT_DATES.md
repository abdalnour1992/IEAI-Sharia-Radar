# KAP official Financial Report Announcement Dates — schedule metadata

**Status:** `DATES_ARCHIVE_INSPECTED / DAILY_TIMESTAMPS_UNCONFIRMED / NOT_FINANCIAL_STATEMENTS`

## User-supplied source archive (2026-10-13)

- Uploaded file: `Finansal Rapor İlan Tarihleri.zip`
- SHA-256: `746e70d2cb2be203604e9266058eca1d24c0cfde7bf9c69519f3f67635f7806f`
- Contains **23 .xlsx** documents (`YYYYMMaylıkfinansalraportarihleri.xlsx`) from 2021/03 through 2026/09 (2026 partial), with four 2021–2025 reporting-period types per year.
- **Not** a KAP financial-statement RAR download and **not** a source for audited income/assets/debt amounts. The official KAP user guide describes `Finansal Rapor Tarihleri` (deadline Excel lists) separately from `Finansal Tablolar → [year] → [period] → İndir` (statement archive). Guide: https://www.kap.org.tr/tr/api/about/content-file/402832a195b3017d0195bd17e2e07e9a
- Original file bytes must remain unchanged; archive itself is not committed to public GitHub, and exact URL/time of user download are not independently recorded.

## Source worksheet semantics

Sample (2021/12, sheet `Şirket-Co.`, row **384**):

| Spreadsheet field | Source meaning | Value for SASA |
|---|---|---|
| `Kod (BIAS Code)` | ticker | `SASA` |
| `Şirket (Company)` | issuer display title | `SASA POLYESTER` |
| `K/KO (C/UC)` | consolidated/nonconsolidated classification | `K`, verify legend before harmonizing |
| `Finansal Tablo (Financial Statement)` | filing's **actual financial statement announcement day**, as presented in the Excel table | **2022-02-25** |
| `FR Son Gönderme Tarihi (Deadlines)` | regulatory **latest submission deadline**, not the actual release | **2022-03-11** |
| `Şirketin Duyurduğu Planlanan KAP'ta Açıklama Tarihi` | company-disclosed **planned** announcement day, not actual release | blank for sample |

SASA KAP original consolidated annual statement for 2021 is notice **1004314**, published on **2022-02-25** at **07:26:37** (timestamp timezone still to be confirmed). The year/quarter is **reporting period**, while the statement publication is later. KAP source: https://www.kap.org.tr/tr/Bildirim/1004314 . Exact date agrees with XLSX; XLSX is **only date-granular** and cannot verify time or revisions.

Sheet structure commonly includes categories such as `Şirket-Co.`, `Nitelikli-Qualified`, `Yatırım Krlş.-Investment Co`, `PYŞ-Portfolio M.C.`, `İşlemGörmeyenŞirketler`, and a deadline rules sheet `SonGönderimTarihleri`. Duplicate tickers may legitimately occur for consolidated/unconsolidated filings; never deduplicate solely by symbol.

## Scientific time-series use and guardrails

- **Never** map `FR Son Gönderme Tarihi` or `Planlanan KAP'ta Açıklama Tarihi` into `published_at`. These are not actual published notices.
- `Finansal Tablo` can corroborate a **calendar day** of a report. It is not sufficient to construct intraday point-in-time history: match issuer, fiscal period, consolidated status, immutable KAP notice index and original release timestamp/corrections.
- Dated capital changes, 2021-10-01 XK100 eligibility and issuer history cannot be inferred from this metadata.
- The official financial statements are **still required**: for each study year and period, use the `Finansal Tablolar` form's **İndir** button, not the independent `Finansal Rapor Tarihleri` link.
- Only records where full original announcement evidence and financial statement figures have been reviewed can graduate to `ieai.intake`, whose `available_at` convention prevents forward-looking leakage.
- The uploaded ZIP includes 2026 records; these are outside the currently configured 2021–2025 empirical study and must remain separated.

**Known limitation:** The presence of a company row here does not prove historical XK100 membership, reporting completeness, correctness of financial contents or that a specific notice was never corrected.

See [KAP_FINANCIAL_REVIEW_PIPELINE.md](KAP_FINANCIAL_REVIEW_PIPELINE.md) and [DATA_CONTRACT.md](DATA_CONTRACT.md).
