# MKK KAP VYK — development access and authentication status

Evidence: user-provided portal screenshots and KAP VYK OpenAPI 3.0.3, reviewed 2026-10-13.

## Verified

- The registered `IEAI-Sharia-Radar` application is subscribed to the free KAP VYK plan (6 calls/minute). This does not establish production archive access.
- The OpenAPI security scheme is `basicAuth` (`type: http`, `scheme: basic`) for the documented `/members` and other GET endpoints.
- The advertised test/development server is `https://apigwdev.mkk.com.tr/api/vyk`. Its `dev` designation is not evidence of production coverage.
- Portal documentation says `GET /auth/generateToken?apiKey=...` is used for **production**, and its tokens expire after 24 hours. It explicitly says test users need not perform this token-acquisition operation.
- **Observed connectivity blocker:** opening `https://apigwdev.mkk.com.tr/api/vyk/members` directly in a browser triggered a native HTTP Basic username/password prompt, and the portal account login did not authenticate. This is consistent with the OpenAPI security scheme. **No-token-generation does not mean anonymous API access.** A successful authorized test call has **not** been observed.

## Correct next action

1. Cancel the browser's HTTP Basic prompt. Do not reuse portal website credentials on the API host merely because the browser asks for them.
2. Return to the signed-in MKK API Portal > `KAP Veri Yayın Servisleri` > `API Specification` and inspect `Yetkilendir` (Authorize). Record **field names only**, never values of username/password, API keys, tokens, or Authorization headers.
3. Determine from the portal documentation whether the test gateway expects a dedicated test username and token, gateway credentials, an app API key, or authorized access through the portal's test console. Do not guess credential placement.
4. If portal instructions do not identify a supported authentication method, use the portal's KAP support channel to ask for the authorized sandbox authentication procedure and production archival eligibility.
5. Only after access is confirmed, perform **one** credential-safe, read-only test. The existing `python -m ieai.kap_probe --output <new-directory>` is an **unauthenticated connectivity diagnostic only**; an HTTP 401 or 403 is expected if the gateway challenges anonymous access. It is not an authenticated data importer and should not be recommended as proof of subscription success.

## Scientific limitations

- No KAP production archive has been retrieved through this application.
- Historical disclosure range, publication timestamps, attachment completeness and license permissions remain unverified.
- Preserve raw source data, SHA-256, provenance, original publication timestamps and reporting revisions once legitimately acquired; never promote development fixtures to research evidence.
- Avoid bulk calls or any rate-limit workaround.

See [KAP_VYK_OPENAPI_ASSESSMENT.md](KAP_VYK_OPENAPI_ASSESSMENT.md).
