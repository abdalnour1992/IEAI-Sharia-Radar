# Evidence-led closure register — 2026-10-12

Scope: **XK100**, 2021-10-01–2025-12-31. This register records verifiable discoveries and *remaining* dependencies; it is not a completed company-level dataset. No membership, accounting amount, factor, or timestamp is inferred.

## A. Verified official facts and their limits

| ID | Verified official fact | Source | Consequence |
|---|---|---|---|
| S01 | BIST Participation 100 (XK100), 30, 50, All, and Sustainability participation indices have calculated closing-price histories since 2021-10-01, and real-time publication began 2021-11-12. | https://www.borsaistanbul.com/endeksler/bist-pay/katilim | Back-calculated start-of-series values **do not** prove constituent names were publicly known as of October 1. Require original publication timestamps for opening membership. |
| S02 | Borsa İstanbul says its participation-stock selection used the TKBB advisory board share-issuance/trading standard. | https://www.borsaistanbul.com/duyuru/12747/borsa-istanbul-katilim-endeksleri-hesaplamaya-basliyor | Do not conflate present-day eligibility rules with historical rules. |
| S03 | The official April 25, 2022 announcement documents changes for 2022-05-01 to 2022-09-30 across participation indices. | https://www.borsaistanbul.com/duyuru/12885/01052022-30092022-donemi-icin-bist-katilim-endeksleri-kapsaminda-yer-alacak-paylarda-degisiklik-yapilmistir | Periodic changes are not a verified opening snapshot and should only be applied after source, index, event and trading-session validation. |
| S04 | Borsa İstanbul describes period-start 10% constituent weight limits and intra-period reset if weights exceed 15%. | https://www.borsaistanbul.com/endeksler/bist-pay/katilim | Index methodology and weighting must be distinguished from investable portfolio rules; check historically applicable rule revisions. |

## B. Existing validated acquisition evidence

- Acquisition CI: https://github.com/abdalnour1992/IEAI-Sharia-Radar/actions/runs/38296962529
- Immutable receipt within repository: [official-acquisition-20261012.json](evidence/official-acquisition-20261012.json)
- 1,066 equity sessions each for XK100 and XU100 price and TRY total-return series, covering 2021-10-01 to 2025-12-31.
- Eight periodic change attachments are **unreviewed**; 432 rows are *candidates*, including 24 reserves; these do not assert constituents.
- Benchmarks and market/risk-free proxy are available. Local FF3/FF5 series and company-level point-in-time history are **not** acquired.

## C. Gap-specific acceptance gates

| Gap | Current classification | Evidence needed before closing | Prohibited shortcut |
|---|---|---|---|
| G01 Opening composition | BLOCKED_EXTERNAL_DATA | Complete XK100 opening list + as-published time + security identifiers + document checksum | Using a modern list, XKTUM, or a retrospectively announced snapshot |
| G02 Exceptional continuity | PENDING_MANUAL_SOURCE_REVIEW | Complete contemporaneous exceptional changes, delistings, ticker/ISIN mappings; independent reconciliation to periodic lists | Promoting reserves, assuming no mid-period changes |
| G03 Financial and participation eligibility | BLOCKED_EXTERNAL_DATA | Original KAP disclosure timestamp, period, consolidation status, original/revised accounting versions, unit and statement-note location for each input | Replacing interest-bearing debt with total liabilities; zero-filling or backdating revisions |
| G04 Capital and share basis | BLOCKED_EXTERNAL_DATA | Point-in-time issued share counts, effective dates, corporate actions, split/lot and price-volume adjustment basis | Using free float in place of issued shares; applying actions on announcement day |
| G05 Local factors | BLOCKED_EXTERNAL_DATA | Reproducible Turkish daily FF3/FF5 methodology/data (distinct SMB constructions) over required windows, with licensing and audit trail | Substituting foreign factors, extrapolating a 2022-ending series, zeros |

## D. Operational close-out checklist

1. Request the **opening XK100 list** and historical constituents for each effective date from Borsa İstanbul / licensed data contact; request availability/announcement timestamps separately from value dates.
2. Review the eight official change PDFs in original form. Filter **XK100-specific** main-list additions/removals; record effective first trading day, ticker/ISIN and source page. Preserve reserve rows only as reserves.
3. Reconcile all 130 indexed candidate notices by category (XK100, other index, methodological, exception, duplicate). No 130-notice blanket-approval.
4. Request original KAP reports, revision histories, KAFİF and listed-company capital events via authorized bulk/licensed route; archive exact retrieval SHA-256 and public availability evidence.
5. Obtain the local factor library via authorized institution or request an updated export through 2025; alternatively construct with a licensed broad-market historical universe and preregistered factor methodology.
6. Populate reviewed ledgers and run:
   ```sh
   python -m ieai.cli compile-intake --source data/reviewed-source-ledgers --output data/compiled-new
   python -m ieai.cli audit-coverage --dataset data/compiled-new
   ```
7. Verify *both* complete observable coverage and the independent validity of each source and methodology before allowing a research run to be described as empirical.

## E. Delivery/request package

Turkish academically scoped request draft: [DATA_REQUEST_TR.md](../DATA_REQUEST_TR.md). The draft is **not sent**, licenses not accepted, and procurement not authorized. Its requested minimum history includes 2019–2020 financial warm-up and 2021 trading warm-up, where applicable.

**Decision:** The official index benchmark and market-control acquisition step is closed; G01–G05 are **not closed**. This document adds independent documentary support, an audit-ready checklist and explicit closure gates, not invented missing research data.
