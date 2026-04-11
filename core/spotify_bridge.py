"""
AIKO SPOTIFY BRIDGE
───────────────────
Local music awareness + playback control via Spotify Web API.
Aiko can see what Master is listening to and comment on it.
"""

import os
import time
import logging
import json
from pathlib import Path

logger = logging.getLogger("Spotify")

try:
    import spotipy
    from spotipy.oauth2 import SpotifyOAuth
    _SPOTIPY_AVAILABLE = True
except ImportError:
    logger.warning("[Spotify] spotipy not installed. Music awareness disabled.")
    _SPOTIPY_AVAILABLE = False


class SpotifyBridge:
    """Connects Aiko to Master's Spotify for awareness and control."""

    SCOPES = "user-read-currently-playing user-read-playback-state user-modify-playback-state user-read-recently-played"
    CACHE_PATH = Path("data/.spotify_cache")

    def __init__(self):
        self.sp = None
        self.is_ready = False
        self._last_track_id = None
        self._last_check = 0
        self._check_interval = 30  # seconds between polls
        self._history = []  # Recent track log for personality

        if not _SPOTIPY_AVAILABLE:
            return

        client_id = os.getenv("SPOTIFY_CLIENT_ID", "")
        client_secret = os.getenv("SPOTIFY_CLIENT_SECRET", "")
        redirect_uri = os.getenv("SPOTIFY_REDIRECT_URI", "http://127.0.0.1:8888/callback")

        if not client_id or not client_secret:
            logger.info("[Spotify] No credentials in .env. Music bridge dormant.")
            return

        try:
            auth_manager = SpotifyOAuth(
                client_id=client_id,
                client_secret=client_secret,
                redirect_uri=redirect_uri,
                scope=self.SCOPES,
                cache_path=str(self.CACHE_PATH),
                open_browser=True
            )
            self.sp = spotipy.Spotify(auth_manager=auth_manager)
            # Quick test
            self.sp.current_user()
            self.is_ready = True
            logger.info("✅ Spotify Bridge connected!")
        except Exception as e:
            logger.warning(f"[Spotify] Auth failed: {e}")
            self.is_ready = False

    # ─── Awareness ───

    def get_now_playing(self) -> dict | None:
        """Returns current track info or None if nothing is playing."""
        if not self.is_ready:
            return None
        try:
            current = self.sp.current_playback()
            if not current or not current.get("is_playing"):
                return None

            track = current["item"]
            info = {
                "track": track["name"],
                "artist": ", ".join(a["name"] for a in track["artists"]),
                "album": track["album"]["name"],
                "track_id": track["id"],
                "progress_ms": current["progress_ms"],
                "duration_ms": track["duration_ms"],
                "is_playing": current["is_playing"],
                "device": current.get("device", {}).get("name", "Unknown"),
            }
            return info
        except Exception as e:
            logger.error(f"[Spotify] Playback check error: {e}")
            return None

    def check_track_change(self) -> dict | None:
        """
        Checks if the track changed since last poll.
        Returns the new track info if changed, None otherwise.
        Used by the Proactive Agent to trigger comments.
        """
        now = time.time()
        if now - self._last_check < self._check_interval:
            return None
        self._last_check = now

        info = self.get_now_playing()
        if not info:
            return None

        if info["track_id"] != self._last_track_id:
            self._last_track_id = info["track_id"]
            self._history.append({
                "track": info["track"],
                "artist": info["artist"],
                "timestamp": now
            })
            # Keep last 20 tracks
            if len(self._history) > 20:
                self._history = self._history[-20:]
            return info

        return None

    def get_recent_tracks(self, limit: int = 5) -> list:
        """Get recently played tracks from Spotify API."""
        if not self.is_ready:
            return []
        try:
            results = self.sp.current_user_recently_played(limit=limit)
            return [
                {
                    "track": item["track"]["name"],
                    "artist": ", ".join(a["name"] for a in item["track"]["artists"]),
                    "played_at": item["played_at"]
                }
                for item in results.get("items", [])
            ]
        except Exception as e:
            logger.error(f"[Spotify] Recent tracks error: {e}")
            return []

    def get_music_context(self) -> str:
        """Build a context string for the LLM about what Master is listening to."""
        info = self.get_now_playing()
        if not info:
            return ""
        return (
            f"[MUSIC_CONTEXT]: Master is currently listening to "
            f"\"{info['track']}\" by {info['artist']} "
            f"(Album: {info['album']}, on {info['device']})"
        )

    # ─── Playback Control ───

    def play(self) -> str:
        """Resume playback."""
        if not self.is_ready:
            return "Spotify is not connected."
        try:
            self.sp.start_playback()
            return "▶️ Playback resumed~"
        except Exception as e:
            return f"Couldn't resume: {e}"

    def pause(self) -> str:
        """Pause playback."""
        if not self.is_ready:
            return "Spotify is not connected."
        try:
            self.sp.pause_playback()
            return "⏸️ Paused the music."
        except Exception as e:
            return f"Couldn't pause: {e}"

    def skip(self) -> str:
        """Skip to next track."""
        if not self.is_ready:
            return "Spotify is not connected."
        try:
            self.sp.next_track()
            time.sleep(0.5)
            info = self.get_now_playing()
            if info:
                return f"⏭️ Skipped! Now playing: {info['track']} by {info['artist']}"
            return "⏭️ Skipped to next track."
        except Exception as e:
            return f"Couldn't skip: {e}"

    def previous(self) -> str:
        """Go to previous track."""
        if not self.is_ready:
            return "Spotify is not connected."
        try:
            self.sp.previous_track()
            time.sleep(0.5)
            info = self.get_now_playing()
            if info:
                return f"⏮️ Going back! Now playing: {info['track']} by {info['artist']}"
            return "⏮️ Went to previous track."
        except Exception as e:
            return f"Couldn't go back: {e}"

    def search_and_play(self, query: str) -> str:
        """Search for a song and play it."""
        if not self.is_ready:
            return "Spotify is not connected."
        try:
            results = self.sp.search(q=query, type="track", limit=1)
            tracks = results.get("tracks", {}).get("items", [])
            if not tracks:
                return f"Couldn't find anything for '{query}'."

            track = tracks[0]
            track_name = track["name"]
            artist = ", ".join(a["name"] for a in track["artists"])
            uri = track["uri"]

            self.sp.start_playback(uris=[uri])
            return f"🎵 Now playing: {track_name} by {artist}"
        except Exception as e:
            return f"Search/play failed: {e}"

    def set_volume(self, level: int) -> str:
        """Set volume (0-100)."""
        if not self.is_ready:
            return "Spotify is not connected."
        try:
            level = max(0, min(100, level))
            self.sp.volume(level)
            return f"🔊 Volume set to {level}%"
        except Exception as e:
            return f"Volume change failed: {e}"

    def execute_command(self, action: str) -> str:
        """Route a [MUSIC: action] command to the right method."""
        action = action.strip().lower()

        if action == "play" or action == "resume":
            return self.play()
        elif action == "pause" or action == "stop":
            return self.pause()
        elif action == "skip" or action == "next":
            return self.skip()
        elif action == "previous" or action == "prev" or action == "back":
            return self.previous()
        elif action == "now" or action == "current" or action == "status":
            info = self.get_now_playing()
            if info:
                return f"🎵 Currently: {info['track']} by {info['artist']} ({info['album']})"
            return "Nothing is playing right now."
        elif action.startswith("volume "):
            try:
                level = int(action.split(" ", 1)[1])
                return self.set_volume(level)
            except ValueError:
                return "Invalid volume level. Use a number 0-100."
        elif action.startswith("play "):
            query = action[5:].strip()
            return self.search_and_play(query)
        else:
            # Treat the whole action as a search query
            return self.search_and_play(action)


# Singleton
spotify = SpotifyBridge()
