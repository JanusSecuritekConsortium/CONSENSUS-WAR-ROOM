from __future__ import annotations

from copy import deepcopy
from string import Formatter
from typing import Any, Dict, List

from config.version import SYSTEM_VERSION


TEMPLATE_VERSION = SYSTEM_VERSION

_TEMPLATES: Dict[str, Dict[str, Any]] = {
    "geopolitical_analysis": {
        "id": "geopolitical_analysis",
        "title": "Geopolitical Analysis",
        "description": "Assess a geopolitical event, actor, region, or escalation path.",
        "default_taxonomy_hint": "RISK_ASSESSMENT",
        "required_fields": ["region", "actors", "question"],
        "optional_fields": ["time_horizon", "known_constraints", "sources"],
        "prompt_body": (
            "Geopolitical analysis request\n"
            "Region: {region}\n"
            "Actors: {actors}\n"
            "Question: {question}\n"
            "Time horizon: {time_horizon}\n"
            "Known constraints: {known_constraints}\n"
            "Sources/context: {sources}"
        ),
        "version": TEMPLATE_VERSION,
        "created_at": "2026-05-27T00:00:00Z",
    },
    "market_finance_analysis": {
        "id": "market_finance_analysis",
        "title": "Market / Finance Analysis",
        "description": "Review a market, asset, company, macro factor, or allocation decision.",
        "default_taxonomy_hint": "MARKET_ANALYSIS",
        "required_fields": ["asset_or_market", "decision_question", "time_horizon"],
        "optional_fields": ["risk_limits", "data_points", "scenario"],
        "prompt_body": (
            "Market / finance analysis request\n"
            "Asset or market: {asset_or_market}\n"
            "Decision question: {decision_question}\n"
            "Time horizon: {time_horizon}\n"
            "Risk limits: {risk_limits}\n"
            "Data points: {data_points}\n"
            "Scenario: {scenario}"
        ),
        "version": TEMPLATE_VERSION,
        "created_at": "2026-05-27T00:00:00Z",
    },
    "technical_decision": {
        "id": "technical_decision",
        "title": "Technical Decision",
        "description": "Evaluate architecture, implementation, vendor, security, or reliability tradeoffs.",
        "default_taxonomy_hint": "TECHNICAL_DECISION",
        "required_fields": ["decision", "options", "constraints"],
        "optional_fields": ["current_system", "risk_tolerance", "deadline"],
        "prompt_body": (
            "Technical decision request\n"
            "Decision: {decision}\n"
            "Options: {options}\n"
            "Constraints: {constraints}\n"
            "Current system: {current_system}\n"
            "Risk tolerance: {risk_tolerance}\n"
            "Deadline: {deadline}"
        ),
        "version": TEMPLATE_VERSION,
        "created_at": "2026-05-27T00:00:00Z",
    },
    "operational_risk": {
        "id": "operational_risk",
        "title": "Operational Risk",
        "description": "Assess business, security, continuity, compliance, or execution risk.",
        "default_taxonomy_hint": "OPERATIONAL_RISK",
        "required_fields": ["operation", "threats", "impact"],
        "optional_fields": ["controls", "timeline", "owner"],
        "prompt_body": (
            "Operational risk request\n"
            "Operation: {operation}\n"
            "Threats: {threats}\n"
            "Impact: {impact}\n"
            "Controls: {controls}\n"
            "Timeline: {timeline}\n"
            "Owner: {owner}"
        ),
        "version": TEMPLATE_VERSION,
        "created_at": "2026-05-27T00:00:00Z",
    },
    "general_tribunal_query": {
        "id": "general_tribunal_query",
        "title": "General Tribunal Query",
        "description": "Submit a general proposal or question to the tribunal.",
        "default_taxonomy_hint": "GENERAL",
        "required_fields": ["query"],
        "optional_fields": ["context", "desired_output"],
        "prompt_body": (
            "General tribunal query\n"
            "Query: {query}\n"
            "Context: {context}\n"
            "Desired output: {desired_output}"
        ),
        "version": TEMPLATE_VERSION,
        "created_at": "2026-05-27T00:00:00Z",
    },
}


def list_templates() -> List[Dict[str, Any]]:
    return [deepcopy(template) for template in _TEMPLATES.values()]


def get_template(template_id: str) -> Dict[str, Any]:
    try:
        return deepcopy(_TEMPLATES[template_id])
    except KeyError as exc:
        raise KeyError(f"Unknown proposal template: {template_id}") from exc


def validate_template_values(template_id: str, values: Dict[str, Any]) -> List[str]:
    template = get_template(template_id)
    errors: List[str] = []
    for field in template["required_fields"]:
        value = values.get(field)
        if value is None or str(value).strip() == "":
            errors.append(f"Missing required field: {field}")
    return errors


def _render_values(template: Dict[str, Any], values: Dict[str, Any]) -> Dict[str, str]:
    rendered: Dict[str, str] = {}
    for _, field_name, _, _ in Formatter().parse(template["prompt_body"]):
        if field_name:
            rendered[field_name] = str(values.get(field_name, "")).strip() or "--"
    return rendered


def render_template(template_id: str, values: Dict[str, Any]) -> str:
    template = get_template(template_id)
    errors = validate_template_values(template_id, values)
    if errors:
        raise ValueError("; ".join(errors))
    rendered_body = template["prompt_body"].format(**_render_values(template, values))
    return (
        f"Title: {template['title']}\n"
        f"Taxonomy hint: {template['default_taxonomy_hint']}\n\n"
        f"{rendered_body}"
    )


def render_template_draft(template_id: str) -> str:
    template = get_template(template_id)
    values = {
        field: f"[{field.upper()}]"
        for field in [*template["required_fields"], *template["optional_fields"]]
    }
    return (
        f"Title: {template['title']}\n"
        f"Taxonomy hint: {template['default_taxonomy_hint']}\n\n"
        f"{template['prompt_body'].format(**_render_values(template, values))}"
    )


__all__ = [
    "get_template",
    "list_templates",
    "render_template",
    "render_template_draft",
    "validate_template_values",
]
