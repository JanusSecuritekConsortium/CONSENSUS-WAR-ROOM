import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from integrations.factal.client import FactalAdapter


def test_factal_is_disabled_without_key_by_default() -> None:
    assert FactalAdapter({"enabled": False}).health_check()["status"] == "DISABLED"
    assert FactalAdapter({"enabled": True}).health_check()["status"] == "MISSING_CREDENTIALS"


if __name__ == "__main__":
    test_factal_is_disabled_without_key_by_default()
    print("test_factal_adapter_disabled_without_key PASS")
