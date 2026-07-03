import os
import logging
from fastapi import FastAPI, Request, Response, status
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
ALLOWED_USER_ID = os.getenv("ALLOWED_TELEGRAM_USER_ID")
API_SECRET = os.getenv("API_SECRET_KEY")
TARGET_NUMBER = os.getenv("TARGET_PHONE_NUMBER", "199")

if ALLOWED_USER_ID:
    ALLOWED_USER_ID = int(ALLOWED_USER_ID)

android_app_connected = False
latest_imei_command = None

# Main Telegram Engine Initialize
tg_app = Application.builder().token(TOKEN).build()
app = FastAPI()

# --- Telegram Functions ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if ALLOWED_USER_ID and update.effective_user.id != ALLOWED_USER_ID:
        return
    await update.message.reply_text("👋 Bot Connected Successfully!\n\n📱 Send a 15-digit IMEI number.")

async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if ALLOWED_USER_ID and update.effective_user.id != ALLOWED_USER_ID:
        return
    status_msg = f"📊 Bot Status:\n\nApp: {'✅ Connected' if android_app_connected else '❌ Disconnected'}\nTarget: {TARGET_NUMBER}"
    await update.message.reply_text(status_msg)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global latest_imei_command
    if ALLOWED_USER_ID and update.effective_user.id != ALLOWED_USER_ID:
        return
    text = update.message.text.strip()
    if text.isdigit() and len(text) == 15:
        latest_imei_command = {"imei": text, "target": TARGET_NUMBER}
        await update.message.reply_text(f"⏳ Valid IMEI ({text}) received. Waiting for Android App...")
    else:
        await update.message.reply_text("❌ Please send exactly 15-digit numeric IMEI.")

# Register Handlers
tg_app.add_handler(CommandHandler("start", start))
tg_app.add_handler(CommandHandler("status", status_command))
tg_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

@app.post("/webhook")
async def telegram_webhook(request: Request):
    try:
        json_data = await request.json()
        update = Update.de_json(json_data, tg_app.bot)
        
        # Isse request directly background queue me deliver ho jayegi bina drop hue
        await tg_app.initialize()
        await tg_app.process_update(update)
    except Exception as e:
        logger.error(f"Webhook processing error: {str(e)}")
    return Response(status_code=status.HTTP_200_OK)

@app.get("/get-command")
async def get_command(request: Request):
    global latest_imei_command, android_app_connected
    if request.headers.get("X-API-SECRET-KEY") != API_SECRET:
        return Response(status_code=status.HTTP_401_UNAUTHORIZED)
    android_app_connected = True
    if latest_imei_command:
        cmd = latest_imei_command.copy()
        latest_imei_command = None
        return cmd
    return {"status": "no_command"}

@app.post("/send-reply")
async def receive_reply_from_android(request: Request):
    if request.headers.get("X-API-SECRET-KEY") != API_SECRET:
        return Response(status_code=status.HTTP_401_UNAUTHORIZED)
    data = await request.json()
    if ALLOWED_USER_ID:
        await tg_app.bot.send_message(chat_id=ALLOWED_USER_ID, text=f"📩 New SMS:\n\n{data.get('message')}")
    return {"status": "success"}

@app.get("/")
def home():
    return {"status": "Server running"}
