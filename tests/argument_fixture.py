import json


def argument_fields(reason, agent=None, context=None, value="APPROVE"):
    argument = {"claim": reason[:220], "evidence": [{"source": "proposal", "detail": "Supplied proposal assertions require verification."}],
                "assumptions": ["Audit and rollback are available."], "strongest_objection": "Resource assumptions need verification.",
                "change_condition": "A verified failure of the audit or rollback plan."}
    peers = []
    disagreements = []
    rounds = (context or {}).get("deliberation", {}).get("previous_rounds", [])
    changed = ""
    if rounds:
        latest = rounds[-1]
        for peer, assessment in latest["assessments"].items():
            if peer == agent:
                if assessment["vote"] != value:
                    changed = reason
                continue
            peers.append({"peer": peer, "round": latest["round"], "claim": assessment["argument"]["claim"],
                          "stance": "support" if assessment["vote"] == value else "challenge", "reason": reason})
            if assessment["vote"] != value:
                disagreements.append(f"{peer} retains a different decision.")
    return (f"\nARGUMENT: {json.dumps(argument)}\nPEER_RESPONSES: {json.dumps(peers)}\n"
            "REVIEW_REQUIRED: false\nREVIEW_REASON: \n"
            f"VOTE_CHANGE_REASON: {changed}\nUNRESOLVED_DISAGREEMENTS: {json.dumps(disagreements)}\n")
