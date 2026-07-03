import os
import logging
from fastapi import FastAPI, Request, Response, status
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# Logging setup
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Environment Variables se data lena
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
ALLOWED_USER_ID = os.getenv("ALLOWED_TELEGRAM_USER_ID")
API_SECRET = os.getenv("API_SECRET_KEY")
TARGET_NUMBER = os.getenv("TARGET_PHONE_NUMBER", "199")

if ALLOWED_USER_ID:
    ALLOWED_USER_ID = int(ALLOWED_USER_ID)

# Global variables to store status and app data
android_app_connected = False
latest_imei_command = None

# FastAPI app create karna
app = FastAPI()

# Telegram Application setup
tg_app = Application.builder().token(TOKEN).build()

# --- TELEGRAM BOT HANDLERS ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ALLOWED_USER_ID:
        return
    await update.message.reply_text("👋 Hello! Welcome to Telegram to Android SMS Bridge Bot.\n\n"
                                    "📱 Send a 15-digit IMEI number to trigger SMS.\n"
                                    "ℹ️ Commands:\n"
                                    "/status - Check connection\n"
                                    "/setnumber <number> - Change target number")

async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ALLOWED_USER_ID:
        return
    status_msg = f"📊 *Bot Status*:\n\n" \
                 f"📲 Android App: {'✅ Connected' if android_app_connected else '❌ Disconnected'}\n" \
                 f"📞 Target Number: {TARGET_NUMBER}"
    await update.message.reply_text(status_msg, parse_mode="Markdown")

async def set_number(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global TARGET_NUMBER
    if update.effective_user.id != ALLOWED_USER_ID:
        return
    if not context.args:
        await update.message.reply_text("❌ Usage: /setnumber <phone_number>")
        return
    TARGET_NUMBER = context.args[0]
    await update.message.reply_text(f"✅ Target phone number updated to: {TARGET_NUMBER}")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global latest_imei_command, android_app_connected
    if update.effective_user.id != ALLOWED_USER_ID:
        return
    
    text = update.message.text.strip()
    
    # IMEI validation (exactly 15 digits)
    if text.isdigit() and len(text) == 15:
        latest_imei_command = {
            "imei": text,
            "target": TARGET_NUMBER
        }
        await update.message.reply_text(f"⏳ Valid IMEI ({text}) received. Waiting for Android App to fetch...")
    else:
        await update.message.reply_text("❌ Invalid Input! Please send exactly a 15-digit numeric IMEI number.")

# Register handlers to telegram app
tg_app.add_handler(CommandHandler("start", start))
tg_app.add_handler(CommandHandler("status", status_command))
tg_app.add_handler(CommandHandler("setnumber", set_number))
tg_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

# --- FASTAPI ENDPOINTS (FOR TELEGRAM & ANDROID) ---

@app.post("/webhook")
async def telegram_webhook(request: Request):
    """Telegram se aane wale updates handle karne ke liye"""
    json_data = await request.json()
    update = Update.de_json(json_data, tg_app.bot)
    await tg_app.initialize()
    await tg_app.process_update(update)
    return Response(status_code=status.HTTP_200_OK)

@app.get("/get-command")
async def get_command(request: Request):
    """Android app is endpoint par baar-baar request bhejkar naya IMEI check karegi"""
    global latest_imei_command, android_app_connected
    
    # Simple Secret Key Verification
    auth_key = request.headers.get("X-API-SECRET-KEY")
    if auth_key != API_SECRET:
        return Response(status_code=status.HTTP_401_UNAUTHORIZED)
    
    android_app_connected = True
    
    if latest_imei_command:
        cmd = latest_imei_command.copy()
        latest_imei_command = None  # Command send karne ke baad clear karna
        return cmd
    
    return {"status": "no_command"}

@app.post("/send-reply")
async def receive_reply_from_android(request: Request):
    """Android app jab reply SMS receive karegi toh is endpoint par forward karegi"""
    auth_key = request.headers.get("X-API-SECRET-KEY")
    if auth_key != API_SECRET:
        return Response(status_code=status.HTTP_401_UNAUTHORIZED)
    
    data = await request.json()
    sender = data.get("sender")
    message = data.get("message")
    
    # Telegram par reply alert bhejna
    notification_text = f"📩 *New SMS Received from {sender}:*\n\n{message}"
    await tg_app.bot.send_message(chat_id=ALLOWED_USER_ID, text=notification_text, parse_mode="Markdown")
    
    return {"status": "success"}

@app.get("/")
def home():
    return {"status": "Server is running perfectly"}
