# KAP historical data intake (2021–2025) — source-controlled process

## 1. Official acquisition options and access boundaries

1. **KAP public website, Financial Statements tab:** https://www.kap.org.tr/tr — choose year (2021–2025) and period (3-month, 6-month, 9-month, annual). The official guide says **without selecting a company**, the selected year/period financial statements can be downloaded in one **RAR archive**. Official guide: https://www.kap.org.tr/tr/api/about/content-file/402832a195b3017d0195bd17e2e07e9a. Check the actual archive content first; downloading a list of financial tables is **not** equivalent to acquiring all underlying audit PDFs, notices, corrections and timestamps.
2. **KAP public original disclosure page:** https://www.kap.org.tr/tr/Bildirim/1004314; original Turkish audit PDF and English reference for the SASA sample were supplied by the user. Keep original publication date/time and attachments as evidence, even if a bulk table export is used for numeric extraction.
3. **KAP MKK API:** the `apigwdev` portal can retrieve synthetic test notices but returned **ER005** for real historical SASA notice 1004314. This is not proof of production coverage. The official MKK distribution notice says high-volume integrated access requires a Borsa İstanbul data distribution agreement, institution authorization and IP-based API key. Do **not** evade limits by scraping the website at scale. See https://www.kap.org.tr/tr/api/about/content-file/8a019492945fbe080194b26d8bed4873.

**Research start:** XK100 began on **2021-10-01** (official Borsa İstanbul). The first usable report at 2021-10-01 was published **before that date**, not the 2021 annual report. Accordingly acquire earlier available snapshots, 2020/2021 opening-period material and issuer changes before claiming point-in-time eligibility. See https://www.borsaistanbul.com/en/index/xk100.

## 2. Offline pilot verification (no network, no credentials)

Keep local originals outside Git (do not rename):
- `SASA SPK 31.12.2021.pdf`
- `ENGLISH-SASA SPK 31.12.2021.pdf`
- `1004314.pdf`

The repository contains `docs/evidence/sasa_2021_pilot/offline_source_manifest.json` (the original files' SHA-256), and `observed_facts.csv` (29 source observations with 1-based PDF page references and original units). The verifier is deliberately **not** an extractor of unknown accounting values: it checks exact printed numeric occurrence, file integrity, original source units and arithmetic identities.

```sh
python -m pip install -r requirements.txt -r requirements-acquisition.txt
python -m ieai.kap_pdf_evidence \
  --pdf-dir "/path/to/source-pdfs" \
  --manifest docs/evidence/sasa_2021_pilot/offline_source_manifest.json \
  --observations docs/evidence/sasa_2021_pilot/observed_facts.csv \
  --output "/path/to/new/audit_sasa_2021.json"
```

- **Fail closed:** wrong SHA, missing PDFs, invalid page/value, duplicate observation, bad source/date/scale or accounting identity mismatch causes failure. Existing output is never overwritten.
- **Always unreviewed:** even successful validation reports `classification_decision=UNKNOWN`, `approved_for_empirical_screening=false`, `research_dataset_complete=false`.
- Numeric text presence on a page does not confirm account-label mapping. Human review of nearby caption and note is essential.
- Arabic decimal dots vs Turkish thousands separators are disambiguated by raw integer fields in the ledger; all monetary values have multiplier **1000 TRY**, share counts are independent `shares` units.
- For another company, build a new versioned manifest, source observations and original PDF hashes. Never copy SASA facts into a different issuer.

## 3. Classification decisions requiring an approved, versioned rulebook

| Question | SASA evidence | Current action |
|---|---|---|
| Financial debt, denominator total assets | Bank loans 9,004,412; convertible bond 2,822,264; leases 172,196; total assets 22,194,163 (all in 1,000 TRY) | Compute both lease-inclusive and lease-exclusive **scenarios**, never declare formal compliance or choose a policy by default |
| Interest-bearing assets | Cash 2,170,396 includes term deposits 1,239,597; financial investments 3,132 are identified as blocked deposits in Note 4 | Avoid double counting; classify earning status, restricted deposits, receivables and derivatives under the actual approved standard |
| Noncompliant revenue | Interest income 20,567 (Note 23); interest-support income 32,077 (Note 20); finance income also includes exchange differences | Neither total finance income 1,189,517 nor all FX differences may be automatically counted as impermissible; review the numerator/denominator definitions |
| Income source activity | Polyester manufacturer | Manufacturing sector alone is not an attested complete business-activity review |
| Issued shares | Paid-in capital 1,120,000 (thousand TRY), 112bn nominal shares of 0.01 TRY | Resolve nominal-lot vs price quotation and dated corporate-action changes before `shares.csv` |
| Historical index eligibility | No XK100 initial membership evidence from this SASA report | Never substitute company membership in KAP or inclusion in BIST 30 for XK100 membership |
| Currency and time | Original 2021 TFRS report published 2022-02-25; TMS 29 later versions possible | Preserve original and restated variants separately. Verify publication timezone; apply decision timing only after review |

**Safety gate:** existing `ieai.intake.compile_facts` demands 7 full financial fields with independently reviewed `activity_pass`, `other_criteria_pass`, source SHA and timestamp before research graduation. No automatic approval occurs.

## 4. Reproducible batch intake workflow

1. Select **one year and one period** on the KAP public website and use its documented archive download feature. Do not construct undocumented endpoints or write a high-volume scraping client.
2. Keep the downloaded original RAR byte-identical with SHA-256, date/time retrieved and source-page URL. Extract with a trusted local RAR tool such as 7-Zip into a new directory, without running embedded programs.
3. For each relevant report, record `issuer, symbol, fiscal_period_end, notice_id, publication_timestamp, consolidation, currency, unit, filename, sha256, note/row/page`. An archive without disclosure timestamps **does not automatically produce point-in-time facts**.
4. Cross-check sampled or all selected relevant records with original disclosure notice (including corrected/replaced versions), classify conflicting versions and map account subtotals. Bank/insurance/participation banks require sector-specific mapping; do not force corporate industrial debt taxonomy on them.
5. Only after reviewed historical XK100 universe, all required source accounting fields and dated share events are available, create an intake ledger and run existing `compile-intake` then `audit-coverage`. Keep price/capital basis aligned. Separate actual Turkish FF3 and FF5 required.
6. Mark gaps for an issuer/period explicitly (missing report, blocked attachment, license restriction, no disclosure timestamp, corrected report, ambiguous asset/revenue classification). Do not substitute `0`, duplicate later years or calculate from published later restatements without point-in-time labels.

## 5. Scientific status

This workflow proves the software can validate **one** historical annual document and supports scalable **offline processing of authorized bulk exports**, not a completed 2021–2025 empirical panel. BIST XK100 universe snapshots, publication metadata/corrections, capital-action and price units, sector-specialized mappings, KAP production rights and Turkish FF3/FF5 remain open.

**No user secrets or full original PDF attachments are stored in GitHub.**


## 6. Inventory official bulk RAR/ZIP exports locally

After downloading from KAP **through its documented UI** and extracting the archive safely with 7-Zip, keep the original archive unchanged. This inventory records exact bytes for every supported file but **does not** call any KAP site/API, extract archives itself or treat filenames as issuer/date proof.

```sh
python -m ieai.kap_archive_inventory \
  --archive "/safe/path/KAP-2021-FY.rar" \
  --extracted-dir "/safe/path/KAP-2021-FY-extracted" \
  --year 2021 --period FY \
  --output "/safe/path/new/kap_2021_FY_inventory.json"
```

Period values: `3M, 6M, 9M, FY, ALL`. The `.rar` extension is only an illustrative filename; use the actual one produced by KAP. File types supported by inventory are PDF, XML, CSV, XLS, XLSX, TXT, JSON, ZIP and RAR. The inventory rejects symlinks, unknown extensions, oversized files and fake archive magic. It never executes embedded content.

**Next step after inventory:** verify report content and the public disclosure URL/timestamp for selected indexed companies before preparing reviewable source ledgers. If the download contains only tabular statements rather than audited PDFs, use the original disclosure pages to collect the notes needed for debt, interest and fiscal disclosure classification.

## 7. Current milestone and blockers

As of this pilot: `SASA_2021_DOCUMENT_INTEGRITY_VERIFIED` for the locally submitted source PDFs, **29** observed values with page evidence, basic borrowing/interest identities reconciled. This is an offline reproducibility milestone only.

Open: first XK100 2021-10-01 snapshot and historical continuity, per-issuer annual/quarterly report and timestamp/revision coverage, financial account treatment and approved Sharia classification rulebook, capital action / share bases, authorized scale of future downloads, separate Turkey FF3/FF5 sources. Do not set empirical dataset complete while any remain.
