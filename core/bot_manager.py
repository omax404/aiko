
import asyncio
import os
import logging
import discord
from discord.ext import commands
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, MessageHandler, filters, CommandHandler
import aiohttp
import re

logger = logging.getLogger("BotManager")

HUB_URL = "http://127.0.0.1:8000"

# --- Shared Helpers ---
async def get_hub_response(message: str, user_id: str, attachments: list = None):
    try:
        async with aiohttp.ClientSession() as session:
            payload = {"message": message, "user_id": str(user_id), "attachments": attachments or []}
            async with session.post(f"{HUB_URL}/api/chat", json=payload, timeout=90) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return data.get("response"), data.get("emotion"), data.get("audio_path")
    except Exception as e:
        logger.error(f"Hub connection error: {e}")
    return "Master, my neural links are fuzzy...", "sad", None

async def render_latex(snippet: str):
    try:
        async with aiohttp.ClientSession() as session:
            payload = {"snippet": snippet}
            async with session.post(f"{HUB_URL}/api/latex/render", json=payload, timeout=30) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    img_path = data.get("path")
                    if img_path and os.path.exists(img_path):
                        return img_path
    except Exception as e:
        logger.error(f"Latex render error: {e}")
    return None

# --- Discord Bot Core ---
async def run_discord_bot():
    token = os.getenv("DISCORD_TOKEN")
    if not token:
        logger.warning("Discord token missing. Satellite offline.")
        return

    intents = discord.Intents.default()
    intents.message_content = True
    bot = commands.Bot(command_prefix="!", intents=intents)

    @bot.event
    async def on_ready():
        logger.info(f"💖 Discord Satellite online: {bot.user}")
        await bot.change_presence(status=discord.Status.dnd, activity=discord.Game(name="with Master's code ♡"))

    @bot.event
    async def on_message(message):
        if message.author == bot.user or message.author.bot: return
        is_mentioned = bot.user in message.mentions
        is_dm = isinstance(message.channel, discord.DMChannel)
        
        if is_mentioned or is_dm or message.content.lower().startswith("aiko"):
            async with message.channel.typing():
                clean_text = message.content
                if is_mentioned: clean_text = clean_text.replace(f"<@{bot.user.id}>", "").strip()
                
                meta_prefix = f"[DISCORD_METADATA: Handle: {message.author.name}, Name: {message.author.display_name}, Status: {'MASTER' if str(message.author.id) == os.getenv('MASTER_ID','0') else 'member'}] "
                full_msg = meta_prefix + clean_text

                local_attachments = []
                os.makedirs("data/uploads", exist_ok=True)
                for a in message.attachments:
                    if a.content_type and 'image' in a.content_type:
                        path = f"data/uploads/discord_{message.id}_{a.filename}"
                        await a.save(path)
                        local_attachments.append(os.path.abspath(path))
                
                response, emotion, audio_path = await get_hub_response(full_msg, message.author.id, local_attachments)
                
                # LaTeX
                latex_file = None
                render_target = None
                block_math = re.findall(r"\$\$(.*?)\$\$", response, re.DOTALL)
                inline_math = re.findall(r"\$([^\$]+)\$", response)
                if block_math: render_target = block_math[0]
                elif inline_math:
                    for math in inline_math:
                        if any(c in math for c in ['\\', '^', '_', '{']):
                            render_target = math
                            break
                if render_target:
                    img_path = await render_latex(render_target)
                    if img_path: latex_file = discord.File(img_path, filename="aiko_math.png")

                # Audio
                audio_file = None
                if audio_path and os.path.exists(audio_path):
                    audio_file = discord.File(audio_path, filename="aiko_voice.wav")
                
                files = []
                if audio_file: files.append(audio_file)
                if latex_file: files.append(latex_file)
                
                if files: await message.reply(response, files=files)
                else: await message.reply(response)

    try:
        await bot.start(token)
    except Exception as e:
        logger.error(f"Discord crash: {e}")

# --- Telegram Bot Core ---
async def run_telegram_bot():
    token = os.getenv("TELEGRAM_TOKEN")
    if not token:
        logger.warning("Telegram token missing. Satellite offline.")
        return

    app = ApplicationBuilder().token(token).build()

    async def chat_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not update.message: return
        user = update.message.from_user
        text = update.message.text or update.message.caption or ""
        
        await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")
        
        local_attachments = []
        if update.message.photo:
            photo = update.message.photo[-1]
            file = await context.bot.get_file(photo.file_id)
            path = f"data/uploads/telegram_{update.message.message_id}.jpg"
            await file.download_to_drive(path)
            local_attachments.append(os.path.abspath(path))
            if not text: text = "[Image]"

        meta_prefix = f"[TELEGRAM_METADATA: Handle: @{user.username}, Name: {user.full_name}, Status: {'MASTER' if str(user.id) == os.getenv('MASTER_ID','0') else 'guest'}] "
        response, _, audio_path = await get_hub_response(meta_prefix + text, user.id, local_attachments)
        
        # Audio
        if audio_path and os.path.exists(audio_path):
            with open(audio_path, 'rb') as f:
                await context.bot.send_voice(chat_id=update.effective_chat.id, voice=f, reply_to_message_id=update.message.message_id)

        # LaTeX images on Telegram (Bonus)
        block_math = re.findall(r"\$\$(.*?)\$\$", response, re.DOTALL)
        if block_math:
            img_path = await render_latex(block_math[0])
            if img_path:
                with open(img_path, 'rb') as f:
                    await context.bot.send_photo(chat_id=update.effective_chat.id, photo=f)

        if response:
            await update.message.reply_text(response, parse_mode='Markdown' if '```' in response else None)

    app.add_handler(MessageHandler(filters.TEXT | filters.PHOTO, chat_handler))
    
    logger.info("💖 Telegram Satellite online.")
    
    async with app:
        await app.initialize()
        await app.start()
        await app.updater.start_polling()
        # Keep alive
        while True: await asyncio.sleep(3600)

async def start_all_satellites():
    """Launch all satellites within the same cluster loop."""
    await asyncio.sleep(2) # Give the Hub a moment to bind to the port
    logger.info("🛰️ Launching Neural Satellites (Consolidated Mode)...")
    asyncio.create_task(run_discord_bot())
    asyncio.create_task(run_telegram_bot())
