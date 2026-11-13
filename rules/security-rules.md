# Security Rules

Binding security requirements for all future implementation and for current repository
practice. No secret, no exception.

---

## SEC1 — No secrets in the repository

MUST NOT commit or write into any tracked file:

- API keys, tokens, passwords, connection strings;
- private keys or certificates;
- session secrets or signing keys;
- provider credentials in notebooks, examples, tests, or documentation.

Practice:
- `.env` is ignored by version control.
- `.env.example` contains variable **names** and non-functional placeholders only.
- Secrets are provided through the environment or a secret manager.
- If a secret is exposed: revoke it first, then investigate, then record the incident. Do not
  rely on deleting the commit.

## SEC2 — Secrets never leak through output

- Do not log secrets, authorization headers, cookies, or full request URLs containing keys.
- Do not include secrets in error messages, stack traces, or crash reports.
- Do not send secrets to LLM providers or third-party services.
- Redact provider payloads before sharing diagnostics.
- Review screenshots and terminal output before attaching them to a report.

## SEC3 — Least privilege

- One credential per service and environment; no shared superuser keys.
- Provider keys use the minimum scope and are rotated on a schedule and on exposure.
- Database roles are scoped to the owning module.
- Agent permissions are least privilege (see `rules/ai-usage-rules.md`).
- Administrative access requires stronger authentication and an audit trail.

## SEC4 — Validate every trust boundary

Trust boundaries include: provider → ingestion, client → API, app → database, app → LLM,
and any future file upload.

- Validate schema, type, range, size, and encoding.
- Use allowlists for enums and formats; reject unknown fields where the contract is strict.
- Enforce payload size and nesting limits.
- Treat provider data as untrusted.
- Never interpolate untrusted input into shell commands, SQL, or prompts without structured
  handling.

## SEC5 — Authentication and authorization (future)

- Use established libraries and standards; never invent cryptography or session formats.
- Deny by default; grant the minimum role.
- Separate authentication from authorization.
- Store passwords only with a modern adaptive hash.
- Define token/session expiry and revocation explicitly.
- Rate-limit authentication attempts and monitor for credential stuffing.

## SEC6 — Rate limiting and abuse prevention

- Protect provider quotas with internal budgets, queueing, backoff, and threshold alerts.
- Protect public endpoints with per-IP and per-account limits and request size caps.
- Cap total retry attempts; do not amplify load during an outage.
- Apply cost-based limits to expensive operations (batch scoring, explanations).
- Document burst behaviour, not just average limits.

## SEC7 — Secure logging and monitoring

- Structured logs with correlation identifiers.
- Redact secrets and personal data.
- Log decisions and failure reasons, not full licensed payloads.
- Bound retention and restrict access.
- Protect log integrity; alerts must be actionable.

## SEC8 — Dependencies and supply chain

- No unreviewed installation.
- Pin versions and commit lockfiles once implementation begins.
- Review licences for compatibility with data-provider terms.
- Monitor advisories; patch on a defined cadence.
- Prefer fewer dependencies, especially in the data and prediction path.
- Do not execute install scripts from untrusted sources.

## SEC9 — Privacy and licensing

- Minimise personal data; collect only what the product needs.
- Define retention and deletion for any personal data.
- Treat provider licensing as a security constraint: unauthorised redistribution is a breach.
- Display required attribution.
- Confirm ambiguous terms before publishing data.

## SEC10 — Prediction integrity

- Store predictions immutably with a pre-kickoff timestamp.
- Hash or sign the prediction record and its inputs so later edits are detectable.
- Restrict write access to the prediction store; evaluation is read-only.
- Keep model, feature, and data versions with every prediction.
- Keep the explanation layer separate; text must not alter the numeric probability.
- Audit any access that modifies or deletes prediction records.

## SEC11 — Fail closed

- Missing required configuration stops startup; it does not fall back to a default credential
  or insecure mode.
- Authorization failures deny access.
- Validation failures quarantine data; they do not pass it through.
- Debug modes are never enabled in exposed environments.

## SEC12 — Incident response

Define before production:
- who is notified and how;
- how credentials are revoked and rotated;
- how affected data and predictions are identified;
- how the incident is recorded without exposing secrets;
- how the root cause is fixed and regression-tested.

## SEC13 — Honest security claims

- Do not describe the project as "secure".
- State which risks are mitigated, which are accepted, and which are unknown.
- Security review is not a penetration test.
- A passing checklist does not prove absence of vulnerabilities.

---

## Pre-implementation checklist

- [ ] `.env` ignored; `.env.example` contains names only.
- [ ] No secret in any tracked file or log.
- [ ] Required configuration fails closed.
- [ ] Every boundary has validation rules.
- [ ] Authorization is deny-by-default.
- [ ] Rate limits protect provider quotas and public endpoints.
- [ ] Logs are redacted and retention-bounded.
- [ ] Dependencies are reviewed and pinned.
- [ ] Predictions are immutable and tamper-evident.
- [ ] Residual risks are documented.

## Enforcement

The security reviewer audits designs and changes. Any finding rated High or Blocker prevents
acceptance until resolved or explicitly accepted by the developer with a recorded rationale.

## Related documents

- `docs/security/security-principles.md`
- `.opencode/skills/security-basics/SKILL.md`
- `rules/engineering-rules.md`
- `rules/data-rules.md`
- OWASP ASVS and Cheat Sheet Series (consult current official versions)
