# Setup Guide

This guide will help you set up the multilingual video dubbing system from scratch.

## Prerequisites Checklist

Before starting, ensure you have:

- [ ] Linux or Windows OS
- [ ] NVIDIA GPU with 12GB+ VRAM
- [ ] CUDA 11.8+ installed
- [ ] Python 3.10 or 3.11 installed
- [ ] 20GB+ free disk space
- [ ] 16GB+ RAM
- [ ] Internet connection (for initial setup only)

## Step-by-Step Installation

### Step 1: System Dependencies

#### Ubuntu/Debian Linux

```bash
# Update package list
sudo apt-get update

# Install FFmpeg
sudo apt-get install -y ffmpeg

# Install Rubberband (optional but recommended)
sudo apt-get install -y rubberband-cli

# Verify installations
ffmpeg -version
rubberband -h
```

#### Windows

1. **Install FFmpeg**:
   - Download from https://ffmpeg.org/download.html
   - Extract to `C:\ffmpeg`
   - Add `C:\ffmpeg\bin` to PATH
   - Verify: `ffmpeg -version`

2. **Rubberband** (optional):
   - Not readily available for Windows
   - System will use FFmpeg fallback

#### macOS

```bash
# Install Homebrew if not already installed
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# Install dependencies
brew install ffmpeg rubberband

# Verify
ffmpeg -version
rubberband -h
```

### Step 2: Clone Repository

```bash
git clone https://github.com/ota-jalol/video-aii.git
cd video-aii
```

### Step 3: Python Environment

#### Using venv (Recommended)

```bash
# Create virtual environment
python3.10 -m venv venv

# Activate virtual environment
source venv/bin/activate  # Linux/Mac
# OR
venv\Scripts\activate  # Windows

# Upgrade pip
pip install --upgrade pip
```

#### Using conda (Alternative)

```bash
# Create conda environment
conda create -n video-dubbing python=3.10

# Activate environment
conda activate video-dubbing
```

### Step 4: Install Python Dependencies

```bash
# Install PyTorch with CUDA support first
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118

# Install other dependencies
pip install -r requirements.txt
```

**Note**: If you have a different CUDA version, adjust the PyTorch installation command accordingly.
Visit https://pytorch.org/get-started/locally/ for the correct command.

### Step 5: HuggingFace Setup

Some models require HuggingFace authentication:

1. **Create HuggingFace Account**:
   - Visit https://huggingface.co/join
   - Sign up for a free account

2. **Accept Model Agreements**:
   - Visit https://huggingface.co/pyannote/speaker-diarization-3.1
   - Accept the user agreement
   - Visit https://huggingface.co/pyannote/segmentation-3.0
   - Accept the user agreement

3. **Generate Access Token**:
   - Go to https://huggingface.co/settings/tokens
   - Create a new token with "read" access
   - Copy the token

4. **Add Token to Config**:
   ```bash
   # Edit configs/config.yaml
   nano configs/config.yaml  # or use your preferred editor
   ```
   
   Add your token:
   ```yaml
   models:
     diarization:
       auth_token: "hf_YourTokenHere"
   ```

### Step 6: Verify Installation

```bash
# Check CUDA availability
python -c "import torch; print('CUDA available:', torch.cuda.is_available())"
python -c "import torch; print('CUDA device:', torch.cuda.get_device_name(0))"

# Check PyTorch version
python -c "import torch; print('PyTorch version:', torch.__version__)"

# Verify main script loads
python main.py --help
```

Expected output from `--help`:
```
usage: main.py [-h] [--target-lang TARGET_LANG] ...
```

### Step 7: Download Models (First Run)

Models will be automatically downloaded on first use. To pre-download:

```bash
# This will download all required models (~20GB)
# It will take 30-60 minutes depending on your internet speed

python -c "
from transformers import AutoModelForSpeechSeq2Seq, AutoProcessor
from transformers import AutoModelForSeq2SeqLM, AutoTokenizer

print('Downloading Whisper...')
AutoProcessor.from_pretrained('openai/whisper-large-v3')
AutoModelForSpeechSeq2Seq.from_pretrained('openai/whisper-large-v3')

print('Downloading NLLB...')
AutoTokenizer.from_pretrained('facebook/nllb-200-1.3B')
AutoModelForSeq2SeqLM.from_pretrained('facebook/nllb-200-1.3B')

print('Models downloaded!')
"
```

## Configuration

### Basic Configuration

Edit `configs/config.yaml`:

```yaml
system:
  gpu_memory_gb: 12  # Adjust to your GPU
  device: "cuda"     # or "cpu" for CPU-only

languages:
  target: "en"       # Default target language
```

### Advanced Configuration

#### Reduce Memory Usage

For GPUs with less memory:

```yaml
models:
  whisper:
    quantization: "int8"  # Keep this
  post_edit_llm:
    quantization: "4bit"  # Or try "8bit"

processing:
  batch_size_stt: 4  # Reduce from 8
```

#### Improve Quality

For better quality (needs more VRAM):

```yaml
audio:
  sample_rate: 22050  # Higher quality audio

output:
  audio_bitrate: "256k"  # Higher quality output

audio:
  alignment:
    stretch_algorithm: "rubberband"  # Better time-stretching
```

## Testing Installation

### Quick Test

```bash
# Create a small test video (or use your own)
ffmpeg -f lavfi -i testsrc=duration=10:size=640x480:rate=30 \
       -f lavfi -i sine=frequency=1000:duration=10 \
       -pix_fmt yuv420p test_input.mp4

# Run dubbing (should complete in a few minutes)
python main.py test_input.mp4 test_output.mp4 --target-lang en
```

### Check Output

```bash
# Play the output video
ffplay test_output.mp4

# Or check file info
ffprobe test_output.mp4
```

## Troubleshooting

### CUDA Out of Memory

**Solution 1**: Reduce batch size
```yaml
processing:
  batch_size_stt: 2
```

**Solution 2**: Use CPU for some models
```yaml
models:
  emotion:
    device: "cpu"  # Move emotion model to CPU
```

### Module Not Found Errors

```bash
# Ensure virtual environment is activated
source venv/bin/activate

# Reinstall dependencies
pip install -r requirements.txt
```

### FFmpeg Not Found

```bash
# Check if in PATH
which ffmpeg

# If not found, install:
# Linux
sudo apt-get install ffmpeg

# macOS
brew install ffmpeg
```

### HuggingFace Authentication Failed

1. Check token is correct in `configs/config.yaml`
2. Ensure you accepted model agreements
3. Try updating token:
   ```bash
   huggingface-cli login
   ```

### Slow Processing

**Normal**: Processing takes 5-10x video length
- 1-minute video = 5-10 minutes processing
- 10-minute video = 50-100 minutes processing

**If excessively slow**:
- Check GPU utilization: `nvidia-smi`
- Ensure CUDA is being used (see verification above)
- Close other GPU-intensive applications

## Updating

```bash
# Pull latest changes
git pull origin main

# Update dependencies
pip install -r requirements.txt --upgrade
```

## Uninstallation

```bash
# Remove virtual environment
rm -rf venv

# Remove downloaded models
rm -rf models/

# Remove logs and temp files
rm -rf logs/
rm -rf /tmp/video_dubbing/

# Remove repository (optional)
cd ..
rm -rf video-aii/
```

## Next Steps

Once installation is complete:

1. Read the [README.md](README.md) for usage examples
2. Check [ARCHITECTURE.md](ARCHITECTURE.md) for system details
3. Try dubbing your first video!

## Getting Help

If you encounter issues:

1. Check the [Troubleshooting](#troubleshooting) section above
2. Review logs in `logs/dubbing.log`
3. Keep temp files with `--keep-temp` flag
4. Open an issue on GitHub with:
   - Error message
   - Log file
   - System information (OS, GPU, Python version)
