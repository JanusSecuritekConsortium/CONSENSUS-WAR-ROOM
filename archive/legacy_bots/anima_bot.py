from __future__ import annotations

import os
import subprocess
import sys
import threading
import time
import uuid
from datetime import datetime
from email.message import EmailMessage
from pathlib import Path
from typing import Any

import openai
import requests
import schedule
import smtplib
from dotenv import load_dotenv
from ib_insync import IB, MarketOrder, Stock
from telebot import TeleBot

SYSTEM_ROOT = Path(__file__).resolve().parents[2]
if str(SYSTEM_ROOT) not in sys.path:
    sys.path.insert(0, str(SYSTEM_ROOT))

from integrations.msty.aurelius_provider import (  # noqa: E402
    ProviderErrorGate,
    resolve_aurelius_provider_config,
    scheduled_provider_error_message,
)

load_dotenv()

API_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
N8N_WEBHOOK_URL = os.getenv("N8N_WEBHOOK_URL", "http://localhost:5678/webhook")
LOG_DIR = Path(os.getenv("AURELIUS_LOG_DIR", "F:/ANIMA - AI Agent/Bot/logs"))
MSTY_API_KEY = os.getenv("MSTY_API_KEY", "msty")

if not API_TOKEN:
    raise EnvironmentError("Missing TELEGRAM_BOT_TOKEN. Check your .env file.")

bot = TeleBot(API_TOKEN)
CHAT_ID = None
user_modes: dict[int, str] = {}
current_model = os.getenv("AURELIUS_MODEL", "mistral")
provider_error_gate = ProviderErrorGate()


def send_email_proton(to: str, subject: str, body: str) -> None:
    msg = EmailMessage()
    msg["From"] = os.getenv("PROTONMAIL_USER")
    msg["To"] = to
    msg["Subject"] = subject
    msg.set_content(body)
    with smtplib.SMTP("127.0.0.1", 1025) as server:
        server.login(msg["From"], os.getenv("PROTONMAIL_PASSWORD"))
        server.send_message(msg)


def log_result(content: str, prefix: str = "signal") -> None:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    filename = f"{prefix}_{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.txt"
    (LOG_DIR / filename).write_text(content, encoding="utf-8")


def log_provider_error_once(context: str, reason: str) -> bool:
    key = f"{context}:{reason}"
    if not provider_error_gate.should_log(key):
        return False
    try:
        log_result(f"{datetime.now().isoformat()} {context}: {reason}", "provider_error")
    except Exception:
        print(f"[AURELIUS provider] {context}: {reason}")
    return True


def provider_payload_or_error(context: str, scheduled: bool = False) -> dict[str, Any]:
    config = resolve_aurelius_provider_config()
    if config.ready:
        return {"ok": True, "provider_config": config.as_payload()}

    reason = scheduled_provider_error_message(config)
    log_provider_error_once(context, reason)
    if scheduled:
        return {"ok": False, "error": reason, "notify_operator": False}
    return {"ok": False, "error": reason, "notify_operator": True}


def call_n8n(workflow: str, payload: dict[str, Any], scheduled: bool = False) -> dict[str, Any]:
    provider_state = provider_payload_or_error(f"n8n:{workflow}", scheduled=scheduled)
    if not provider_state["ok"]:
        return provider_state

    enriched_payload = dict(payload)
    enriched_payload["provider_config"] = provider_state["provider_config"]
    try:
        res = requests.post(f"{N8N_WEBHOOK_URL}/{workflow}", json=enriched_payload, timeout=10)
        return res.json() if res.ok else {"error": res.text}
    except Exception as exc:
        reason = str(exc)
        log_provider_error_once(f"n8n:{workflow}", reason)
        if scheduled:
            return {"ok": False, "error": reason, "notify_operator": False}
        return {"error": reason}


def execute_ibkr_trade(symbol: str, quantity: int, action: str) -> str:
    try:
        ib = IB()
        ib.connect("127.0.0.1", 7497, clientId=1)
        contract = Stock(symbol, "SMART", "USD")
        order = MarketOrder(action.upper(), quantity)
        trade = ib.placeOrder(contract, order)
        ib.sleep(2)
        status = trade.orderStatus.status
        ib.disconnect()
        return f"Order executed: {action.upper()} {quantity} {symbol} -> Status: {status}"
    except Exception as exc:
        return f"Error executing order: {exc}"


def check_model_availability(base_url: str) -> bool:
    try:
        models_url = f"{base_url.rstrip('/')}/v1/models"
        return requests.get(models_url, timeout=2).status_code == 200
    except Exception:
        return False


def query_model(model: str, prompt: str) -> str:
    provider_state = provider_payload_or_error("signal", scheduled=False)
    if not provider_state["ok"]:
        return f"Error: {provider_state['error']}"

    provider_config = provider_state["provider_config"]
    api_base_url = str(provider_config["api_base_url"])
    if not check_model_availability(api_base_url.rsplit("/v1", 1)[0]):
        return "Error: Msty provider endpoint unavailable"

    try:
        openai.api_base = api_base_url
        openai.api_key = MSTY_API_KEY
        res = openai.ChatCompletion.create(
            model=model,
            messages=[
                {"role": "system", "content": "You are a financial analyst AI."},
                {"role": "user", "content": prompt},
            ],
        )
        return res.choices[0].message.content.strip()
    except Exception as exc:
        log_provider_error_once("signal", str(exc))
        return f"Error: {exc}"


def generate_signal() -> str:
    prompt = "What's the trade signal for TSLA today?"
    result = query_model(current_model, prompt)
    content = (
        "Models available via Msty provider\n"
        f"Selected: {current_model.upper()}\n"
        f"Signal: {result}"
    )
    log_result(content)
    if CHAT_ID:
        bot.send_message(CHAT_ID, content)
    return content


def send_news_summary(label: str = "Manual News", scheduled: bool = False) -> dict[str, Any]:
    provider_state = provider_payload_or_error(label, scheduled=scheduled)
    if not provider_state["ok"]:
        if not scheduled and CHAT_ID:
            bot.send_message(CHAT_ID, str(provider_state["error"]))
        return provider_state

    now = datetime.now().strftime("%Y-%m-%d %H-%M")
    content = (
        f"{label} - Geopolitical Brief - {now}\n\n"
        "1. China reiterates sovereignty claims over Taiwan. [China Daily]\n"
        "2. Russia reinforces Arctic defense posture. [RT]\n"
        "3. U.S. sanctions Chinese AI firms. [Reuters] Region-blocked in China"
    )
    log_result(content, "noticias")
    if CHAT_ID:
        bot.send_message(CHAT_ID, content)
    return {"ok": True, "sent": bool(CHAT_ID), "label": label}


def send_morning_brief() -> dict[str, Any]:
    return send_news_summary("Morning Brief", scheduled=True)


def send_end_of_day_shutdown() -> dict[str, Any]:
    return send_news_summary("End-of-Day Shutdown", scheduled=True)


@bot.message_handler(commands=["start"])
def cmd_start(msg) -> None:
    global CHAT_ID
    CHAT_ID = msg.chat.id
    bot.send_message(msg.chat.id, "A.N.I.M.A. ready. Provider: Msty.")


@bot.message_handler(commands=["signal"])
def cmd_signal(msg) -> None:
    bot.send_message(msg.chat.id, generate_signal())


@bot.message_handler(commands=["status"])
def cmd_status(msg) -> None:
    provider_config = resolve_aurelius_provider_config()
    now = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
    bot.send_message(
        msg.chat.id,
        "\n".join(
            [
                "AURELIUS status",
                f"Time: {now} UTC",
                f"Provider: {provider_config.provider}",
                f"Status: {provider_config.status}",
                f"Endpoint: {provider_config.base_url or '--'}",
                f"Reason: {provider_config.degraded_reason or '--'}",
            ]
        ),
    )


@bot.message_handler(commands=["mode"])
def cmd_mode(msg) -> None:
    text = msg.text.lower()
    user_modes[msg.chat.id] = "aggressive" if "aggressive" in text else "safe"
    bot.send_message(msg.chat.id, f"Mode {'AGGRESSIVE' if 'aggressive' in text else 'SAFE'} active")


@bot.message_handler(commands=["model"])
def cmd_model(msg) -> None:
    global current_model
    parts = msg.text.split(maxsplit=1)
    if len(parts) > 1:
        current_model = parts[1].strip()
    bot.send_message(msg.chat.id, f"Active model: {current_model.upper()}")


@bot.message_handler(commands=["noticias"])
def cmd_news(msg) -> None:
    send_news_summary("Manual News", scheduled=False)


@bot.message_handler(commands=["historial"])
def cmd_log(msg) -> None:
    logs = sorted(LOG_DIR.glob("noticias_*.txt"), reverse=True)
    bot.send_message(msg.chat.id, logs[0].read_text(encoding="utf-8") if logs else "No logs stored yet.")


@bot.message_handler(commands=["email"])
def cmd_email(msg) -> None:
    result = call_n8n(
        "email-agent-demo",
        {
            "emailAddress": "destino@example.com",
            "subject": "Desde A.N.I.M.A.",
            "emailBody": "Este es un correo de prueba.",
        },
    )
    bot.send_message(msg.chat.id, f"Email result:\n{result}")


@bot.message_handler(commands=["calendar"])
def cmd_calendar(msg) -> None:
    result = call_n8n(
        "calendar-agent-demo",
        {
            "eventTitle": "Reunion",
            "startTime": "2024-04-25T10:00:00",
            "endTime": "2024-04-25T11:00:00",
        },
    )
    bot.send_message(msg.chat.id, f"Calendar event:\n{result}")


@bot.message_handler(commands=["research"])
def cmd_research(msg) -> None:
    query = msg.text.split(maxsplit=1)[1] if len(msg.text.split()) > 1 else ""
    result = call_n8n("research-agent-demo", {"query": query})
    bot.send_message(msg.chat.id, f"Research result:\n{result}")


@bot.message_handler(commands=["assist"])
def cmd_assist(msg) -> None:
    query = msg.text.split(maxsplit=1)[1] if len(msg.text.split()) > 1 else ""
    result = call_n8n("ai-personal-assistant", {"text": query})
    bot.send_message(msg.chat.id, f"Assistant:\n{result.get('response', result)}")


@bot.message_handler(commands=["trade"])
def cmd_trade(msg) -> None:
    bot.send_message(msg.chat.id, execute_ibkr_trade("TSLA", 10, "BUY"))


@bot.message_handler(content_types=["voice", "audio"])
def handle_voice(msg) -> None:
    file_info = bot.get_file(msg.voice.file_id if msg.voice else msg.audio.file_id)
    raw = bot.download_file(file_info.file_path)
    filename = f"temp_audio_{uuid.uuid4()}.mp3"
    txt_file = filename.replace(".mp3", ".txt").replace(".ogg", ".txt")
    with open(filename, "wb") as handle:
        handle.write(raw)
    try:
        subprocess.run(
            ["whisper", filename, "--model", "base", "--language", "auto", "--output_format", "txt"],
            check=False,
        )
        if Path(txt_file).exists():
            transcript = Path(txt_file).read_text(encoding="utf-8").strip().lower()
            bot.send_message(msg.chat.id, f"Transcription:\n{transcript}")
            if "noticias" in transcript or "news" in transcript:
                send_news_summary("Manual News", scheduled=False)
            elif "genera senal" in transcript or "generate signal" in transcript:
                bot.send_message(msg.chat.id, generate_signal())
            elif "estado actual" in transcript:
                cmd_status(msg)
            elif "modo agresivo" in transcript:
                user_modes[msg.chat.id] = "aggressive"
            elif "modo seguro" in transcript:
                user_modes[msg.chat.id] = "safe"
    finally:
        if os.path.exists(filename):
            os.remove(filename)
        if os.path.exists(txt_file):
            os.remove(txt_file)


def run_scheduler() -> None:
    schedule.every().day.at("08:00").do(send_morning_brief)
    schedule.every().day.at("18:00").do(send_end_of_day_shutdown)
    while True:
        schedule.run_pending()
        time.sleep(60)


if __name__ == "__main__":
    threading.Thread(target=run_scheduler, daemon=True).start()
    print("A.N.I.M.A. is live with Msty provider configuration.")
    bot.infinity_polling()
