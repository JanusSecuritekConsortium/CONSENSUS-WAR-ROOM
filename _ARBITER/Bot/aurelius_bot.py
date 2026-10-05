from __future__ import annotations

import logging
import os
import re
import sys
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Optional

from dotenv import load_dotenv

SYSTEM_ROOT = Path(__file__).resolve().parents[2]
if str(SYSTEM_ROOT) not in sys.path:
    sys.path.insert(0, str(SYSTEM_ROOT))

from integrations.msty.aurelius_provider import (  # noqa: E402
    ProviderErrorGate,
    resolve_aurelius_provider_config,
    scheduled_provider_error_message,
)

load_dotenv(SYSTEM_ROOT / ".env")

LOGGER = logging.getLogger("aurelius.telegram")
LOG_DIR = Path(os.getenv("AURELIUS_LOG_DIR", str(Path(__file__).resolve().parent / "logs")))
MODEL = os.getenv("AURELIUS_MODEL", "mistral")
CHAT_ID: Optional[str] = os.getenv("AURELIUS_TELEGRAM_CHAT_ID") or os.getenv("TELEGRAM_CHAT_ID")
BOT: Any = None
AGENT_OPERATOR: Any = None
provider_error_gate = ProviderErrorGate()
TELEGRAM_INITIAL_RETRY_SECONDS = 3
TELEGRAM_MAX_RETRY_SECONDS = 60

BRIEF_PROMPTS = {
    "Morning Brief": (
        "Prepare a concise AURELIUS morning brief using only facts returned by tools or "
        "source material supplied during this run. Never rely on model memory for current "
        "events, dates, prices, percentages, market movements, or political developments. "
        "Never print bracketed placeholders or sample values. Include a development only "
        "when its source, publication time, and direct URL are available. Every market value "
        "must include its as-of time and source. If no current sources were successfully "
        "verified, return exactly: NO VERIFIED CURRENT DATA — No factual morning brief was generated. "
        "Return plain text only; the delivery wrapper adds the title and timestamp."
    ),
    "End-of-Day Shutdown": (
        "Prepare a concise AURELIUS end-of-day report using only task activity, tool results, "
        "documents, or other evidence supplied during this run. Never invent completed work, "
        "open work, blockers, deadlines, events, or tomorrow's priorities. Never print bracketed "
        "placeholders or sample values. State unavailable information as unavailable. If no "
        "operational evidence was successfully verified, return exactly: NO VERIFIED ACTIVITY — "
        "No factual end-of-day report was generated. Return plain text only; the delivery wrapper "
        "adds the title and timestamp."
    ),
}


def configure_logging() -> None:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    if LOGGER.handlers:
        return
    formatter = logging.Formatter("%(asctime)s %(levelname)s %(message)s")
    file_handler = logging.FileHandler(LOG_DIR / "aurelius_bot.log", encoding="utf-8")
    file_handler.setFormatter(formatter)
    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(formatter)
    LOGGER.addHandler(file_handler)
    LOGGER.addHandler(stream_handler)
    LOGGER.setLevel(logging.INFO)


def log_once(context: str, reason: str) -> bool:
    if not provider_error_gate.should_log(reason):
        return False
    LOGGER.error("%s: %s", context, reason)
    return True


def validate_startup(environ: Optional[Mapping[str, str]] = None) -> str:
    env = os.environ if environ is None else environ
    token = env.get("TELEGRAM_BOT_TOKEN", "").strip()
    if not token:
        raise RuntimeError(
            "Missing TELEGRAM_BOT_TOKEN. Set it before starting the AURELIUS Telegram bot."
        )

    provider_config = resolve_aurelius_provider_config(env)
    if not provider_config.ready:
        log_once("startup", scheduled_provider_error_message(provider_config))
    return token


def send_telegram_message(message: str, chat_id: Optional[str] = None) -> bool:
    target = chat_id or CHAT_ID
    if BOT is None:
        log_once("telegram", "Telegram bot is not initialized")
        return False
    if not target:
        log_once("telegram", "Telegram chat id not configured; send /start to register a chat")
        return False
    try:
        BOT.send_message(target, message)
        return True
    except Exception as exc:
        log_once("telegram", f"Telegram send failed: {exc}")
        return False


def call_msty(prompt: str, context: str, scheduled: bool = False) -> Optional[str]:
    if not scheduled:
        try:
            from integrations.odysseus.client import OdysseusConfig
            from assistant.agent.config import AgentConfig
            odysseus_enabled = OdysseusConfig.from_env().enabled
            agent_enabled = False if odysseus_enabled else AgentConfig.from_env().enabled
            if odysseus_enabled or agent_enabled:
                global AGENT_OPERATOR
                if AGENT_OPERATOR is None:
                    from integrations.msty.aurelius import AureliusOperator
                    AGENT_OPERATOR = AureliusOperator()
                return (AGENT_OPERATOR.run_odysseus(prompt).text if odysseus_enabled
                        else AGENT_OPERATOR.run_agent(prompt).text)
        except Exception as error:
            log_once(context, 'Agent unavailable: ' + type(error).__name__)
            return None
    provider_config = resolve_aurelius_provider_config()
    if not provider_config.ready:
        log_once(context, scheduled_provider_error_message(provider_config))
        return None

    try:
        from openai import OpenAI

        client = OpenAI(
            base_url=provider_config.api_base_url,
            api_key=os.getenv("MSTY_API_KEY", "msty"),
            timeout=60.0,
        )
        response = client.chat.completions.create(
            model=MODEL,
            messages=[
                {
                    "role": "system",
                    "content": "You are AURELIUS, the concise Telegram assistant for CONSENSUS SYSTEM.",
                },
                {"role": "user", "content": prompt},
            ],
        )
        content = response.choices[0].message.content
        return content.strip() if content else ""
    except Exception as exc:
        reason = f"Msty provider unavailable: {exc}"
        log_once(context, reason)
        if not scheduled:
            LOGGER.debug("Interactive Msty request failed", exc_info=True)
        return None


def generate_brief(label: str, scheduled: bool = False) -> Optional[str]:
    # Keep legacy outbound schedules factual too; never ask an ungrounded model for news.
    from assistant.agent.service import scheduled_report

    kind = {'Morning Brief': 'morning', 'End-of-Day Shutdown': 'evening'}[label]
    try:
        return scheduled_report(kind)
    except Exception as exc:
        log_once(label, 'Report source collection failed: ' + type(exc).__name__)
        return None


def send_brief(label: str, scheduled: bool = False, chat_id: Optional[str] = None) -> bool:
    content = generate_brief(label, scheduled=scheduled)
    if content is None:
        if not scheduled and chat_id:
            send_telegram_message("AURELIUS Msty provider unavailable. Check bot logs.", chat_id)
        return False
    return send_telegram_message(content, chat_id)


def send_morning_brief() -> bool:
    return send_brief("Morning Brief", scheduled=True)


def send_end_of_day_shutdown() -> bool:
    return send_brief("End-of-Day Shutdown", scheduled=True)


def register_handlers(bot: Any) -> None:
    @bot.message_handler(commands=["start"])
    def cmd_start(message: Any) -> None:
        global CHAT_ID
        CHAT_ID = str(message.chat.id)
        send_telegram_message("AURELIUS Telegram assistant ready. Provider: Msty.", CHAT_ID)

    @bot.message_handler(commands=["status"])
    def cmd_status(message: Any) -> None:
        provider_config = resolve_aurelius_provider_config()
        send_telegram_message(
            "\n".join(
                [
                    "AURELIUS status",
                    f"Provider: {provider_config.provider}",
                    f"Status: {provider_config.status}",
                    f"Endpoint: {provider_config.base_url or '--'}",
                    f"Reason: {provider_config.degraded_reason or '--'}",
                ]
            ),
            str(message.chat.id),
        )

    @bot.message_handler(commands=["brief"])
    def cmd_brief(message: Any) -> None:
        send_brief("Morning Brief", chat_id=str(message.chat.id))

    @bot.message_handler(commands=["ask"])
    def cmd_ask(message: Any) -> None:
        prompt = message.text.split(maxsplit=1)[1] if len(message.text.split()) > 1 else ""
        if not prompt:
            send_telegram_message("Usage: /ask <question>", str(message.chat.id))
            return
        answer = call_msty(prompt, "interactive")
        send_telegram_message(
            answer or "AURELIUS Msty provider unavailable. Check bot logs.",
            str(message.chat.id),
        )


def create_bot(token: str) -> Any:
    from telebot import TeleBot

    bot = TeleBot(token)
    register_handlers(bot)
    return bot


def sanitize_telegram_error(error: Exception, token: str) -> str:
    """Return a concise polling error without exposing the bot token."""
    detail = str(error)
    if token:
        detail = detail.replace(token, "<redacted>")
    detail = re.sub(r"/bot[^/\s\"']+", "/bot<redacted>", detail)
    if "NameResolutionError" in detail or "getaddrinfo failed" in detail:
        return "DNS resolution failed for api.telegram.org"
    return " ".join(detail.split())[:500]


def poll_telegram(bot: Any, token: str, sleep: Any = time.sleep) -> None:
    """Poll Telegram with concise logging and bounded exponential backoff."""
    retry_seconds = TELEGRAM_INITIAL_RETRY_SECONDS
    waiting_for_network = False
    while True:
        try:
            bot.get_me()
            if waiting_for_network:
                LOGGER.info("Telegram connectivity restored; polling resumed.")
            retry_seconds = TELEGRAM_INITIAL_RETRY_SECONDS
            bot.polling(non_stop=True, logger_level=logging.NOTSET)
            return
        except KeyboardInterrupt:
            raise
        except Exception as exc:
            detail = sanitize_telegram_error(exc, token)
            LOGGER.warning(
                "Telegram polling unavailable; retrying in %ss: %s",
                retry_seconds,
                detail,
            )
            waiting_for_network = True
            sleep(retry_seconds)
            retry_seconds = min(retry_seconds * 2, TELEGRAM_MAX_RETRY_SECONDS)


def run_scheduler() -> None:
    import schedule
    from assistant.agent.jobs import register_legacy_schedule

    register_legacy_schedule(schedule, send_morning_brief, send_end_of_day_shutdown)
    while True:
        schedule.run_pending()
        time.sleep(60)


def telegram_polling_enabled(environ: Optional[Mapping[str, str]] = None) -> bool:
    """Return whether this legacy service should consume inbound Telegram updates."""
    env = os.environ if environ is None else environ
    value = env.get("AURELIUS_TELEGRAM_POLLING", "1").strip().lower()
    return value not in {"0", "false", "no", "off"}


def main() -> int:
    global BOT
    configure_logging()
    try:
        token = validate_startup()
    except RuntimeError as exc:
        LOGGER.error("%s", exc)
        return 1

    BOT = create_bot(token)
    if not telegram_polling_enabled():
        LOGGER.info(
            "AURELIUS scheduled Telegram delivery started; inbound polling is owned by Msty Go."
        )
        run_scheduler()
        return 0

    threading.Thread(target=run_scheduler, daemon=True, name="aurelius-scheduler").start()
    LOGGER.info("AURELIUS Telegram assistant started with Msty provider routing.")
    poll_telegram(BOT, token)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
