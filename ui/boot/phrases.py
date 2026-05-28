from __future__ import annotations

import random
from itertools import product
from typing import Mapping, Tuple

from config.names import ARBITER, AETERNUM, BELLATOR, RATIONALIS
from ui.themes.catalog import resolve_theme_key


BOOT_NODE_IDS: Tuple[str, ...] = (BELLATOR, AETERNUM, RATIONALIS, ARBITER)

NODE_ONLINE_PREFIXES: Mapping[str, str] = {
    RATIONALIS: "RATIONALIS....ONLINE",
    AETERNUM: "AETERNUM......ONLINE",
    BELLATOR: "BELLATOR......ONLINE",
    ARBITER: "ARBITER.......ONLINE",
}

_THEME_ACTIONS: Mapping[str, Tuple[str, ...]] = {
    "military": (
        "verified",
        "synchronized",
        "cleared for command",
        "locked to war room bus",
        "standing by",
        "operational",
    ),
    "eva": (
        "synchronized",
        "pattern-stable",
        "interlock confirmed",
        "harmonics within tolerance",
        "ready for central dogma link",
        "cortical bridge aligned",
    ),
    "nerv": (
        "synchronized",
        "pattern-stable",
        "interlock confirmed",
        "harmonics within tolerance",
        "ready for central dogma link",
        "cortical bridge aligned",
    ),
    "wh40k": (
        "noospheric sanctified",
        "omnissiah appeased",
        "bound to the noosphere",
        "sanction rite accepted",
        "omnissiah purity seal confirmed",
        "noospheric machine spirit placated",
    ),
    "helldivers": (
        "authorized",
        "democracy-certified",
        "ready for liberty tasking",
        "cleared by command",
        "patriot signal confirmed",
        "managed democracy approved",
    ),
    "arasaka": (
        "cleared",
        "audited",
        "locked to executive grid",
        "countermeasure-ready",
        "black-channel verified",
        "corporate oversight confirmed",
    ),
    "janus": (
        "mirrored",
        "counterpart aligned",
        "dual-channel stable",
        "reversibility checked",
        "parallax lock confirmed",
        "twin-core synchronized",
    ),
}

_THEME_NODE_SUBJECTS: Mapping[str, Mapping[str, Tuple[str, ...]]] = {
    "military": {
        RATIONALIS: ("logic matrix", "ruleset lattice", "command reason core", "EXCOMM logic engine"),
        AETERNUM: ("forecast desk", "strategic ledger", "continuity archive", "AETERNUM memory context"),
        BELLATOR: ("threat board", "tactical grid", "engagement matrix", "BELLATOR tactical assessor"),
        ARBITER: ("authorization channel", "tribunal vector", "command lock", "verdict transmission channel"),
    },
    "eva": {
        RATIONALIS: ("CASPER logic node", "MAGI consistency lattice", "pattern analysis core", "RATIONALIS logic engine"),
        AETERNUM: ("BALTHASAR forecast node", "temporal sync table", "future drift monitor", "AETERNUM temporal analyst"),
        BELLATOR: ("MELCHIOR defense node", "AT-field risk model", "engagement interlock", "BELLATOR tactical assessor"),
        ARBITER: ("MAGI consensus gate", "NERV tribunal vector", "central dogma channel", "ARBITER judgement gate"),
    },
    "nerv": {
        RATIONALIS: ("CASPER scientific analysis core", "MAGI consistency lattice", "pattern analysis core", "RATIONALIS logic engine"),
        AETERNUM: ("BALTHASAR maternal intuition core", "temporal sync table", "future drift monitor", "AETERNUM temporal analyst"),
        BELLATOR: ("MELCHIOR paternal instinct core", "AT-field risk model", "engagement interlock", "BELLATOR tactical assessor"),
        ARBITER: ("MAGI consensus gate", "NERV tribunal vector", "central dogma channel", "ARBITER judgement gate"),
    },
    "wh40k": {
        RATIONALIS: ("Logis cogitator", "noospheric proof engine", "logic reliquary", "rationalis cogitator"),
        AETERNUM: ("Administratum archive", "chrono-rite ledger", "data-vault augur", "aeternum data-vault"),
        BELLATOR: ("Munitorum tacticus", "sanction protocol", "war-rite matrix", "bellator tactica engine"),
        ARBITER: ("Omnissiah verdict seal", "inquisitorial vector", "council rite channel", "arbiter holy synod"),
    },
    "helldivers": {
        RATIONALIS: ("democracy assessment engine", "civic truth core", "liberty logic lattice", "rationalis patriot protocol"),
        AETERNUM: ("freedom forecasting system", "requisition forecast board", "patriot ledger", "aeternum freedom forecast"),
        BELLATOR: ("liberty defense matrix", "stratagem safety grid", "super earth firebreak", "bellator threat prioritizer"),
        ARBITER: ("managed democracy verdict", "authorization ballot channel", "command oath relay", "arbiter liberty authorization"),
    },
    "arasaka": {
        RATIONALIS: ("compliance logic grid", "due-diligence core", "board analysis lattice", "rationalis executive logic"),
        AETERNUM: ("capital ledger node", "executive yield forecast", "asset continuity table", "aeternum capital forecast"),
        BELLATOR: ("counterintelligence grid", "black/red security core", "threat acquisition channel", "bellator counter-intrusion matrix"),
        ARBITER: ("executive verdict channel", "clearance authority bus", "corporate sanction gate", "arbiter corporate oversight"),
    },
    "janus": {
        RATIONALIS: ("analytic mirror", "cold logic core", "first-face proof channel", "rationalis dual-vector mirror"),
        AETERNUM: ("counterpart horizon", "dual-front forecast core", "second-face archive", "aeternum bifurcated horizon"),
        BELLATOR: ("Janus gatekeeper", "mirror threat core", "countermove lattice", "bellator mirrored response"),
        ARBITER: ("dual mandate gate", "reversibility tribunal", "one-will verdict channel", "arbiter twin-core gate"),
    },
}

_DIRECT_NODE_PHRASES: Mapping[str, Mapping[str, Tuple[str, ...]]] = {
    "eva": {
        RATIONALIS: (
            "PATTERN ANALYSIS CORE READY FOR CENTRAL DOGMA LINK",
            "LOGIC MATRICES SYNCHRONIZED",
            "HEURISTIC LATTICE CALIBRATED",
            "DECISION ENGINE READY",
            "STRATEGIC REASONING MESH STABLE",
        ),
        AETERNUM: (
            "BALTHASAR FORECAST NODE PATTERN-STABLE",
            "TEMPORAL VECTOR ENGINE LOCKED",
            "LONG-HORIZON FORECAST ENGINE READY",
            "PROBABILITY CASCADE STABILIZED",
            "FUTURE BRANCH INDEX SYNCHRONIZED",
        ),
        BELLATOR: (
            "ENGAGEMENT INTERLOCK HARMONICS WITHIN TOLERANCE",
            "THREAT PRIORITIZATION MATRIX READY",
            "ESCALATION HEURISTICS NOMINAL",
            "STRATEGIC RESPONSE GRID SYNCHRONIZED",
            "ENGAGEMENT DOCTRINE VERIFIED",
        ),
        ARBITER: (
            "NERV TRIBUNAL VECTOR PATTERN-STABLE",
            "CONSENSUS VECTOR STABLE",
            "TRIBUNAL CORE SYNCHRONIZED",
            "VERDICT ENGINE NOMINAL",
            "CENTRAL ADJUDICATION MATRIX ONLINE",
        ),
    },
    "nerv": {
        RATIONALIS: (
            "PATTERN ANALYSIS CORE READY FOR CENTRAL DOGMA LINK",
            "LOGIC MATRICES SYNCHRONIZED",
            "HEURISTIC LATTICE CALIBRATED",
            "DECISION ENGINE READY",
            "STRATEGIC REASONING MESH STABLE",
        ),
        AETERNUM: (
            "BALTHASAR FORECAST NODE PATTERN-STABLE",
            "TEMPORAL VECTOR ENGINE LOCKED",
            "LONG-HORIZON FORECAST ENGINE READY",
            "PROBABILITY CASCADE STABILIZED",
            "FUTURE BRANCH INDEX SYNCHRONIZED",
        ),
        BELLATOR: (
            "ENGAGEMENT INTERLOCK HARMONICS WITHIN TOLERANCE",
            "THREAT PRIORITIZATION MATRIX READY",
            "ESCALATION HEURISTICS NOMINAL",
            "STRATEGIC RESPONSE GRID SYNCHRONIZED",
            "ENGAGEMENT DOCTRINE VERIFIED",
        ),
        ARBITER: (
            "NERV TRIBUNAL VECTOR PATTERN-STABLE",
            "CONSENSUS VECTOR STABLE",
            "TRIBUNAL CORE SYNCHRONIZED",
            "VERDICT ENGINE NOMINAL",
            "CENTRAL ADJUDICATION MATRIX ONLINE",
        ),
    },
}


def _theme_key(theme_id: str) -> str:
    return resolve_theme_key(theme_id)


def boot_phrase_bank(theme_id: str, node_id: str) -> Tuple[str, ...]:
    theme_key = _theme_key(theme_id)
    subjects = _THEME_NODE_SUBJECTS[theme_key][node_id]
    actions = _THEME_ACTIONS[theme_key]
    generated = tuple(f"{subject} {action}".upper() for subject, action in product(subjects, actions))
    direct = _DIRECT_NODE_PHRASES.get(theme_key, {}).get(node_id, ())
    return tuple(dict.fromkeys((*direct, *generated)))


def all_theme_boot_phrases(theme_id: str) -> Tuple[str, ...]:
    phrases = []
    for node_id in BOOT_NODE_IDS:
        phrases.extend(boot_phrase_bank(theme_id, node_id))
    return tuple(phrases)


def theme_boot_phrase_count(theme_id: str) -> int:
    return len(set(all_theme_boot_phrases(theme_id)))


def node_boot_phrase(theme_id: str, node_id: str, rng: random.Random) -> str:
    return rng.choice(boot_phrase_bank(theme_id, node_id))


def node_boot_lines(theme_id: str, rng: random.Random) -> Tuple[str, ...]:
    return tuple(
        f"{NODE_ONLINE_PREFIXES[node_id]} :: {node_boot_phrase(theme_id, node_id, rng)}"
        for node_id in BOOT_NODE_IDS
    )


__all__ = [
    "BOOT_NODE_IDS",
    "NODE_ONLINE_PREFIXES",
    "all_theme_boot_phrases",
    "boot_phrase_bank",
    "node_boot_lines",
    "node_boot_phrase",
    "theme_boot_phrase_count",
]
