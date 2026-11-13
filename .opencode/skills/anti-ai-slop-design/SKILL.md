---
name: Anti-AI-Slop Design
description: Prevent generic AI-template visual design. Enforces a professional sports-analytics language, honest data visualisation, accessibility, and a strict ban on gradients, blobs, glassmorphism, neon, fake charts, and decorative motion. Mandatory for any interface research or design.
---

# Anti-AI-Slop Design

## Objective

Make the product look and behave like a serious sports intelligence tool, not a generated
landing page. Every pixel must serve comprehension. If an element does not help the user
understand a match, remove it.

## Activation

Mandatory whenever an agent researches, specifies, reviews, or designs any future product
interface, chart, dashboard, report, or visual identity. Also use when reviewing copy that
sounds like generic AI marketing.

## Required context

- The user decision the screen supports.
- The data that genuinely exists (and what is missing).
- The uncertainty attached to every number.
- Accessibility requirements and target devices.

## Workflow

1. **State the decision** the interface must support.
2. **Inventory the real data**: available, uncertain, missing.
3. **Order information** by decision value, not visual convenience.
4. **Choose representations** that are honest about scale and uncertainty.
5. **Apply the constraints** below before aesthetics.
6. **Check accessibility** (contrast, keyboard, focus, reduced motion, non-visual alternatives).
7. **Review against the forbidden list**; remove anything decorative.
8. **Test degraded states**: missing data, low sample, extreme probabilities, long team names,
   narrow viewports.

## Detailed procedures

### Forbidden — do not propose, design, or accept

- Blue-to-purple gradients, purple/pink "AI" branding, or any gradient used as identity.
- Random decorative gradients, mesh backgrounds, aurora effects.
- Animated background blobs, floating particles, or looping ambient motion.
- Unnecessary animated backgrounds or parallax.
- Excessive glassmorphism, frosted panels, or translucent layers stacked for effect.
- Excessive rounded cards; pills for everything; cards inside cards.
- Random neon glows, coloured drop shadows, or "cyber" accents.
- Generic AI dashboard layouts: hero + three floating stat cards + gradient CTA.
- Fake charts, fabricated statistics, placeholder data presented as real.
- Decorative icons that repeat the label; illustrations that add no information.
- Animation without a usability purpose (entrance animations, hover bounce, counting-up
  numbers that delay reading).
- AI-slop copy: "unlock insights", "supercharge your analysis", "revolutionary", "seamless",
  "game-changing", "delve into".

### Required direction

- Professional sports-analytics visual language: dense but calm, data-forward, editorial
  restraint.
- Strong information hierarchy: match context → headline probabilities → supporting evidence →
  model detail → provenance.
- Clear typography with tabular numerals for statistics and consistent alignment.
- Meaningful data visualisation with labelled axes, units, and uncertainty.
- Consistent spacing scale and alignment grid.
- Restrained colour used semantically, not decoratively.
- Functional interaction: hover/focus reveals detail; nothing moves unless it communicates
  state.
- Visual consistency across screens and states.

### Information hierarchy

| Level | Content | Treatment |
| --- | --- | --- |
| 1 | Fixture identity, kickoff, competition, venue | Persistent, unambiguous |
| 2 | Headline probabilities and market | Largest type, explicit units and timestamp |
| 3 | Evidence: form, strength, availability, key metrics | Scannable tables/sparklines with windows |
| 4 | Model detail: assumptions, inputs, calibration context | Expandable/progressive disclosure |
| 5 | Provenance: source, fetched_at, model version | Available on demand, never hidden entirely |

Do not let level 4-5 detail crowd level 1-2. Do not let level 2 appear without level 5
reachable.

### Data visualisation rules

- Never truncate the y-axis on probability or count charts to exaggerate differences.
- Never use 3D, perspective, or area distortion for quantitative data.
- Keep scales consistent across compared entities; label them.
- Show uncertainty: intervals, sample size, or an explicit "low confidence" state.
- Do not imply causation from correlation; label descriptive vs predictive metrics.
- Use colour-blind-safe palettes; never encode meaning by hue alone — pair with shape, label,
  or position.
- Avoid pie charts for more than two categories; avoid dual axes unless unavoidable and
  labelled.
- Sparklines need a baseline and a defined window.
- Probabilities are shown as percentages with one decimal at most, plus the sample/model
  context; never as a fake "confidence score".
- Missing data is shown as missing, not as zero or a gap that looks like zero.

### Typography and density

- Use a restrained type scale (e.g. 4-6 sizes); no decorative display faces.
- Tabular numerals for tables and aligned statistics.
- Line height adequate for dense reading; avoid all-caps body text.
- Limit column width for prose; allow dense tables for data.
- Use weight and spacing for hierarchy before colour.

### Colour policy

- No final palette or brand in Phase 1.
- Define semantic roles: surface, surface-raised, text-primary, text-secondary, border, data
  ink, selection accent, positive/negative (validated for contrast and colour blindness),
  warning, critical.
- Do not use semantic colours decoratively.
- Dark mode is a deliberate design, not an inversion; validate contrast in both.

### Motion policy

- Motion only for state change, loading, or spatial continuity.
- Respect `prefers-reduced-motion`.
- No ambient or looping animation.
- No counting animations that delay access to the number.

### Accessibility

- Target WCAG 2.2 AA.
- Contrast ratios verified, not assumed.
- Full keyboard operation with visible focus.
- Charts have text alternatives (summary table or accessible description).
- Touch targets large enough; no hover-only information.
- Error and empty states are announced to assistive technology.

### Copy discipline

- Label the market, the probability, the timestamp, and the model/version.
- Say "estimated probability", not "prediction confidence" or "chance of winning".
- State when evidence is insufficient: "insufficient data for a reliable estimate".
- Avoid urgency, hype, and gambling-adjacent language.

## Quality checklist

- [ ] Every element has a functional purpose.
- [ ] No forbidden pattern is present.
- [ ] Hierarchy matches the decision workflow.
- [ ] Probabilities show units, timestamp, and uncertainty context.
- [ ] Charts have honest axes, labels, and uncertainty.
- [ ] Missing data is visibly missing.
- [ ] Contrast and keyboard access verified.
- [ ] Reduced motion respected.
- [ ] No fake data, fake charts, or AI marketing copy.
- [ ] No final palette or brand invented.

## Common failure patterns

- "Modern" gradient hero replacing the fixture context.
- Glass cards that reduce contrast and legibility.
- Three identical stat cards with no analytical relationship.
- A confidence ring that is not a calibrated probability.
- Truncated axes to make a team look dominant.
- Decorative particles behind live numbers.
- Placeholder charts shipped as if real.
- Hover-only explanations inaccessible on touch and to screen readers.

## Expected outputs

- Interface principles and workflow specifications.
- Component rules for probability, uncertainty, comparison, and provenance.
- Data-visualisation and accessibility checklists.
- Review notes rejecting specific slop patterns with reasons.

## Sources and references

- `rules/design-rules.md`
- `docs/design/design-principles.md`
- WCAG 2.2 (W3C Recommendation) — consult the current official specification.
- Data-visualisation guidance from established statistical graphics practice; cite specific
  sources when making a claim.

## Limitations

This skill defines constraints, not a brand. Final identity, palette, and component library
require developer approval and validation with real content and users. It does not authorise
UI implementation in Phase 1.
