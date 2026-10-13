# MKK KAP VYK — development access and authentication status

Evidence: user-provided portal screenshots and KAP VYK OpenAPI 3.0.3, reviewed 2026-10-13.

## Verified

- The registered `IEAI-Sharia-Radar` application is subscribed to the free KAP VYK plan (6 calls/minute). This does not establish production archive access.
- The OpenAPI security scheme is `basicAuth` (`type: http`, `scheme: basic`) for the documented `/members` and other GET endpoints.
- The advertised test/development server is `https://apigwdev.mkk.com.tr/api/vyk`. Its `dev` designation is not evidence of production coverage.
- Portal documentation says `GET /auth/generateToken?apiKey=...` is used for **production**, and its tokens expire after 24 hours. It explicitly says test users need not perform this token-acquisition operation.
- **Initial authentication challenge:** opening the dev `/members` URL directly in a browser triggered a native HTTP Basic username/password prompt, and portal website login did not authenticate. No-token-generation does not mean anonymous API access.
- **SUCCESSFUL FIRST AUTHENTICATED PORTAL TEST (2026-10-13, user screenshot):** following authorization of the subscribed application through the portal's `Yetkilendir` UI, its built-in API console returned `200 OK` for `GET https://apigwdev.mkk.com.tr/api/vyk/members`; screenshot shows ~283 ms, ~141.3 KiB and a nonempty JSON array containing `id`, `title`, `stockCode`, `memberType`, `kfifUrl`. This is proof of **development console access only**. The response bytes, source timestamp and original authentication headers were not captured in an independently reproducible research archive, and therefore no source SHA-256 or complete empirical coverage is attested.

## Next low-volume, portal-console checks

1. Keep credentials, API keys, tokens and Authorization headers private; a key was visible in an earlier screenshot and should be rotated before production use.
2. In the authorized portal API Specification, test `GET /lastDisclosureIndex` **once** to verify disclosure metadata access and the response format. It returns the latest disclosure identifier, **not a historical date boundary**.
3. Then use `GET /disclosures` with the mandatory numeric-string `disclosureIndex` from an authentic, selected notice. The API specifies up to 50 notices per page and optional filters `disclosureTypes` (e.g., `FR`), `disclosureClass`, and `companyId`; it does not document date-range filtering. Avoid guessing old identifiers or crawling historic pages by brute force.
4. Only for one authorized returned index, test `GET /disclosureDetail/{disclosureIndex}?fileType=data`, retaining its `time`, `year`, `period`, `consolidation`, `relatedDisclosureIndex`, `attachmentUrls` and `flatData` fields for schema validation. Do not assume development response examples are production originals.
5. Confirm environment-specific scope, license, timestamp timezone and attachment download access before any bulk historical import.

## Scientific limitations

- No KAP **production** archive was retrieved through this application as of this update.
- Historical 2021–2025 financial disclosure coverage, publication timestamps, attachment completeness and redistribution/retention permissions remain unverified.
- The existing `python -m ieai.kap_probe --output <new-directory>` is an **unauthenticated connectivity diagnostic** and can still return 401. Do not run it as a substitute for the proven authenticated portal-console path or assume it proves access to research data.
- Preserve raw source bytes, SHA-256, UTC retrieval timestamps, official publication timestamps, reporting revisions and units when legitimately acquired. Never promote development fixtures to empirical research evidence.
- Avoid bulk calls or any rate-limit workaround.

See [KAP_VYK_OPENAPI_ASSESSMENT.md](KAP_VYK_OPENAPI_ASSESSMENT.md).

## Verified portal-console disclosure chain — 2026-10-13

**User-provided screenshots (no actual API response archives; no secrets saved):**

| Request (dev gateway through portal) | Result | Evidence limitations |
|---|---|---|
| `GET /lastDisclosureIndex` | HTTP 200; `lastDisclosureIndex: "1231017"`, 236 ms | Development index, not production maximum |
| `GET /disclosures?disclosureIndex=1231017` | HTTP 200; one `DUY` / `DUY` record for `companyId=51`; `subReportIds=["oda-90000_TestNotification"]` | Explicit **test notification**, not financial data |
| `GET /disclosureDetail/1231017?fileType=html` | HTTP 200; 87.3 KiB, 54 ms; sender KAMUYU AYDINLATMA PLATFORMU, subject `Test Notification` | Detail-chain functionality only; no verified 2021–2025 company financial history |

An initial missing-auth `401` for `/disclosures` resolved after portal reauthorization. Repeated request errors cannot be ascribed to provider outage without evidence.

**Next falsifiable historical-archive check:** The public KAP website lists a **real financial report** for SASA POLYESTER SANAYİ A.Ş., disclosure index `1004314`, sent **2022-02-25 07:26:37**, year `2021`, type `FR`, with 2021 annual financial reports and attached PDF documents. Official public source: https://www.kap.org.tr/tr/Bildirim/1004314. Subject to portal authorization, perform **one** `GET /disclosureDetail/1004314?fileType=html` on the dev console. If 200 with matching real issuer/date/report, distinguish true historical coverage from synthetic fixtures; if 404 or empty, this only limits the *dev gateway* and does not establish the production archive's status. In either case, avoid broad indexing until production permissions and history are confirmed.

**Important:** Do not infer SASA belongs to XK100 from this choice. This one company is solely a public financial-report API compatibility test.


## Historical report negative test (user portal screenshot, 2026-10-13)

- In the authorized **development** API console, `GET /disclosureDetail/1004314?fileType=html` returned **HTTP 400**, JSON `{"code":"ER005","message":"Bildirim bulunamadı. Disclosure not found."}`, 69 ms. Request path and `fileType` were correctly supplied; this is **not** an HTTP 401 authentication failure.
- Independently, the **public production KAP website** visibly serves the original historical record [Disclosure 1004314](https://www.kap.org.tr/tr/Bildirim/1004314): SASA POLYESTER SANAYİ A.Ş., published 2022-02-25 07:26:37, type FR, annual 2021 financial report, consolidated financial statements, currency presentation **1,000 TRY**, with two original PDF attachments.
- The distinction establishes that an **existing public historical KAP website record is absent from the queried development API dataset**. It does **not** prove whether authorized production API access includes the same historical record.
- **Do not use date 2021-12-31 as public availability**; 2022-02-25 07:26:37 is the source-reported publication timestamp (verify timezone for point-in-time transformation). Preserve the original nominal unit multiplier.
- SASA is an **illustrative technical sample**, not evidence of past XK100 constituents.

### Safe next direction

1. Stop testing randomly selected historical IDs on the development gateway. Verify the **production gateway URL and subscription/authorization requirements** in the account's official instructions; do not assume that the documented test token mechanism grants production rights.
2. Meanwhile, original historical reports are accessible via KAP's public website. Assess permitted manual downloads and original PDF collection as an **alternative source path**, recording checksum, disclosure publication timestamp, fiscal period, accounting units, consolidation and corrections for every observation. Do not bulk scrape without permission.
3. Before any real research import, verify license conditions, source availability and completeness, and distinguish data collected from production website versus API sandbox. The blocker for G03/G04 remains open; the software interface smoke-test milestone is complete.

