# Stage 1: Build React
FROM node:20 AS builder
WORKDIR /app
# We need to copy the aiko-app folder specifically
COPY aiko-app/package*.json ./
RUN npm install
COPY aiko-app/ .
# Disable Tauri specific plugins during build if needed
RUN npm run build

# Stage 2: Final image (Python Hub)
FROM python:3.11-slim
WORKDIR /app

# Install system dependencies for audio/ONNX
RUN apt-get update && apt-get install -y \
    ffmpeg \
    libsndfile1 \
    python3-dev \
    gcc \
    texlive-latex-base \
    texlive-latex-extra \
    texlive-fonts-recommended \
    && rm -rf /var/lib/apt/lists/*

# Install python requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
# Moonshine + Pocket-TTS
RUN pip install onnxruntime-browser moonshine-voice pocket-tts || pip install onnxruntime moonshine-voice pocket-tts

# Copy project files
COPY core/ core/
COPY modeles/ modeles/
COPY Reference\ Audios/ Reference\ Audios/
COPY stickers/ stickers/
COPY data/ data/
# Note: we will use environment variables instead of a real .env for security

# Copy build from builder
COPY --from=builder /app/dist ./dist

# Hugging Face Spaces specifically looks for user 1000
RUN useradd -m -u 1000 user
USER user
ENV HOME=/home/user \
    PATH=/home/user/.local/bin:$PATH \
    HEADLESS=true \
    PORT=7860

WORKDIR /app

# Ensure directories exist and are writable
RUN mkdir -p data/voices uploads && chmod -R 777 data/voices uploads

EXPOSE 7860
CMD ["python", "core/neural_hub.py", "--host", "0.0.0.0", "--port", "7860"]
