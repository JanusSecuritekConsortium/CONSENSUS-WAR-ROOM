import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from integrations.ibkr.client import IbkrAdapter


def test_ibkr_rejects_order_placement() -> None:
    adapter = IbkrAdapter({"enabled": True, "base_url": "https://example.test", "read_only": True})
    try:
        adapter.place_order({"symbol": "TEST"})
    except PermissionError:
        pass
    else:
        raise AssertionError("IBKR order placement must be rejected")


if __name__ == "__main__":
    test_ibkr_rejects_order_placement()
    print("test_ibkr_read_only_guard PASS")
