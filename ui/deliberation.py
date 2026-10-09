"""Live view of the structured, public assessments emitted by the tribunal."""
from __future__ import annotations

import flet as ft
from core.models import Vote
from core.public_text import public_text


def assessment_record(vote: Vote, round_number: int, phase: str, *, simulation: bool = False) -> dict:
    """Allowlist output fields; omit prompts, context and raw provider responses."""
    lines = []
    if vote.validation_errors:
        lines.append("Assessment unavailable: the response failed validation. Review local diagnostics.")
    else:
        lines.append(public_text(vote.reasoning))
        argument = vote.argument or {}
        for key, label in (("claim", "Claim"), ("strongest_objection", "Strongest objection"),
                           ("change_condition", "Would change decision if")):
            if argument.get(key):
                lines.append(f"{label}: {public_text(argument[key])}")
        for evidence in argument.get("evidence", []) or []:
            if isinstance(evidence, dict):
                lines.append(f"Evidence stated by model [{public_text(evidence.get('source'))}]: {public_text(evidence.get('detail'))}")
        for assumption in argument.get("assumptions", []) or []:
            lines.append(f"Assumption: {public_text(assumption)}")
        for peer in vote.peer_responses:
            lines.append(f"{public_text(peer.get('stance'))} {public_text(peer.get('peer'))}: {public_text(peer.get('reason'))}")
        for key, label in (("vote_change_reason", "Decision revision"), ("review_reason", "Review requested")):
            if getattr(vote, key):
                lines.append(f"{label}: {public_text(getattr(vote, key))}")
        for values, label in ((vote.risks, "Risk"), (vote.conditions, "Condition"),
                              (vote.unresolved_disagreements, "Unresolved disagreement")):
            lines.extend(f"{label}: {public_text(value)}" for value in values)
    return {"agent_id": vote.node_key, "round": round_number, "phase": phase,
            "vote": vote.vote.value, "model": public_text(vote.model), "timestamp": vote.timestamp,
            "body": "\n\n".join(line for line in lines if line), "simulation": simulation}


def build_assessments(state) -> ft.Column:
    theme = state.theme
    def text(value, color=None, size=12):
        return ft.Text(value, color=color or theme.text_color, size=size, selectable=True,
                       font_family=theme.font_family)
    records = tuple(state.deliberation_records)
    controls = [text("Assessments appear when each model turn finishes. Assessment → critique → revision.",
                     theme.secondary_text or theme.text_color)]
    if state.config.backend == "mock" or any(record["simulation"] for record in records):
        controls.append(text("SIMULATION — mock assessments", theme.warning_color))
    controls.append(text(f"TRIBUNAL: {state.lifecycle_state}"))
    for agent, turn in tuple(state.deliberation_pending.items()):
        controls.append(text(f"{agent} / {turn} — preparing assessment", theme.accent_color))
    if not records:
        controls.append(text("No completed assessments in this session."))
    for record in records:
        controls.append(ft.Container(ft.Column([
            text(f"ROUND {record['round']} / {record['phase'].upper()} / {record['agent_id']} / {record['vote']}",
                 theme.accent_color),
            text(f"{record['timestamp']} · {record['model']}", size=10),
            text(record["body"]),
        ], spacing=8), padding=12, border=ft.border.all(1, theme.secondary_color),
            bgcolor=theme.background_color, data={"role": "public_assessment"}))
    if state.current_result:
        controls.append(text(f"ARBITER / {state.current_result.verdict.value}\n{public_text(state.current_result.reason)}"))
    # Keep this Column mounted during updates so the operator's reading position survives.
    return ft.Column(controls, scroll=ft.ScrollMode.AUTO, expand=True, spacing=12,
                     auto_scroll=False, data={"role": "deliberation_assessments"})
