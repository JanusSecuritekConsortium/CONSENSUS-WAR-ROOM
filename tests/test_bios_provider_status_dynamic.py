from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from config.version import SYSTEM_VERSION
import ui.animations.bios_boot as bios_boot
from ui.animations.bios_boot import generate_bios_boot_lines


READY_PROVIDER = {
    "status": "ready",
    "active_backend": "msty-local",
    "base_url": "http://127.0.0.1:11964",
    "model_count": 9,
    "missing_required_models": {},
    "mock_fallback_enabled": True,
}

DEGRADED_PROVIDER = {
    "status": "degraded",
    "active_backend": "msty-local",
    "base_url": "http://127.0.0.1:11964",
    "model_count": 2,
    "missing_required_models": {"BELLATOR": "cogito:latest"},
    "mock_fallback_enabled": True,
}

OFFLINE_WITH_FALLBACK = {
    "status": "offline",
    "active_backend": "msty-local",
    "base_url": "http://127.0.0.1:11964",
    "model_count": 0,
    "missing_required_models": {},
    "mock_fallback_enabled": True,
}

OFFLINE_STRICT = {
    "status": "offline",
    "active_backend": "msty-local",
    "base_url": "http://127.0.0.1:11964",
    "model_count": 0,
    "missing_required_models": {},
    "mock_fallback_enabled": False,
}


def _boot_text(provider_status: dict) -> str:
    return "\n".join(
        generate_bios_boot_lines(
            "EVA",
            SYSTEM_VERSION,
            include_logo=False,
            include_loading=False,
            provider_status=provider_status,
        )
    )


def test_ready_provider_boot_post_uses_ok_not_warn() -> None:
    text = _boot_text(READY_PROVIDER)

    assert "[OK] MAGI Runtime" in text
    assert "http://127.0.0.1:11964" not in text
    assert "models=9" not in text
    assert "[WARN] MSTY PROVIDER DEGRADED" not in text


def test_degraded_provider_boot_post_uses_warn() -> None:
    text = _boot_text(DEGRADED_PROVIDER)

    assert "[WARN] MSTY PROVIDER DEGRADED (1 missing)" in text
    assert "http://127.0.0.1:11964" not in text


def test_offline_provider_with_fallback_uses_fallback_warning() -> None:
    text = _boot_text(OFFLINE_WITH_FALLBACK)

    assert "[WARN] PROVIDER OFFLINE - MOCK FALLBACK ACTIVE" in text
    assert "http://127.0.0.1:11964" not in text


def test_offline_provider_without_fallback_uses_error() -> None:
    text = _boot_text(OFFLINE_STRICT)

    assert "[ERROR] MSTY PROVIDER OFFLINE" in text
    assert "http://127.0.0.1:11964" not in text


def test_ready_boot_output_has_no_hardcoded_degraded_warning() -> None:
    text = _boot_text(READY_PROVIDER)

    assert "MSTY PROVIDER DEGRADED" not in text


def test_boot_requires_injected_provider_context() -> None:
    text = "\n".join(
        generate_bios_boot_lines(
            "ARASAKA",
            SYSTEM_VERSION,
            include_logo=False,
            include_loading=False,
            provider_status=None,
        )
    )

    assert "[WARN] PROVIDER STATUS UNRESOLVED" in text
    assert "MSTY PROVIDER DEGRADED" not in text
    context = bios_boot._provider_boot_context(READY_PROVIDER)
    assert context["status"] == "ready"


if __name__ == "__main__":
    test_ready_provider_boot_post_uses_ok_not_warn()
    test_degraded_provider_boot_post_uses_warn()
    test_offline_provider_with_fallback_uses_fallback_warning()
    test_offline_provider_without_fallback_uses_error()
    test_ready_boot_output_has_no_hardcoded_degraded_warning()
    test_boot_requires_injected_provider_context()
    print("test_bios_provider_status_dynamic PASS")
