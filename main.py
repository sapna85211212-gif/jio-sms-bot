import os
import logging
import asyncio
from queue import Queue
from typing import Optional, Any
from contextlib import asynccontextmanager
from fastapi import FastAPI, Header, HTTPException
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters

# Setup logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuration Variables
BOT_TOKEN = "8732437160:AAFix7b38ifW-8oIk-uGRoT53-1RD0Zdo4s"
TARGET_NUMBER = "199"

# Shared memory/queue for commands
command_queue = Queue()
latest_reply = "No reply received yet."
app_status = "Disconnected"

# --- TELEGRAM BOT HANDLERS ---

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🚀 *Bot Connected Successfully!*\n\n"
        "Send any 15-digit IMEI number to trigger SMS.",
        parse_mode="Markdown"
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "ℹ️ *Help Menu:*\n\n"
        "1. Just send a 15-digit IMEI number directly in chat.\n"
        "2. Use `/status` to check system health.",
        parse_mode="Markdown"
    )

async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    status_text = (
        "📊 *System Status:*\n\n"
        f"🔹 *App Connection:* {app_status}\n"
        f"🔹 *Latest App Reply:* {latest_reply}\n"
        f"🔹 *Queue Status:* {'Pending command' if not command_queue.empty() else 'Empty (Ready)'}"
    )
    await update.message.reply_text(status_text, parse_mode="Markdown")

async def handle_imei_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global app_status
    text = update.message.text.strip()
    
    if len(text) == 15 and text.isdigit():
        formatted_command = f"JIO {text}"
        
        command_data = {
            "text": formatted_command,
            "target": TARGET_NUMBER
        }
        command_queue.put(command_data)
        
        await update.message.reply_text(
            f"✅ *Valid IMEI Received.*\n"
            f"Command queued: `{formatted_command}`\n\n"
            f"⏳ Waiting for Android App to fetch and trigger SMS...",
            parse_mode="Markdown"
        )
    else:
        await update.message.reply_text("❌ *Error:* Please enter a valid 15-digit IMEI number.")

# Initialize Telegram Application global instance
telegram_app = Application.builder().token(BOT_TOKEN).build()
telegram_app.add_handler(CommandHandler("start", start_command))
telegram_app.add_handler(CommandHandler("help", help_command))
telegram_app.add_handler(CommandHandler("status", status_command))
telegram_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_imei_message))

# --- FASTAPI LIFESPAN FOR SECURE BOT RUNNING ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Initialize and Start Telegram Bot perfectly in the background loop
    await telegram_app.initialize()
    await telegram_app.start()
    # Start polling safely as an independent async task
    polling_task = asyncio.create_task(telegram_app.updater.start_polling())
    logger.info("Telegram Bot started polling successfully inside FastAPI Lifespan.")
    
    yield
    
    # Shutdown: Stop bot cleanly when server restarts
    polling_task.cancel()
    await telegram_app.updater.stop()
    await telegram_app.stop()
    await telegram_app.shutdown()
    logger.info("Telegram Bot shut down cleanly.")

# Initialize FastAPI with lifespan routing
app = FastAPI(lifespan=lifespan)

# --- FASTAPI ENDPOINTS ---

@app.get("/")
async def root():
    return {"status": "Server running smoothly without formatting issues."}

@app.get("/get-command")
async def get_command(x_api_secret_key: Optional[str] = Header(None)):
    global app_status
    app_status = "Connected"
    
    if not command_queue.empty():
        current_command = command_queue.get()
        logger.info(f"Command fetched by app: {current_command['text']}")
        
        return {
            "status": "success",
            "command": current_command["text"],
            "message": current_command["text"],
            "imei": current_command["text"],
            "target_number": current_command["target"],
            "number": current_command["target"],
            "phone": current_command["target"]
        }
        
    return {"status": "no_command"}

@app.post("/send-reply")
async def receive_reply(data: dict, x_api_secret_key: Optional[str] = Header(None)):
    global latest_reply, app_status
    app_status = "Connected"
    
    sender = data.get("sender", "Unknown")
    message = data.get("message", "Empty Reply")
    latest_reply = f"From {sender}: {message}"
    
    try:
        await telegram_app.bot.send_message(
            chat_id=8732437160,
            text=f"📩 *New SMS Received!*\n\n👤 *From:* {sender}\n💬 *Message:* {message}",
            parse_mode="Markdown"
        )
    except Exception as e:
        logger.error(f"Failed to forward message to Telegram: {e}")
        
    return {"status": "reply_forwarded"}
