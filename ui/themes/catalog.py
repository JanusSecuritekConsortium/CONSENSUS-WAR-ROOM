from __future__ import annotations

from pathlib import Path
from typing import Dict, List

from config.names import AETERNUM, BELLATOR, RATIONALIS, TRIBUNAL_AGENT_IDS
from core.models import Theme
from ui.themes.boot_profiles import BOOT_PROFILES


SYSTEM_ROOT = Path(__file__).resolve().parents[2]
LOGO_DIR = SYSTEM_ROOT / "static" / "logos"


def _labels(
    rationalis: str,
    rationalis_core: str,
    aeternum: str,
    aeternum_core: str,
    bellator: str,
    bellator_core: str,
) -> Dict[str, Dict[str, str]]:
    return {
        RATIONALIS: {"node": rationalis, "core": rationalis_core, "monolith": RATIONALIS},
        AETERNUM: {"node": aeternum, "core": aeternum_core, "monolith": AETERNUM},
        BELLATOR: {"node": bellator, "core": bellator_core, "monolith": BELLATOR},
    }


def _interface_labels(
    history: str,
    analytics: str,
    system_status: str,
    vote_status: str,
    vote_approve: str,
    vote_deny: str,
    vote_deadlock: str,
) -> Dict[str, str]:
    return {
        "history": history,
        "analytics": analytics,
        "system_status": system_status,
        "vote_status": vote_status,
        "vote_approve": vote_approve,
        "vote_deny": vote_deny,
        "vote_deadlock": vote_deadlock,
    }


MAGI_MONOLITH_LABELS = _labels(
    "MAGI CASPER-3",
    "LOGICAL SUBSYSTEM",
    "MAGI BALTHASAR-2",
    "TEMPORAL PREDICTION CORE",
    "MAGI MELCHIOR-1",
    "PATERNAL DEFENSE PROTOCOL",
)

MAGI_INTERFACE_LABELS = _interface_labels(
    "CENTRAL DOGMA ARCHIVES",
    "PATTERN RECOGNITION SYSTEM",
    "MAGI SYSTEM STATUS",
    "CONSENSUS CALCULATION",
    "PATTERN BLUE CONFIRMED",
    "PATTERN RED DETECTED",
    "PATTERN ORANGE - INDETERMINATE",
)


THEMES: Dict[str, Theme] = {
    "military": Theme(
        key="military",
        display_name="CONSENSUS War Room",
        aliases=["MILITARY", "WAR_ROOM", "TACTICAL"],
        primary_color="#39ff14",
        secondary_color="#9bbf9b",
        accent_color="#ffbf00",
        background_color="#050806",
        surface_color="#101810",
        text_color="#d8ffe0",
        warning_color="#ffbf00",
        error_color="#ff3b30",
        font_family="Consolas, Cascadia Mono, monospace",
        logo_id="consensus",
        logo_path=str(LOGO_DIR / "consensus_logo.txt"),
        boot_profile_id="military_boot",
        loading_animation_type="tactical_green_bar",
        panel_style="terminal",
        border_style="single-line tactical",
        monolith_labels=_labels(
            "LOGICAL ANALYSIS MATRIX",
            "EXCOMM REASON CORE",
            "ECONOMIC INTELLIGENCE DIVISION",
            "EXCOMM LEDGER CORE",
            "TACTICAL OPERATIONS CENTER",
            "EXCOMM TACTICAL CORE",
        ),
        interface_labels=_interface_labels(
            "DECISION ARCHIVE",
            "INTELLIGENCE ANALYTICS",
            "EXCOMM ONLINE",
            "TRIBUNAL DELIBERATION",
            "AUTHORIZATION GRANTED",
            "AUTHORIZATION DENIED",
            "COMMAND DEADLOCK",
        ),
        muted_text="#9bbf9b",
        secondary_text="#b8d8b8",
        panel_label="#ffbf00",
        panel_value="#d8ffe0",
    ),
    "eva": Theme(
        key="eva",
        display_name="MAGI Consensus Array",
        aliases=["EVA", "EVANGELION", "MAGI"],
        primary_color="#ff7a00",
        secondary_color="#cc1f1a",
        accent_color="#00d5ff",
        background_color="#120704",
        surface_color="#24100a",
        text_color="#fff2df",
        warning_color="#ff9b00",
        error_color="#ff2d20",
        font_family="Consolas, Cascadia Mono, monospace",
        logo_id="nerv",
        logo_path=str(LOGO_DIR / "nerv_logo.txt"),
        boot_profile_id="eva_boot",
        loading_animation_type="magi_sync_rate",
        panel_style="magi diagnostic",
        border_style="segmented warning",
        monolith_labels=MAGI_MONOLITH_LABELS,
        interface_labels=MAGI_INTERFACE_LABELS,
        muted_text="#ffb38a",
        secondary_text="#ff6a4d",
        panel_label="#ff7a00",
        panel_value="#fff2df",
    ),
    "nerv": Theme(
        key="nerv",
        display_name="NERV Tribunal Interlock",
        aliases=["NERV", "EVA/NERV"],
        primary_color="#ff5400",
        secondary_color="#b11226",
        accent_color="#ffffff",
        background_color="#110607",
        surface_color="#211010",
        text_color="#fff4e8",
        warning_color="#ff9d00",
        error_color="#ff1f1f",
        font_family="Consolas, Cascadia Mono, monospace",
        logo_id="nerv",
        logo_path=str(LOGO_DIR / "nerv_logo.txt"),
        boot_profile_id="nerv_boot",
        loading_animation_type="nerv_magi_interlock",
        panel_style="nerv command",
        border_style="red alert segmented",
        monolith_labels=MAGI_MONOLITH_LABELS,
        interface_labels=MAGI_INTERFACE_LABELS,
        muted_text="#ffb199",
        secondary_text="#ff6a5f",
        panel_label="#ff5400",
        panel_value="#fff4e8",
    ),
    "wh40k": Theme(
        key="wh40k",
        display_name="Cogitator Tribunal",
        aliases=["WH40K", "WARHAMMER", "COGITATOR"],
        primary_color="#d9a441",
        secondary_color="#8c1d18",
        accent_color="#e8d8a8",
        background_color="#0c0907",
        surface_color="#1b1510",
        text_color="#f4ead2",
        warning_color="#d9a441",
        error_color="#b82020",
        font_family="Consolas, Cascadia Mono, monospace",
        logo_id="cogitator",
        logo_path=str(LOGO_DIR / "cogitator_logo.txt"),
        boot_profile_id="wh40k_boot",
        loading_animation_type="cogitator_litany",
        panel_style="imperial cogitator",
        border_style="gothic double",
        monolith_labels=_labels(
            "ADEPTUS MECHANICUS LOGIS",
            "COGITATOR LOGIS CORE",
            "ADMINISTRATUM HISTORICUS",
            "IMPERIAL ARCHIVE CORE",
            "MUNITORUM TACTICUS",
            "TACTICA SANCTORUM CORE",
        ),
        interface_labels=_interface_labels(
            "IMPERIAL ARCHIVE SANCTORUM",
            "COGITATOR AUGURY",
            "MACHINE SPIRIT PURITY",
            "COUNCIL OF TERRA DELIBERATION",
            "IMPERIAL SANCTION GRANTED",
            "IMPERIAL SANCTION DENIED",
            "COUNCIL DISCORD - INQUISITORIAL REVIEW",
        ),
        muted_text="#c8b894",
        secondary_text="#e8d8a8",
        panel_label="#d9a441",
        panel_value="#f4ead2",
    ),
    "helldivers": Theme(
        key="helldivers",
        display_name="Managed Democracy Tribunal",
        aliases=["HELLDIVERS", "SUPER_EARTH", "DEMOCRACY"],
        primary_color="#1f8cff",
        secondary_color="#101820",
        accent_color="#f5f5f5",
        background_color="#061018",
        surface_color="#102033",
        text_color="#e8f4ff",
        warning_color="#ffd100",
        error_color="#ff3b30",
        font_family="Consolas, Cascadia Mono, monospace",
        logo_id="helldivers",
        logo_path=str(LOGO_DIR / "helldivers_logo.txt"),
        boot_profile_id="helldivers_boot",
        loading_animation_type="managed_democracy",
        panel_style="super earth command",
        border_style="hazard stripe",
        monolith_labels=_labels(
            "DEMOCRACY ASSESSMENT ENGINE",
            "CIVIC TRUTH CORE",
            "FREEDOM FORECASTING SYSTEM",
            "REQUISITION FORECAST CORE",
            "LIBERTY DEFENSE MATRIX",
            "SUPER EARTH FIREBREAK CORE",
        ),
        interface_labels=_interface_labels(
            "PATRIOTIC OPERATIONS RECORD",
            "MANAGED DEMOCRACY INSIGHTS",
            "SUPER EARTH: ONLINE",
            "DEMOCRATIC DELIBERATION",
            "LIBERTY ASSURED",
            "FREEDOM ENDANGERED",
            "DEMOCRACY COMPROMISED",
        ),
        muted_text="#9fcfff",
        secondary_text="#b9ddff",
        panel_label="#1f8cff",
        panel_value="#e8f4ff",
    ),
    "arasaka": Theme(
        key="arasaka",
        display_name="Arasaka Executive Tribunal",
        aliases=["ARASAKA", "CORPORATE", "SECURITY_GRID"],
        primary_color="#ff1f2d",
        secondary_color="#1a1a1a",
        accent_color="#f5f5f5",
        background_color="#050505",
        surface_color="#151515",
        text_color="#f2f2f2",
        warning_color="#ffb000",
        error_color="#ff1f2d",
        font_family="Consolas, Cascadia Mono, monospace",
        logo_id="arasaka",
        logo_path=str(LOGO_DIR / "arasaka_logo.txt"),
        boot_profile_id="arasaka_boot",
        loading_animation_type="corporate_clearance_grid",
        panel_style="corporate blackwall",
        border_style="thin red corporate",
        monolith_labels=_labels(
            "COMPLIANCE LOGIC GRID",
            "DUE-DILIGENCE CORE",
            "CAPITAL LEDGER NODE",
            "EXECUTIVE YIELD CORE",
            "COUNTERINTELLIGENCE GRID",
            "BLACK/RED SECURITY CORE",
        ),
        interface_labels=_interface_labels(
            "CORPORATE MEMORY VAULT",
            "COUNTERPARTY EXPOSURE ANALYTICS",
            "ARASAKA CLEARANCE GRID",
            "EXECUTIVE TRIBUNAL REVIEW",
            "CORPORATE SANCTION GRANTED",
            "CORPORATE SANCTION DENIED",
            "BOARD DEADLOCK - COUNTERINTELLIGENCE REVIEW",
        ),
        muted_text="#b8b8b8",
        secondary_text="#ff6b70",
        panel_label="#ff5a5f",
        panel_value="#f2f2f2",
    ),
    "janus": Theme(
        key="janus",
        display_name="Janus Security Consortium",
        aliases=["JANUS", "DUAL_FRONT", "MIRROR"],
        primary_color="#ff4fd8",
        secondary_color="#5d2a6f",
        accent_color="#ffc2f2",
        background_color="#100713",
        surface_color="#1f1028",
        text_color="#ffeafd",
        warning_color="#c084fc",
        error_color="#ff5f57",
        font_family="Consolas, Cascadia Mono, monospace",
        logo_id="janus",
        logo_path=str(LOGO_DIR / "janus_logo.txt"),
        boot_profile_id="janus_boot",
        loading_animation_type="dual_front_mirror",
        panel_style="dual intelligence",
        border_style="split cold-line",
        monolith_labels=_labels(
            "ANALYTIC MIRROR",
            "COLD LOGIC CORE",
            "COUNTERPART HORIZON",
            "DUAL-FRONT FORECAST CORE",
            "JANUS GATEKEEPER",
            "MIRROR THREAT CORE",
        ),
        interface_labels=_interface_labels(
            "DUAL-FACE CASE ARCHIVE",
            "MIRROR ANALYSIS ARRAY",
            "DUAL CHANNEL OPEN",
            "COUNTERPART DELIBERATION",
            "DUOBUS VULTIBUS - CONSENT",
            "DUOBUS VULTIBUS - REJECTION",
            "ANALYTIC MIRROR DEADLOCK",
        ),
        muted_text="#d9a7ec",
        secondary_text="#ffc2f2",
        panel_label="#ff4fd8",
        panel_value="#ffeafd",
    ),
}


THEME_ALIASES: Dict[str, str] = {
    alias.upper(): key
    for key, theme in THEMES.items()
    for alias in [key, *theme.aliases]
}

GUI_THEME_KEYS = ("eva", "arasaka", "janus", "wh40k", "helldivers", "military")
GUI_THEME_FAMILY_KEYS = {"nerv": "eva"}


def resolve_theme_key(theme_key: str) -> str:
    normalized = theme_key.strip()
    return THEME_ALIASES.get(normalized.upper(), normalized.lower())


def get_gui_theme_key(theme_key: str) -> str:
    resolved = resolve_theme_key(theme_key)
    return GUI_THEME_FAMILY_KEYS.get(resolved, resolved)


def get_gui_theme_options() -> List[Theme]:
    return [THEMES[key] for key in GUI_THEME_KEYS]


def validate_theme_catalog() -> None:
    required = {"military", "eva", "nerv", "wh40k", "helldivers", "arasaka", "janus"}
    missing = required - set(THEMES)
    if missing:
        raise RuntimeError(f"Missing required themes: {', '.join(sorted(missing))}")

    seen_aliases: Dict[str, str] = {}
    for key, theme in THEMES.items():
        if key != theme.key:
            raise RuntimeError(f"Theme key mismatch: {key} != {theme.key}")
        if not Path(theme.logo_path).exists():
            raise RuntimeError(f"Theme {key} logo asset is missing: {theme.logo_path}")
        if theme.boot_profile_id not in BOOT_PROFILES:
            raise RuntimeError(f"Theme {key} boot profile is missing: {theme.boot_profile_id}")
        if BOOT_PROFILES[theme.boot_profile_id].theme_key != key:
            raise RuntimeError(f"Theme {key} boot profile points at {BOOT_PROFILES[theme.boot_profile_id].theme_key}")
        missing_labels = set(TRIBUNAL_AGENT_IDS) - set(theme.monolith_labels)
        if missing_labels:
            raise RuntimeError(
                f"Theme {key} is missing monolith labels for: {', '.join(sorted(missing_labels))}"
            )
        required_interface_labels = {
            "history",
            "analytics",
            "system_status",
            "vote_status",
            "vote_approve",
            "vote_deny",
            "vote_deadlock",
        }
        missing_interface_labels = required_interface_labels - set(theme.interface_labels)
        if missing_interface_labels:
            raise RuntimeError(
                f"Theme {key} is missing interface labels for: {', '.join(sorted(missing_interface_labels))}"
            )
        for field_name in (
            "primary_color",
            "secondary_color",
            "accent_color",
            "background_color",
            "surface_color",
            "text_color",
            "warning_color",
            "error_color",
            "font_family",
            "logo_id",
            "logo_path",
            "boot_profile_id",
            "loading_animation_type",
            "panel_style",
            "border_style",
            "muted_text",
            "secondary_text",
            "panel_label",
            "panel_value",
        ):
            if not getattr(theme, field_name):
                raise RuntimeError(f"Theme {key} is missing {field_name}")
        for alias in theme.aliases:
            normalized = alias.upper()
            owner = seen_aliases.setdefault(normalized, key)
            if owner != key:
                raise RuntimeError(f"Theme alias {alias} is assigned to both {owner} and {key}")


def list_themes() -> None:
    validate_theme_catalog()
    for key in sorted(THEMES):
        theme = THEMES[key]
        print(
            f"{key} | {theme.display_name} | aliases={', '.join(theme.aliases)} | "
            f"boot_profile={theme.boot_profile_id}"
        )
