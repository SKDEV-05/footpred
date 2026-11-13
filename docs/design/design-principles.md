# Design Principles

## Purpose and scope

These principles govern future product interfaces: match analysis pages, probability views, evidence tables, and any exported reports. Nothing is being implemented in Phase 1, and no brand, palette, logo, or component library has been chosen. The constraints are binding on later design work; visual rules in [`../../rules/design-rules.md`](../../rules/design-rules.md) remain authoritative where they overlap.

Design is subordinate to evidence: an interface succeeds when a reader can judge what the model claims, how uncertain it is, and why — not when it looks impressive in isolation.

## Mandatory anti-AI-slop constraints

### Never

- Blue-to-purple gradients, or purple/pink branding associated with generic AI products.
- Decorative gradients used as backgrounds, borders, or text fills without informational purpose.
- Animated background blobs, floating particles, or moving ambient shapes.
- Unnecessary animated backgrounds or autoplaying visual effects.
- Excessive glassmorphism, frosted panels, and translucent layers that reduce contrast.
- Excessive rounded cards, pill-shaped containers, and nested card-on-card layouts.
- Random neon accents, glow effects, and coloured shadows.
- Generic AI dashboard layouts: metric tiles with invented sparklines, a chat panel as the primary interface, or a grid assembled without hierarchy.
- Fake charts, placeholder statistics, or sample numbers presented as real.
- Decoration without function, and animation without a usability purpose.

These patterns signal generated output and erode trust in a product whose only differentiator is evidence quality. A professional analysis tool is judged by the legibility of its data, not by ambient motion.

## Required direction

The visual language should read as professional sports analytics: dense but calm, typographic, and data-led. Concretely:

- strong information hierarchy, with one obvious reading order per screen, and clear, restrained typography;
- meaningful data visualisation tied to a stated question, with consistent spacing and alignment across views;
- readability at typical laptop widths, with accessibility treated as a design input rather than a later audit;
- restrained colour used to encode meaning, functional interaction with visible state, and visual consistency across fixtures, models, and evidence views.

## Information hierarchy for an analysis product

| Level | Content | Presentation intent |
|-------|---------|---------------------|
| 1. Fixture context | Competition, teams, kickoff, venue, status | Establish what is being analysed before any number |
| 2. Headline probabilities | 1X2 or relevant market estimates with uncertainty | One clear claim, never detached from its uncertainty |
| 3. Evidence | Form, historical matchups, availability, key statistical drivers | Show what moved the estimate |
| 4. Model detail | Method, inputs, assumptions, calibration, limitations | Available to readers who want to audit |
| 5. Provenance | Data sources, versions, timestamps, known gaps | Reachable from every prediction |

A probability must never appear without accessible uncertainty context and a path to the model identity. Lower levels may be collapsed by default, but never removed.

## Data visualisation rules

- Probability and score charts start at a true zero baseline; never truncate an axis to exaggerate a difference.
- No 3D charts, perspective distortion, or decorative depth.
- Comparable charts share scales; do not rescale one panel to make a point.
- Show uncertainty explicitly: intervals, calibration context, or sample size as appropriate.
- Label units, denominators, and time windows on the chart itself.
- Remove chartjunk: no redundant gridlines, drop shadows, gradients, or ornamental icons.
- Encode with colour-blind-safe palettes and a redundant channel (shape, label, or pattern).
- Never imply causation from correlation; annotate observational comparisons as such.
- Distinguish "no data" from "zero" visually and in text, consistent with [data-quality.md](../data/data-quality.md).

## Typography and density

- Use tabular numerals for statistics so columns align and digits do not shift.
- Keep a small, fixed type scale; hierarchy comes from size, weight, and spacing, not from many styles.
- Use a professional sans-serif for interface text; no decorative display fonts, no novelty numerals.
- Analysts scan tables: favour compact rows with clear separation over oversized hero sections on data pages, and keep line length readable so density does not become cramped.
- Numbers carry units and precision appropriate to their uncertainty; do not display spurious decimal places.

## Accessibility

- Target WCAG 2.2 AA for all future interfaces.
- Meet contrast requirements for text and for data marks, not just for labels.
- Never rely on colour alone to convey an outcome or state.
- Support full keyboard operation with visible focus indicators and logical order.
- Respect `prefers-reduced-motion`; provide a non-animated equivalent for every transition.
- Provide text alternatives and accessible data tables for charts, plus a short screen-reader summary of the finding.
- Support zoom and reflow without loss of content or function.

## Colour policy

No palette is chosen in Phase 1. Colour is defined by semantic role, not by brand:

| Role | Purpose |
|------|---------|
| Neutral surface | Backgrounds and containers; must not compete with data |
| Data ink | Marks, lines, and values; highest legibility priority |
| Accent | Selection, focus, and interactive affordance; used sparingly |
| Warning | Degraded data, staleness, or partial coverage |
| Critical | Errors, invalid states, or integrity failures |

Positive and negative outcomes are not assigned fixed hues until a palette passes contrast and colour-blind checks. Any categorical encoding for teams or outcomes is validated per chart rather than reused blindly across contexts.

## Motion policy

Motion exists only to explain a state change: expansion, transition between related views, or progress on a known waiting action. It is short, interruptible, and disabled under reduced-motion. It never carries meaning that is unavailable in static form, never delays reading, and never runs for decoration.

## Component discipline

- Components derive from shared tokens and semantic roles, not ad-hoc values; one component per concept, with variants documented rather than forked silently.
- Every data component defines loading, empty, partial, stale, error, and success states, plus default, hover, focus, active, and disabled interaction states.
- No component ships without an accessibility pass and a data-state review; charts are components with documented assumptions, not one-off drawings.

## Review checklist

- [ ] No forbidden decoration from the "Never" list.
- [ ] Reading order matches the five-level hierarchy.
- [ ] Probability shown with uncertainty and a path to provenance.
- [ ] Axes honest, scales consistent, units labelled; missing data distinguished from zero.
- [ ] Contrast and colour-blind checks pass.
- [ ] Keyboard, focus, and reduced-motion behaviour verified.
- [ ] No fabricated charts, metrics, or sample results; loading, empty, partial, stale, and error states designed.
- [ ] Typography and spacing consistent with existing views.

## Related documents

- [`../../rules/design-rules.md`](../../rules/design-rules.md)
- [`../../rules/engineering-rules.md`](../../rules/engineering-rules.md)
- [`../data/data-quality.md`](../data/data-quality.md)
- [`../data/data-provenance.md`](../data/data-provenance.md)
- [`../../AGENTS.md`](../../AGENTS.md)
