---
name: Security Basics
description: Apply secret management, input validation, authentication/authorization principles, rate limiting, secure logging, dependency security, privacy, and prediction-integrity controls. Use for any design touching credentials, user input, or published predictions.
---

# Security Basics

## Objective

Prevent credential loss, data tampering, and integrity failures. Security is a property of the
whole system, including prompts, logs, configuration, and prediction records.

## Activation

Use when handling secrets, external inputs, user accounts, public endpoints, provider
credentials, logs, dependencies, or prediction records.

## Required context

- Assets and their sensitivity (provider keys, raw data, predictions, user data).
- Trust boundaries and who can call what.
- Deployment model (local, single host, public).
- Legal/licensing obligations attached to the data.

## Workflow

1. **List assets** and classify sensitivity.
2. **Map trust boundaries**: provider → ingestion, client → API, app → database, app → LLM.
3. **Threat-model each boundary**: who can send what, and what is the worst outcome.
4. **Apply prevention at the boundary**: validation, authentication, least privilege.
5. **Design detection**: logging, metrics, alerts without sensitive payloads.
6. **Define response**: revocation, rotation, containment, disclosure.
7. **Record residual risk**; never claim a system is "secure".

## Detailed procedures

### Secrets

- Never hardcode keys, tokens, passwords, or connection strings in source, docs, tests, or
  prompts.
- Keep `.env` out of version control; commit `.env.example` with variable **names** and safe
  placeholders only.
- One credential per environment and per service; least privilege.
- Rotate on exposure and on a schedule; revoke old keys after rotation.
- Never log secrets, authorization headers, full request bodies, or provider URLs that
  contain keys.
- Do not paste secrets into LLM prompts or research notes.
- If a secret is exposed: revoke first, then investigate, then record the incident. Do not
  "clean up" git history without approval.

### Configuration

- Fail closed: missing required configuration stops startup rather than silently using a
  default credential or an insecure mode.
- Separate development, test, and production configuration.
- Validate configuration at startup and report missing names, never values.
- Do not enable debug modes in exposed environments.

### Input validation

- Validate at every trust boundary: provider payloads, API requests, query parameters, webhook
  bodies, uploaded files (future).
- Use allowlists for enums and formats; reject unknown fields where the contract is strict.
- Enforce size and depth limits (JSON nesting, array length, payload size).
- Validate types, ranges, and referential integrity before persistence.
- Never interpolate untrusted input into shell commands, SQL, or LLM prompts without
  structured handling.
- Treat all provider data as untrusted: it can be malformed, oversized, or malicious.

### Authentication and authorization (future)

- Prefer established libraries and standards; never invent cryptography or session formats.
- Deny by default; grant the minimum role.
- Separate authentication (who) from authorization (what).
- Protect against credential stuffing with rate limits and monitoring.
- Store passwords only with a modern adaptive hash; never reversible encryption.
- Design session/token expiry and revocation explicitly.
- Admin actions require stronger authentication and an audit trail.

### Rate limiting and abuse

- Protect provider quotas: internal budgets, queueing, backoff, and alerts at thresholds.
- Protect public endpoints: per-IP and per-account limits, request size caps, timeouts.
- Use token-bucket or leaky-bucket limits; document burst behaviour.
- Do not let retries amplify load; cap total attempts.
- Consider cost-based limits for expensive computations (batch scoring, explanations).

### Secure logging

- Structured logs with correlation IDs.
- Redact secrets, tokens, cookies, and personal data.
- Log decisions and failure reasons, not full payloads.
- Bound retention; restrict access; protect log integrity.
- Never log a full provider response containing licensed data for longer than necessary.

### Dependencies and supply chain

- No unreviewed installs; record why a dependency is needed.
- Use lockfiles and pinned versions once implementation begins.
- Review licences for compatibility with the product's licensing obligations.
- Monitor advisories; patch on a defined cadence.
- Prefer fewer dependencies, especially in the data and model path.

### Privacy and licensing

- Minimise personal data; do not collect what the product does not need.
- Treat provider data licensing as a security constraint: unauthorised redistribution is a
  breach, not a feature.
- Record attribution requirements and enforce them in the UI.
- Define retention and deletion for any personal data (future user accounts).

### Prediction integrity

- Store predictions immutably with a pre-kickoff timestamp.
- Hash or sign the prediction record and its inputs so later edits are detectable.
- Restrict write access to the prediction store.
- Keep an audit trail of model and input versions.
- Separate the explanation layer from the numeric output so text cannot silently change a
  probability.

## Quality checklist

- [ ] No secret in source, logs, docs, tests, or prompts.
- [ ] `.env.example` lists names only.
- [ ] Required configuration fails closed.
- [ ] Every boundary validates input.
- [ ] Authorization is deny-by-default.
- [ ] Rate limits protect provider quotas and public endpoints.
- [ ] Logs are redacted and retention-bounded.
- [ ] Dependencies are reviewed and pinned (when implementation begins).
- [ ] Predictions are immutable and tamper-evident.
- [ ] Residual risks are documented.

## Common failure patterns

- API key committed in a notebook or example script.
- Secrets echoed in error messages or stack traces.
- Trusting provider data without schema validation.
- Home-grown token or crypto schemes.
- Unlimited retries against a quota-limited API.
- Logging full request bodies with credentials.
- Treating a licence violation as a legal afterthought.
- Mutable predictions that can be "improved" after the result.

## Expected outputs

- Threat notes per boundary.
- Secret and configuration standards.
- Validation rules for each input.
- Logging and rate-limit specifications.
- Prediction-integrity design.
- Residual-risk register.

## Sources and references

- `docs/security/security-principles.md`
- `rules/security-rules.md`
- OWASP Application Security Verification Standard and Cheat Sheet Series (consult the current
  official versions; do not rely on remembered checklists).

## Limitations

This skill provides engineering guidance, not legal advice or a penetration test. Compliance
with data-protection law and provider contracts must be confirmed by the developer and, where
necessary, qualified counsel.
