from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.models import FinalVerdict, TribunalResult
from voice.arbiter_verdict_voice import dispatch_arbiter_verdict_voice


def _coerce_verdict(value: str) -> FinalVerdict:
    normalized = value.strip().upper()
    if normalized == "CLASSIFICATION_FAILURE":
        return FinalVerdict.NO_CONSENSUS
    if normalized == "ESCALATION_REQUIRED":
        return FinalVerdict.ESCALATE
    if normalized == "DENY":
        return FinalVerdict.DENY
    if normalized in FinalVerdict.__members__:
        return FinalVerdict[normalized]
    try:
        return FinalVerdict(normalized)
    except ValueError:
        return FinalVerdict.ERROR


def main() -> int:
    parser = argparse.ArgumentParser(description="Play a manual ARBITER/GLaDOS verdict announcement.")
    parser.add_argument("--verdict", required=True, help="Terminal verdict, for example NO_CONSENSUS.")
    parser.add_argument("--proposal-id", default="manual_voice_test", help="Synthetic proposal id for once-only dispatch.")
    parser.add_argument("--terminal-branch", default="", help="Optional terminal branch, for example classification_failure.")
    args = parser.parse_args()

    verdict = _coerce_verdict(args.verdict)
    terminal_branch = args.terminal_branch or ("classification_failure" if args.verdict.upper() == "CLASSIFICATION_FAILURE" else "")
    result = TribunalResult(
        query="Manual ARBITER voice test.",
        verdict=verdict,
        confidence=0.0,
        reason="Manual voice test.",
        votes={},
        vote_distribution={},
        quorum_met=False,
        review_triggers=["classification_failure"] if terminal_branch == "classification_failure" else [],
        session_id=args.proposal_id,
        theme="military",
        terminal_branch=terminal_branch,
        proposal_classification={"status": "FAILED"} if terminal_branch == "classification_failure" else {},
    )
    dispatch = dispatch_arbiter_verdict_voice(result, async_dispatch=False, enabled=True)
    print(f"{dispatch.status}: {dispatch.text}")
    if dispatch.degraded_reason:
        print(f"degraded_reason: {dispatch.degraded_reason}")
    return 0 if dispatch.status in {"success", "degraded"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
