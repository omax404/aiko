# Aiko Desktop

Aiko Desktop is a powerful, AI-driven personal assistant designed to run on your desktop. It integrates with various platforms like Discord, Telegram, and VTube Studio to provide a seamless assistant experience.

## Features

- **Multi-Platform Integration**: Connect with Discord and Telegram.
- **VTube Studio Integration**: Control your VTube Studio avatar directly through Aiko.
- **System Monitoring**: Monitor your PC's health and performance.
- **Image Generation**: Generate images using the Pollinations API.
- **Vision Capabilities**: Analyze images and screen content.
- **Voice Assistant**: Integrated TTS and speech recognition capabilities.
- **Memory & RAG**: Context-aware interactions using long-term memory.

## Prerequisites

- Python 3.10+
- (Optional) VTube Studio for avatar control.
- API Keys for Discord, Telegram, Pollinations, and DeepSeek.

## Installation

1. **Clone the repository**:
   ```bash
   git clone https://github.com/your-username/Aiko-desktop.git
   cd Aiko-desktop
   ```

2. **Set up a virtual environment**:
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment variables**:
   - Rename `.env.example` to `.env`.
   - Add your API keys to the `.env` file.

5. **Run the application**:
   ```bash
   python main.py
   ```

## Configuration

You can customize Aiko's behavior by editing the `data/config.json` file. This includes settings for:
- Username
- Theme mode
- Enabled platforms (Discord, Telegram)
- VTube Studio port

## License

MIT License. See `LICENSE` for more details.
