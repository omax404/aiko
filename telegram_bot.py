
"""
AIKO TELEGRAM BOT (V2 - Satellite Mode)
───────────────────────────────────────
Powered by Aiko Neural Hub.
Very lightweight, concurrent safe.
"""

import os
import logging
import asyncio
import aiohttp
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, MessageHandler, filters, CommandHandler
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger("AikoTelegramV2")
logging.basicConfig(level=logging.INFO)

TOKEN = os.getenv("TELEGRAM_TOKEN")
MASTER_ID = int(os.getenv("MASTER_ID", "0"))
HUB_URL = "http://127.0.0.1:8000"

async def get_hub_response(message: str, user_id: int, attachments: list = None):
    try:
        async with aiohttp.ClientSession() as session:
            payload = {"message": message, "user_id": str(user_id), "attachments": attachments or []}
            # Increase timeout for long responses
            async with session.post(f"{HUB_URL}/api/chat", json=payload, timeout=90) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return data.get("response"), data.get("audio_path")
    except Exception as e:
        logger.error(f"Hub connection error: {e}")
    return "I can't reach my brain... *pouts*", None

def split_message(text, limit=4000):
    """Splits long messages for Telegram."""
    return [text[i:i+limit] for i in range(0, len(text), limit)]

async def chat_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text: return
    
    chat_type = update.effective_chat.type # 'private', 'group', 'supergroup'
    bot_user = await context.bot.get_me()
    is_mentioned = False
    
    # 1. Logic for Groups: Respond if mentioned or replied to
    if chat_type in ['group', 'supergroup']:
        text = update.message.text
        if f"@{bot_user.username}" in text or (update.message.reply_to_message and update.message.reply_to_message.from_user.id == bot_user.id):
            is_mentioned = True
            # Clean the mention from the text for her brain
            text = text.replace(f"@{bot_user.username}", "").strip()
        
        if not is_mentioned:
            return  # Ignore group noise unless called

    user = update.message.from_user
    text = update.message.text or update.message.caption or ""
    
    # Send "Typing..." action
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")
    
    # Pre-process image payloads for Aiko
    local_attachments = []
    os.makedirs("data/uploads", exist_ok=True)
    if update.message.photo:
        # Grabs the highest resolution version
        photo = update.message.photo[-1]
        file = await context.bot.get_file(photo.file_id)
        path = f"data/uploads/telegram_{update.message.message_id}.jpg"
        await file.download_to_drive(path)
        local_attachments.append(os.path.abspath(path))
        
        # If photo is sent without text, synthesize a placeholder
        if not text:
            text = "[System: User sent an image]"

    # Metadata for persona recognition
    meta_prefix = f"[TELEGRAM_METADATA: Handle: @{user.username}, Name: {user.full_name}, ChatType: {chat_type}, Status: {'MASTER' if user.id == MASTER_ID else 'guest'}] "
    
    full_msg = meta_prefix + text
    response, audio_path = await get_hub_response(full_msg, user.id, local_attachments)
    
    if not response: 
        response = "My brain is empty... *confused fox noise*"

    # Send Voice Note physically from disk
    if audio_path and os.path.exists(audio_path):
        try:
            with open(audio_path, 'rb') as audio_file:
                await context.bot.send_voice(
                    chat_id=update.effective_chat.id, 
                    voice=audio_file, 
                    reply_to_message_id=update.message.message_id
                )
        except Exception as e:
            logger.error(f"Voice Note Local Auth Error: {e}")

    # Split and send text
    chunks = split_message(response)
    for chunk in chunks:
        try:
            await update.message.reply_text(chunk, parse_mode='Markdown' if '```' in chunk else None)
        except Exception as e:
            await update.message.reply_text(chunk)

async def start_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Salam! I am Aiko Bot V2. I'm connected to my master brain! ♡")

if __name__ == "__main__":
    if not TOKEN:
        print(" [X] Error: TELEGRAM_TOKEN not found!")
    else:
        # Build app with context for groups
        app = ApplicationBuilder().token(TOKEN).build()
        
        app.add_handler(CommandHandler("start", start_cmd))
        # Remove filters.PRIVATE to allow groups, then logic inside handler will filter
        app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), chat_handler))
        
        logger.info("💖 Aiko Telegram Satellite (v2.1 Group Edition) is starting...")
        app.run_polling()
