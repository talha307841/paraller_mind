#!/usr/bin/env bash
# =============================================================================
# Parallel Mind — Raspberry Pi Setup Script
# Run once on a fresh Pi 5 (Ubuntu 24.04 64-bit or Raspberry Pi OS 64-bit).
# Requires internet access for the initial model downloads.
# =============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DATA_DIR="${HOME}/.parallel_mind"
VOICES_DIR="${DATA_DIR}/voices"
VOICE="${PIPER_VOICE:-en_US-lessac-medium}"

echo ""
echo "╔══════════════════════════════════════════╗"
echo "║      PARALLEL MIND — PI SETUP            ║"
echo "╚══════════════════════════════════════════╝"
echo ""

# ── 1. System dependencies ────────────────────────────────────────────────────
echo "[1/6] Installing system packages..."
sudo apt-get update -qq
sudo apt-get install -y \
    portaudio19-dev \
    python3-pyaudio \
    espeak \
    ffmpeg \
    git \
    curl \
    libsndfile1 \
    2>/dev/null
echo "      ✓ System packages ready"

# ── 2. Python packages ────────────────────────────────────────────────────────
echo "[2/6] Installing Python packages..."
pip install --upgrade pip -q
pip install -r "${SCRIPT_DIR}/requirements.txt" -q
echo "      ✓ Python packages installed"

# ── 3. spaCy model ────────────────────────────────────────────────────────────
echo "[3/6] Downloading spaCy language model..."
python -m spacy download en_core_web_sm -q
echo "      ✓ spaCy en_core_web_sm ready"

# ── 4. Piper TTS voice ────────────────────────────────────────────────────────
echo "[4/6] Downloading Piper TTS voice: ${VOICE}..."
mkdir -p "${VOICES_DIR}"

# Build HuggingFace URL from voice name: en_US-lessac-medium
# Path pattern: /en/en_US/lessac/medium/<voicefile>
IFS='-' read -ra PARTS <<< "${VOICE}"
LANG_REG="${PARTS[0]}"          # e.g. en_US
LANG="${LANG_REG%%_*}"          # e.g. en
SPEAKER="${PARTS[1]:-lessac}"   # e.g. lessac
QUALITY="${PARTS[2]:-medium}"   # e.g. medium

HF_BASE="https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0"
HF_DIR="${HF_BASE}/${LANG}/${LANG_REG}/${SPEAKER}/${QUALITY}"

for EXT in ".onnx" ".onnx.json"; do
    FNAME="${VOICE}${EXT}"
    DEST="${VOICES_DIR}/${FNAME}"
    if [ -f "${DEST}" ]; then
        echo "      ✓ Already exists: ${FNAME}"
    else
        echo "      Downloading ${FNAME}..."
        curl -fsSL -o "${DEST}" "${HF_DIR}/${FNAME}" || {
            echo "      ✗ Download failed for ${FNAME}"
            echo "        Manual download: ${HF_DIR}/${FNAME}"
        }
    fi
done
echo "      ✓ Piper voice ready at ${VOICES_DIR}"

# ── 5. Silero VAD pre-download ────────────────────────────────────────────────
echo "[5/6] Pre-downloading Silero VAD model (requires internet, ~5MB)..."
python -c "
import torch, sys
print('      Downloading from snakers4/silero-vad on GitHub...')
try:
    torch.hub.load('snakers4/silero-vad', 'silero_vad', force_reload=False, verbose=False)
    print('      ✓ Silero VAD cached')
except Exception as e:
    print(f'      ✗ Warning: {e}')
    print('      Will retry on first run.')
    sys.exit(0)
"

# ── 6. .env setup ─────────────────────────────────────────────────────────────
echo "[6/6] Setting up environment file..."
if [ ! -f "${SCRIPT_DIR}/.env" ]; then
    cp "${SCRIPT_DIR}/env.template" "${SCRIPT_DIR}/.env"
    echo "      ✓ Created .env — EDIT IT and set NVIDIA_API_KEY before running"
else
    echo "      ✓ .env already exists"
fi

mkdir -p "${DATA_DIR}/chromadb"

echo ""
echo "══════════════════════════════════════════════"
echo "Setup complete!"
echo ""
echo "Next steps:"
echo "  1. Edit .env and set NVIDIA_API_KEY"
echo "  2. Run: python ${SCRIPT_DIR}/main.py"
echo ""
echo "API will be available at: http://$(hostname -I | awk '{print $1}'):${API_PORT:-8765}"
echo "══════════════════════════════════════════════"
#!/usr/bin/env bash
# ╔══════════════════════════════════════════════════════════╗
# ║     PARALLEL MIND — Raspberry Pi 5 Setup Script         ║
# ║  Run once after cloning the repo.                        ║
# ║  Usage:  bash setup.sh                                   ║
# ╚══════════════════════════════════════════════════════════╝

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# ── Colours ───────────────────────────────────────────────────────────────────
GREEN='\033[0;32m'; YELLOW='\033[1;33m'; RED='\033[0;31m'; NC='\033[0m'
info()  { echo -e "${GREEN}[INFO]${NC}  $*"; }
warn()  { echo -e "${YELLOW}[WARN]${NC}  $*"; }
error() { echo -e "${RED}[ERR]${NC}   $*"; exit 1; }

# ── Detect architecture ───────────────────────────────────────────────────────
ARCH=$(uname -m)
case "$ARCH" in
  aarch64|arm64) PIPER_ARCH="aarch64"  ;;
  armv7l)        PIPER_ARCH="armv7l"   ;;
  x86_64)        PIPER_ARCH="x86_64"   ;;
  *)             warn "Unknown arch $ARCH — defaulting to aarch64"; PIPER_ARCH="aarch64" ;;
esac
info "Architecture: $ARCH (Piper arch: $PIPER_ARCH)"

# ── System packages ───────────────────────────────────────────────────────────
info "Installing system packages …"
sudo apt-get update -qq
sudo apt-get install -y --no-install-recommends \
    portaudio19-dev \
    python3-dev \
    python3-pip \
    alsa-utils \
    libasound2-dev \
    wget \
    curl \
    tar \
    libgomp1
info "System packages installed"

# ── Python dependencies ───────────────────────────────────────────────────────
info "Installing Python packages (this may take 10–20 min on Pi) …"
pip3 install --upgrade pip --quiet
pip3 install -r requirements.txt --quiet
info "Python packages installed"

# ── spaCy model ───────────────────────────────────────────────────────────────
info "Downloading spaCy English model …"
python3 -m spacy download en_core_web_sm --quiet
info "spaCy model ready"

# ── Piper TTS binary ──────────────────────────────────────────────────────────
PIPER_VERSION="2023.11.14-2"
PIPER_DIR="$SCRIPT_DIR/data/models/piper"
mkdir -p "$PIPER_DIR"

if [ -f "$PIPER_DIR/piper" ]; then
    info "Piper binary already present — skipping download"
else
    info "Downloading Piper TTS binary (${PIPER_ARCH}) …"
    PIPER_TARBALL="piper_${PIPER_ARCH}.tar.gz"
    PIPER_URL="https://github.com/rhasspy/piper/releases/download/${PIPER_VERSION}/${PIPER_TARBALL}"

    wget -q --show-progress -O "/tmp/$PIPER_TARBALL" "$PIPER_URL" || \
        error "Failed to download Piper from $PIPER_URL"

    tar -xzf "/tmp/$PIPER_TARBALL" -C "$PIPER_DIR" --strip-components=1
    rm -f "/tmp/$PIPER_TARBALL"
    chmod +x "$PIPER_DIR/piper"
    info "Piper TTS installed at $PIPER_DIR/piper"
fi

# ── Piper voice model ─────────────────────────────────────────────────────────
VOICE="en_US-lessac-medium"
VOICE_ONNX="$PIPER_DIR/${VOICE}.onnx"
VOICE_JSON="$PIPER_DIR/${VOICE}.onnx.json"
HF_BASE="https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0"

if [ -f "$VOICE_ONNX" ] && [ -f "$VOICE_JSON" ]; then
    info "Default voice model already present — skipping download"
else
    info "Downloading voice model: ${VOICE} …"
    LANG_SHORT="en"
    LANG_REGION="en_US"
    URL_BASE="${HF_BASE}/${LANG_SHORT}/${LANG_REGION}/${VOICE}"
    wget -q --show-progress -O "$VOICE_ONNX" "${URL_BASE}.onnx" || \
        warn "Voice ONNX download failed — will retry at runtime"
    wget -q --show-progress -O "$VOICE_JSON" "${URL_BASE}.onnx.json" || \
        warn "Voice JSON download failed — will retry at runtime"
    info "Voice model ready: $VOICE"
fi

# ── .env file ─────────────────────────────────────────────────────────────────
if [ ! -f "$SCRIPT_DIR/.env" ]; then
    cp "$SCRIPT_DIR/.env.template" "$SCRIPT_DIR/.env"
    warn "Created .env from template — EDIT IT NOW and add your NVIDIA_API_KEY!"
    warn "  nano $SCRIPT_DIR/.env"
else
    info ".env already exists — not overwriting"
fi

# ── ReSpeaker HAT driver (optional) ──────────────────────────────────────────
echo ""
echo -e "${YELLOW}Optional: ReSpeaker 2-Mic HAT driver${NC}"
echo "  If using a ReSpeaker HAT and audio is not detected, run:"
echo "  https://github.com/HinTak/seeed-voicecard"
echo ""

# ── Done ──────────────────────────────────────────────────────────────────────
echo ""
echo -e "${GREEN}╔══════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║              Setup complete!                             ║${NC}"
echo -e "${GREEN}╚══════════════════════════════════════════════════════════╝${NC}"
echo ""
echo "Next steps:"
echo "  1. Add your NVIDIA_API_KEY to .env:"
echo "       nano $SCRIPT_DIR/.env"
echo "  2. (Optional) add your Groq key too for fallback coverage"
echo "  3. Start Parallel Mind:"
echo "       bash run.sh"
echo "  4. To list audio input devices:"
echo "       python3 main.py --list-devices"
echo ""
