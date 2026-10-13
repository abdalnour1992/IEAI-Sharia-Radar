# MKK KAP VYK — non-secret development connectivity probe

The portal's **Nasıl Kullanılır** and **Token Alma Servisi** documentation (observed 2026-10-13) clarifies the ambiguous OpenAPI Basic authentication scheme:

- **Production (canlı):** use the account's authorized API key with \`GET /auth/generateToken?apiKey=...\`. Issued tokens last 24 hours. The header mechanics for authenticated production requests remain unverified and must not be guessed.
- **Development/test:** the documentation explicitly says that users **do not perform token acquisition** for test. The published OpenAPI advertises \`https://apigwdev.mkk.com.tr/api/vyk\`. The development environment must not be assumed to contain complete production or historical disclosures.
- A sample API key and sample token appeared in the portal's documentation screenshot. They are **not** stored, copied or used in this repository. If a real key was displayed, rotate it.

## Safe smoke test (optional)

Run only after confirming that the account permits this development request:

\`\`\`sh
python -m ieai.kap_probe --output outputs/kap-dev-smoke-20261013
\`\`\`

- Exactly one \`GET /api/vyk/members\` request to the development host; no token, no retries, no hidden pagination, no bulk collection, no redirects, and no production access.
- A successful JSON response is archived with SHA-256 and acquisition UTC time; it is **always marked DEVELOPMENT / UNREVIEWED / NOT EMPIRICAL**.
- 401, 403, 404, 429, network denial and invalid responses are diagnostic outcomes; they must not be bypassed. An inaccessible development server does not prove production is unavailable.
- Choose a NEW local output directory. Do **not** commit the response or any credentials. Do not print secrets.
- The portal's free plan shows a maximum of **6 calls/minute**. This one-request probe makes one call; no bulk collector is enabled.

Before any historical production import, obtain confirmation of authorized archival use, the proper token header and production host, and test a tiny authenticated sample with account credentials held only in a local secret store. Keep actual financial evidence distinct from development fixtures and subject to the research data contract.

See [KAP_VYK_OPENAPI_ASSESSMENT.md](KAP_VYK_OPENAPI_ASSESSMENT.md).
