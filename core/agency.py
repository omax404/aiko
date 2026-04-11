import asyncio
import logging
import threading
import os
import urllib.parse
import re
import random
import json
from pathlib import Path

try:
    import discord
    from discord.ext import commands
except ImportError:
    discord = None
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
    from telegram.ext import (
        ApplicationBuilder,
        ContextTypes,
        CommandHandler,
        MessageHandler,
        filters,
    )

    HAS_TELEGRAM = True
except ImportError:
    HAS_TELEGRAM = False

logger = logging.getLogger("Agency")


class AikoMultiPlatformBridge:
    def __init__(self, brain, config, main_loop=None):
        self.brain = brain
        self.config = config
        self.main_loop = main_loop
        self.discord_thread = None
        self.telegram_thread = None

        # User profiles for gender detection
        self.user_profiles_path = Path("data/user_profiles.json")
        self.user_profiles = self._load_user_profiles()

        # Load .env if exists for tokens
        load_dotenv()

    def _load_user_profiles(self):
        """Load user profiles from JSON file."""
        if self.user_profiles_path.exists():
            try:
                with open(self.user_profiles_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except:
                return {}
        return {}

    def _save_user_profiles(self):
        """Save user profiles to JSON file."""
        self.user_profiles_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.user_profiles_path, "w", encoding="utf-8") as f:
            json.dump(self.user_profiles, f, indent=2)

    def _detect_gender_from_name(self, first_name: str) -> str:
        """Simple heuristics to detect gender from first name (focused on common names)."""
        if not first_name:
            return "unknown"

        first_name_lower = first_name.lower()

        # Common female names (Moroccan/Arabic & English)
        female_names = {
            "aiko",
            "sara",
            "sarah",
            "fatima",
            "khadija",
            "amina",
            "amine",
            "yasmine",
            "nour",
            "nora",
            "hafsa",
            "laila",
            "leila",
            "maria",
            "mariam",
            "oumaima",
            "asma",
            "hind",
            "salma",
            "faty",
            "dounia",
            "hanane",
            "ikram",
            "ily",
            "emma",
            "sophie",
            "lily",
            "rose",
            "chloe",
            "mia",
            "ella",
            "ava",
            "olivia",
            "emma",
            "sophie",
            "isabella",
            "mia",
            "charlotte",
            "amelia",
            "harper",
            "evelyn",
            "abigail",
            "ella",
            "avery",
        }

        # Common male names (Moroccan/Arabic & English)
        male_names = {
            "omaxu",
            "youssef",
            "youcef",
            "amine",
            "brahim",
            "ibrahim",
            "mohamed",
            "mohammad",
            "abdellah",
            "othmane",
            "younes",
            "ayoub",
            "karim",
            "hicham",
            "tarik",
            "redouane",
            "fadi",
            "imad",
            "hamza",
            "rachid",
            "abdelkader",
            "abdelhak",
            "moustapha",
            "moussa",
            "ali",
            "omar",
            "ossama",
            "ayman",
            "ahmed",
            "khalid",
            "anas",
            "walid",
            "mahdi",
            "saad",
            "riad",
            "riadh",
            "john",
            "james",
            "michael",
            "david",
            "richard",
            "william",
            "robert",
            "charles",
            "joseph",
            "thomas",
            "christopher",
            "daniel",
            "matthew",
            "anthony",
            "mark",
            "donald",
            "steven",
            "paul",
            "andrew",
            "joshua",
        }

        if first_name_lower in female_names:
            return "female"
        elif first_name_lower in male_names:
            return "male"

        # Check for common endings
        if first_name_lower.endswith("a") or first_name_lower.endswith("e"):
            return "female"  # Often female in many languages
        if first_name_lower.endswith("n") or first_name_lower.endswith("s"):
            return "male"  # Often male

        return "unknown"

    def get_user_gender(self, user_id: str, first_name: str = None) -> str:
        """Get user gender, detecting if not stored."""
        if user_id in self.user_profiles:
            return self.user_profiles[user_id].get("gender", "unknown")

        # Try to detect from name
        detected_gender = "unknown"
        if first_name:
            detected_gender = self._detect_gender_from_name(first_name)

        # Store for future
        self.user_profiles[user_id] = {
            "gender": detected_gender,
            "first_name": first_name,
        }
        self._save_user_profiles()

        return detected_gender

    def set_user_gender(self, user_id: str, gender: str):
        """Set user gender explicitly."""
        if user_id not in self.user_profiles:
            self.user_profiles[user_id] = {}
        self.user_profiles[user_id]["gender"] = gender
        self._save_user_profiles()

    def start_all(self):
        """Start all enabled platforms."""
        logger.info(
            f"Agency initialized. Discord enabled: {self.config.get('discord_enabled')}, HAS_DISCORD: {HAS_DISCORD}"
        )
        logger.info(
            f"Agency initialized. Telegram enabled: {self.config.get('telegram_enabled')}, HAS_TELEGRAM: {HAS_TELEGRAM}"
        )

        if self.config.get("discord_enabled", False) and HAS_DISCORD:
            self.start_discord()
        if self.config.get("telegram_enabled", False) and HAS_TELEGRAM:
            self.start_telegram()
        else:
            if not HAS_TELEGRAM:
                logger.warning("Telegram dependencies missing (HAS_TELEGRAM is False)")
            if not self.config.get("telegram_enabled"):
                logger.warning("Telegram is disabled in config")

    # --- DISCORD ---
    def start_discord(self):
        token = os.getenv("DISCORD_TOKEN")
        if not token:
            logger.warning("Discord Token not found in .env")
            return

        self.discord_thread = threading.Thread(
            target=self._run_discord, args=(token,), daemon=True
        )
        self.discord_thread.start()
        logger.info("Discord Bridge Started.")

    def _run_discord(self, token):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        from core.gifs import AIKO_GIFS

        intents = discord.Intents.default()
        intents.message_content = True
        intents.voice_states = True

        # Use Client instead of Bot to avoid command processing issues
        client = discord.Client(intents=intents)

        # Thread-safe tracking for processed messages
        processed_messages = set()
        processing_lock = asyncio.Lock()

        # Voice connection state
        voice_connections = {}

        @client.event
        async def on_ready():
            logger.info(f"Agency: Discord Bot connected as {client.user}")

        @client.event
        async def on_message(message):
            # Skip bot's own messages
            if message.author == client.user:
                return

            # Check if Aiko is mentioned or DM
            if client.user not in message.mentions and not isinstance(
                message.channel, discord.DMChannel
            ):
                return

            # Use lock to prevent race conditions
            async with processing_lock:
                # Check if already processed
                if message.id in processed_messages:
                    logger.debug(f"Skipping duplicate message: {message.id}")
                    return

                # Mark as processed FIRST
                processed_messages.add(message.id)

                # Cleanup old IDs (keep last 50)
                if len(processed_messages) > 50:
                    to_remove = list(processed_messages)[:25]
                    for mid in to_remove:
                        processed_messages.discard(mid)

            # Safer reply function to avoid "Unknown message" errors
            async def safe_reply(target_message, content):
                try:
                    return await target_message.reply(content)
                except Exception as e:
                    logger.debug(f"Reply failed ({e}), falling back to channel.send")
                    return await target_message.channel.send(content)

            # Extract clean text
            text = message.content.replace(f"<@{client.user.id}>", "").strip()

            # Voice commands (Join/Leave)
            if "join" in text.lower() and (
                "voice" in text.lower() or "vc" in text.lower()
            ):
                if message.author.voice and message.author.voice.channel:
                    try:
                        vc = await message.author.voice.channel.connect()
                        voice_connections[message.guild.id] = vc
                        await safe_reply(message, "I'm here, Master! I can hear you now~ ♡")
                    except Exception as e:
                        await safe_reply(message, f"Couldn't join voice: {e}")
                    return

            if "leave" in text.lower() and (
                "voice" in text.lower() or "vc" in text.lower()
            ):
                if message.guild and message.guild.id in voice_connections:
                    await voice_connections[message.guild.id].disconnect()
                    del voice_connections[message.guild.id]
                    await safe_reply(message, "Bye bye~ I'll miss you! ♡")
                    return

            # Identity Injection for Aiko context
            handle = f"@{message.author.name}"
            full_name = message.author.display_name or message.author.name
            first_name = message.author.global_name or message.author.name
            detected_gender = self._detect_gender_from_name(first_name)
            
            # Special logic for Master (Discord ID)
            is_master = str(message.author.id) == os.getenv(
                "MASTER_ID", "766774147832873012"
            )
            status = "MASTER" if is_master else "GUEST"
            
            # Metadata block to help Aiko "spot" gender and identity
            context_header = f"[DISCORD_METADATA: Handle: {handle}, Name: {full_name}, Gender: {detected_gender}, Status: {status}]"
            chat_input = f"{context_header}\n{text}"

            # Get AI response
            if self.main_loop:
                # Delegate safely to UI thread threadsafe!
                future = asyncio.run_coroutine_threadsafe(
                    self.brain.chat(
                        chat_input, user_id=str(message.author.id), save_input=True
                    ),
                    self.main_loop,
                )
                response_tuple = await asyncio.wrap_future(future)
            else:
                response_tuple = await self.brain.chat(
                    chat_input, user_id=str(message.author.id), save_input=True
                )

            response = response_tuple[0]
            emotion = response_tuple[1] if len(response_tuple) > 1 else "neutral"
            image_prompts = response_tuple[2] if len(response_tuple) > 2 else []
            video_prompts = response_tuple[3] if len(response_tuple) > 3 else []

            # Send text response
            await safe_reply(message, response)

            # Send GIF separately
            if emotion in AIKO_GIFS:
                chance = (
                    1.0
                    if emotion
                    in ["hug", "kiss", "pat", "lick", "smug", "cry", "yandere"]
                    else 0.4
                )
                if random.random() < chance:
                    gif_url = random.choice(AIKO_GIFS[emotion])
                    await message.channel.send(gif_url)

            # Generated images
            for prompt in image_prompts:
                encoded = urllib.parse.quote(prompt)
                url = f"https://image.pollinations.ai/prompt/{encoded}?seed={random.randint(1, 99999)}&nologo=true"
                await message.channel.send(url)

            # Generated videos
            for prompt in video_prompts:
                encoded = urllib.parse.quote(prompt)
                url = f"https://pollinations.ai/p/{encoded}?model=video&seed={random.randint(1, 99999)}"
                await message.channel.send(f"🎬 **AI Video Generated**: {url}")

            # Math previews
            await self._send_math_previews(response, message.channel)

            # TTS in voice
            if message.guild and message.guild.id in voice_connections:
                vc = voice_connections[message.guild.id]
                if vc.is_connected():
                    try:
                        await self._speak_in_voice(vc, response)
                    except Exception as e:
                        logger.warning(f"Voice speak error: {e}")

        client.run(token)

    # --- TELEGRAM ---
    def start_telegram(self):
        token = os.getenv("TELEGRAM_TOKEN")
        if not token:
            logger.warning("Telegram Token not found in .env")
            return

        self.telegram_thread = threading.Thread(
            target=self._run_telegram, args=(token,), daemon=True
        )
        self.telegram_thread.start()
        logger.info("Telegram Bridge Started.")

    def _run_telegram(self, token):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        async def handle_msg(update: Update, context: ContextTypes.DEFAULT_TYPE):
            user = update.effective_user
            user_text = update.message.text

            # Identity Injection for Aiko context
            handle = f"@{user.username}" if user.username else "Anonymous"
            full_name = (
                f"{user.first_name or ''} {user.last_name or ''}".strip() or "Friend"
            )
            detected_gender = self._detect_gender_from_name(user.first_name)

            # Special logic for @omaxu (Master)
            is_master = handle.lower() == "@omaxu"
            status = "MASTER" if is_master else "GUEST"

            # Metadata block to help Aiko "spot" gender and identity
            # This is invisible to the user but contextually rich for the Brain
            context_header = f"[TELEGRAM_METADATA: Handle: {handle}, Name: {full_name}, Gender: {detected_gender}, Status: {status}]"
            chat_input = f"{context_header}\n{user_text}"

            if self.main_loop:
                # Delegate heavy lifting safely to main UI thread's asyncio loop!
                future = asyncio.run_coroutine_threadsafe(
                    self.brain.chat(chat_input, user_id=str(user.id), save_input=True),
                    self.main_loop,
                )
                response_tuple = await asyncio.wrap_future(future)
            else:
                response_tuple = await self.brain.chat(
                    chat_input, user_id=str(user.id), save_input=True
                )

            response = response_tuple[0]
            emotion = response_tuple[1] if len(response_tuple) > 1 else "neutral"
            image_prompts = response_tuple[2] if len(response_tuple) > 2 else []
            video_prompts = response_tuple[3] if len(response_tuple) > 3 else []

            await context.bot.send_message(
                chat_id=update.effective_chat.id, text=response
            )

            for prompt in image_prompts:
                encoded = urllib.parse.quote(prompt)
                url = f"https://image.pollinations.ai/prompt/{encoded}?seed={random.randint(1, 99999)}&nologo=true"
                await context.bot.send_message(
                    chat_id=update.effective_chat.id, text=url
                )

            for prompt in video_prompts:
                encoded = urllib.parse.quote(prompt)
                url = f"https://pollinations.ai/p/{encoded}?model=video&seed={random.randint(1, 99999)}"
                await context.bot.send_message(
                    chat_id=update.effective_chat.id, text=f"🎬 AI Video: {url}"
                )

        application = ApplicationBuilder().token(token).build()
        msg_handler = MessageHandler(filters.TEXT & (~filters.COMMAND), handle_msg)
        application.add_handler(msg_handler)

        application.run_polling()

    async def _send_math_previews(self, text, channel, is_telegram=False, context=None):
        """Extract math and send as images for non-native platforms."""
        math_blocks = re.findall(r"\$\$(.*?)\$\$", text, re.DOTALL)
        for formula in math_blocks[:3]:
            encoded = urllib.parse.quote(formula.strip())
            url = f"https://latex.codecogs.com/png.latex?\\bg_black\\white\\huge {encoded}"
            if is_telegram and context:
                await context.bot.send_message(
                    chat_id=channel.id, text=f"📐 Math Preview: {url}"
                )
            elif discord:
                embed = discord.Embed(title="📐 Math Formula", color=0xE11D48)
                embed.set_image(url=url)
                await channel.send(embed=embed)

    async def _speak_in_voice(self, voice_client, text: str):
        """Generate TTS audio using Piper TTS and play in voice channel."""
        import tempfile
        import subprocess

        # Clean text for TTS (remove emojis, kaomoji, etc.)
        clean_text = re.sub(r'[^\w\s.,!?\'"\\-]', "", text)
        clean_text = clean_text[:500]

        if not clean_text.strip():
            return

        temp_path = os.path.join(tempfile.gettempdir(), "aiko_voice.wav")

        try:
            # Use Piper TTS (fast, local, high quality)
            # Install: pip install piper-tts
            # Voice models at: https://github.com/rhasspy/piper/releases

            # Check if piper is available
            piper_voice = os.path.join(
                os.path.dirname(__file__), "..", "voices", "en_US-amy-medium.onnx"
            )

            # Fallback to system piper or bundled
            if os.path.exists(piper_voice):
                # Use bundled voice
                result = subprocess.run(
                    ["piper", "--model", piper_voice, "--output_file", temp_path],
                    input=clean_text,
                    capture_output=True,
                    text=True,
                )
            else:
                # Try system piper with default voice
                result = subprocess.run(
                    ["piper", "--output_file", temp_path],
                    input=clean_text,
                    capture_output=True,
                    text=True,
                )

            if voice_client.is_connected() and os.path.exists(temp_path):
                audio_source = discord.FFmpegPCMAudio(temp_path)
                voice_client.play(audio_source)

                while voice_client.is_playing():
                    await asyncio.sleep(0.5)

        except FileNotFoundError:
            logger.warning("Piper TTS not found. Install with: pip install piper-tts")
        except Exception as e:
            logger.warning(f"Piper TTS Error: {e}")

    # --- WHATSAPP (Placeholder/Instructions) ---
    def start_whatsapp(self):
        logger.info(
            "WhatsApp Bridge: Currently requires Twilio or Meta Business API keys."
        )
        pass
