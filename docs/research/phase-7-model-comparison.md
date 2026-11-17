# Phase 7 — Model Selection and Match Comparison

**Date:** 2026-11-17
**Status:** Implemented, tested and browser-checked
**Scope:** How a user or client requests one named model, how the three models are compared
on one fixture, and why no model is ever silently substituted.

## 1. Requirement

Before Phase 7 the analysis API answered every request with Poisson. DC and Elo existed but
were reachable only from the evaluation engine. That created two risks:

- a client could believe it was comparing models when it was reading Poisson three times;
- adding a "comparison" that defaulted on failure would manufacture agreement.

The requirement was therefore:

1. an explicit `model` selector, defaulting to the permanent Poisson baseline;
2. a comparison that runs every model on the **same point-in-time dataset**;
3. an unknown or failing model is surfaced, never replaced;
4. every returned number carries the model id and version that produced it.

## 2. API contract

### 2.1 Single-model analysis

```
POST /api/v1/analysis/matches/{match_id}?model={poisson|dixon_coles|elo}&force={bool}
```

- `model` defaults to `poisson`.
- An unknown key returns HTTP 422 with envelope code **`unknown_model`**, the offending
  value, the field name and the allowed list. Nothing is persisted.
- The report's `statistical_model.model_id` / `model_version` identify the model that ran.
- `evaluation` (the embedded 50-match Poisson rolling-origin block) is populated **only** for
  Poisson reports. For DC and Elo it is `null`, because attaching a Poisson measurement to an
  Elo report would misdescribe it.

`force=true` regenerates; otherwise a repeated identical request returns the stored report.

### 2.2 Comparison

```
POST /api/v1/analysis/matches/{match_id}/comparison
```

POST, not GET, because the endpoint **computes and persists** one report per model. It is
not a cache read; describing it as GET would misstate its side effects.

Response:

```json
{
  "match_id": 410,
  "analysis_as_of": "...",
  "dataset_id": "ds_match_410_...",
  "dataset_digest": "...",
  "models": [
    {
      "key": "poisson",
      "model_id": "poisson_baseline",
      "model_version": "poisson-v1.1.0",
      "status": "READY",
      "home_win_probability": 0.6092,
      "draw_probability": 0.2320,
      "away_win_probability": 0.1588,
      "expected_home_goals": 1.74,
      "expected_away_goals": 0.76,
      "reason": null,
      "analysis_id": 37,
      "limitations": ["..."]
    }
  ],
  "notes": ["..."]
}
```

Guarantees:

- every item reads the same `dataset_digest`;
- each ready item has a persisted `analysis_id`, retrievable through `GET /analysis/{id}`;
- repeating the comparison reuses the same persisted reports (tested);
- an abstaining model returns its own status and `analysis_id: null`, while other models are
  still reported;
- an unknown match returns 404.

## 3. Implementation

`app/intelligence/model_selection.py` is the single key → implementation map:

| Key | Model id | Version | Output |
|---|---|---|---|
| `poisson` | `poisson_baseline` | `poisson-v1.1.0` | 1X2, xG, markets, scorelines |
| `dixon_coles` | `dixon_coles_baseline` | `dixon-coles-v1.0.0` | 1X2, xG, markets, scorelines |
| `elo` | `elo_baseline` | `elo-v1.0.0` | 1X2 only |

`compute_model_prediction` dispatches once, attaches the dataset id and digest to every
result, and records `requested_model`. There is no fallback branch: an unknown key raises
before any computation, and a model-specific abstention returns that model's
`INSUFFICIENT_DATA` with a reason.

Design details worth recording:

- **Poisson is untouched.** The live path still uses `predict_from_features`; Phase 7 did not
  rewrite the baseline while adding comparisons.
- **DC reuses the shared rate estimator**, then fits `rho` on prior competition matches and
  clips it so every low-score correction stays positive.
- **Elo replays the corpus chronologically**, captures pre-match ratings before applying a
  kickoff group, fits the Davidson mapping on pre-window matches, and returns no xG, no
  scorelines, no BTTS and no over/under. Those fields are `null`/`[]`, not borrowed from
  Poisson.
- `model_parameters` changed from a fixed Poisson-shaped object to
  `dict[str, Any] | None`, because Elo reports ratings and a Davidson fit while DC adds
  `rho`. Forcing Elo to publish Poisson fields would have been fabricated structure.

## 4. Example: match 410

Executed on 2026-11-17 against the current corpus. All three models used dataset
`ds_match_410_61252c4622bbc0db`, digest `2e2120e17f474329…`, `analysis_as_of`
2026-11-17T09:32:35Z.

| Model | Home | Draw | Away | xG home | xG away | Report |
|---|---:|---:|---:|---:|---:|---:|
| Poisson | 60.92% | 23.20% | 15.88% | 1.74 | 0.76 | #37 |
| Dixon-Coles | 60.16% | 24.72% | 15.12% | 1.74 | 0.76 | #28 |
| Elo | 68.36% | 19.77% | 11.87% | — | — | #27 |

Reading this correctly:

- DC moves ~1.5 pp from home/away into the draw, exactly the low-score correction's job,
  while leaving expected goals unchanged (it does not re-estimate rates).
- Elo is materially more confident about the home side. That is not evidence that it is
  right; on the 970-match evaluation Elo was directionally worse and not proven different.
- The three reports are different persisted documents for the same fixture and dataset.

## 5. Frontend

`MatchAnalysisPanel` now provides:

- a three-button model selector with a short description of each model;
- "Analyze with …" using the selected model;
- "Compare all models", which calls the comparison endpoint and renders a table of status,
  1X2, xG (or "not produced") and a link to each persisted report;
- model-aware copy: Elo reports state that expected goals and secondary markets are not
  produced by that model, rather than showing blanks or Poisson numbers;
- generic parameter rendering, so Poisson rates, DC `rho` and Elo ratings all display
  without hard-coded field names or `undefined`;
- selecting a model clears the previously displayed report, so a report can never be
  labelled with a model that did not produce it.

## 6. What the comparison does not mean

Model outputs differing is not evidence that one is better. The only accuracy evidence is
the stored evaluation on an identical chronological match set. The comparison response says
this in its notes, and the UI repeats it.

In particular:

- DC's higher draw probability is a structural consequence of the correction, not a
  prediction of a draw;
- Elo's confidence comes from a rating difference, not from goals, lineups or form detail;
- none of the three numbers is a guarantee or a betting edge.

## 7. Failure semantics tested

| Scenario | Behaviour |
|---|---|
| Unknown model key | 422 `unknown_model`, nothing persisted |
| Unknown match | 404 |
| Finished/unanalysable match | every comparison item `DATA_UNAVAILABLE`, no ids |
| Team with no Elo history | Elo abstains with `no_historical_ratings`; other models still answer |
| Repeated single-model request | same analysis id |
| Repeated comparison | same analysis ids |
| Missing stored analysis | 404, never 500 |

## 8. Related documents

- `phase-7-multi-competition-backtest.md`
- `phase-7-independent-model-review.md`
- `apps/backend/app/intelligence/model_selection.py`
- `apps/backend/tests/integration/test_analysis_api.py`
- `apps/web/src/components/MatchAnalysisPanel.tsx`
