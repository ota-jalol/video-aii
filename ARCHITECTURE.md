# Architecture Documentation

## System Overview

This is a fully local, offline end-to-end multilingual video dubbing system that processes videos through 11 distinct pipeline stages to produce high-quality dubbed content.

## Design Principles

1. **Modularity**: Each pipeline stage is an independent service with clear interfaces
2. **Memory Efficiency**: GPU memory is carefully managed to run on 12GB VRAM
3. **Offline Operation**: All models run locally without internet dependency
4. **Reliability**: Retry logic and error handling throughout
5. **Observability**: Comprehensive logging and intermediate artifact saving

## Pipeline Stages

### 1. Video Ingestion (`services/ingestion/`)
- **Purpose**: Validate and extract video metadata
- **Implementation**: `VideoIngestionService`
- **Output**: Video metadata (duration, resolution, codecs)
- **Dependencies**: FFmpeg (ffprobe)

### 2. Audio Extraction (`services/audio_extraction/`)
- **Purpose**: Extract audio from video file
- **Implementation**: `AudioExtractionService`
- **Output**: WAV audio file (mono, 16kHz)
- **Dependencies**: FFmpeg

### 3. Music/Speech Separation (`services/separation/`)
- **Purpose**: Separate vocals from background music
- **Implementation**: `SeparationService`
- **Model**: Demucs htdemucs
- **Output**: Vocals audio, background audio
- **Memory**: ~3GB VRAM

### 4. Speaker Diarization (`services/diarization/`)
- **Purpose**: Identify and segment different speakers
- **Implementation**: `DiarizationService`
- **Model**: pyannote.audio 3.1
- **Output**: List of segments with speaker labels and timestamps
- **Memory**: ~2GB VRAM
- **Note**: Requires HuggingFace authentication

### 5. Speech-to-Text (`services/stt/`)
- **Purpose**: Transcribe speech with timestamps
- **Implementation**: `STTService`
- **Model**: Whisper Large v3 (INT8 quantized)
- **Processing**: Batch processing (configurable batch size)
- **Output**: Segments with transcribed text
- **Memory**: ~4GB VRAM with INT8 quantization

### 6. Emotion Analysis (`services/emotion/`)
- **Purpose**: Detect emotional tone of speech
- **Implementation**: `EmotionService`
- **Model**: SpeechBrain Wav2Vec2-IEMOCAP
- **Output**: Segments with emotion labels and confidence
- **Memory**: ~2GB VRAM
- **Emotions**: neutral, happy, sad, angry, fearful, disgusted, surprised

### 7. Translation (`services/translation/`)
- **Purpose**: Translate text to target language
- **Implementation**: `TranslationService`
- **Model**: NLLB-200 1.3B
- **Languages**: 200+ language pairs
- **Output**: Segments with translated text
- **Memory**: ~3GB VRAM

### 8. Post-Editing (`services/translation/`)
- **Purpose**: Refine translations for natural spoken language
- **Implementation**: `PostEditService`
- **Model**: Qwen2.5-7B-Instruct (4-bit quantized)
- **Output**: Segments with post-edited text
- **Memory**: ~5GB VRAM with 4-bit quantization

### 9. Text-to-Speech (`services/tts/`)
- **Purpose**: Synthesize speech with voice cloning
- **Implementation**: `TTSService`
- **Model**: XTTS v2
- **Processing**: Sequential (to avoid OOM)
- **Voice Cloning**: Uses reference audio from original speaker
- **Output**: Individual audio files per segment
- **Memory**: ~6GB VRAM
- **Note**: Most memory-intensive step

### 10. Audio Alignment (`services/alignment/`)
- **Purpose**: Time-stretch and mix dubbed audio
- **Implementation**: `AlignmentService`
- **Processing**: 
  - Time-stretch each segment to match original duration
  - Mix all segments together
  - Combine with background music
- **Tools**: Rubberband (preferred) or FFmpeg atempo
- **Output**: Final mixed audio track

### 11. Video Muxing (`services/muxing/`)
- **Purpose**: Combine original video with new audio
- **Implementation**: `MuxingService`
- **Processing**: Mux video stream with dubbed audio
- **Output**: Final dubbed video file
- **Dependencies**: FFmpeg

## Core Components

### Orchestrator (`orchestrator/`)
- **Purpose**: Coordinate all pipeline stages
- **Implementation**: `DubbingOrchestrator`
- **Features**:
  - Sequential execution of stages
  - Retry logic with exponential backoff
  - GPU memory management between stages
  - Intermediate artifact saving
  - Error handling and recovery

### Configuration (`configs/`)
- **Purpose**: Centralized configuration management
- **Implementation**: YAML-based configuration
- **Features**:
  - Model settings
  - Processing parameters
  - System constraints
  - Language settings

### Utilities (`utils/`)
- **Logging**: Structured logging to file and console
- **File Management**: Directory creation, JSON handling
- **GPU Management**: Memory tracking and cleanup

## Memory Management Strategy

The system is designed to fit in 12GB VRAM through several strategies:

1. **Quantization**:
   - Whisper: INT8 (3x reduction)
   - Qwen LLM: 4-bit (4x reduction)

2. **Sequential Processing**:
   - TTS processes one segment at a time
   - Models loaded and unloaded between stages

3. **Batch Processing**:
   - STT batches segments for efficiency
   - Configurable batch sizes

4. **Cache Clearing**:
   - GPU cache cleared after each stage
   - Explicit model cleanup

## Data Flow

```
Video File
    ↓
[Metadata] → JSON artifact
    ↓
[Audio WAV] → Audio file
    ↓
[Vocals + Background] → Two audio files
    ↓
[Segments + Speakers] → JSON with timestamps
    ↓
[Segments + Text] → JSON with transcriptions
    ↓
[Segments + Emotions] → JSON with emotion labels
    ↓
[Segments + Translations] → JSON with translations
    ↓
[Segments + Final Text] → JSON with post-edited text
    ↓
[TTS Audio Files] → Multiple WAV files
    ↓
[Mixed Audio] → Single WAV file
    ↓
[Final Video] → Dubbed video file
```

## Error Handling

1. **Service Level**:
   - Each service handles its own errors
   - Returns meaningful error messages
   - Logs errors with context

2. **Orchestrator Level**:
   - Retry logic for transient failures
   - Saves error state to JSON
   - Graceful degradation where possible

3. **User Level**:
   - Clear error messages
   - Troubleshooting guidance
   - Option to keep temp files for debugging

## Extensibility

The system is designed for easy extension:

1. **Adding New Models**:
   - Update service implementation
   - Add model config to `config.yaml`
   - No changes to orchestrator needed

2. **Adding New Pipeline Stages**:
   - Create new service module
   - Update orchestrator to call service
   - Add to config if needed

3. **Custom Processing**:
   - Override service implementations
   - Inject custom logic via config
   - Use intermediate JSON artifacts

## Performance Considerations

1. **Processing Time**:
   - Depends on video length
   - Typical: 5-10x real-time
   - Bottlenecks: TTS and translation

2. **Memory Usage**:
   - Peak: ~10GB VRAM during TTS
   - Average: ~4GB VRAM
   - Can run on 12GB card

3. **Disk Usage**:
   - Models: ~20GB
   - Temp files: ~2GB per hour of video
   - Cleaned up after processing

## Known Limitations

1. **Real-time Processing**: Not supported (by design)
2. **Very Long Videos**: May need chunking (>2 hours)
3. **Many Speakers**: Performance degrades with 5+ speakers
4. **Background Noise**: May affect quality
5. **Fast Speech**: May lose some temporal accuracy

## Future Improvements

1. **Parallelization**: Run independent stages in parallel
2. **Streaming**: Process video in chunks
3. **Quality Metrics**: Automatic quality assessment
4. **A/B Testing**: Compare different model combinations
5. **Fine-tuning**: Train models on specific voice data
