# Decision evaluation

Run from the repository root with the project Python environment. The runner
uses the same provider adapter, role prompts, response parser and voting engine
as the desktop. It bypasses personal memory retrieval, external enrichment,
decision history and session writes. Synthetic supplied evidence is identical
across strategies. Worker logs and reports stay under ignored `.local/evaluations`.
They can contain local configuration and must not be published wholesale.

## Real-provider smoke test

```powershell
.\.venv\Scripts\python.exe tools/evaluate_consensus.py smoke --repeats 2
```

Smoke requires all nine valid turns in assessment/critique/revision order,
with an actual model and real provider recorded for every role. It returns
nonzero for incomplete exchanges and simulations. It checks execution, not
whether the decision is correct. Normal real-model substitutions remain allowed
and recorded. `--strict-model` disables them; `--model MODEL_ID` selects one
installed model for all roles without changing their doctrines or temperatures.
Shared-model operation is not independent model diversity.

Use `--config LOCAL_CONFIG.json` to read an existing runtime configuration
without modifying it, and `--backend` to override the provider. Without a config
file the runner uses code defaults rather than private operator settings.
No models are downloaded and no provider is restarted or unloaded.

`--call-timeout` defaults to 90 seconds per candidate generation attempt.
`--run-timeout` defaults to 900 seconds per case/strategy/repeat; an isolated
worker is terminated at that deadline. Health checks, fallback attempts and
model loading all count against the run deadline. Closing the local worker
does not guarantee a provider immediately stops its own queued computation.
Partial model responses never count as completed votes.
Completed turn records survive a worker deadline in the aggregate report; the
unfinished turn is not invented and raw response text remains excluded.

## Decision benchmark

```powershell
.\.venv\Scripts\python.exe tools/evaluate_consensus.py benchmark --repeats 3
```

The versioned rubric has 24 synthetic cases: bounded approvals, confirmed
prohibitions, missing prerequisites, conflicting records, negation, arithmetic,
stale evidence and advisory-majority pressure. Labels specify acceptable
verdict sets and explain the grading rule; they require human review before
being used as a real-world policy benchmark. No labels are sent to models.

Strategies are `single` (RATIONALIS, one independent assessment, quorum one),
`independent` (three separate assessments and normal arbitration), and `debate`
(the normal full nine-turn exchange). Other arbitration thresholds remain the
same. Different role/model assignments are a possible confound; to isolate
protocol effects run all strategies with the same `--model` first. This single
role baseline does not represent the best possible single-agent system.

Select cases with repeatable `--case CASE_ID`, strategies with repeatable
`--strategy`, and a report path with `--output`. Each role's configured output
limit is preserved (900 tokens in code defaults); `--max-output-tokens` overrides
it for all compared strategies.
Each row records actual models, substitutions, duration, protocol completion,
verdict, public argument fields and next steps. Prompts and raw responses are
excluded from the aggregate report. Worker diagnostic logs remain local.

Summary metrics include completion rate, acceptable-verdict accuracy (all runs
in the denominator), inappropriate approvals divided by unsafe-case runs,
median/max latency, substitutions, changed votes, correct-to-incorrect and
incorrect-to-correct revisions. A correct minority opportunity requires one
initial correct vote among three and a completed revision for that role.
Cases with advisory pressure do not guarantee that the initial tribunal will
actually split; the opportunity count makes that limitation explicit.
`expected_votes` defines correctness for these revision metrics separately
from the acceptable final verdict set.

A failed provider that returns NO_CONSENSUS cannot pass a missing-evidence
case merely because the expected verdict is also NO_CONSENSUS. Benchmark exits
nonzero for any failed rubric row. Explicit `--backend mock` exercises the
pipeline but does not establish real decision quality; smoke always fails in
mock mode even if all nine simulation turns complete. A full mock benchmark
can fail rubric cases because the demo backend is not an evidence reasoner.

## Evidence passage audits

Normal submissions now carry host-supplied passages into each monolith prompt.
For cited sources with supplied text, models are asked to include a short exact
`quote` alongside `source` and `detail` in each argument evidence entry. Quotes
are checked with whitespace normalization, preserving case, negation and
quantities. A mismatched quote fails validation. Missing quotes remain explicit
`not_quoted` audit entries for compatibility; unavailable text is not invented.

Complete multiline JSON fields are accepted as well as compact JSON; truncated
or malformed JSON still fails validation. The raw local audit remains unchanged.

Quote anchoring establishes that words appeared in a supplied passage. It does
not establish semantic support or source truth. Claim support remains
`unreviewed` unless a host supplies an attributed review of that exact claim
and quote in a separate host-controlled `host_claim_reviews` list in the supplied
memory context. Reviews embedded in retrieved passages and model-written support
assertions do not count as those reviews.
Contradictory host reviews prevent approval. A review must contain `claim`,
`source`, `quote`, `reviewer` and `verdict` (`supports` or `contradicts`).

When a host record specifies `max_age_days`, freshness uses `published_at`,
never the download/retrieval date. Unknown, future-dated or expired publication
evidence prevents approval. Archives without an explicit freshness requirement
are not automatically rejected. These checks preserve majority denial and do
not turn unreviewed evidence into a calibrated confidence percentage.

## Unresolved decisions

JSON result serialization, decision traces and regular JSON/Markdown verdict
exports include `next_steps`. The DIRECTORATE cable adds
the same proposed steps for NO_CONSENSUS, ESCALATE and CAUTION, using validated
change conditions, explicit objections, review reasons and evidence blockers.
Failed responses produce a diagnostics-and-retry step. These are suggestions
for reassessment; they do not authorize or schedule actions.
