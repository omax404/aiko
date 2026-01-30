
import asyncio
import logging
import threading
import os
import urllib.parse
import re
from dotenv import load_dotenv

# Optional Platform Imports
try:
    import discord
    from discord.ext import commands
    HAS_DISCORD = True
except ImportError:
    HAS_DISCORD = False

try:
    from telegram import Update
    from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, MessageHandler, filters
    HAS_TELEGRAM = True
except ImportError:
    HAS_TELEGRAM = False

logger = logging.getLogger("Agency")

class AikoMultiPlatformBridge:
    def __init__(self, brain, config):
        self.brain = brain
        self.config = config
        self.discord_thread = None
        self.telegram_thread = None
        
        # Load .env if exists for tokens
        load_dotenv()
        
    def start_all(self):
        """Start all enabled platforms."""
        if self.config.get("discord_enabled", False) and HAS_DISCORD:
            self.start_discord()
        if self.config.get("telegram_enabled", False) and HAS_TELEGRAM:
            self.start_telegram()

    # --- DISCORD ---
    def start_discord(self):
        token = os.getenv("DISCORD_TOKEN")
        if not token:
            logger.warning("Discord Token not found in .env")
            return
            
        self.discord_thread = threading.Thread(target=self._run_discord, args=(token,), daemon=True)
        self.discord_thread.start()
        logger.info("Discord Bridge Started.")

    def _run_discord(self, token):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        intents = discord.Intents.default()
        intents.message_content = True
        bot = commands.Bot(command_prefix="!", intents=intents)

        @bot.event
        async def on_ready():
            logger.info(f"Agency: Discord Bot connected as {bot.user}")

        @bot.event
        async def on_message(message):
            if message.author == bot.user: return
            if bot.user in message.mentions or isinstance(message.channel, discord.DMChannel):
                async with message.channel.typing():
                    # Clean message
                    text = message.content.replace(f"<@{bot.user.id}>", "").strip()
                    # Aiko Brain Response
                    response, emotion, image_prompts, video_prompts = await self.brain.chat(text, user_id=str(message.author.id), save_input=True)
                    await message.reply(response)
                    
                    import random
                    for prompt in image_prompts:
                        encoded = urllib.parse.quote(prompt)
                        # Add seed to bypass caching/tier limits
                        url = f"https://image.pollinations.ai/prompt/{encoded}?seed={random.randint(1,99999)}&nologo=true"
                        await message.channel.send(url)
                    
                    for prompt in video_prompts:
                        encoded = urllib.parse.quote(prompt)
                        url = f"https://pollinations.ai/p/{encoded}?model=video&seed={random.randint(1,99999)}"
                        await message.channel.send(f"🎬 **AI Video Generated**: {url}")
                    
                    # LaTeX Previews for Discord
                    await self._send_math_previews(response, message.channel)

        bot.run(token)

    # --- TELEGRAM ---
    def start_telegram(self):
        token = os.getenv("TELEGRAM_TOKEN")
        if not token:
            logger.warning("Telegram Token not found in .env")
            return
            
        self.telegram_thread = threading.Thread(target=self._run_telegram, args=(token,), daemon=True)
        self.telegram_thread.start()
        logger.info("Telegram Bridge Started.")

    def _run_telegram(self, token):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        async def handle_msg(update: Update, context: ContextTypes.DEFAULT_TYPE):
            user_text = update.message.text
            response, emotion, image_prompts, video_prompts = await self.brain.chat(user_text, user_id=str(update.effective_user.id), save_input=True)
            await context.bot.send_message(chat_id=update.effective_chat.id, text=response)
            
            import random
            for prompt in image_prompts:
                encoded = urllib.parse.quote(prompt)
                url = f"https://image.pollinations.ai/prompt/{encoded}?seed={random.randint(1,99999)}&nologo=true"
                await context.bot.send_message(chat_id=update.effective_chat.id, text=url)

            for prompt in video_prompts:
                encoded = urllib.parse.quote(prompt)
                url = f"https://pollinations.ai/p/{encoded}?model=video&seed={random.randint(1,99999)}"
                await context.bot.send_message(chat_id=update.effective_chat.id, text=f"🎬 AI Video: {url}")

            # LaTeX Previews for Telegram
            await self._send_math_previews(response, update.effective_chat, is_telegram=True, context=context)

        application = ApplicationBuilder().token(token).build()
        msg_handler = MessageHandler(filters.TEXT & (~filters.COMMAND), handle_msg)
        application.add_handler(msg_handler)
        
        application.run_polling()

    async def _send_math_previews(self, text, channel, is_telegram=False, context=None):
        """Extract math and send as images for non-native platforms."""
        math_blocks = re.findall(r'\$\$(.*?)\$\$', text, re.DOTALL)
        for formula in math_blocks[:3]: # Limit to 3 to avoid spam
            encoded = urllib.parse.quote(formula.strip())
            url = f"https://latex.codecogs.com/png.latex?\\bg_black\\white\\huge {encoded}"
            if is_telegram and context:
                await context.bot.send_message(chat_id=channel.id, text=f"📐 **Math Preview**: {url}")
            else:
                import discord
                # Discord embed style
                embed = discord.Embed(title="📐 Math Formula", color=0xE11D48)
                embed.set_image(url=url)
                await channel.send(embed=embed)

    # --- WHATSAPP (Placeholder/Instructions) ---
    def start_whatsapp(self):
        logger.info("WhatsApp Bridge: Currently requires Twilio or Meta Business API keys.")
        # Meta API logic would go here
        pass
