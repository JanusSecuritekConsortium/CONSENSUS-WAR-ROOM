from __future__ import annotations

import random
from itertools import product
from typing import Mapping, Tuple

from config.names import ARBITER, AETERNUM, BELLATOR, RATIONALIS
from ui.themes.catalog import resolve_theme_key


BOOT_NODE_IDS: Tuple[str, ...] = (RATIONALIS, AETERNUM, BELLATOR, ARBITER)

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
    ),
    "eva": (
        "synchronized",
        "pattern-stable",
        "interlock confirmed",
        "harmonics within tolerance",
        "ready for central dogma link",
    ),
    "wh40k": (
        "sanctified",
        "appeased",
        "bound to the noosphere",
        "rite accepted",
        "purity seal confirmed",
    ),
    "helldivers": (
        "authorized",
        "democracy-certified",
        "ready for liberty tasking",
        "cleared by command",
        "patriot signal confirmed",
    ),
    "arasaka": (
        "cleared",
        "audited",
        "locked to executive grid",
        "countermeasure-ready",
        "black-channel verified",
    ),
    "janus": (
        "mirrored",
        "counterpart aligned",
        "dual-channel stable",
        "reversibility checked",
        "parallax lock confirmed",
    ),
}

_THEME_NODE_SUBJECTS: Mapping[str, Mapping[str, Tuple[str, ...]]] = {
    "military": {
        RATIONALIS: ("logic matrix", "ruleset lattice", "command reason core"),
        AETERNUM: ("forecast desk", "strategic ledger", "continuity archive"),
        BELLATOR: ("threat board", "tactical grid", "engagement matrix"),
        ARBITER: ("authorization channel", "tribunal vector", "command lock"),
    },
    "eva": {
        RATIONALIS: ("CASPER logic node", "MAGI consistency lattice", "pattern analysis core"),
        AETERNUM: ("BALTHASAR forecast node", "temporal sync table", "future drift monitor"),
        BELLATOR: ("MELCHIOR defense node", "AT-field risk model", "engagement interlock"),
        ARBITER: ("MAGI consensus gate", "NERV tribunal vector", "central dogma channel"),
    },
    "wh40k": {
        RATIONALIS: ("Logis cogitator", "noospheric proof engine", "logic reliquary"),
        AETERNUM: ("Administratum archive", "chrono-rite ledger", "data-vault augur"),
        BELLATOR: ("Munitorum tacticus", "sanction protocol", "war-rite matrix"),
        ARBITER: ("Omnissiah verdict seal", "inquisitorial vector", "council rite channel"),
    },
    "helldivers": {
        RATIONALIS: ("democracy assessment engine", "civic truth core", "liberty logic lattice"),
        AETERNUM: ("freedom forecasting system", "requisition forecast board", "patriot ledger"),
        BELLATOR: ("liberty defense matrix", "stratagem safety grid", "super earth firebreak"),
        ARBITER: ("managed democracy verdict", "authorization ballot channel", "command oath relay"),
    },
    "arasaka": {
        RATIONALIS: ("compliance logic grid", "due-diligence core", "board analysis lattice"),
        AETERNUM: ("capital ledger node", "executive yield forecast", "asset continuity table"),
        BELLATOR: ("counterintelligence grid", "black/red security core", "threat acquisition channel"),
        ARBITER: ("executive verdict channel", "clearance authority bus", "corporate sanction gate"),
    },
    "janus": {
        RATIONALIS: ("analytic mirror", "cold logic core", "first-face proof channel"),
        AETERNUM: ("counterpart horizon", "dual-front forecast core", "second-face archive"),
        BELLATOR: ("Janus gatekeeper", "mirror threat core", "countermove lattice"),
        ARBITER: ("dual mandate gate", "reversibility tribunal", "one-will verdict channel"),
    },
}


def _visual_theme_key(theme_id: str) -> str:
    theme_key = resolve_theme_key(theme_id)
    return "eva" if theme_key == "nerv" else theme_key


def boot_phrase_bank(theme_id: str, node_id: str) -> Tuple[str, ...]:
    theme_key = _visual_theme_key(theme_id)
    subjects = _THEME_NODE_SUBJECTS[theme_key][node_id]
    actions = _THEME_ACTIONS[theme_key]
    return tuple(f"{subject} {action}".upper() for subject, action in product(subjects, actions))


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
