"""Text-to-speech service with voice cloning using XTTS."""

import torch
import torchaudio
from pathlib import Path
from typing import Dict, Any, List
from utils import get_logger, cleanup_model

logger = get_logger(__name__)


class TTSService:
    """Performs text-to-speech with voice cloning using XTTS."""
    
    def __init__(
        self,
        model_name: str = "tts_models/multilingual/multi-dataset/xtts_v2",
        device: str = "cuda"
    ):
        """
        Initialize TTS service.
        
        Args:
            model_name: XTTS model name
            device: Device for inference
        """
        self.model_name = model_name
        self.device = device if torch.cuda.is_available() else "cpu"
        self.tts = None
    
    def load_model(self):
        """Load XTTS model."""
        if self.tts is not None:
            return
        
        try:
            logger.info(f"Loading XTTS model: {self.model_name}")
            from TTS.api import TTS
            
            self.tts = TTS(self.model_name).to(self.device)
            
            logger.info("XTTS model loaded successfully")
            
        except Exception as e:
            logger.error(f"Failed to load XTTS model: {e}")
            raise
    
    def unload_model(self):
        """Unload model from memory."""
        cleanup_model(self.tts)
        self.tts = None
    
    def extract_voice_sample(
        self,
        audio_path: str,
        start: float,
        end: float,
        output_path: str,
        min_duration: float = 6.0
    ) -> str:
        """
        Extract voice sample for cloning.
        
        Args:
            audio_path: Path to audio file
            start: Start time (seconds)
            end: End time (seconds)
            output_path: Path for voice sample
            min_duration: Minimum duration for voice sample
            
        Returns:
            Path to voice sample
        """
        # Ensure minimum duration
        duration = end - start
        if duration < min_duration:
            # Extend the sample
            end = start + min_duration
        
        # Limit maximum duration (10 seconds is good for XTTS)
        if duration > 10.0:
            end = start + 10.0
        
        try:
            # Extract audio segment using ffmpeg
            import subprocess
            
            cmd = [
                'ffmpeg',
                '-i', audio_path,
                '-ss', str(start),
                '-t', str(end - start),
                '-ar', '22050',  # XTTS works well with 22050Hz
                '-ac', '1',  # Mono
                '-y',
                output_path
            ]
            
            subprocess.run(cmd, capture_output=True, check=True)
            
            return output_path
            
        except Exception as e:
            logger.error(f"Failed to extract voice sample: {e}")
            raise
    
    def synthesize_speech(
        self,
        text: str,
        speaker_wav: str,
        language: str,
        output_path: str,
        emotion: str = None
    ) -> str:
        """
        Synthesize speech with voice cloning.
        
        Args:
            text: Text to synthesize
            speaker_wav: Path to speaker reference audio
            language: Target language code
            output_path: Path for output audio
            emotion: Emotion label (optional, not directly supported by XTTS)
            
        Returns:
            Path to synthesized audio
        """
        if not text.strip():
            # Create silent audio for empty text
            silence = torch.zeros(1, 22050)  # 1 second of silence
            torchaudio.save(output_path, silence, 22050)
            return output_path
        
        self.load_model()
        
        try:
            logger.debug(f"Synthesizing: {text[:50]}...")
            
            # Synthesize
            self.tts.tts_to_file(
                text=text,
                speaker_wav=speaker_wav,
                language=language,
                file_path=output_path
            )
            
            return output_path
            
        except Exception as e:
            logger.error(f"Failed to synthesize speech: {e}")
            # Create silent audio on error
            silence = torch.zeros(1, 22050)
            torchaudio.save(output_path, silence, 22050)
            return output_path
    
    def process_segments(
        self,
        segments: List[Dict[str, Any]],
        vocals_path: str,
        output_dir: str,
        target_language: str
    ) -> List[Dict[str, Any]]:
        """
        Process TTS for all segments sequentially.
        
        Args:
            segments: List of segments with text
            vocals_path: Path to original vocals
            output_dir: Directory for output files
            target_language: Target language code
            
        Returns:
            List of segments with synthesized audio paths
        """
        self.load_model()
        
        logger.info(f"Synthesizing speech for {len(segments)} segments")
        
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        # Group segments by speaker for voice cloning
        speakers = {}
        for segment in segments:
            speaker = segment.get('speaker', 'SPEAKER_00')
            if speaker not in speakers:
                speakers[speaker] = []
            speakers[speaker].append(segment)
        
        logger.info(f"Found {len(speakers)} unique speakers")
        
        # Extract voice samples for each speaker
        voice_samples = {}
        for speaker, speaker_segments in speakers.items():
            # Use first segment as voice sample (should be long enough)
            first_segment = speaker_segments[0]
            
            sample_path = str(output_path / f"voice_sample_{speaker}.wav")
            
            try:
                voice_sample = self.extract_voice_sample(
                    vocals_path,
                    first_segment['start'],
                    first_segment['end'],
                    sample_path
                )
                voice_samples[speaker] = voice_sample
                logger.info(f"Extracted voice sample for {speaker}")
            except Exception as e:
                logger.error(f"Failed to extract voice sample for {speaker}: {e}")
                voice_samples[speaker] = None
        
        # Synthesize speech for each segment (sequential to avoid OOM)
        synthesized_segments = []
        
        for i, segment in enumerate(segments):
            text = segment.get('final_text', '')
            speaker = segment.get('speaker', 'SPEAKER_00')
            emotion = segment.get('emotion', 'neutral')
            
            # Output path for synthesized audio
            segment_audio_path = str(output_path / f"tts_segment_{i:04d}.wav")
            
            try:
                # Get voice sample for this speaker
                speaker_wav = voice_samples.get(speaker)
                
                if speaker_wav is None or not Path(speaker_wav).exists():
                    # Use first available voice sample
                    speaker_wav = next(iter(voice_samples.values()), None)
                
                if speaker_wav is None:
                    logger.error("No voice samples available")
                    raise ValueError("No voice samples available")
                
                # Synthesize
                output_audio = self.synthesize_speech(
                    text=text,
                    speaker_wav=speaker_wav,
                    language=target_language,
                    output_path=segment_audio_path,
                    emotion=emotion
                )
                
                # Add to segment
                synthesized_segment = segment.copy()
                synthesized_segment['tts_audio_path'] = output_audio
                synthesized_segments.append(synthesized_segment)
                
                if (i + 1) % 10 == 0:
                    logger.info(f"Synthesized {i + 1}/{len(segments)} segments")
                
            except Exception as e:
                logger.error(f"Failed to synthesize segment {i}: {e}")
                # Add segment with error
                error_segment = segment.copy()
                error_segment['tts_audio_path'] = None
                error_segment['error'] = str(e)
                synthesized_segments.append(error_segment)
        
        logger.info("TTS synthesis completed")
        
        return synthesized_segments
    
    def process(
        self,
        post_edit_metadata: Dict[str, Any],
        vocals_path: str,
        output_dir: str
    ) -> Dict[str, Any]:
        """
        Process TTS.
        
        Args:
            post_edit_metadata: Metadata from post-editing step
            vocals_path: Path to original vocals for voice cloning
            output_dir: Directory for output files
            
        Returns:
            Dictionary with TTS results
        """
        segments = post_edit_metadata['segments']
        target_language = post_edit_metadata['target_language']
        
        try:
            # Synthesize speech for all segments
            synthesized_segments = self.process_segments(
                segments=segments,
                vocals_path=vocals_path,
                output_dir=output_dir,
                target_language=target_language
            )
            
            result = {
                'segments': synthesized_segments,
                'num_segments': len(synthesized_segments),
                'target_language': target_language
            }
            
            return result
            
        finally:
            # Clean up model after use
            self.unload_model()
