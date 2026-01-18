# Quick Start Guide

Get up and running with the video dubbing system in 5 minutes!

## TL;DR

```bash
# Install
git clone https://github.com/ota-jalol/video-aii.git
cd video-aii
python3.10 -m venv venv
source venv/bin/activate
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118
pip install -r requirements.txt

# Configure (add your HuggingFace token)
nano configs/config.yaml

# Run
python main.py input.mp4 output.mp4 --target-lang en
```

## Prerequisites

- ✅ Linux/Windows with NVIDIA GPU (12GB VRAM)
- ✅ Python 3.10+
- ✅ FFmpeg installed
- ✅ 20GB free disk space

## Installation (3 minutes)

### 1. Install System Dependencies

**Linux:**
```bash
sudo apt-get install -y ffmpeg rubberband-cli
```

**macOS:**
```bash
brew install ffmpeg rubberband
```

**Windows:**
- Download FFmpeg from https://ffmpeg.org/download.html
- Add to PATH

### 2. Clone and Setup Python

```bash
git clone https://github.com/ota-jalol/video-aii.git
cd video-aii

# Create virtual environment
python3.10 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install --upgrade pip
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118
pip install -r requirements.txt
```

### 3. Configure HuggingFace Token

1. Get token from https://huggingface.co/settings/tokens
2. Accept agreements:
   - https://huggingface.co/pyannote/speaker-diarization-3.1
   - https://huggingface.co/pyannote/segmentation-3.0
3. Add to `configs/config.yaml`:
   ```yaml
   models:
     diarization:
       auth_token: "your_token_here"
   ```

## Usage (1 minute)

### Basic Usage

```bash
python main.py input.mp4 output.mp4 --target-lang en
```

### Common Examples

```bash
# Auto-detect source language, dub to English
python main.py video.mp4 dubbed.mp4 --target-lang en

# Spanish to French
python main.py video.mp4 dubbed.mp4 --source-lang es --target-lang fr

# Japanese to English with debug output
python main.py video.mp4 dubbed.mp4 --target-lang en --log-level DEBUG

# Keep temporary files for inspection
python main.py video.mp4 dubbed.mp4 --target-lang en --keep-temp
```

## Language Codes

| Code | Language   | Code | Language    | Code | Language   |
|------|------------|------|-------------|------|------------|
| en   | English    | es   | Spanish     | fr   | French     |
| de   | German     | zh   | Chinese     | ja   | Japanese   |
| ko   | Korean     | ar   | Arabic      | hi   | Hindi      |
| pt   | Portuguese | ru   | Russian     | it   | Italian    |
| tr   | Turkish    | pl   | Polish      | nl   | Dutch      |

## Expected Processing Time

- **1-minute video**: ~5-10 minutes
- **10-minute video**: ~50-100 minutes
- **30-minute video**: ~2.5-5 hours

First run will be slower due to model downloads (~20GB).

## Troubleshooting Quick Fixes

### Out of Memory
```bash
# Edit configs/config.yaml
processing:
  batch_size_stt: 4  # Reduce from 8
```

### FFmpeg Not Found
```bash
# Linux
sudo apt-get install ffmpeg

# macOS
brew install ffmpeg
```

### Diarization Fails
- Check HuggingFace token in `configs/config.yaml`
- Ensure you accepted model agreements
- Try: `huggingface-cli login`

## Output

The system will:
1. ✅ Extract and analyze the video
2. ✅ Separate music and speech
3. ✅ Identify speakers
4. ✅ Transcribe speech
5. ✅ Detect emotions
6. ✅ Translate to target language
7. ✅ Synthesize new speech with voice cloning
8. ✅ Mix with background music
9. ✅ Create final dubbed video

## Next Steps

- 📖 Read full [README.md](README.md) for detailed usage
- 🏗️ Check [ARCHITECTURE.md](ARCHITECTURE.md) to understand the system
- ⚙️ See [SETUP.md](SETUP.md) for advanced configuration

## Need Help?

1. Check logs: `logs/dubbing.log`
2. Run with debug: `--log-level DEBUG`
3. Keep temp files: `--keep-temp`
4. Open issue on GitHub

## Tips

- **First run**: Will download ~20GB of models (takes time)
- **GPU usage**: Monitor with `nvidia-smi`
- **Quality**: Use rubberband for better time-stretching
- **Speed**: Faster GPU = faster processing
- **Memory**: Close other GPU applications during processing

## Common Workflows

### Batch Processing

```bash
# Process multiple videos
for video in *.mp4; do
    python main.py "$video" "dubbed_${video}" --target-lang en
done
```

### Different Languages

```bash
# Dub the same video to multiple languages
python main.py input.mp4 english.mp4 --target-lang en
python main.py input.mp4 spanish.mp4 --target-lang es
python main.py input.mp4 french.mp4 --target-lang fr
```

### Testing

```bash
# Create test video
ffmpeg -f lavfi -i testsrc=duration=10:size=640x480:rate=30 \
       -f lavfi -i sine=frequency=1000:duration=10 \
       test.mp4

# Process test video
python main.py test.mp4 test_output.mp4 --target-lang en
```

---

**Ready to start?** Just run:
```bash
python main.py your_video.mp4 output.mp4 --target-lang en
```

🎬 Happy dubbing!
