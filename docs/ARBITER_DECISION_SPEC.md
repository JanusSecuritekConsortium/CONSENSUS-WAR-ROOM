# CONSENSUS SYSTEM - Arbiter Decision Specification

Status: normative for the active Python implementation.

This document defines the decision contract for voting monoliths, the Arbiter,
history, UI, TTS, and automation consumers.

## Vote Schema

Each voting monolith emits one vote per proposal:

```json
{
  "monolith": "RATIONALIS",
  "result": "APPROVE",
  "confidence": 0.82,
  "evidence_quality": 0.71,
  "critical_risk": false,
  "rationale": "string"
}
```

Required fields:

- `monolith`: canonical voting monolith id.
- `result`: only `APPROVE`, `DENY`, or `ABSTAIN`.
- `confidence`: float from `0.0` to `1.0`; audit/display only.
- `evidence_quality`: float from `0.0` to `1.0`; evidence sufficiency, not confidence.
- `critical_risk`: boolean; the only monolith field that triggers the CAUTION path.
- `rationale`: human-readable reasoning; never parsed for numeric fields.

Voting monoliths must not emit Arbiter-only terminal results:

- `NO_CONSENSUS`
- `CAUTION`
- `ESCALATE`

Malformed votes are coerced to `ABSTAIN` with `evidence_quality = 0.0`,
`critical_risk = false`, and validation errors recorded.

## Arbiter-Assigned Domain Relevance

`critical_domain_relevance` is assigned by the Arbiter, never by a monolith.

The Arbiter derives it from:

- the proposal classification
- `monolith_domain_map` in runtime config

A monolith is domain-critical when its configured domain classes intersect the
proposal classes for the current command.

## Proposal Classification

Classification is mandatory before a decision can be certified.

The classifier receives the proposal text and structured command context, but
not monolith votes. It returns:

```json
{
  "proposal_classes": ["security", "risk"],
  "primary_class": "security",
  "classifier_confidence": 0.88,
  "classifier_version": "1.0.0",
  "classified_at": "2026-05-20T03:17:00Z"
}
```

Classification failure occurs when output is missing, malformed, outside the
configured taxonomy, or below `classification_confidence_threshold`.

On classification failure:

- return `ESCALATE` if any voting monolith reported `critical_risk = true`
- otherwise return `NO_CONSENSUS`
- do not tally votes under majority or tie-break rules

## Terminal Results

The Arbiter terminal result vocabulary is:

- `APPROVE`
- `DENY`
- `ABSTAIN`
- `NO_CONSENSUS`
- `CAUTION`
- `ESCALATE`

Consumers must not assume a binary approve/deny outcome.

## Majority Rule

The voting tribunal should preserve an odd number of voting monoliths. Default:

- RATIONALIS
- AETERNUM
- BELLATOR

Majority threshold:

```text
M = floor(N / 2) + 1
```

`ABSTAIN` counts toward neither `APPROVE` nor `DENY`.

If `APPROVE` or `DENY` reaches majority, that result is final. Tie-break logic
does not run.

## Tie-Break State Machine

Tie-break runs only when no majority exists.

Branches are evaluated in this exact order:

1. CAUTION

If any voting monolith reported `critical_risk = true`, return `CAUTION`.

2. NO_CONSENSUS

Return `NO_CONSENSUS` if either condition holds:

- mean `evidence_quality` across all voting monoliths is below `evidence_threshold`
- any domain-critical monolith has `evidence_quality < evidence_threshold`

3. Priority Resolution

Use configured `tie_break_priority`. Return the `APPROVE` or `DENY` vote from
the highest-priority non-abstaining monolith.

If all monoliths abstain, return `NO_CONSENSUS`.

Tie-break must not consider confidence, advisor output, time, RNG, or model
calls.

## Advisor Semantics

Non-voting advisors may produce dossier material, but they do not influence
voting, tallying, tie-breaks, or voting-monolith prompt context.

Promotion of an advisor into the voting tribunal must be explicit and must
preserve the odd-count invariant or provide a deterministic tie-break rule.

## Conformance

An implementation conforms when:

- voting monoliths emit only `APPROVE`, `DENY`, or `ABSTAIN`
- malformed votes are safely coerced and logged
- classification is mandatory
- `critical_domain_relevance` is Arbiter-assigned
- majority short-circuits tie-break
- tie-break is deterministic and total
- all terminal results are handled by history, UI, TTS, and automation consumers
