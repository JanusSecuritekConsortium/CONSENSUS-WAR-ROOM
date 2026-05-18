from __future__ import annotations

from typing import Any, Dict

from core.models import NodeIdentity
from core.prompting.assembler import assemble_monolith_prompt


def build_node_prompt(node: NodeIdentity, query: str, context: Dict[str, Any]) -> str:
    return assemble_monolith_prompt(node, query, context)
