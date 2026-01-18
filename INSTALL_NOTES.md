# Installation Notes

## Dependency Resolution

This project has been optimized for faster and more reliable installation by:

1. **Using transformers' Whisper implementation**: Instead of the standalone `openai-whisper` package, we use the Whisper model from the `transformers` library, which is already included in the dependencies. This avoids dependency conflicts.

2. **Version constraints**: All major dependencies have upper version bounds to help pip's dependency resolver find compatible versions faster.

3. **Expected installation time**: 5-10 minutes on a typical internet connection.

## Why Not openai-whisper?

The `openai-whisper` package can cause dependency resolution issues because:
- It has strict version requirements that may conflict with other packages
- The `transformers` library provides the same Whisper models with better integration
- Using `transformers` reduces dependency conflicts and installation time

## Whisper Usage

The STT service (`services/stt/stt.py`) uses `transformers.AutoModelForSpeechSeq2Seq` which provides:
- Same Whisper Large v3 model
- Better integration with the ecosystem
- Consistent API with other models
- Automatic INT8 quantization support

## Alternative: Install openai-whisper separately

If you prefer to use the original `openai-whisper` package:

```bash
# After installing requirements.txt
pip install openai-whisper==20231117 --no-deps
```

Note: This may cause conflicts. Only do this if you need specific features from the original package.

## Troubleshooting

### Slow pip resolution
If you see "pip is looking at multiple versions", this is normal during first install. The version constraints in requirements.txt should resolve this within 5-10 minutes.

### Dependency conflicts
If you encounter conflicts:
1. Use a fresh virtual environment
2. Install PyTorch first: `pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118`
3. Then install requirements: `pip install -r requirements.txt`

### Already installed packages causing issues
```bash
# Create fresh environment
deactivate
rm -rf venv
python3.10 -m venv venv
source venv/bin/activate
pip install --upgrade pip
# Then follow installation steps
```
