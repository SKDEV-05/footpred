# Statistical and Probability Primitives

**Status:** Mathematical behavior tested with synthetic inputs. No model is fitted or
validated on real football.

## Independent Poisson

For caller-supplied rates:

`P(X=k) = exp(-lambda) * lambda^k / k!`

The implementation computes exact probabilities for `0..K` and keeps one explicit overflow
category per team, so the matrix is a complete finite distribution and no mass is discarded
or renormalized. Representation size is `(K+2) x (K+2)`; the final row and column mean
"more than `K` goals", not an exact scoreline.

`K` is chosen so the unresolved overflow-overflow cell is no more than
`unresolved_tolerance`. That cell cannot decide which team scored more, so 1X2 returns
lower and upper bounds plus the unresolved mass; markets that remain logically determined
(over/under, BTTS) use the overflow cells directly. Correct-score output excludes the
overflow categories.

No function estimates home or away expected goals. A supplied rate is not an official xG
value and is not evidence that Poisson fits a competition.

## Dixon-Coles

The four standard low-score cells receive a supplied `rho` adjustment. The admissible
interval is checked explicitly, negative adjustment factors are rejected, and total mass
must be conserved within tolerance; the adjusted matrix is not silently renormalized. The
implementation does not estimate `rho`, apply time decay, or claim improvement over
independent Poisson.

## Elo

Elo applies a caller-supplied initial rating, K-factor, scale, and home offset. Neutral
fixtures receive no home offset. Results are applied chronologically; same-kickoff matches
use the same pre-batch state. Not-yet-observed outcomes are excluded.

Elo expected score is a two-outcome rating expectation, not a three-way match probability,
goal rate, or scoreline distribution.

## Markets

From one score matrix the package derives:

- regulation-time 1X2;
- double chance;
- over 0.5, 1.5, 2.5, and 3.5;
- BTTS;
- ranked explicit scorelines.

No first-half market is implemented because full-time rates cannot be assumed valid for the
first half.
