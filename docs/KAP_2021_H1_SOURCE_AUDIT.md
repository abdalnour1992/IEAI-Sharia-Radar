# KAP 2021 half-year reports — user-uploaded audited source catalog

**Evidence analyzed 2026-10-13.** Original archive `FinancialTable 6 aylik.zip`, SHA-256 `8ebb059e19d31f56ea23c4eaafe383761a8fac2ec2160e3dec656d32da0afc7d`. Original user archive stays outside GitHub. No public API or unapproved bulk crawler was used.

## What passed

- **554** HTML-as-XLS member reports in ZIP. All 554 have internally consistent `Yıl=2021`, `Periyot=2` (six months), `Bildirim Tipi=FR` and parseable `Gönderim Tarihi` plus a supported currency unit and a filename containing the disclosure index.
- **513** distinct ticker/symbol **strings**, not a number of historically XK100-listed companies.
- **308** consolidated; **246** nonconsolidated.
- Monetary source unit: **408 TL**, **145 1.000 TL**, **1 1.000.000 TL**. Monetary source figures require the exact multiplier; don't mix these formats.
- Taxonomy first balance sheet: **446 general**, **50 banking**, **38 finance**, **10 insurance**, **8 holding**, **2 participation banking**. **108** specialized templates are not handled by the limited standard industrial-company account selector.
- **2,848** source-account extraction **candidates**, all **unreviewed**: `total_assets` 446, `balance_sheet_sources` 446, `shareholders_equity` 446, `cash_equivalents` 446, `short_term_borrowings_line` 378, `long_term_borrowings_line` 382, `revenue` 304.
- Of 446 general-balance reports with matched top-line fields, **446/446** pass the identity `total_assets == balance_sheet_sources`. This checks numerical parse consistency, **not** every financial account's correct classification.

## Critical information-timing result

- **538/554** reported publication timestamps before **2021-10-01**: candidates for the starting information set.
- **16/554** were dated **2021-10-01 or later**; none can be used for a decision before that day, even though their *fiscal period* is 2021/06. Of the 16, **8** were published during October–December 2021, **8** during January–June 2022.
- Publication-year totals: **546 in 2021**, **8 in 2022**. First timestamp in archive **2021-07-12 02:06:22**, last **2022-06-09 23:51:49**. Source timezone and possible post-release corrections must be independently confirmed. Do **not** treat the period-end 2021-06-30 as an announcement date.
- The conservative offline `ieai.kap_temporal_catalog` accepts per-report source hashes and original timestamps and classifies strictly **prior-day** reports as `PRE_CUTOFF_CANDIDATE`. Reports with a publication day equal to the study start are excluded from the *opening-date* snapshot. It is **not** verification of intraday timing or XK100 membership.

### SASA control example

`SASA_955229_2021_2.xls` (original notice https://www.kap.org.tr/tr/Bildirim/955229), source-published `06.08.2021 07:47:00`, consolidated, original unit `1.000 TL`:

| Exact template item | 2021/06 raw value (1,000 TRY) |
|---|---:|
| `TOPLAM VARLIKLAR` | 13,522,606 |
| `Nakit ve Nakit Benzerleri` | 384,677 |
| `TOPLAM ÖZKAYNAKLAR` | 3,533,710 |
| `Hasılat` (six-month cumulative) | 5,258,100 |
| `Kısa Vadeli Borçlanmalar` (single line only) | 2,217,591 |
| `Uzun Vadeli Borçlanmalar` (single line only) | 3,842,957 |

Do **not** call those two borrowing lines the fully defined interest-bearing debt ratio; other current financial debt, leases and convertible instruments require detailed account mappings and approved standards. SASA is a source consistency example only; no verified historical XK100 membership.

### Overlap with 2021 annual filing catalog

- Annual: 575 reports, 538 symbol **strings**.
- Half-year: 554 reports, 513 symbol **strings**.
- Shared: **493**, interim-only: **20**, annual-only: **45**. These string differences do **not** establish additions/deletions from the XK100 index; issuer-code changes, membership/corporate events and filing population need independent reconciliation.

## Reproducible and non-promoting processing

The code in `ieai/kap_bulk_html.py` from PR #16 already reads both 2021 period 2 and period 4 archives. With the unmodified, authorized user download available **locally**:

```sh
python -m ieai.kap_bulk_html \
  --archive "/local/FinancialTable 6 aylik.zip" \
  --output-dir "/local/kap-2021-h1-source"
```

The resulting `filing_catalog.csv` is a **non-certified source index**. With a separately generated annual catalog, run the date gate:

```sh
python -m ieai.kap_temporal_catalog \
  --catalog "/local/kap-2021-h1-source/filing_catalog.csv" \
  --catalog "/local/kap-2021-fy-source/filing_catalog.csv" \
  --as-of 2021-10-01 \
  --output-dir "/local/new/kap-cutoff-review"
```

This preserves KAP disclosure ID, issuer/symbol string, publication day, original file SHA-256, and the conservative pre-cutoff bucket. It **does not promote** financial facts to `ieai.intake.compile_facts`, or mark `membership`, `research_dataset_complete` or source rights as verified. Keep two original archives privately.

## Next priorities

1. Obtain **2021/09** (nine-month) and **2021/03** exports for later decisions in the October–December 2021 training window and pre-start history. A Q3 report first made public **after** 1 October cannot be backfilled on 1 October.
2. Obtain 2022–2025 quarter/year exports and original corrections/annexes, and independently reconcile 2021/06 announcement-date workbook error documented in `KAP_FINANCIAL_REPORT_ANNOUNCEMENT_DATES.md`.
3. Collect official 2021-10-01 XK100 constituent history and its changes, corporate-action/share basis, factor models and sector-specific financial templates.
4. Approve a source-dated standard for liabilities, interest-bearing assets and incompatible revenues; cash and all finance income cannot be classified blindly.
5. Verify publication timestamp timezone, data reuse license, and per-value financial statement location before certifying research use.

**Status: HALF_YEAR_REPORTS_STRUCTURALLY_VERIFIED / FINANCIAL_LABELS_UNREVIEWED / ASOF_OPENING_CANDIDATES_IDENTIFIED / HISTORICAL_INDEX_MEMBERSHIP_UNKNOWN.**
