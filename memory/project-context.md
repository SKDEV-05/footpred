# Project Context

Stable summary of what this project is. Detailed product documentation lives in
`docs/product/`; this file is the short version for humans and agents.

## Product

**Football Intelligence Platform** — a global football match-analysis and intelligence
platform.

The product helps users understand football matches through reliable statistics, historical
performance, mathematical analysis, and carefully evaluated probability estimates. It is not a
live-score site, a news site, a generic chatbot, or a tipster service.

## Core objective

Make football analysis **correct, reproducible, and honest about uncertainty**:

- trustworthy data with traceable provenance;
- explicit probability estimates derived from stated mathematical assumptions;
- predictions timestamped before kickoff and evaluated against actual results;
- explanations that state why a number exists and when evidence is insufficient.

The platform must never promise guaranteed outcomes or a fixed accuracy figure.

## Target users

- **Serious fans** who want to understand a match beyond the result.
- **Analysts and semi-professionals** comparing teams, form, and context.
- **Researchers** evaluating model performance over time.
- **The internal team** building and auditing the models.

Users need evidence and transparent uncertainty, not confident assertions.

## Philosophy

**DATA FIRST · MATHEMATICS FIRST · RELIABILITY FIRST · PREDICTION QUALITY FIRST ·
USER EXPERIENCE SECOND · VISUAL DECORATION LAST.**

## Long-term direction

Capabilities, in rough order of dependency:

1. Fixture and competition discovery across countries and tiers.
2. Historical results, events, and statistics collection.
3. Team and match context modelling (home/away, form, availability).
4. Attack, defence, and strength estimation with opposition adjustment.
5. Mathematically grounded probability estimates for defined markets.
6. Prediction evaluation against actual results (calibration, proper scoring rules).
7. Uncertainty and abstention when evidence is insufficient.
8. Explanations grounded in verified inputs.
9. Continuous evaluation and model improvement.

Prediction markets under consideration: 1X2, double chance, over/under goals, both teams to
score, correct score, first-half goals — each only when data quality supports it.

## Architectural stance

Modular monolith plus background worker first. One relational database. Raw payloads retained.
No microservices, message broker, or distributed infrastructure without measured need.

## Constraints

- Small team; cost-sensitive.
- Data quality and licensing are gating constraints, not afterthoughts.
- No LLM in the numerical prediction path.
- Every prediction must be reconstructable from stored inputs.

## Related documents

- `docs/product/vision.md`
- `docs/product/requirements.md`
- `docs/product/scope.md`
- `docs/product/non-goals.md`
- `docs/architecture/system-overview.md`
- `memory/decisions.md`
