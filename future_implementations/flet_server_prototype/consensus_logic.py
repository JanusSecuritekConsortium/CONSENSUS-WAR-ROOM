
# consensus_logic.py

from consensus_config import VoteResult, VoteData
from datetime import datetime
import random
import time

def simulate_vote(monolith: str, query: str) -> VoteData:
    start = time.time()
    vote = random.choice(list(VoteResult))
    reasoning = f"{monolith} voted {vote.name.lower()} due to simulated logic."
    confidence = round(random.uniform(0.4, 0.95), 2)
    end = time.time()
    return VoteData(
        monolith=monolith,
        query=query,
        vote=vote,
        reasoning=reasoning,
        confidence=confidence,
        response_time=round(end - start, 3),
        timestamp=datetime.now(),
        session_id=datetime.now().strftime("%Y%m%d%H%M%S")
    )
