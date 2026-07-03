import os
import logging
import httpx
from fastapi import FastAPI, Request, Response, status

# Logging config
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Environment Variables
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
API_SECRET = os.getenv("API_SECRET_KEY")
TARGET_NUMBER = os.getenv("TARGET_PHONE_NUMBER", "199")

# Global Variables
android_app_connected = False
latest_imei_command = None

app = FastAPI()

# Standard Helper function to send instant reply to Telegram
async def send_tg_message(chat_id: int, text: str):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "Markdown"
    }
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(url, json=payload, timeout=10.0)
            logger.info(f"Telegram send status: {response.status_code}")
    except Exception as e:
        logger.error(f"Failed to send message to Telegram: {str(e)}")

# --- FASTAPI WEBHOOK ENDPOINTS ---

@app.post("/webhook")
async def telegram_webhook(request: Request):
    global latest_imei_command
    try:
        json_data = await request.json()
        logger.info(f"Incoming Update: {json_data}")
        
        if "message" in json_data:
            message_data = json_data["message"]
            chat_id = message_data["chat"]["id"]
            text = message_data.get("text", "").strip()
            
            # 1. Start Command
            if text == "/start":
                await send_tg_message(chat_id, "👋 *Bot Connected Successfully!*\n\n📱 Send any 15-digit IMEI number to trigger SMS.\n\n_Note: All user restrictions have been removed._")
            
            # 2. Status Command
            elif text == "/status":
                status_msg = f"📊 *Bot Status*:\n\n" \
                             f"📱 App Connection: {'✅ Connected' if android_app_connected else '❌ Disconnected'}\n" \
                             f"📞 Target Phone: `{TARGET_NUMBER}`"
                await send_tg_message(chat_id, status_msg)
            
            # 3. IMEI Number handling (15 Digits Check)
            elif text.isdigit() and len(text) == 15:
                latest_imei_command = {
                    "imei": text,
                    "target": TARGET_NUMBER,
                    "chat_id": chat_id  # Save chat_id to route response back correctly
                }
                await send_tg_message(chat_id, f"⏳ *Valid IMEI ({text}) Received.*\n\nWaiting for Android Companion App to fetch and trigger SMS...")
            
            # 4. Invalid Inputs
            else:
                await send_tg_message(chat_id, "❌ *Invalid Input!*\n\nPlease send exactly a 15-digit numeric IMEI number.")
                
    except Exception as e:
        logger.error(f"Error handling webhook data: {str(e)}")
        
    return Response(status_code=status.HTTP_200_OK)


@app.get("/get-command")
async def get_command(request: Request):
    global latest_imei_command, android_app_connected
    
    # Secret Key Validation for Android
    if request.headers.get("X-API-SECRET-KEY") != API_SECRET:
        return Response(status_code=status.HTTP_401_UNAUTHORIZED)
    
    android_app_connected = True
    
    if latest_imei_command:
        cmd = latest_imei_command.copy()
        latest_imei_command = None  # Clear once fetched
        return cmd
        
    return {"status": "no_command"}


@app.post("/send-reply")
async def receive_reply_from_android(request: Request):
    if request.headers.get("X-API-SECRET-KEY") != API_SECRET:
        return Response(status_code=status.HTTP_401_UNAUTHORIZED)
    
    try:
        data = await request.json()
        sender = data.get("sender", "Unknown")
        message = data.get("message", "No content")
        chat_id = data.get("chat_id")  # Getting saved routing chat id
        
        notification_text = f"📩 *New SMS Received from {sender}:*\n\n{message}"
        
        # Dispatch alert back to user chat
        if chat_id:
            await send_tg_message(chat_id, notification_text)
            
    except Exception as e:
        logger.error(f"Error routing back reply from android: {str(e)}")
        
    return {"status": "success"}


@app.get("/")
def home():
    return {"status": "Server is running perfectly without any user restrictions."}
