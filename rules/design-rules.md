# Design Rules

Binding rules for any future interface, chart, report, or visual identity. Nothing here
authorises UI implementation in Phase 1.

The product must read as a professional sports-analytics instrument: dense, calm, legible,
and honest. It must never read as a generated template.

---

## V1 — No AI-slop patterns

MUST NOT use:

- blue-to-purple gradients or purple/pink "AI" branding;
- decorative gradients, mesh backgrounds, aurora effects;
- animated background blobs, floating particles, or ambient loops;
- unnecessary animated backgrounds or parallax;
- excessive glassmorphism or stacked translucent panels;
- excessive rounded cards, cards inside cards, pills for every label;
- random neon glows, coloured shadows, or "cyber" accents;
- generic AI dashboard layouts (hero + three floating stat cards + gradient CTA);
- fake charts, fabricated statistics, or placeholder data presented as real;
- icons that merely repeat their label;
- animation without a usability purpose;
- AI marketing copy ("unlock insights", "supercharge", "revolutionary", "seamless").

## V2 — Information before decoration

- Every element must serve a user decision.
- If removing an element does not reduce understanding, remove it.
- Hierarchy: fixture context → headline probability → evidence → model detail → provenance.
- Decoration may not compete with data for attention.

## V3 — Probability honesty

- A displayed percentage is a calibrated probability estimate, not a confidence score.
- Always show: the market, the estimate, the timestamp, and the uncertainty context.
- Never show false precision; one decimal at most unless justified.
- Never imply certainty through size, colour, or copy.
- When evidence is insufficient, show an explicit abstention state instead of a number.
- Never present a model output as a guarantee or a tip.

## V4 — Data visualisation integrity

- No truncated axes on probability or count charts.
- No 3D, perspective distortion, or area tricks.
- Consistent scales across compared entities; label axes and units.
- Show uncertainty: intervals, sample size, or a low-confidence marker.
- Never encode meaning by colour alone; pair with shape, label, or position.
- No pie charts beyond two categories; no dual axes without strong justification and labels.
- Sparklines require a baseline and a defined window.
- Missing data is shown as missing, never as zero or an empty gap that reads as zero.
- Descriptive and predictive metrics are visually distinguished.
- No chart without a title that states what it shows and over what window.

## V5 — Typography and density

- Restrained type scale; no decorative display faces for data.
- Tabular numerals for aligned statistics.
- Sufficient line height for dense reading; no all-caps body text.
- Hierarchy through weight, size, and spacing before colour.
- Long team and competition names must not break layout; test them.

## V6 — Colour

- No final palette in Phase 1.
- Use semantic roles: surface, raised surface, primary/secondary text, border, data ink,
  selection, positive/negative (validated), warning, critical.
- Semantic colours are never decorative.
- Dark mode is designed, not inverted; verify contrast independently.
- Verify colour-blind safety for every data encoding.

## V7 — Accessibility

- Target WCAG 2.2 AA.
- Verify contrast; do not assume it.
- Full keyboard operation with visible focus.
- Charts have text alternatives (summary table or accessible description).
- No hover-only information; touch and keyboard must reach it.
- Respect `prefers-reduced-motion`.
- Errors, empty states, and abstentions are announced to assistive technology.
- Touch targets are adequately sized.

## V8 — Motion

- Motion only for state change, loading, or spatial continuity.
- No ambient, looping, or attention-seeking animation.
- No counting animations that delay reading a number.
- Reduced-motion preference is honoured everywhere.

## V9 — Copy and tone

- Label precisely: market, estimate, window, source, timestamp.
- Say "estimated probability", not "chance of winning" or "prediction confidence".
- State uncertainty and insufficiency plainly.
- No urgency, hype, or gambling-adjacent language.
- No claims of accuracy that have not been measured and documented.

## V10 — Consistency

- One component per job; no near-duplicate variants.
- Consistent spacing scale, alignment, and interaction patterns.
- Consistent state language: loading, stale, partial, missing, abstained, error.
- Visual consistency is verified across screens and data states.

## V11 — Provenance is reachable

- Every displayed number has a path to its source, fetch time, and model version.
- Provenance may be collapsed, but not hidden entirely.
- Attribution required by data licences is displayed as specified.

## V12 — No premature identity

- No logo, brand name, palette, or typeface selection without developer approval.
- Design explorations must be labelled as proposals.
- Do not let a visual identity decision block analytical correctness.

---

## Review checklist

- [ ] No V1 pattern present.
- [ ] Every element has a function.
- [ ] Probabilities show market, timestamp, and uncertainty context.
- [ ] Charts have honest axes, labels, units, and uncertainty.
- [ ] Missing and abstained states are explicit.
- [ ] Contrast and keyboard access verified.
- [ ] Reduced motion respected.
- [ ] Copy is precise, not promotional.
- [ ] Provenance is reachable.
- [ ] No brand or palette invented.

## Enforcement

The UX designer applies these rules and reviews all proposals. The orchestrator rejects
deliverables that violate V1, V3, or V4. Exceptions require developer approval and a recorded
rationale.

## Related documents

- `docs/design/design-principles.md`
- `.opencode/skills/anti-ai-slop-design/SKILL.md`
- `rules/engineering-rules.md`
