import os
import uuid
import time
import openai
import smtplib
import schedule
import requests
import threading
import subprocess
from pathlib import Path
from dotenv import load_dotenv
from email.message import EmailMessage
from datetime import datetime
from telebot import TeleBot
from ib_insync import IB, Stock, MarketOrder

load_dotenv()

API_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
N8N_WEBHOOK_URL = os.getenv("N8N_WEBHOOK_URL", "http://localhost:5678/webhook")
LOG_DIR = Path("F:/ANIMA - AI Agent/Bot/logs")

# Validate required variables
if not API_TOKEN or not OPENAI_API_KEY:
    raise EnvironmentError("Missing required environment variables. Check your .env file.")

bot = TeleBot(API_TOKEN)
CHAT_ID = None
user_modes = {}
current_model = "mistral"

def send_email_proton(to, subject, body):
    msg = EmailMessage()
    msg["From"] = os.getenv("PROTONMAIL_USER")
    msg["To"] = to
    msg["Subject"] = subject
    msg.set_content(body)
    with smtplib.SMTP("127.0.0.1", 1025) as server:
        server.login(msg["From"], os.getenv("PROTONMAIL_PASSWORD"))
        server.send_message(msg)

def call_n8n(workflow, payload):
    try:
        res = requests.post(f"{N8N_WEBHOOK_URL}/{workflow}", json=payload, timeout=10)
        return res.json() if res.ok else {"error": res.text}
    except Exception as e:
        return {"error": str(e)}

def execute_ibkr_trade(symbol, quantity, action):
    try:
        ib = IB()
        ib.connect('127.0.0.1', 7497, clientId=1)
        contract = Stock(symbol, 'SMART', 'USD')
        order = MarketOrder(action.upper(), quantity)
        trade = ib.placeOrder(contract, order)
        ib.sleep(2)
        status = trade.orderStatus.status
        ib.disconnect()
        return f"✅ Orden ejecutada: {action.upper()} {quantity} {symbol} → Estado: {status}"
    except Exception as e:
        return f"❌ Error ejecutando la orden: {str(e)}"

def check_model_availability(url):
    try:
        return requests.get(url, timeout=2).status_code == 200
    except:
        return False

def query_model(model, base_url, prompt):
    try:
        openai.api_base = base_url
        openai.api_key = "ollama" if model in ["mistral", "deepseek"] else OPENAI_API_KEY
        res = openai.ChatCompletion.create(
            model=model,
            messages=[
                {"role": "system", "content": "You are a financial analyst AI."},
                {"role": "user", "content": prompt}
            ]
        )
        return res.choices[0].message.content.strip()
    except Exception as e:
        return f"Error: {str(e)}"

def log_result(content, prefix="signal"):
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    filename = f"{prefix}_{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.txt"
    Path(LOG_DIR / filename).write_text(content, encoding='utf-8')

def generate_signal():
    prompt = "What's the trade signal for TSLA today?"
    endpoints = {
        "mistral": "http://localhost:11434/v1",
        "deepseek": "http://localhost:11434/v1",
        "gpt-4": "https://api.openai.com/v1"
    }
    available = {m: u for m, u in endpoints.items() if check_model_availability(u)}
    results = {m: query_model(m, u, prompt) for m, u in available.items()}
    best = max(results, key=lambda k: len(results[k]) / (1 + results[k].count('Error')))
    summary = "🧠 Modelos disponibles:\n" + "\n".join([f"{'✔️' if m in available else '❌'} {m.capitalize()}" for m in endpoints])
    result = f"{summary}\n🏆 Seleccionado: {best.upper()}\n📈 Señal: {results[best]}"
    log_result(result)
    if CHAT_ID:
        bot.send_message(CHAT_ID, result)
    return result

def send_news_summary():
    now = datetime.now().strftime('%Y-%m-%d %H-%M')
    content = (
        f"📰 Informe Geopolítico – {now}\n\n"
        "1. 🇨🇳 China reitera su soberanía sobre Taiwán. [China Daily]\n"
        "2. 🇷🇺 Putin refuerza defensa del Ártico. [RT]\n"
        "3. 🇺🇸 EE.UU. sanciona empresas chinas de IA. [Reuters] ⚠️ Bloqueado en 🇨🇳"
    )
    log_result(content, "noticias")
    if CHAT_ID:
        bot.send_message(CHAT_ID, content)

@bot.message_handler(commands=['start'])
def cmd_start(msg):
    global CHAT_ID
    CHAT_ID = msg.chat.id
    bot.send_message(msg.chat.id, "🤖 A.N.I.M.A. lista para operar.")

@bot.message_handler(commands=['signal'])
def cmd_signal(msg): bot.send_message(msg.chat.id, generate_signal())

@bot.message_handler(commands=['status'])
def cmd_status(msg):
    now = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')
    bot.send_message(msg.chat.id, f"📄 Última operación\nBUY — NVDA\n⏱️ {now} UTC\n📈 Confianza: 81.2%\n🔍 Razón: Insider + RSI")

@bot.message_handler(commands=['mode'])
def cmd_mode(msg):
    m = msg.text.lower()
    user_modes[msg.chat.id] = "aggressive" if "aggressive" in m else "safe"
    bot.send_message(msg.chat.id, f"Modo {'AGRESIVO' if 'aggressive' in m else 'SEGURO'} activado")

@bot.message_handler(commands=['model'])
def cmd_model(msg):
    global current_model
    m = msg.text.lower()
    if "mistral" in m: current_model = "mistral"
    elif "deepseek" in m: current_model = "deepseek"
    elif "gpt4" in m or "gpt-4" in m: current_model = "gpt-4"
    bot.send_message(msg.chat.id, f"🧠 Modelo activo: {current_model.upper()}")

@bot.message_handler(commands=['noticias'])
def cmd_news(msg): send_news_summary()

@bot.message_handler(commands=['historial'])
def cmd_log(msg):
    logs = sorted(LOG_DIR.glob("noticias_*.txt"), reverse=True)
    bot.send_message(msg.chat.id, logs[0].read_text(encoding='utf-8') if logs else "No hay logs guardados aún.")

@bot.message_handler(commands=['email'])
def cmd_email(msg):
    r = call_n8n("email-agent-demo", {
        "emailAddress": "destino@example.com",
        "subject": "Desde A.N.I.M.A.",
        "emailBody": "Este es un correo de prueba."
    })
    bot.send_message(msg.chat.id, f"📧 Resultado:\n{r}")

@bot.message_handler(commands=['calendar'])
def cmd_calendar(msg):
    r = call_n8n("calendar-agent-demo", {
        "eventTitle": "Reunión",
        "startTime": "2024-04-25T10:00:00",
        "endTime": "2024-04-25T11:00:00"
    })
    bot.send_message(msg.chat.id, f"📅 Evento:\n{r}")

@bot.message_handler(commands=['research'])
def cmd_research(msg):
    q = msg.text.split(maxsplit=1)[1] if len(msg.text.split()) > 1 else ""
    r = call_n8n("research-agent-demo", {"query": q})
    bot.send_message(msg.chat.id, f"🔍 Resultado:\n{r}")

@bot.message_handler(commands=['assist'])
def cmd_assist(msg):
    q = msg.text.split(maxsplit=1)[1] if len(msg.text.split()) > 1 else ""
    r = call_n8n("ai-personal-assistant", {"text": q})
    bot.send_message(msg.chat.id, f"🧠 Asistente:\n{r.get('response', r)}")

@bot.message_handler(commands=['trade'])
def cmd_trade(msg): bot.send_message(msg.chat.id, execute_ibkr_trade("TSLA", 10, "BUY"))

@bot.message_handler(content_types=['voice', 'audio'])
def handle_voice(msg):
    file_info = bot.get_file(msg.voice.file_id if msg.voice else msg.audio.file_id)
    raw = bot.download_file(file_info.file_path)
    filename = f"temp_audio_{uuid.uuid4()}.mp3"
    with open(filename, 'wb') as f:
        f.write(raw)
    try:
        subprocess.run(["whisper", filename, "--model", "base", "--language", "auto", "--output_format", "txt"])
        txt_file = filename.replace(".mp3", ".txt").replace(".ogg", ".txt")
        if Path(txt_file).exists():
            transcript = Path(txt_file).read_text(encoding='utf-8').strip().lower()
            bot.send_message(msg.chat.id, f"🗣 Transcripción:\n{transcript}")
            if "noticias" in transcript or "news" in transcript: send_news_summary()
            elif "genera señal" in transcript or "generate signal" in transcript: bot.send_message(msg.chat.id, generate_signal())
            elif "estado actual" in transcript: cmd_status(msg)
            elif "modo agresivo" in transcript: user_modes[msg.chat.id] = "aggressive"
            elif "modo seguro" in transcript: user_modes[msg.chat.id] = "safe"
    finally:
        os.remove(filename)
        if os.path.exists(txt_file): os.remove(txt_file)

def run_scheduler():
    schedule.every().day.at("08:00").do(send_news_summary)
    schedule.every().day.at("18:00").do(send_news_summary)
    while True:
        schedule.run_pending()
        time.sleep(60)

if __name__ == "__main__":
    threading.Thread(target=run_scheduler, daemon=True).start()
    print("✅ A.N.I.M.A. is live with voice and multilingual support.")
    bot.infinity_polling()
"""

# Save script
path = "/mnt/data/anima_bot_final_multilingual.py"
with open(path, "w", encoding="utf-8") as f:
    f.write(updated_script)

path
