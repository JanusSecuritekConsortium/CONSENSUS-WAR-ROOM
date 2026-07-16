from __future__ import annotations

import logging
import os
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
provider_error_gate = ProviderErrorGate()

BRIEF_PROMPTS = {
    "Morning Brief": (
        "Prepare the AURELIUS morning brief. Summarize the most important operational, "
        "geopolitical, and market items concisely. Mark uncertainty and do not invent facts."
    ),
    "End-of-Day Shutdown": (
        "Prepare the AURELIUS end-of-day shutdown brief. Summarize material developments, "
        "open risks, and items requiring attention tomorrow. Mark uncertainty and do not invent facts."
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
    prompt = BRIEF_PROMPTS[label]
    content = call_msty(prompt, label, scheduled=scheduled)
    if content is None:
        return None
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    return f"{label} - {timestamp}\n\n{content}"


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


def run_scheduler() -> None:
    import schedule

    schedule.every().day.at("08:00").do(send_morning_brief)
    schedule.every().day.at("18:00").do(send_end_of_day_shutdown)
    while True:
        schedule.run_pending()
        time.sleep(60)


def main() -> int:
    global BOT
    configure_logging()
    try:
        token = validate_startup()
    except RuntimeError as exc:
        LOGGER.error("%s", exc)
        return 1

    BOT = create_bot(token)
    threading.Thread(target=run_scheduler, daemon=True, name="aurelius-scheduler").start()
    LOGGER.info("AURELIUS Telegram assistant started with Msty provider routing.")
    BOT.infinity_polling()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
