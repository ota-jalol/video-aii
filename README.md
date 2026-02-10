# Video AI - Multilingual Video Dubbing System

![Python](https://img.shields.io/badge/python-3.10+-blue.svg)
![License](https://img.shields.io/badge/license-MIT-green.svg)
![Status](https://img.shields.io/badge/status-production--ready-brightgreen.svg)

A **multilingual video dubbing system** that translates and dubs videos from any language to any language while preserving speaker identity, emotion, and prosody.

**Two Modes Available:**
- **Cloud Mode (GitHub Models)**: Uses cloud-based AI models via GitHub - no GPU required! ☁️
- **Local Mode**: 100% offline with local models - requires 12GB GPU 💻

## 🎯 Features

- **Cloud or Local**: Choose between GitHub Models (cloud) or local models
- **No GPU Required (Cloud Mode)**: Use GitHub Models with just a GitHub account
- **100% Offline (Local Mode)**: No internet required after setup
- **Multilingual**: Supports 200+ languages (any → any translation)
- **Voice Cloning**: Preserves speaker identity in the target language
- **Emotion Preservation**: Maintains emotional tone and prosody
- **Speaker Diarization**: Handles multiple speakers automatically
- **Production Ready**: Modular, extensible, and memory-efficient

## 🏗️ Pipeline Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    INPUT: Video File                        │
└──────────────────────┬──────────────────────────────────────┘
                       │
    ┌──────────────────┴──────────────────┐
    │   1. Video Ingestion & Validation   │
    └──────────────────┬──────────────────┘
                       │
    ┌──────────────────┴──────────────────┐
    │   2. Audio Extraction (FFmpeg)      │
    └──────────────────┬──────────────────┘
                       │
    ┌──────────────────┴──────────────────┐
    │   3. Music/Speech Separation        │
    │      (Demucs htdemucs)              │
    └──────────────────┬──────────────────┘
                       │
    ┌──────────────────┴──────────────────┐
    │   4. Speaker Diarization            │
    │      (pyannote.audio 3.1)           │
    └──────────────────┬──────────────────┘
                       │
    ┌──────────────────┴──────────────────┐
    │   5. Speech-to-Text with Timestamps │
    │      (Whisper Large v3 INT8)        │
    └──────────────────┬──────────────────┘
                       │
    ┌──────────────────┴──────────────────┐
    │   6. Emotion & Prosody Analysis     │
    │      (SpeechBrain Wav2Vec2-IEMOCAP) │
    └──────────────────┬──────────────────┘
                       │
    ┌──────────────────┴──────────────────┐
    │   7. Translation (NLLB-200 1.3B)    │
    └──────────────────┬──────────────────┘
                       │
    ┌──────────────────┴──────────────────┐
    │   8. Post-Editing for Natural Speech│
    │      (Qwen2.5-7B-Instruct 4-bit)    │
    └──────────────────┬──────────────────┘
                       │
    ┌──────────────────┴──────────────────┐
    │   9. Text-to-Speech with Cloning    │
    │      (XTTS v2 - Sequential)         │
    └──────────────────┬──────────────────┘
                       │
    ┌──────────────────┴──────────────────┐
    │   10. Audio Alignment & Mixing      │
    │       (Rubberband/FFmpeg)           │
    └──────────────────┬──────────────────┘
                       │
    ┌──────────────────┴──────────────────┐
    │   11. Video Muxing (FFmpeg)         │
    └──────────────────┬──────────────────┘
                       │
┌──────────────────────┴──────────────────────────────────────┐
│              OUTPUT: Dubbed Video File                       │
└──────────────────────────────────────────────────────────────┘
```

## 📋 Requirements

### Cloud Mode (GitHub Models) - Recommended for Beginners
- **OS**: Linux, macOS, or Windows
- **GPU**: Not required (uses cloud-based models)
- **RAM**: 8GB+ recommended
- **Python**: 3.10 or higher
- **GitHub Account**: Free account required
- **Internet**: Required for API calls

### Local Mode (Offline)
- **OS**: Linux or Windows
- **GPU**: 12GB VRAM (CUDA-capable)
- **RAM**: 16GB+ recommended
- **Python**: 3.10 or higher
- **Storage**: ~20GB for models

### Software Dependencies
- **FFmpeg**: For audio/video processing
- **Rubberband** (optional): For high-quality time stretching

## 🚀 Installation

### Quick Start with Cloud Mode (GitHub Models)

This is the easiest way to get started - no GPU or model downloads required!

#### 1. Clone the Repository

```bash
git clone https://github.com/ota-jalol/video-aii.git
cd video-aii
```

#### 2. Create Virtual Environment

```bash
python3.10 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

#### 3. Install Dependencies

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

#### 4. Get GitHub Token

1. Go to https://github.com/settings/tokens
2. Click "Generate new token" (classic)
3. No special permissions needed - just create the token
4. Copy the token

#### 5. Set Environment Variable

```bash
# Linux/macOS
export GITHUB_TOKEN="your_github_token_here"

# Windows (PowerShell)
$Env:GITHUB_TOKEN="your_github_token_here"

# Windows (CMD)
set GITHUB_TOKEN=your_github_token_here
```

#### 6. Configure for Cloud Mode

Edit `configs/config.yaml`:
```yaml
github_models:
  enabled: true  # Enable GitHub Models
  endpoint: "https://models.inference.ai.azure.com"
  token: null  # Uses GITHUB_TOKEN env variable
```

#### 7. Install System Dependencies

```bash
# Linux (Ubuntu/Debian)
sudo apt-get update
sudo apt-get install -y ffmpeg rubberband-cli

# macOS
brew install ffmpeg rubberband

# Windows: Download FFmpeg from https://ffmpeg.org/download.html
```

That's it! You're ready to use the system with GitHub Models. No GPU or model downloads needed!

---

### Advanced: Local Mode Installation

For offline use with local models (requires 12GB GPU):

Follow steps 1-3 above, then:

#### 4. Install PyTorch with CUDA

```bash
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118
```

#### 5. Configure for Local Mode

Edit `configs/config.yaml`:
```yaml
github_models:
  enabled: false  # Disable GitHub Models to use local models
```

#### 6. Get HuggingFace Token (Required for Diarization)

1. Create account at https://huggingface.co
2. Accept user agreement for pyannote models:
   - https://huggingface.co/pyannote/speaker-diarization-3.1
   - https://huggingface.co/pyannote/segmentation-3.0
3. Generate token: https://huggingface.co/settings/tokens
4. Add to `configs/config.yaml`:
   ```yaml
   models:
     diarization:
       auth_token: "your_token_here"
   ```

#### 7. Install System Dependencies

Same as cloud mode (FFmpeg, Rubberband)

#### 8. Download Models (First Run)

Models will be automatically downloaded on first use (~20GB)

## 💻 Usage

### Basic Usage

```bash
python main.py input.mp4 output.mp4 --target-lang en
```

### Advanced Usage

```bash
# Specify both source and target languages
python main.py video.mp4 dubbed.mp4 --source-lang es --target-lang fr

# Keep temporary files for debugging
python main.py input.mp4 output.mp4 --target-lang en --keep-temp

# Use custom configuration
python main.py input.mp4 output.mp4 --config my_config.yaml --target-lang ja

# Set log level
python main.py input.mp4 output.mp4 --target-lang en --log-level DEBUG
```

### Command-Line Arguments

| Argument | Description | Default |
|----------|-------------|---------|
| `input_video` | Path to input video (required) | - |
| `output_video` | Path for output video (required) | - |
| `--target-lang` | Target language code | From config (en) |
| `--source-lang` | Source language code | Auto-detect |
| `--config` | Custom config file path | configs/config.yaml |
| `--keep-temp` | Keep temporary files | False |
| `--log-level` | Logging level | INFO |

### Supported Languages

The system supports 200+ languages via NLLB-200. Common codes:

| Code | Language | Code | Language | Code | Language |
|------|----------|------|----------|------|----------|
| `en` | English | `es` | Spanish | `fr` | French |
| `de` | German | `zh` | Chinese | `ja` | Japanese |
| `ko` | Korean | `ar` | Arabic | `hi` | Hindi |
| `pt` | Portuguese | `ru` | Russian | `it` | Italian |
| `tr` | Turkish | `pl` | Polish | `nl` | Dutch |
| `vi` | Vietnamese | `th` | Thai | `id` | Indonesian |

## 📁 Project Structure

```
video-aii/
├── configs/                    # Configuration files
│   ├── __init__.py            # Config loader
│   └── config.yaml            # Main configuration
├── models/                    # Downloaded models (auto-created)
├── services/                  # Pipeline services
│   ├── ingestion/            # Video validation
│   ├── audio_extraction/     # Audio extraction
│   ├── separation/           # Music/speech separation
│   ├── diarization/          # Speaker diarization
│   ├── stt/                  # Speech-to-text
│   ├── emotion/              # Emotion analysis
│   ├── translation/          # Translation + post-editing
│   ├── tts/                  # Text-to-speech
│   ├── alignment/            # Audio alignment
│   └── muxing/               # Video muxing
├── orchestrator/             # Pipeline orchestrator
│   ├── __init__.py
│   └── orchestrator.py       # Main orchestration logic
├── utils/                    # Utility modules
│   ├── __init__.py
│   ├── logging_utils.py      # Logging setup
│   ├── file_utils.py         # File operations
│   └── gpu_utils.py          # GPU memory management
├── main.py                   # CLI entry point
├── requirements.txt          # Python dependencies
└── README.md                 # This file
```

## ⚙️ Configuration

### Switching Between Cloud and Local Mode

Edit `configs/config.yaml`:

**For Cloud Mode (GitHub Models):**
```yaml
github_models:
  enabled: true  # Enable cloud-based models
  endpoint: "https://models.inference.ai.azure.com"
  token: null  # Uses GITHUB_TOKEN environment variable

models:
  translation:
    github_model: "gpt-4o-mini"  # Fast and cost-effective
    # Alternative: "phi-4", "mistral-large-3"

  post_edit_llm:
    github_model: "gpt-4o-mini"  # Fast and cost-effective
    # Alternative: "phi-4", "gpt-4o"
```

**For Local Mode:**
```yaml
github_models:
  enabled: false  # Use local models

models:
  translation:
    name: "facebook/nllb-200-1.3B"
    device: "cuda"

  post_edit_llm:
    name: "Qwen/Qwen2.5-7B-Instruct"
    quantization: "4bit"
    device: "cuda"
```

### Available GitHub Models

For translation and post-editing:
- **gpt-4o-mini**: Fast, cost-effective, recommended for most users
- **gpt-4o**: More capable, higher quality
- **phi-4**: Microsoft's efficient model, good balance
- **mistral-large-3**: Open weights, strong performance

### System Settings
```yaml
system:
  gpu_memory_gb: 12          # Available GPU memory
  device: "cuda"             # or "cpu"
  temp_dir: "/tmp/video_dubbing"
```

### Model Settings
```yaml
models:
  whisper:
    quantization: "int8"     # Reduce memory usage
  post_edit_llm:
    quantization: "4bit"     # 4-bit quantization for LLM
```

### Processing Settings
```yaml
processing:
  batch_size_stt: 8          # Batch size for STT
  sequential_tts: true       # Process TTS sequentially
  retry_attempts: 3          # Retry on failure
```

### Language Settings
```yaml
languages:
  source: "auto"             # Auto-detect source
  target: "en"               # Default target language
```

## 🔧 Troubleshooting

### Out of Memory (OOM) Errors

1. **Reduce batch size** in config:
   ```yaml
   processing:
     batch_size_stt: 4  # Reduce from 8
   ```

2. **Enable more aggressive quantization**:
   ```yaml
   models:
     whisper:
       quantization: "int8"
   ```

3. **Process sequentially**: Already enabled by default for TTS

### Diarization Fails

- Ensure you have HuggingFace token configured
- Accept model agreements on HuggingFace
- Check internet connection during first model download

### Installation Issues

If you experience slow pip dependency resolution or conflicts, see [INSTALL_NOTES.md](INSTALL_NOTES.md) for:
- Why we use `transformers` Whisper instead of `openai-whisper`
- Troubleshooting dependency conflicts
- Fresh environment setup

### FFmpeg Not Found

```bash
# Linux
sudo apt-get install ffmpeg

# macOS
brew install ffmpeg

# Windows: Download from ffmpeg.org and add to PATH
```

### Poor Audio Quality

1. **Install rubberband** for better time-stretching:
   ```bash
   sudo apt-get install rubberband-cli  # Linux
   brew install rubberband              # macOS
   ```

2. **Adjust audio settings** in config:
   ```yaml
   audio:
     sample_rate: 22050  # Higher quality
   output:
     audio_bitrate: "256k"  # Higher bitrate
   ```

## 🎓 How It Works

### 1. Architecture Decisions

- **Modular Design**: Each step is an independent service
- **Sequential TTS**: Prevents GPU memory overflow
- **Batch STT**: Processes multiple segments efficiently
- **Memory Management**: Automatic cleanup between steps
- **JSON Artifacts**: Each step saves intermediate results

### 2. Key Technologies

- **Whisper Large v3**: State-of-the-art multilingual STT
- **NLLB-200**: Supports 200+ languages
- **XTTS v2**: Zero-shot voice cloning
- **Demucs**: High-quality source separation
- **pyannote.audio**: Accurate speaker diarization

### 3. Performance Optimization

- INT8 quantization for Whisper (3x memory reduction)
- 4-bit quantization for LLM (4x memory reduction)
- Batch processing where possible
- Sequential processing to avoid OOM
- Automatic GPU cache clearing

## 🤝 Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

This project uses the following open-source models and libraries:

- **Whisper** by OpenAI
- **NLLB-200** by Meta AI
- **XTTS** by Coqui AI
- **pyannote.audio** by Hervé Bredin
- **Demucs** by Facebook Research
- **SpeechBrain** by SpeechBrain Team
- **Qwen2.5** by Alibaba Cloud

## 📧 Support

For issues, questions, or contributions:
- Open an issue on GitHub
- Check existing issues for solutions
- Review the troubleshooting section

## 🔮 Future Enhancements

- [ ] Real-time processing support
- [ ] Web UI interface
- [ ] Docker containerization
- [ ] Cloud deployment support
- [ ] Additional TTS engines
- [ ] Custom voice training
- [ ] Batch video processing
- [ ] Progress webhooks/callbacks

---

## 🌐 GitHub Models Integration

This project now supports GitHub Models, providing cloud-based AI inference through Microsoft's Azure AI platform. This means:

### Benefits of GitHub Models

- **No GPU Required**: Run AI models without expensive hardware
- **Easy Setup**: Just a GitHub token - no model downloads
- **Always Up-to-Date**: Access to latest models without manual updates
- **Cost-Effective**: Free tier available for experimentation
- **Flexible**: Switch between multiple models instantly

### How It Works

The system uses the Azure AI Inference SDK to connect to GitHub's model catalog. When enabled:

1. **Translation**: Uses GPT-4o-mini or other LLMs instead of NLLB-200
2. **Post-Editing**: Uses cloud-based LLMs instead of local Qwen model
3. **Other Services**: STT, TTS, and diarization still run locally (for now)

### Cost Considerations

GitHub Models offers:
- **Free Tier**: Limited requests for prototyping and testing
- **Paid Tier**: Higher rate limits for production use

Check [GitHub Models documentation](https://github.com/marketplace?type=models) for current pricing and limits.

### Fallback to Local Models

If GitHub Models fails or is unavailable, the system automatically falls back to local models (if configured). This ensures reliability even when the cloud service is down.

---

**Note**: The system is designed to be flexible - you can use GitHub Models (cloud), local models (offline), or a hybrid approach where some services use cloud and others use local models.