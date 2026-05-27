from __future__ import annotations

from typing import Any, Dict, Iterable, List


def flatten_text(control: object) -> List[str]:
    values: List[str] = []
    if hasattr(control, "value") and isinstance(getattr(control, "value"), str):
        values.append(getattr(control, "value"))
    content = getattr(control, "content", None)
    if content is not None:
        values.extend(flatten_text(content))
    controls = getattr(control, "controls", None)
    if isinstance(controls, Iterable):
        for child in controls:
            values.extend(flatten_text(child))
    return values


def main_layout_expands(layout: object) -> List[int]:
    shell = getattr(layout, "content", None)
    body_container = shell.controls[1]  # type: ignore[attr-defined]
    body_row = body_container.content
    return [int(control.expand) for control in body_row.controls]


def evaluate_visual_invariants(layout: object) -> Dict[str, Any]:
    texts = flatten_text(layout)
    joined = "\n".join(texts)
    expands = main_layout_expands(layout)
    shell = getattr(layout, "content", None)
    body_row = shell.controls[1].content  # type: ignore[attr-defined]
    right_column = body_row.controls[2].content
    return {
        "layout_proportions_2_6_2": expands == [2, 6, 2],
        "layout_expands": expands,
        "diagnostics_overlay_not_layout_mutation": hasattr(layout, "diagnostics_drawer") and "DIAGNOSTICS" not in joined,
        "provider_status_block_visible": "SYSTEM STATUS" in texts and "PROVIDER" in texts,
        "active_model_list_visible": "ACTIVE MODELS" in texts,
        "no_duplicate_system_status_panel": len(right_column.controls) == 2 and "SYSTEM STATUS" in texts,
        "no_duplicate_active_model_panel": texts.count("ACTIVE MODELS") == 1,
        "no_duplicate_header_logo_panel": len(getattr(getattr(layout, "content", None), "controls", [])) == 3,
    }


def assert_visual_invariants(layout: object) -> Dict[str, Any]:
    invariants = evaluate_visual_invariants(layout)
    failed = [key for key, value in invariants.items() if key != "layout_expands" and value is not True]
    if failed:
        raise AssertionError(f"GUI visual invariant failures: {', '.join(failed)}")
    return invariants
