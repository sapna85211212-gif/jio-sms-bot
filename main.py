import os
import logging
import asyncio
from fastapi import FastAPI, Request, Response, status
from telegram import Update, Bot
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

app = FastAPI()
bot = Bot(token=TOKEN)

# Simple FastAPI endpoints directly handling requests
@app.post("/webhook")
async def telegram_webhook(request: Request):
    global latest_imei_command
    try:
        json_data = await request.json()
        logger.info(f"Webhook received data: {json_data}")
        
        if "message" in json_data:
            message_data = json_data["message"]
            chat_id = message_data["chat"]["id"]
            text = message_data.get("text", "").strip()
            
            # Check User ID
            if ALLOWED_USER_ID and chat_id != ALLOWED_USER_ID:
                logger.warning(f"Unauthorized access from ID: {chat_id}")
                return Response(status_code=status.HTTP_200_OK)
                
            if text == "/start":
                async with bot:
                    await bot.send_message(chat_id=chat_id, text="👋 Bot Connected!\n\n📱 Send 15-digit IMEI number.")
            elif text == "/status":
                status_msg = f"📊 Bot Status:\n\nApp: {'✅ Connected' if android_app_connected else '❌ Disconnected'}\nTarget: {TARGET_NUMBER}"
                async with bot:
                    await bot.send_message(chat_id=chat_id, text=status_msg)
            elif text.isdigit() and len(text) == 15:
                latest_imei_command = {
                    "imei": text,
                    "target": TARGET_NUMBER
                }
                async with bot:
                    await bot.send_message(chat_id=chat_id, text=f"⏳ Valid IMEI ({text}) received. Waiting for Android App...")
            else:
                async with bot:
                    await bot.send_message(chat_id=chat_id, text="❌ Please send exactly 15-digit numeric IMEI.")
                    
    except Exception as e:
        logger.error(f"Error in webhook: {str(e)}")
        
    return Response(status_code=status.HTTP_200_OK)

@app.get("/get-command")
async def get_command(request: Request):
    global latest_imei_command, android_app_connected
    auth_key = request.headers.get("X-API-SECRET-KEY")
    if auth_key != API_SECRET:
        return Response(status_code=status.HTTP_401_UNAUTHORIZED)
    
    android_app_connected = True
    if latest_imei_command:
        cmd = latest_imei_command.copy()
        latest_imei_command = None
        return cmd
    return {"status": "no_command"}

@app.post("/send-reply")
async def receive_reply_from_android(request: Request):
    auth_key = request.headers.get("X-API-SECRET-KEY")
    if auth_key != API_SECRET:
        return Response(status_code=status.HTTP_401_UNAUTHORIZED)
    
    data = await request.json()
    sender = data.get("sender")
    message = data.get("message")
    
    if ALLOWED_USER_ID:
        notification_text = f"📩 New SMS Received from {sender}:\n\n{message}"
        async with bot:
            await bot.send_message(chat_id=ALLOWED_USER_ID, text=notification_text)
            
    return {"status": "success"}

@app.get("/")
def home():
    return {"status": "Server is running perfectly"}
