# Product Requirements

## Purpose

Records what the platform must do and the qualities it must preserve. Requirements are candidates until the developer signs off. This document defines behaviour, not design; architecture decisions are recorded separately as ADRs.

## Requirement conventions

- IDs are stable: `FR-nn` for functional, `NFR-nn` for non-functional, `DR-nn` for deferred.
- Status values: **Proposed**, **Approved**, **Deferred**. Everything below is Proposed.
- No requirement becomes Approved without explicit developer sign-off. Approval is per requirement, not per document.

## Functional requirements

### Fixture and competition discovery

| ID | Requirement | Rationale | Status |
| --- | --- | --- | --- |
| FR-01 | Enumerate competitions by country, confederation, season and stage. | Analysis needs competition context; a match is not an isolated event. | Proposed |
| FR-02 | Discover fixtures with UTC kickoff, venue, home/away designation and competition stage. | Every downstream calculation depends on correct fixture identity and orientation. | Proposed |
| FR-03 | Track fixture status transitions: scheduled, postponed, rescheduled, abandoned, awarded. | Status changes alter which matches are valid training or evaluation data. | Proposed |
| FR-04 | Record source and retrieval timestamp for every fixture record. | Provenance is required to resolve conflicts and reproduce outputs. | Proposed |
| FR-05 | Report coverage per competition and season, including known gaps. | Users must see the boundary of what the platform knows. | Proposed |

### Historical data

| ID | Requirement | Rationale | Status |
| --- | --- | --- | --- |
| FR-06 | Store final scores with regulation, half-time, extra-time and penalty components separated. | Markets and models operate on specific periods; aggregate scores are ambiguous. | Proposed |
| FR-07 | Store match events with type, period, minute, team and player where available. | Event data supports context, validation and later feature work. | Proposed |
| FR-08 | Store lineups, roles and substitutions with source attribution. | Squad availability affects match interpretation and data quality. | Proposed |
| FR-09 | Store standings as dated snapshots with tie-break context. | Standings are time-dependent and cannot be reconstructed from a final table alone. | Proposed |
| FR-10 | Version corrections and retain the superseded record. | Silent overwrites destroy auditability and make regressions untraceable. | Proposed |

### Team and match intelligence

| ID | Requirement | Rationale | Status |
| --- | --- | --- | --- |
| FR-11 | Compute team metrics over explicit, configurable windows with stated definitions. | Window choice materially changes the result and must be visible. | Proposed |
| FR-12 | Maintain separate home and away baselines per team and competition. | Home advantage is not constant; pooled baselines distort comparison. | Proposed |
| FR-13 | Adjust comparisons for opponent strength and schedule. | Raw totals reward weak schedules and penalise strong ones. | Proposed |
| FR-14 | Estimate attack and defence strength with an uncertainty range. | Point estimates conceal instability, especially in short windows. | Proposed |
| FR-15 | Present match context: rest days, fixture congestion, travel and competition priority. | Context explains deviations that form alone cannot. | Proposed |
| FR-16 | Flag squad availability concerns when lineup or injury data is missing or stale. | Absence of data must not be read as a fully available squad. | Proposed |

### Probability estimation

| ID | Requirement | Rationale | Status |
| --- | --- | --- | --- |
| FR-17 | Produce a scoreline probability matrix for each analysed fixture. | One coherent object can derive mutually consistent markets. | Proposed |
| FR-18 | Derive selected markets from that matrix using documented formulas. | Derived markets must agree with each other and with the matrix. | Proposed |
| FR-19 | Attach uncertainty or interval information to each published estimate. | A probability without a reliability statement invites overreading. | Proposed |
| FR-20 | Record model version, parameters, input data window and timestamp for every prediction. | Reproducibility and post-hoc evaluation require a complete record. | Proposed |
| FR-21 | Enforce consistency constraints across related markets before publication. | Contradictory published probabilities are a correctness defect. | Proposed |
| FR-22 | Abstain when inputs fail minimum evidence gates. | A forced estimate under thin data is worse than no estimate. | Proposed |

### Prediction evaluation

| ID | Requirement | Rationale | Status |
| --- | --- | --- | --- |
| FR-23 | Persist predictions before kickoff with an immutable timestamp. | Post-hoc editing invalidates evaluation. | Proposed |
| FR-24 | Score predictions against results using proper scoring rules and calibration measures. | Accuracy alone hides confidence errors and rewards lucky extremes. | Proposed |
| FR-25 | Report evaluation by market, competition, confidence band and model version. | Aggregate scores mask systematic weaknesses in subgroups. | Proposed |
| FR-26 | Detect performance drift and flag models for review. | Silent degradation is the default failure mode of deployed models. | Proposed |

### Explanation

| ID | Requirement | Rationale | Status |
| --- | --- | --- | --- |
| FR-27 | Explain the dominant factors behind each estimate in domain terms. | Users need reasons, not only numbers, to judge an estimate. | Proposed |
| FR-28 | State assumptions, data limitations and the effect of missing inputs. | Explanations that omit limits overstate confidence. | Proposed |
| FR-29 | Distinguish observed values from model-inferred values in explanations. | Conflating measurement with inference is a reliability failure. | Proposed |

### Data quality and provenance

| ID | Requirement | Rationale | Status |
| --- | --- | --- | --- |
| FR-30 | Validate schema, ranges, referential integrity and cross-field consistency on ingest. | Errors are cheaper to contain at the boundary than downstream. | Proposed |
| FR-31 | Resolve team, competition and venue identity across sources with an auditable mapping. | Ambiguous names corrupt joins and historical comparability. | Proposed |
| FR-32 | Maintain an end-to-end provenance chain from source record to published output. | Provenance supports debugging, licensing compliance and user trust. | Proposed |
| FR-33 | Quarantine conflicting records instead of selecting one silently. | Automatic conflict resolution hides data defects. | Proposed |
| FR-34 | Measure and publish completeness and freshness per dataset. | Quality claims must be based on tracked metrics, not assertion. | Proposed |

## Non-functional requirements

| ID | Requirement | Rationale | Status |
| --- | --- | --- | --- |
| NFR-01 | Given identical inputs, versions and parameters, calculations produce identical outputs. | Reproducibility is a precondition for evaluation and debugging. | Proposed |
| NFR-02 | Every published estimate exposes method version, data window and uncertainty. | Transparency is part of correctness for probabilistic output. | Proposed |
| NFR-03 | Interactive responses meet latency targets set per phase; targets are TBD until the data spike. | Premature latency commitments constrain design without evidence. | Proposed |
| NFR-04 | The system remains a modular monolith with documented module boundaries. | Operational simplicity is preferred until scale evidence justifies decomposition. | Proposed |
| NFR-05 | Secrets are managed outside source control; access follows least privilege. | Data-source credentials and internal data are sensitive. | Proposed |
| NFR-06 | Data-source licence terms, redistribution rights and attribution duties are recorded and enforced. | Unlicensed storage or redistribution creates legal and operational risk. | Proposed |
| NFR-07 | Ingestion, computation and evaluation emit structured logs, metrics and an audit trail. | Failures must be observable without reproducing them locally. | Proposed |
| NFR-08 | Models and data transformations have regression tests against fixed fixtures. | Undetected behaviour changes undermine calibration claims. | Proposed |
| NFR-09 | Personal data handling is minimised; no user accounts are required in early phases. | Collecting identity data creates obligations the product does not need yet. | Proposed |
| NFR-10 | Failure of one data source degrades coverage explicitly rather than silently. | Partial data presented as complete is worse than a visible gap. | Proposed |

## Explicitly deferred requirements

| ID | Requirement | Reason |
| --- | --- | --- |
| DR-01 | User accounts, preferences and saved analyses. | No validated need; adds security and privacy scope. |
| DR-02 | Web or mobile frontend. | Depends on a stable API and proven analysis outputs. |
| DR-03 | Live in-play predictions and streaming updates. | Requires latency, data quality and validation not yet established. |
| DR-04 | Payment, subscription and entitlement handling. | Monetisation is out of Phase 1 scope. |
| DR-05 | Public API with rate limits and developer keys. | Interface stability is unproven. |
| DR-06 | Additional sports. | Football-specific domain assumptions are not yet validated. |
| DR-07 | Automated model retraining in production. | Evaluation and rollback controls must exist first. |

## Open questions

- Which data sources and competition tiers are viable, given licensing, storage rights, coverage and historical depth? Licensing review required; UNVERIFIED.
- What minimum historical depth and sample size support stable strength estimates and the market evidence gates? To be determined by the data spike.
- Which uncertainty representation and abstention policy are appropriate per market and acceptable to users? Needs evaluation and user research.
- How should provider-specific xG differences be reconciled or disclosed? See [performance metrics](../football/performance-metrics.md).

## Traceability note

Each requirement will link to the ADRs that constrain it and to the phase plan that schedules it. ADRs live in `docs/decisions/`; phase status is tracked in `PROJECT_STATUS.md` and `memory/next-steps.md`. A requirement without an owner, an acceptance check and a phase assignment is not ready for approval. Requirement changes follow [scope](./scope.md) change control.
