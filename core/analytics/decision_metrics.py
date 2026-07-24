from __future__ import annotations

import csv
import json
import math
from collections import Counter, defaultdict
from datetime import datetime, timezone
from io import StringIO
from pathlib import Path
from statistics import mean, median
from typing import Any, Dict, Iterable, List, Mapping, Sequence

from core.paths import HISTORY_PATH


VERDICT_ALIASES = {
    "APPROVED": "APPROVE",
    "DENIED": "DENY",
    "CONDITIONAL_APPROVAL": "CONDITIONAL",
    "HUMAN_REVIEW_REQUIRED": "ESCALATE",
    "DEADLOCK": "NO_CONSENSUS",
}


def load_decisions(path: Path = HISTORY_PATH) -> List[Dict[str, Any]]:
    if not path.exists():
        return []
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    if not isinstance(payload, list):
        return []
    return [record for record in payload if isinstance(record, dict)]


def build_decision_summary(path: Path = HISTORY_PATH) -> Dict[str, Any]:
    return summarize_decisions(load_decisions(path))


def summarize_decisions(decisions: Iterable[Mapping[str, Any]]) -> Dict[str, Any]:
    records = [record for record in decisions if isinstance(record, Mapping)]
    verdict_counts = Counter(_normalize_verdict(record.get("verdict")) for record in records)
    verdict_counts.pop("", None)
    branch_counts = Counter(str(record.get("terminal_branch") or "UNSPECIFIED") for record in records)
    confidences = [_bounded_float(record.get("confidence")) for record in records]
    timestamps = [_parse_timestamp(record.get("timestamp")) for record in records]
    parsed_timestamps = sorted(item for item in timestamps if item is not None)

    agent_votes: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    pairwise: Dict[tuple[str, str], List[bool]] = defaultdict(list)
    unanimous_count = 0
    majority_count = 0
    fully_split_count = 0

    for record in records:
        votes = record.get("votes")
        if not isinstance(votes, Mapping):
            continue
        normalized_votes: Dict[str, str] = {}
        final_verdict = _normalize_verdict(record.get("verdict"))
        for raw_agent, raw_vote in votes.items():
            if not isinstance(raw_vote, Mapping):
                continue
            agent = str(raw_agent).upper()
            vote = _normalize_verdict(raw_vote.get("vote"))
            normalized_votes[agent] = vote
            agent_votes[agent].append(
                {
                    "vote": vote,
                    "confidence": _bounded_float(raw_vote.get("confidence")),
                    "response_time": max(0.0, _safe_float(raw_vote.get("response_time"))),
                    "validation_errors": raw_vote.get("validation_errors") or [],
                    "matches_final": bool(vote and vote == final_verdict),
                }
            )

        vote_values = [value for value in normalized_votes.values() if value]
        if vote_values:
            distribution = Counter(vote_values)
            if len(distribution) == 1:
                unanimous_count += 1
            elif distribution.most_common(1)[0][1] >= 2:
                majority_count += 1
            else:
                fully_split_count += 1

        agents = sorted(normalized_votes)
        for left_index, left in enumerate(agents):
            for right in agents[left_index + 1 :]:
                if normalized_votes[left] and normalized_votes[right]:
                    pairwise[(left, right)].append(normalized_votes[left] == normalized_votes[right])

    response_times = [
        vote["response_time"]
        for votes in agent_votes.values()
        for vote in votes
        if vote["response_time"] > 0
    ]
    decision_count = len(records)
    voting_decisions = unanimous_count + majority_count + fully_split_count
    return {
        "schema_version": 1,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "decision_count": decision_count,
        "period": _period_metrics(parsed_timestamps, decision_count),
        "verdicts": {
            "counts": dict(sorted(verdict_counts.items())),
            "rates": _rates(verdict_counts, decision_count),
        },
        "terminal_branches": {
            "counts": dict(sorted(branch_counts.items())),
            "rates": _rates(branch_counts, decision_count),
        },
        "confidence": _numeric_summary(confidences),
        "response_time_seconds": _numeric_summary(response_times),
        "agents": {
            agent: _agent_summary(votes)
            for agent, votes in sorted(agent_votes.items())
        },
        "agreement": {
            "voting_decisions": voting_decisions,
            "unanimous_count": unanimous_count,
            "unanimous_rate": _ratio(unanimous_count, voting_decisions),
            "majority_split_count": majority_count,
            "majority_split_rate": _ratio(majority_count, voting_decisions),
            "fully_split_count": fully_split_count,
            "fully_split_rate": _ratio(fully_split_count, voting_decisions),
            "pairwise": {
                f"{left}|{right}": {
                    "compared": len(matches),
                    "agreements": sum(matches),
                    "agreement_rate": _ratio(sum(matches), len(matches)),
                }
                for (left, right), matches in sorted(pairwise.items())
            },
        },
    }


def summary_to_csv(summary: Mapping[str, Any]) -> str:
    output = StringIO(newline="")
    writer = csv.writer(output, lineterminator="\n")
    writer.writerow(["category", "subject", "metric", "value"])
    writer.writerow(["system", "all", "decision_count", summary.get("decision_count", 0)])

    period = summary.get("period", {})
    if isinstance(period, Mapping):
        for metric in ("start", "end", "calendar_days", "decisions_per_day"):
            writer.writerow(["period", "all", metric, period.get(metric, "")])

    for category in ("verdicts", "terminal_branches"):
        payload = summary.get(category, {})
        if not isinstance(payload, Mapping):
            continue
        counts = payload.get("counts", {})
        rates = payload.get("rates", {})
        subjects = sorted(set(counts) | set(rates)) if isinstance(counts, Mapping) and isinstance(rates, Mapping) else []
        for subject in subjects:
            writer.writerow([category, subject, "count", counts.get(subject, 0)])
            writer.writerow([category, subject, "rate", rates.get(subject, 0.0)])

    for category in ("confidence", "response_time_seconds"):
        payload = summary.get(category, {})
        if isinstance(payload, Mapping):
            for metric, value in payload.items():
                writer.writerow([category, "all", metric, value])

    agents = summary.get("agents", {})
    if isinstance(agents, Mapping):
        for agent, metrics in sorted(agents.items()):
            if isinstance(metrics, Mapping):
                for metric, value in metrics.items():
                    if isinstance(value, Mapping):
                        for nested_metric, nested_value in sorted(value.items()):
                            writer.writerow([f"agent_{metric}", agent, nested_metric, nested_value])
                    else:
                        writer.writerow(["agent", agent, metric, value])

    agreement = summary.get("agreement", {})
    if isinstance(agreement, Mapping):
        for metric, value in agreement.items():
            if metric != "pairwise" and not isinstance(value, Mapping):
                writer.writerow(["agreement", "all", metric, value])
        pairwise_metrics = agreement.get("pairwise", {})
        if isinstance(pairwise_metrics, Mapping):
            for pair, metrics in sorted(pairwise_metrics.items()):
                if isinstance(metrics, Mapping):
                    for metric, value in metrics.items():
                        writer.writerow(["pairwise_agreement", pair, metric, value])
    return output.getvalue()


def _agent_summary(votes: Sequence[Mapping[str, Any]]) -> Dict[str, Any]:
    confidences = [_safe_float(vote.get("confidence")) for vote in votes]
    response_times = [_safe_float(vote.get("response_time")) for vote in votes if _safe_float(vote.get("response_time")) > 0]
    vote_counts = Counter(str(vote.get("vote") or "UNKNOWN") for vote in votes)
    errors = sum(
        1
        for vote in votes
        if vote.get("vote") == "ERROR" or bool(vote.get("validation_errors"))
    )
    final_matches = sum(bool(vote.get("matches_final")) for vote in votes)
    return {
        "vote_count": len(votes),
        "error_count": errors,
        "error_rate": _ratio(errors, len(votes)),
        "agreement_with_final_rate": _ratio(final_matches, len(votes)),
        "average_confidence": _round(mean(confidences)) if confidences else 0.0,
        "average_response_time_seconds": _round(mean(response_times)) if response_times else 0.0,
        "p95_response_time_seconds": _round(_percentile(response_times, 95)) if response_times else 0.0,
        "vote_distribution": dict(sorted(vote_counts.items())),
    }


def _numeric_summary(values: Sequence[float]) -> Dict[str, Any]:
    clean = [value for value in values if math.isfinite(value)]
    if not clean:
        return {"count": 0, "minimum": 0.0, "maximum": 0.0, "mean": 0.0, "median": 0.0, "p95": 0.0}
    return {
        "count": len(clean),
        "minimum": _round(min(clean)),
        "maximum": _round(max(clean)),
        "mean": _round(mean(clean)),
        "median": _round(median(clean)),
        "p95": _round(_percentile(clean, 95)),
    }


def _period_metrics(timestamps: Sequence[datetime], decision_count: int) -> Dict[str, Any]:
    if not timestamps:
        return {"start": None, "end": None, "calendar_days": 0, "decisions_per_day": 0.0}
    start = timestamps[0]
    end = timestamps[-1]
    days = max(1, (end.date() - start.date()).days + 1)
    return {
        "start": start.isoformat(),
        "end": end.isoformat(),
        "calendar_days": days,
        "decisions_per_day": _round(decision_count / days),
    }


def _parse_timestamp(value: Any) -> datetime | None:
    raw = str(value or "").strip()
    if not raw:
        return None
    try:
        parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _normalize_verdict(value: Any) -> str:
    normalized = str(getattr(value, "value", value) or "").strip().upper()
    return VERDICT_ALIASES.get(normalized, normalized)


def _safe_float(value: Any) -> float:
    try:
        result = float(value)
    except (TypeError, ValueError):
        return 0.0
    return result if math.isfinite(result) else 0.0


def _bounded_float(value: Any) -> float:
    return min(1.0, max(0.0, _safe_float(value)))


def _percentile(values: Sequence[float], percentile: float) -> float:
    ordered = sorted(values)
    if not ordered:
        return 0.0
    position = (len(ordered) - 1) * percentile / 100.0
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return ordered[lower]
    return ordered[lower] + (ordered[upper] - ordered[lower]) * (position - lower)


def _rates(counts: Mapping[str, int], total: int) -> Dict[str, float]:
    return {key: _ratio(value, total) for key, value in sorted(counts.items())}


def _ratio(numerator: int, denominator: int) -> float:
    return _round(numerator / denominator) if denominator else 0.0


def _round(value: float) -> float:
    return round(float(value), 6)


__all__ = ["build_decision_summary", "load_decisions", "summarize_decisions", "summary_to_csv"]
