# Non-Goals

## Purpose

Records what the product deliberately will not be, so that scope decisions have a stable reference. Each non-goal includes a rationale and a revisit trigger. Absence from this list does not imply inclusion; see [scope](./scope.md).

## Explicit non-goals

| Non-goal | Rationale | Revisit trigger |
| --- | --- | --- |
| Live-score portal | Live scores reward speed over correctness and create uptime obligations unrelated to analysis quality. | A validated user need that cannot be met by scheduled pre-match analysis, plus a data and latency plan. |
| Football news or content site | Editorial publishing is a different product with different accuracy and moderation risks. | None foreseen; would require a separate product decision. |
| Generic LLM chatbot | Free-form generation cannot guarantee traceable, reproducible, calibrated answers. | A constrained interface that cites stored evidence and passes evaluation. |
| Guaranteed tips or fixed accuracy claims | Football outcomes are uncertain; a fixed accuracy promise is false by construction. | Never. This is a permanent constraint, not a deferral. |
| Betting facilitation or odds advice | Advising stakes or selections creates regulatory, ethical and liability exposure unrelated to analysis. | Never under the current product definition. |
| Social or community features | Moderation, identity and engagement incentives conflict with evidence-first analysis. | A separate product with its own governance. |
| Mobile apps early | Native clients add release and platform scope before the analysis is proven. | Stable API and demonstrated demand. |
| Microservices early | Distributed complexity is unjustified before scale or team boundaries require it. | Measured scaling or organisational constraint documented in an ADR. |
| Multi-sport early | Football-specific modelling assumptions do not transfer cleanly to other sports. | Football analysis validated and a sport-specific design approved. |
| Real-time in-play prediction early | In-play models need low-latency data, rapid recalibration and different validation. | Data latency, coverage and evaluation infrastructure proven. |
| User-generated data | Unverified contributions undermine provenance and reproducibility. | A moderation and verification design that preserves provenance. |
| Premature branding | Naming, palette and identity before the product is defined consume effort and bias decisions. | Product scope and audience validated; design work approved. |

## How non-goals are revisited

- A non-goal is changed only by an ADR in `docs/decisions/` and explicit developer approval.
- The ADR states which evidence changed, what the new scope is, and what is being given up.
- Permanent constraints (guaranteed accuracy, betting advice) are not reopenable through the normal ADR path; they require a product redefinition.
- A non-goal may be clarified without approval when the clarification removes ambiguity, but it may not be weakened to permit previously excluded work without an ADR.

## Permanent constraints and deferrals

| Class | Examples | Change path |
| --- | --- | --- |
| Permanent | No fixed accuracy promise; no betting advice or odds; no fabricated data | Product redefinition, not a routine ADR |
| Deferred until evidence exists | Live scores, mobile apps, social features, microservices, in-play prediction | ADR with the revisit trigger satisfied |
| Excluded by current design | News publishing, generic chatbot, multi-sport | Separate product decision with its own scope |

Conflating these classes causes two errors: treating a permanent constraint as a scheduling problem, or treating a deferral as a permanent ban and missing a justified change.

## Applying non-goals in review

Before accepting a proposal, answer these questions in the review record:

- Does it create a user-facing promise the platform cannot evaluate?
- Does it add an output channel before the underlying analysis is validated?
- Does it shift effort from evidence to presentation or engagement?
- Is it justified by competitor presence rather than user need or measured quality?
- Does it require data the platform is not licensed or able to verify?

## Warning signs of scope creep

- A request framed as "just a small addition" that introduces a new user type, data source or output channel.
- Live data appearing in a pre-match feature "for convenience".
- A UI request arriving before the underlying estimate is evaluated.
- A model feature justified by an anecdote rather than a measured baseline improvement.
- A provider added because it is available, not because it passes the source criteria.
- Engagement metrics proposed as success measures for analysis quality.
- A non-goal being treated as "not yet" rather than "not this product".
- Requirements expanding during implementation without a corresponding scope record.

## Related documents

- [Vision](./vision.md)
- [Scope](./scope.md)
- [Requirements](./requirements.md)
- [Product principles](./vision.md#core-philosophy)
