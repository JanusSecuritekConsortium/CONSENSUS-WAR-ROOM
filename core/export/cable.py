"""An optional cable view of public decision fields, never raw model output."""
from __future__ import annotations

from pathlib import Path
from typing import Any

from core.export.verdict import _safe_proposal_id
from core.models import TribunalResult
from core.paths import EXPORT_DIR
from core.public_text import public_text


def _items(packet: Any, key: str = "items") -> list:
    value = packet.get(key, []) if isinstance(packet, dict) else []
    return value if isinstance(value, list) else []


def retrieved_sources(context: dict[str, Any] | None) -> list[dict[str, str]]:
    # Only host-retrieved references are attributed as sources. A model's
    # argument.evidence is a claim, not evidence of retrieval.
    context = context or {}
    matches = list(_items(context.get("external_reference_context"), "matches"))
    packet = context.get("bellator_context_packet", {})
    if isinstance(packet, dict):
        matches.extend(_items(packet.get("rss_intelligence")))
        matches.extend(_items(packet.get("real_data_layer")))
    matches.extend(_items(context.get("aeternum_data_packet")))
    sources = []
    for item in matches:
        if not isinstance(item, dict):
            continue
        url = str(item.get("source_url") or item.get("url") or "")
        if not url.startswith(("https://", "http://")):
            continue
        source = {"title": str(item.get("title") or "Retrieved reference"), "url": url}
        if item.get("page") is not None:
            source["page"] = str(item["page"])
        if item.get("retrieved_at"):
            source["retrieved_at"] = str(item["retrieved_at"])
        elif item.get("fetched_at"):
            source["retrieved_at"] = str(item["fetched_at"])
        if source not in sources:
            sources.append(source)
    memory = context.get("memory_context", context)
    for item in _items(memory):
        if isinstance(item, dict) and item.get("session_id"):
            source = {"title": "Local prior decision", "reference_id": str(item["session_id"])}
            if item.get("timestamp"):
                source["date"] = str(item["timestamp"])
            if source not in sources:
                sources.append(source)
    return sources


def render_cable(result: TribunalResult | None, sources: list[dict[str, str]] | None = None) -> str:
    if result is None:
        return "DIRECTORATE / CABLE\n\nNo assessment available. Submit a proposal to create a report."
    lines = ["DIRECTORATE / CABLE", "OFFICIAL TRIBUNAL DISPATCH", "=" * 48,
             f"ID: {result.session_id or 'Not available'}",
             f"DATE: {result.timestamp or 'Not available'}",
             f"SUBJECT: {' '.join(result.query.split())[:120] or 'Not available'}",
             "MODE: SIMULATION ONLY" if result.simulation else "MODE: PROVIDER DELIBERATION",
             "", "ORIGINAL QUERY", result.query or "Not available",
             "", "FINAL ASSESSMENT", result.verdict.value, result.reason or "Not available",
             "", "PARTICIPATING MODELS"]
    lines.extend(f"- {key}: {vote.model or 'Not available'} / {vote.backend} / {vote.vote.value}"
                 for key, vote in result.votes.items())
    if not result.votes:
        lines.append("Not available")
    lines.extend(["", "PUBLIC JUSTIFICATIONS"])
    for key, vote in result.votes.items():
        if vote.validation_errors:
            lines.append(f"- {key}: Assessment unavailable; response failed validation.")
            continue
        claim = (vote.argument or {}).get("claim")
        lines.append(f"- {key}: {public_text(claim) or 'No structured justification recorded.'}")
        if vote.vote_change_reason:
            lines.append(f"  Vote revision: {public_text(vote.vote_change_reason)}")
    if not result.votes:
        lines.append("Not available")
    models = {(key, vote.model) for key, vote in result.votes.items()}
    for turn in result.deliberation_transcript:
        identity = (str(turn.get("agent_id", "Unknown")), str(turn.get("model", "Not available")))
        if identity not in models:
            lines.append(f"- {identity[0]}: {identity[1]} / earlier round {turn.get('round', 'Not available')}")
            models.add(identity)
    substitutions = []
    for turn in result.deliberation_transcript:
        if turn.get("model_fallback"):
            line = (f"- {turn.get('agent_id', 'Unknown')}: requested {turn.get('requested_model', 'Not available')}"
                    f" / executed {turn.get('model', 'Not available')}; role instructions retained.")
            if line not in substitutions:
                substitutions.append(line)
    if substitutions:
        lines.extend(["", "MODEL SUBSTITUTIONS", *substitutions])
    lines.extend(["", "RETRIEVED SOURCES"])
    for source in sources or []:
        line = f"- {source['title']}: {source.get('url') or source.get('reference_id', 'Not available')}"
        if "date" in source:
            line += f" / recorded {source['date']}"
        if "page" in source:
            line += f" / page {source['page']}"
        if "retrieved_at" in source:
            line += f" / retrieved {source['retrieved_at']}"
        lines.append(line)
    if not sources:
        lines.append("Not available")
    lines.extend(["", "EXPLICIT DISSENT"])
    dissent = []
    for key, vote in result.votes.items():
        dissent.extend(f"- {key}: {item}" for item in vote.unresolved_disagreements)
        for peer in vote.peer_responses:
            if peer.get("stance") in {"reject", "challenge"}:
                dissent.append(f"- {key} -> {peer.get('peer', 'peer')}: {peer.get('reason', 'Not available')}")
    lines.extend(dissent or ["Not available; no explicit dissent recorded in the final votes."])
    earlier = []
    for turn in result.deliberation_transcript:
        prefix = f"- Round {turn.get('round', '?')} / {turn.get('agent_id', 'Unknown')}"
        earlier.extend(f"{prefix}: {item}" for item in turn.get("unresolved_disagreements", []))
        for peer in turn.get("peer_responses", []):
            if peer.get("stance") in {"challenge", "reject"}:
                earlier.append(f"{prefix} -> {peer.get('peer', 'peer')}: {peer.get('reason', 'Not available')}")
    if earlier:
        lines.extend(["", "DISSENT IN THE EXCHANGE (may have been resolved before the final votes)", *earlier])
    lines.extend(["", "CONDITIONS AND REQUIRED REVIEW"])
    conditions = []
    for key, vote in result.votes.items():
        conditions.extend(f"- Condition ({key}): {item}" for item in vote.conditions)
        if vote.review_required:
            conditions.append(f"- {key} requests review: {vote.review_reason or 'Not available'}")
    conditions.extend(f"- Review trigger: {trigger}" for trigger in result.review_triggers)
    lines.extend(conditions or ["None recorded. No follow-up action has been scheduled."])
    lines.extend(["", "REPORTED RISKS"])
    risks = [f"- {key}: {risk}" for key, vote in result.votes.items() for risk in vote.risks]
    lines.extend(risks or ["None recorded."])
    lines.extend(["", "LIMITATIONS"])
    if result.simulation:
        lines.append("- Simulated responses; no real model calls.")
    if not result.deliberation_complete:
        lines.append("- Deliberation incomplete.")
    for key, vote in result.votes.items():
        if vote.validation_errors:
            lines.append(f"- {key}: Response failed validation; see local diagnostics.")
    lines.extend(["- Retrieved references are dated source claims, not independent verification.",
                  "", "CONFIDENCE: Not available as a calibrated probability.",
                  "The tribunal score is a rule-based aggregate of model self-reports; it is not a measured probability.",
                  "", "ARCHIVE: Local export available on request; this report is not an archive receipt.", "END OF CABLE"])
    # The report allowlists structured public fields; raw responses and private
    # reasoning tags never enter either the desktop roll or exported copy.
    return "\n".join(public_text(line) for line in lines)


def export_cable(result: TribunalResult, sources: list[dict[str, str]] | None = None,
                 output_dir: Path = EXPORT_DIR) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    target = output_dir / f"directorate_cable_{_safe_proposal_id(result.session_id)}.txt"
    target.write_text(render_cable(result, sources), encoding="utf-8")
    return target


def export_dispatch(dispatch, output_dir: Path = EXPORT_DIR) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    target = output_dir / f"directorate_cable_{_safe_proposal_id(dispatch.session_id)}.txt"
    target.write_text(dispatch.report, encoding="utf-8")
    return target
