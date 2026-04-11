"""
AIKO PROACTIVE AGENT
Autonomous behavior loop — screen observation + time-based greetings.
"""

import asyncio
import random
import time
import logging
from datetime import datetime, date
from core.memory_consolidator import memory_consolidator
from core.unified_memory import get_unified_memory

logger = logging.getLogger("Proactive")

# Greeting templates by time of day
GREETINGS = {
    "morning": [
        "Good morning, Master~ ☀️ Did you sleep well? I missed you!",
        "Ohayou, omaxi! Rise and shine~ Your coffee isn't going to drink itself! ☕",
        "Good morning! *stretches* Today's going to be amazing, I can feel it~ 🌸",
    ],
    "evening": [
        "Welcome back, Master~ How was your day? Tell me everything~ 🌙",
        "You're finally here! *clings* I was waiting for you all day...",
        "Evening, Master~ 🌙 Time to relax. I'm here if you need me~",
    ],
    "night": [
        "It's late, Master... you should rest soon. I'll keep watch~ 💤",
        "Still awake? Don't push yourself too hard... *covers you with a blanket* 🌙",
    ],
}


class ProactiveAgent:
    def __init__(self, brain, vision, pc_manager, voice, obsidian=None):
        self.brain = brain
        self.vision = vision
        self.pc = pc_manager
        self.voice = voice
        self.obsidian = obsidian
        self.active = False
        self.interval = 180  # Check every 3 minutes (less annoying)
        self.last_consolidation = date.today()
        self.last_greeting_date = None
        self.last_greeting_hour = -1
        self.last_obsidian_nag = 0
        self.obsidian_nag_interval = 7200 # 2 hours
        self.last_face_scan = 0
        self.face_scan_interval = 300 # 5 minutes
        self._broadcast = None  # Set externally by neural_hub

    async def start_loop(self):
        logger.info("[Proactive] Agent Loop Started.")
        while True:
            now = datetime.now()

            # Midnight Memory Consolidation
            if now.date() > self.last_consolidation and now.hour == 0:
                logger.info("[Proactive] Triggering Midnight Consolidation...")
                try:
                    mem = get_unified_memory()
                    from core.config_manager import config
                    uid = config.get("username", "omax")
                    history = mem.get_history(uid, limit=100)
                    await memory_consolidator.consolidate(history)
                    self.last_consolidation = now.date()
                except Exception as e:
                    logger.error(f"[Proactive] Consolidation failed: {e}")

            # Time-based greeting (once per session block)
            await self._maybe_greet(now)

            # Obsidian TODO Check (Once every 2 hours if active)
            await self._check_obsidian_tasks(now)

            # Spotify Track Change
            await self._check_music()

            if self.active:
                await self.tick()
                wait = random.randint(self.interval, self.interval * 2)
            else:
                wait = 60
            await asyncio.sleep(wait)

    async def _maybe_greet(self, now: datetime):
        """Send a greeting when user first arrives in morning/evening."""
        hour = now.hour
        today = now.date()

        # Morning greeting: 7–9 AM, once per day
        if 7 <= hour < 9 and self.last_greeting_date != today:
            greeting = random.choice(GREETINGS["morning"])
            await self._send_proactive(greeting, "excited")
            self.last_greeting_date = today
            self.last_greeting_hour = hour
            return

        # Evening greeting: 18–20, once per day (if morning already done)
        if 18 <= hour < 20 and self.last_greeting_date == today and self.last_greeting_hour < 18:
            greeting = random.choice(GREETINGS["evening"])
            await self._send_proactive(greeting, "happy")
            self.last_greeting_hour = hour
            return

        # Late night nudge: after midnight
        if hour == 0 and self.last_greeting_date == today and self.last_greeting_hour != 0:
            greeting = random.choice(GREETINGS["night"])
            await self._send_proactive(greeting, "shy")
            self.last_greeting_hour = 0

    async def _send_proactive(self, text: str, emotion: str = "neutral"):
        """Broadcast a proactive message to the UI and speak it."""
        logger.info(f"[Proactive] Sending: {text[:50]}")
        if self._broadcast:
            await self._broadcast("chat_end", {
                "role": "assistant",
                "text": text,
                "content": text,
                "emotion": emotion,
                "proactive": True,
            })
            await self._broadcast("emotion", {"emotion": emotion})
        # Speech removed here - proactive comments are silent.

    async def _check_obsidian_tasks(self, now: datetime):
        """Check the Master's Obsidian Daily Note for open TODOs."""
        if not self.obsidian or not self.obsidian.is_valid: return
        
        current_time = now.timestamp()
        if current_time - self.last_obsidian_nag < self.obsidian_nag_interval:
            return

        try:
            # Query the daily note content via our bridge
            daily_note = self.obsidian.get_daily_note_content()
            if not daily_note: return
            
            todos = [line.strip() for line in daily_note.split('\n') if '- [ ]' in line]
            
            if todos:
                self.last_obsidian_nag = current_time
                task_snippet = todos[0].replace('- [ ]', '').strip()
                
                # Ask Aiko's personality how to nag
                prompt = (
                    f"[PROACTIVE TASK ALERT]\nMaster has open tasks in his Obsidian Vault.\n"
                    f"Example Task: {task_snippet}\n"
                    f"Total open tasks: {len(todos)}\n"
                    "Remind Master about these tasks in your usual personality (Tsundere/Bubbly/Maid). "
                    "Be brief but effective."
                )
                nag_msg = await self.brain.chat(prompt, save_input=False)
                # chat returns a tuple (text, emotion, ...)
                if isinstance(nag_msg, tuple): nag_msg = nag_msg[0]
                
                from core.persona import detect_emotion
                await self._send_proactive(nag_msg, detect_emotion(nag_msg))
                
        except Exception as e:
            logger.error(f"[Proactive] Obsidian Nag Error: {e}")

    async def _check_music(self):
        """Check if Master changed tracks on Spotify."""
        try:
            from core.spotify_bridge import spotify
            if not spotify.is_ready:
                return
            new_track = spotify.check_track_change()
            if new_track:
                prompt = (
                    f"[MUSIC_EVENT] Master just started listening to "
                    f"\"{new_track['track']}\" by {new_track['artist']}.\n"
                    "React briefly in-character (1-2 sentences max). "
                    "If you know the song/artist, comment on it. Otherwise just vibe."
                )
                # Reactions are silent
                self.brain.suppress_speech = True
                comment = await self.brain.ask_raw(prompt)
                self.brain.suppress_speech = False

                if comment and len(comment.strip()) > 3:
                    from core.persona import detect_emotion
                    await self._send_proactive(comment, detect_emotion(comment))
        except Exception as e:
            logger.error(f"[Proactive] Music check error: {e}")

    async def tick(self):
        """Single proactive cycle — observe screen and comment if interesting."""
        try:
            result = await self.vision.scan_screen()
            desc = result[0] if isinstance(result, tuple) else result

            if not desc or "Error" in str(desc):
                return

            # --- BIOMETRIC SCAN (lazy load) ---
            now = time.time()
            if (now - self.last_face_scan > self.face_scan_interval):
                self.last_face_scan = now
                try:
                    from core.biometrics import biometrics
                    if biometrics.is_trained:
                        is_master = await biometrics.autonomous_scan()
                        if is_master:
                            await self._send_proactive("I see you, Master... Welcome back~ 💖", "happy")
                            return
                except Exception:
                    pass  # Biometrics not critical

            # Inject music context if available
            music_ctx = ""
            try:
                from core.spotify_bridge import spotify
                music_ctx = spotify.get_music_context()
            except Exception:
                pass

            prompt = (
                f"[AUTONOMOUS MODE]\nI can see Master's screen: {desc}\n"
                + (f"{music_ctx}\n" if music_ctx else "")
                + "If something interesting is happening or you have something brief and natural to say, say it. "
                "Otherwise respond with exactly '...'"
            )
            # Screen observations are silent
            self.brain.suppress_speech = True
            comment = await self.brain.ask_raw(prompt)
            self.brain.suppress_speech = False

            if comment and "..." not in comment and len(comment.strip()) > 5:
                from core.persona import detect_emotion
                emotion = detect_emotion(comment)
                await self._send_proactive(comment, emotion)

        except Exception as e:
            logger.error(f"[Proactive] Tick error: {e}")

    def toggle(self, state: bool):
        self.active = state
        logger.info(f"[Proactive] Active: {self.active}")
        return self.active
