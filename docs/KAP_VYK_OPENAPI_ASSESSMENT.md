# KAP VYK API — OpenAPI feasibility assessment (2026-10-13)

**Source:** user-provided official portal export `apispec.json`, OpenAPI 3.0.3, title `KAP VYK API`, version `0.0.1-apinizer-337-07a3583`. No credentials, account tokens or private user data are stored here.

## Verified contract

- Advertised server: `https://apigwdev.mkk.com.tr/api/vyk`. **Development-named host**; do not assume production access or production historical coverage.
- Authentication scheme: HTTP Basic (`basicAuth`). Portal UI shows username/token; exact credential semantics must be established via its documentation, not guessed.
- `GET /disclosures`: mandatory numeric-string `disclosureIndex`; optional `disclosureTypes`, `disclosureClass`, `companyId`. Documented to return the first **50** notices from the supplied starting index. No date-start or date-end filter is documented. Verify pagination semantics and response shape empirically on a small authorized sample.
- `GET /disclosureDetail/{disclosureIndex}`: mandatory `fileType=html|data`; optional `subReportList`. May include `time`, `year`, `period`, `consolidation`, `relatedDisclosureIndex`, `relatedStocks`, `attachmentUrls`, `flatData`, `presentation`, and block status.
- `GET /downloadAttachment/{id}`: attachment identifiers are obtained from the detail response, not guessed. The OpenAPI response is described as binary under `application/json`; confirm actual Content-Type and byte format before archival/decoding.
- `GET /members`: KAP company/member identities, `stockCode`, `kfifUrl`; **not** XK100 historical membership.
- `GET /memberSecurities`: security identities and current capital-related fields. These are not certified *historical* issued shares.
- `GET /memberDetail/{id}`: company details, possible `publishDateTime`.
- `GET /caEventStatus?processRefId=...`: status **for known process identifiers**, not a capital-event history feed.
- `GET /blockedDisclosures`: notices/attachments blocked up to present; archive completeness must respect blocks.
- Other: `GET /lastDisclosureIndex`, `GET /funds`, `GET /fundDetail/{id}`.

## Scientific implementation requirements

1. Before bulk acquisition, verify application subscription, production versus development environment, authorized historical scope, response shape, and retention/license conditions. Portal's free plan (per account screenshot) indicates **6 requests/minute**, not an entitlement to unlimited historical scraping.
2. Test at most a handful of authorized requests: one company list, one selected disclosure page, one detail with `fileType=data`, one attachment if permitted. No credential/token in GitHub, logs, reports, screenshots or chat.
3. Store raw bytes and SHA-256, source endpoint and sanitized query, UTC retrieval time, returned publication `time` (with verified timezone), disclosure index, revision linkage and original attachments. Preserve raw/normalized versions separately.
4. Do **not** assign `available_at` from the period-end date. Map source publication timestamp to the portfolio's after-close decision convention; preserve revision relationships and TMS 29 prior versions.
5. Classify blocked, missing or unsupported records as explicit gaps. Require human-reviewed financial labels and monetary units before `source_facts.csv` graduation. Do not treat company-list membership as index membership.
6. Integrate into existing `ieai.intake` and `ieai.coverage` without changing empirical readiness flags until completeness and origin are verified.

## Remaining five research gaps

This API **may substantially reduce G03 financial disclosures and G04 capital events**, and provide company/ISIN context to support G02. It **does not directly establish** an XK100 initial constituent snapshot (G01), complete historical capital amounts (G04), or Turkish FF3/FF5 factors (G05).

**Status: SPEC_REVIEWED / AUTHORIZED_LIVE_TEST_PENDING / HISTORICAL_COVERAGE_UNPROVEN.**
