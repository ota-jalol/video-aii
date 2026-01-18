"""Speech-to-text service using Whisper."""

import torch
import numpy as np
from pathlib import Path
from typing import Dict, Any, List, Optional
from utils import get_logger, cleanup_model
import torchaudio

logger = get_logger(__name__)


class STTService:
    """Performs speech-to-text using Whisper."""
    
    def __init__(
        self,
        model_name: str = "openai/whisper-large-v3",
        device: str = "cuda",
        quantization: str = "int8"
    ):
        """
        Initialize STT service.
        
        Args:
            model_name: Whisper model name
            device: Device for inference
            quantization: Quantization mode (int8, fp16, none)
        """
        self.model_name = model_name
        self.device = device if torch.cuda.is_available() else "cpu"
        self.quantization = quantization
        self.model = None
        self.processor = None
    
    def load_model(self):
        """Load Whisper model and processor."""
        if self.model is not None:
            return
        
        try:
            logger.info(f"Loading Whisper model: {self.model_name}")
            from transformers import AutoModelForSpeechSeq2Seq, AutoProcessor
            
            # Load processor
            self.processor = AutoProcessor.from_pretrained(self.model_name)
            
            # Configure model loading based on quantization
            if self.quantization == "int8":
                logger.info("Using INT8 quantization")
                self.model = AutoModelForSpeechSeq2Seq.from_pretrained(
                    self.model_name,
                    torch_dtype=torch.float16 if self.device == "cuda" else torch.float32,
                    low_cpu_mem_usage=True,
                    use_safetensors=True
                )
            else:
                self.model = AutoModelForSpeechSeq2Seq.from_pretrained(
                    self.model_name,
                    torch_dtype=torch.float16 if self.device == "cuda" else torch.float32,
                    low_cpu_mem_usage=True
                )
            
            self.model.to(self.device)
            self.model.eval()
            
            logger.info("Whisper model loaded successfully")
            
        except Exception as e:
            logger.error(f"Failed to load Whisper model: {e}")
            raise
    
    def unload_model(self):
        """Unload model from memory."""
        cleanup_model(self.model)
        cleanup_model(self.processor)
        self.model = None
        self.processor = None
    
    def load_audio_segment(
        self,
        audio_path: str,
        start: float,
        end: float,
        target_sr: int = 16000
    ) -> np.ndarray:
        """
        Load audio segment.
        
        Args:
            audio_path: Path to audio file
            start: Start time (seconds)
            end: End time (seconds)
            target_sr: Target sample rate
            
        Returns:
            Audio array
        """
        # Load audio
        waveform, sr = torchaudio.load(audio_path)
        
        # Convert to mono if needed
        if waveform.shape[0] > 1:
            waveform = torch.mean(waveform, dim=0, keepdim=True)
        
        # Calculate frame indices
        start_frame = int(start * sr)
        end_frame = int(end * sr)
        
        # Extract segment
        segment = waveform[:, start_frame:end_frame]
        
        # Resample if needed
        if sr != target_sr:
            resampler = torchaudio.transforms.Resample(sr, target_sr)
            segment = resampler(segment)
        
        # Convert to numpy
        audio_array = segment.squeeze().numpy()
        
        return audio_array
    
    def transcribe_segment(
        self,
        audio_array: np.ndarray,
        language: str = None
    ) -> Dict[str, Any]:
        """
        Transcribe audio segment.
        
        Args:
            audio_array: Audio data
            language: Source language code (optional, auto-detect if None)
            
        Returns:
            Transcription result
        """
        self.load_model()
        
        try:
            # Process audio
            inputs = self.processor(
                audio_array,
                sampling_rate=16000,
                return_tensors="pt"
            )
            
            # Move to device
            inputs = {k: v.to(self.device) for k, v in inputs.items()}
            
            # Generate transcription
            with torch.no_grad():
                if language:
                    # Force specific language
                    forced_decoder_ids = self.processor.get_decoder_prompt_ids(
                        language=language,
                        task="transcribe"
                    )
                    generated_ids = self.model.generate(
                        **inputs,
                        forced_decoder_ids=forced_decoder_ids
                    )
                else:
                    # Auto-detect language
                    generated_ids = self.model.generate(**inputs)
            
            # Decode transcription
            transcription = self.processor.batch_decode(
                generated_ids,
                skip_special_tokens=True
            )[0]
            
            return {
                'text': transcription.strip(),
                'language': language or 'auto'
            }
            
        except Exception as e:
            logger.error(f"Failed to transcribe segment: {e}")
            raise
    
    def transcribe_segments(
        self,
        audio_path: str,
        segments: List[Dict[str, Any]],
        batch_size: int = 8,
        language: str = None
    ) -> List[Dict[str, Any]]:
        """
        Transcribe multiple segments with batching.
        
        Args:
            audio_path: Path to audio file
            segments: List of segments with start/end times
            batch_size: Batch size for processing
            language: Source language code (optional)
            
        Returns:
            List of segments with transcriptions
        """
        self.load_model()
        
        transcribed_segments = []
        
        logger.info(f"Transcribing {len(segments)} segments")
        
        # Process in batches
        for i in range(0, len(segments), batch_size):
            batch = segments[i:i + batch_size]
            
            logger.info(f"Processing batch {i//batch_size + 1}/{(len(segments)-1)//batch_size + 1}")
            
            for segment in batch:
                try:
                    # Load audio segment
                    audio_array = self.load_audio_segment(
                        audio_path,
                        segment['start'],
                        segment['end']
                    )
                    
                    # Transcribe
                    result = self.transcribe_segment(audio_array, language)
                    
                    # Add transcription to segment
                    transcribed_segment = segment.copy()
                    transcribed_segment['text'] = result['text']
                    transcribed_segment['language'] = result['language']
                    
                    transcribed_segments.append(transcribed_segment)
                    
                    logger.debug(
                        f"Segment {segment['start']:.2f}-{segment['end']:.2f}s: "
                        f"{result['text'][:50]}..."
                    )
                    
                except Exception as e:
                    logger.error(f"Failed to transcribe segment {segment}: {e}")
                    # Add segment with empty text
                    error_segment = segment.copy()
                    error_segment['text'] = ""
                    error_segment['error'] = str(e)
                    transcribed_segments.append(error_segment)
        
        logger.info("Transcription completed")
        
        return transcribed_segments
    
    def process(
        self,
        diarization_metadata: Dict[str, Any],
        output_dir: str,
        batch_size: int = 8,
        source_language: str = None
    ) -> Dict[str, Any]:
        """
        Process speech-to-text.
        
        Args:
            diarization_metadata: Metadata from diarization step
            output_dir: Directory for output files
            batch_size: Batch size for processing
            source_language: Source language (None for auto-detect)
            
        Returns:
            Dictionary with STT results
        """
        vocals_path = diarization_metadata['vocals_path']
        segments = diarization_metadata['segments']
        
        try:
            # Transcribe all segments
            transcribed_segments = self.transcribe_segments(
                audio_path=vocals_path,
                segments=segments,
                batch_size=batch_size,
                language=source_language
            )
            
            # Detect most common language
            languages = [s.get('language', 'unknown') for s in transcribed_segments]
            detected_language = max(set(languages), key=languages.count)
            
            result = {
                'segments': transcribed_segments,
                'num_segments': len(transcribed_segments),
                'detected_language': detected_language,
                'vocals_path': vocals_path
            }
            
            logger.info(f"STT completed - Detected language: {detected_language}")
            
            return result
            
        finally:
            # Clean up model after use
            self.unload_model()
