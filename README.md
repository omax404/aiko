# Aiko Desktop v3.0

> Your devoted AI assistant with emotional intelligence, voice synthesis, and Live2D avatar.

## Quick Start

### Prerequisites

```bash
# Install Python dependencies
pip install -r requirements.txt

# Install Ollama (for local LLM)
# Download from https://ollama.ai

# Pull a model (optional - can also use cloud providers)
ollama pull deepseek-r1:1.5b
```

### Environment Setup

Two configuration files and a persona template are required for Aiko to run. We have provided `example` files to get you started easily:

1. **Copy** `.env.example` to `.env` in the root directory and fill in any Bot/API keys.
2. **Copy** `data/config.example.json` to `data/config.json`. You can leave it as default to use the local Ollama backend, or change `MODEL_NAME` to your preferred LLM.
3. **Copy** `core/persona.example.py` to `core/persona.py`. This is Aiko's character prompt! You can read the instructions at the top of the file to heavily customize her archetype, dialect, and memory to fit your exact lifestyle.

```env
# LLM Configuration
PROVIDER=OpenRouter
MODEL_NAME=google/gemma-3-27b-it:free
API_KEY=sk-or-v1-your-key

# Bot Tokens (optional)
DISCORD_TOKEN=your_discord_bot_token
TELEGRAM_TOKEN=your_telegram_bot_token
MASTER_ID=your_user_id

# TTS/STT (optional)
GEMINI_API_KEY=your_gemini_key
```

### Launch

```bash
# Windows
python start_aiko_tauri.py

# The launcher will:
# 1. Start Ollama Serve
# 2. Start Neural Hub (port 8000)
# 3. Start OpenClaw Bridge
# 4. Launch Discord & Telegram bots
# 5. Open Tauri desktop app
```

---

## Architecture

```
Aiko Desktop/
├── start_aiko_tauri.py    # Main launcher
├── core/
│   ├── neural_hub.py      # Master server (aiohttp, port 8000)
│   ├── chat_engine.py     # ReAct AI brain with LLM
│   ├── persona.py         # Character definition & emotions
│   ├── memory.py          # Conversation history & affection
│   ├── rag_memory.py      # Semantic memory search
│   ├── emotion_engine.py  # Emotion detection (22+ categories)
│   ├── voice.py           # TTS engine (Pocket-TTS/Gemini)
│   ├── hearing.py         # STT engine (Moonshine)
│   ├── vision.py          # Screen analysis
│   ├── vts_connector.py   # VTube Studio integration
│   ├── mcp_bridge.py      # File system tools
│   ├── sandbox_bridge.py  # Python sandbox execution
│   ├── clawdbot_bridge.py # OpenClaw agent delegation
│   ├── pc_manager.py      # PC control utilities
│   ├── image_engine.py    # AI image generation
│   ├── latex_engine.py    # LaTeX to PDF conversion
│   ├── startup_manager.py # Background task launcher
│   └── config_manager.py  # Configuration handler
├── aiko-app/
│   ├── src/
│   │   ├── App.tsx            # Main UI component
│   │   ├── main.tsx           # Entry point
│   │   ├── components/
│   │   │   ├── Live2DAvatar.tsx   # Live2D rendering
│   │   │   ├── ChatBubble.tsx     # Message display
│   │   │   ├── Sidebar.tsx        # Session navigation
│   │   │   ├── InputDock.tsx      # Chat input
│   │   │   └── SettingsModal.tsx  # App settings
│   │   └── store/
│   │       └── useNeuralStore.ts  # Zustand state
│   └── src-tauri/         # Rust backend (Tauri)
├── data/
│   ├── config.json        # App configuration
│   ├── memory.json        # Chat memory storage
│   └── knowledge/         # RAG document ingestion
├── scripts/               # Utility scripts
├── tests/                 # Test suite
├── discord_bot.py         # Discord satellite
├── telegram_bot.py        # Telegram satellite
├── requirements.txt       # Python dependencies
├── docker-compose.yml     # Docker orchestration
└── Dockerfile             # Container build
```

---

## Features

### AI Brain
- **ReAct Agent Loop** - Multi-step reasoning with tool execution
- **RAG Memory** - Semantic search over conversation history
- **Affection System** - Tracks relationship level (0-100%)
- **22+ Emotions** - Love, happy, yandere, panic, victory, etc.

### Voice & Avatar
- **Pocket-TTS** - Real-time voice synthesis with emotion
- **VTube Studio** - Live2D lip-sync and expressions
- **15+ Expressions** - Mapped to detected emotions

### Multi-Platform
- **Tauri Desktop** - Main application (Windows/Linux/macOS)
- **Discord Bot** - Chat via mentions and DMs
- **Telegram Bot** - Group chat support

### Tools
- **Spotify Hub** - Playback awareness & music mood reactions
- **Direct Vision** - Screens and images processed natively by Gemma 4
- **MCP Bridge** - File system, clipboard, process management
- **Sandbox** - Safe Python code execution
- **OpenClaw** - Delegate complex coding tasks
- **Image Gen** - AI image generation
- **LaTeX** - Math to PDF conversion
- **Auto-Janitor** - Automated 6h/24h cache cleanup & log rotation
- **Status API** - Diagnostics at `http://localhost:8000/api/status`

---

## Configuration

### Provider Options

**OpenRouter (Default)**
```json
{
  "PROVIDER": "OpenRouter",
  "MODEL_NAME": "google/gemma-3-27b-it:free"
}
```

**Ollama (Local)**
```json
{
  "PROVIDER": "Ollama",
  "MODEL_NAME": "qwen3.5:397b-cloud"
}
```

**Gemini**
```json
{
  "PROVIDER": "Gemini",
  "MODEL_NAME": "gemini-2.0-flash"
}
```

### TTS Providers

- `Pocket` - Local TTS (default, offline)
- `Gemini` - Cloud TTS (higher quality)

---

## Project Structure

| Directory | Purpose |
|-----------|---------|
| `core/` | Python AI backend (50+ modules) |
| `aiko-app/` | React + Tauri frontend |
| `data/` | Configuration and runtime data |
| `scripts/` | Utility and deployment scripts |
| `tests/` | Integration tests |
| `assets/` | Live2D models and UI assets |
| `.logs/` | Runtime logs |

---

## Logs

All background processes log to `.logs/`:
- `neural_hub.log` - Main AI server
- `ollama.log` - Ollama serve
- `discord_bot.log` - Discord activity
- `telegram_bot.log` - Telegram activity
- `tauri_dev.log` - Frontend development

---

## Docker Deployment

```bash
# Build and run with Docker Compose
docker-compose up -d

# Services:
# - aiko-desktop (port 8550)
# - aiko-sandbox (port 8080)
# - clawdbot (port 8765)
```

---

## Development

```bash
# Backend only
python core/neural_hub.py

# Frontend only
cd aiko-app && npm run tauri dev

# Full stack
python start_aiko_tauri.py
```

---

## License

MIT License - Made by Antigravity

---

*"Always here to help~"*
