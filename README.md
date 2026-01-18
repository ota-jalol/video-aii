# Video AI - Multilingual Video Dubbing System

![Python](https://img.shields.io/badge/python-3.10+-blue.svg)
![License](https://img.shields.io/badge/license-MIT-green.svg)
![Status](https://img.shields.io/badge/status-production--ready-brightgreen.svg)

A **fully local, offline, end-to-end multilingual video dubbing system** that translates and dubs videos from any language to any language while preserving speaker identity, emotion, and prosody.

## 🎯 Features

- **100% Offline**: No internet required after setup
- **Multilingual**: Supports 200+ languages (any → any translation)
- **Voice Cloning**: Preserves speaker identity in the target language
- **Emotion Preservation**: Maintains emotional tone and prosody
- **Speaker Diarization**: Handles multiple speakers automatically
- **Production Ready**: Modular, extensible, and memory-efficient
- **GPU Optimized**: Runs on 12GB VRAM with intelligent memory management

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

### System Requirements
- **OS**: Linux or Windows
- **GPU**: 12GB VRAM (CUDA-capable)
- **RAM**: 16GB+ recommended
- **Python**: 3.10 or higher
- **Storage**: ~20GB for models

### Software Dependencies
- **FFmpeg**: For audio/video processing
- **Rubberband** (optional): For high-quality time stretching

## 🚀 Installation

### 1. Clone the Repository

```bash
git clone https://github.com/ota-jalol/video-aii.git
cd video-aii
```

### 2. Create Virtual Environment

```bash
python3.10 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 3. Install Python Dependencies

```bash
pip install --upgrade pip

# Install PyTorch with CUDA support first (adjust for your CUDA version)
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118

# Install other dependencies
pip install -r requirements.txt
```

**Note on dependency resolution**: 
- This project uses `transformers` implementation of Whisper (included in requirements.txt)
- If you experience slow dependency resolution, the requirements have upper bounds to speed up resolution
- Installation typically takes 5-10 minutes

### 4. Install System Dependencies

#### Linux (Ubuntu/Debian)
```bash
sudo apt-get update
sudo apt-get install -y ffmpeg rubberband-cli
```

#### macOS
```bash
brew install ffmpeg rubberband
```

#### Windows
- Download FFmpeg from https://ffmpeg.org/download.html
- Add to PATH
- Rubberband is optional on Windows

### 5. Download Models (First Run)

Models will be automatically downloaded on first use. Ensure you have:
- HuggingFace access for pyannote models (requires token)
- ~20GB free disk space

#### Get HuggingFace Token (Required for Diarization)

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

Edit `configs/config.yaml` to customize:

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

**Note**: This system is designed for offline use with local models. First-time setup requires internet to download models (~20GB). After initial setup, the system runs completely offline.