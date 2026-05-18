from __future__ import annotations

import textwrap
from typing import Any, Dict

from config.names import TRIBUNAL_AGENT_IDS
from core.models import NodeIdentity, Theme, TribunalResult
from ui.animations.bios_boot import render_bios_boot_console


def render_boot(
    theme: Theme,
    speed: float = 0.08,
    seed: int | None = None,
    provider_status: Dict[str, Any] | None = None,
) -> None:
    render_bios_boot_console(theme_id=theme.key, speed="random", seed=seed, provider_status=provider_status)


def render_node_roster(theme: Theme, nodes: Dict[str, NodeIdentity]) -> None:
    print("NODE ROSTER")
    print("-" * 72)
    for key in TRIBUNAL_AGENT_IDS:
        node = nodes[key]
        alias = theme.monolith_labels[key]
        print(
            f"{node.symbol} | {alias['node']} | {alias['core']} | "
            f"{alias['monolith']} | role={node.role} | model={node.model}"
        )
    print()


def render_result(result: TribunalResult, theme: Theme) -> None:
    print("=" * 72)
    print(f"FINAL VERDICT: {result.verdict.value} | confidence={result.confidence:.0%}")
    print(f"Session: {result.session_id} | Theme: {theme.key}")
    print(f"Reason: {result.reason}")
    if result.review_triggers:
        print("Review triggers: " + ", ".join(result.review_triggers))
    print("-" * 72)
    for key in TRIBUNAL_AGENT_IDS:
        vote = result.votes[key]
        alias = theme.monolith_labels[key]
        print(f"{alias['monolith']} / {alias['node']}: {vote.vote.value} ({vote.confidence:.0%})")
        print(textwrap.fill(vote.reasoning, width=70, initial_indent="  ", subsequent_indent="  "))
        if vote.conditions:
            print("  Conditions: " + "; ".join(vote.conditions))
    print("=" * 72)
