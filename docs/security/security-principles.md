# Security Principles

## Purpose and scope

This document states the security principles future implementation must satisfy. No application code exists, so nothing here is a claim about current security posture. The scope covers services, ingestion pipelines, scheduled jobs, agent tooling, and documentation. Binding requirements are in [`../../rules/security-rules.md`](../../rules/security-rules.md); this document explains intent without duplicating them.

Security is a property of the evidence chain: if predictions can be altered, or provider credentials stolen, the product's core claim collapses regardless of model quality.

## Threat model summary

| Asset | Why it matters | Primary adversaries |
|-------|----------------|---------------------|
| Provider API keys and credentials | Theft causes cost, quota exhaustion, or account termination | Credential thieves, scrapers, malicious insiders |
| User data, if accounts are added | Privacy and legal exposure | Data thieves, abusers, accidental insiders |
| Prediction integrity | Tampered or silently edited predictions destroy auditability | Insiders, compromised services |
| Availability | Ingestion and analysis depend on scheduled access | Denial-of-service, quota exhaustion |
| Licensed data | Redistribution can breach provider terms | Scrapers, careless exports |

Assumed adversaries: external credential thieves, automated scrapers, abusers who exhaust quotas or endpoints, accidental insiders, and supply-chain attackers. This is a summary, not a completed threat model; a formal one is required before any public deployment.

## Secret management

- Never hardcode secrets in source, fixtures, notebooks, documentation, or agent prompts.
- `.env` files are excluded from version control. `.env.example` lists variable names and safe placeholders only.
- Keys are least-privilege and scoped to the minimum environment and capability.
- Each environment uses separate credentials; production keys never appear in development.
- Rotation is planned and possible without code changes; a leaked key is revoked before investigation continues.
- Secrets never appear in logs, error messages, stack traces, screenshots, or prompts sent to LLMs and external agents.

## Configuration practice

- Configuration is separated from code and validated at startup against a declared schema.
- Security-critical configuration fails closed: a missing secret or policy stops the service rather than degrading silently.
- Defaults are safe: deny by default, no debug mode in production, no accidental permissive CORS; environment-specific behaviour is explicit configuration, not hidden branches in code.

## Input validation and output encoding

- Validate at every trust boundary: public API requests, provider responses, uploaded files, webhooks, and agent inputs.
- Use schema validation with explicit types and allowed values; reject unknown fields where the source contract is strict.
- Where providers evolve, tolerate and record unknown fields rather than crashing, but never pass them through unvalidated.
- Encode output for its context. Provider strings must not reach HTML, SQL, shell, or logs without appropriate handling.
- Bound sizes: request bodies, payloads, pagination, and file uploads all have limits.
- Validation failures are logged with enough context to debug and without echoing sensitive values.

## Authentication and authorization

- Future user-facing features assume deny-by-default authorization.
- Authorization is checked server-side on every request; client-side hiding is not a control.
- Least privilege applies to users, services, and scheduled jobs alike.
- Do not implement home-grown cryptography or password hashing; use vetted, maintained libraries and follow their guidance.
- Administrative actions are separately authorized, rate-limited, and audited; session and token lifetimes are bounded and revocation is possible.

## Rate limiting and abuse prevention

- Provider quota is a protected resource: per-provider budgets, backoff, circuit breakers, and alerting before exhaustion.
- Public endpoints enforce per-identity and per-IP limits; expensive analysis endpoints are stricter than static reads.
- Bulk export is authenticated, authorized, and rate-limited; there is no unauthenticated bulk download.
- Scraping patterns are detected and blocked at the edge.
- Rate limiting complements authorization and never substitutes for it.

## Secure logging

- Logs are structured and include correlation identifiers for runs and requests.
- Redaction is allowlist-based where feasible: fields are included deliberately, not filtered by pattern after the fact.
- Never log secrets, tokens, credentials, full provider payloads containing keys, or unnecessary personal data.
- Retention is bounded and documented; access is restricted, and security-relevant events (authentication failures, authorization denials, key rotation, configuration changes) are logged separately from application noise.

## Dependency and supply-chain security

- Lockfiles are committed and dependency versions are pinned.
- New dependencies require review for maintenance status, licence, and necessity; no unreviewed installs.
- Automated vulnerability scanning belongs in CI once CI exists.
- Install scripts and binaries from unverified sources are not executed; updates are applied deliberately, with tests, rather than by blind auto-upgrade.

## Data privacy and licensing

- Collect the minimum personal data required for a stated purpose; do not collect speculative fields.
- Provider terms govern storage, derived use, and redistribution; attribution is displayed where required.
- Do not republish licensed data beyond its terms, including through exports or model outputs that reconstruct it.
- Retention and deletion paths are defined before personal data is collected.
- Access to licensed or personal data is role-restricted and logged.

## Prediction integrity as a security concern

- Prediction records are append-only and tamper-evident. The mechanism (hash chain, signature, or external timestamp) is not yet chosen.
- Each record is timestamped at creation and bound to model, calibration, and input snapshot versions.
- Corrections create new records with a supersedes link; historical predictions are never edited.
- Public claims must map to a stored record; an unverifiable number is not published.
- Integrity checks are part of evaluation, not only of storage.

## Incident response outline

1. Detect and record the event with timestamps and affected assets.
2. Triage severity and classify: credential exposure, data integrity, availability, or privacy.
3. Contain: revoke keys, disable endpoints or jobs, isolate affected data.
4. Eradicate the cause, verify containment, and recover from known-good state; reconcile data affected during the incident.
5. Notify according to legal and contractual obligations.
6. Hold a post-mortem with concrete follow-up actions and owners; roles, contact paths, and notification timeframes are not yet defined.

## Pre-implementation security checklist

- [ ] Threat model documented for the component and its data flows.
- [ ] Secrets externalised; `.env.example` contains names only.
- [ ] Configuration schema validated; secure defaults; fail-closed behaviour.
- [ ] Every trust boundary has validation and contextual output encoding.
- [ ] Authorization deny-by-default and enforced server-side.
- [ ] Rate limits defined for public and provider-facing calls.
- [ ] Logging redacted, structured, and retention-bounded.
- [ ] Dependencies pinned, reviewed, and scanned.
- [ ] Provider licence and attribution obligations implemented.
- [ ] Prediction records append-only and integrity-checked.
- [ ] Incident contacts and key-revocation procedure written down.

## Related documents

- [`../../rules/security-rules.md`](../../rules/security-rules.md)
- [`../../rules/data-rules.md`](../../rules/data-rules.md)
- [`../data/data-provenance.md`](../data/data-provenance.md)
- [System overview](../architecture/system-overview.md) and [architecture principles](../architecture/architecture-principles.md)
- [`../../AGENTS.md`](../../AGENTS.md)
