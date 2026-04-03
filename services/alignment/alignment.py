"""Audio alignment and mixing service."""

import torch
import torchaudio
import subprocess
from pathlib import Path
from typing import Dict, Any, List
from utils import get_logger
import numpy as np

logger = get_logger(__name__)


class AlignmentService:
    """Aligns and mixes synthesized audio with background."""
    
    def __init__(self, stretch_algorithm: str = "rubberband"):
        """
        Initialize alignment service.
        
        Args:
            stretch_algorithm: Time-stretching algorithm (rubberband or phase_vocoder)
        """
        self.stretch_algorithm = stretch_algorithm
    
    def get_audio_duration(self, audio_path: str) -> float:
        """
        Get audio file duration.
        
        Args:
            audio_path: Path to audio file
            
        Returns:
            Duration in seconds
        """
        try:
            waveform, sr = torchaudio.load(audio_path)
            duration = waveform.shape[1] / sr
            return duration
        except Exception as e:
            logger.error(f"Failed to get audio duration: {e}")
            return 0.0
    
    def time_stretch_audio(
        self,
        audio_path: str,
        output_path: str,
        stretch_ratio: float
    ) -> str:
        """
        Time-stretch audio to match target duration.
        
        Args:
            audio_path: Path to input audio
            output_path: Path for output audio
            stretch_ratio: Stretch ratio (target_duration / source_duration)
            
        Returns:
            Path to stretched audio
        """
        if abs(stretch_ratio - 1.0) < 0.01:
            # No stretching needed
            import shutil
            shutil.copy(audio_path, output_path)
            return output_path
        
        try:
            if self.stretch_algorithm == "rubberband":
                # Use rubberband CLI for high-quality time stretching
                cmd = [
                    'rubberband',
                    '-t', str(stretch_ratio),
                    audio_path,
                    output_path
                ]
                
                try:
                    subprocess.run(cmd, capture_output=True, check=True)
                    return output_path
                except (subprocess.CalledProcessError, FileNotFoundError):
                    logger.warning("Rubberband not available, falling back to ffmpeg")
                    # Fall through to ffmpeg method
            
            # Use ffmpeg atempo filter (works for ratios between 0.5 and 2.0)
            # For larger ratios, chain multiple atempo filters
            tempo_filters = []
            remaining_ratio = stretch_ratio
            
            while remaining_ratio > 2.0:
                tempo_filters.append("atempo=2.0")
                remaining_ratio /= 2.0
            
            while remaining_ratio < 0.5:
                tempo_filters.append("atempo=0.5")
                remaining_ratio /= 0.5
            
            if remaining_ratio != 1.0:
                tempo_filters.append(f"atempo={remaining_ratio}")
            
            if not tempo_filters:
                # No stretching needed
                import shutil
                shutil.copy(audio_path, output_path)
                return output_path
            
            filter_complex = ",".join(tempo_filters)
            
            cmd = [
                'ffmpeg',
                '-i', audio_path,
                '-filter:a', filter_complex,
                '-y',
                output_path
            ]
            
            subprocess.run(cmd, capture_output=True, check=True)
            return output_path
            
        except Exception as e:
            logger.error(f"Failed to time-stretch audio: {e}")
            # Copy original on error
            import shutil
            shutil.copy(audio_path, output_path)
            return output_path
    
    def align_segment_audio(
        self,
        segment: Dict[str, Any],
        output_path: str,
        max_stretch: float = 1.5
    ) -> str:
        """
        Align segment audio to match original timing.
        
        Args:
            segment: Segment with timing info
            output_path: Path for aligned audio
            max_stretch: Maximum allowed stretch ratio
            
        Returns:
            Path to aligned audio
        """
        tts_audio_path = segment.get('tts_audio_path')
        
        if not tts_audio_path or not Path(tts_audio_path).exists():
            logger.warning(f"TTS audio not found for segment")
            # Create silence
            target_duration = segment['end'] - segment['start']
            silence = torch.zeros(1, int(22050 * target_duration))
            torchaudio.save(output_path, silence, 22050)
            return output_path
        
        # Get durations
        original_duration = segment['end'] - segment['start']
        synthesized_duration = self.get_audio_duration(tts_audio_path)
        
        if synthesized_duration == 0:
            logger.warning("Synthesized audio has zero duration")
            # Create silence
            silence = torch.zeros(1, int(22050 * original_duration))
            torchaudio.save(output_path, silence, 22050)
            return output_path
        
        # Calculate stretch ratio
        stretch_ratio = original_duration / synthesized_duration
        
        # Limit stretch ratio
        if stretch_ratio > max_stretch:
            logger.warning(
                f"Stretch ratio {stretch_ratio:.2f} exceeds maximum {max_stretch}, "
                f"limiting to {max_stretch}"
            )
            stretch_ratio = max_stretch
        elif stretch_ratio < (1.0 / max_stretch):
            logger.warning(
                f"Stretch ratio {stretch_ratio:.2f} below minimum, "
                f"limiting to {1.0/max_stretch:.2f}"
            )
            stretch_ratio = 1.0 / max_stretch
        
        # Time-stretch audio
        stretched_path = self.time_stretch_audio(
            tts_audio_path,
            output_path,
            stretch_ratio
        )
        
        return stretched_path
    
    def mix_audio_segments(
        self,
        segments: List[Dict[str, Any]],
        background_path: str,
        output_path: str,
        vocals_volume: float = 1.0,
        background_volume: float = 0.3
    ) -> str:
        """
        Mix aligned segments with background audio.
        
        Args:
            segments: List of segments with aligned audio
            background_path: Path to background audio
            output_path: Path for mixed output
            vocals_volume: Volume for vocals (0-1)
            background_volume: Volume for background (0-1)
            
        Returns:
            Path to mixed audio
        """
        try:
            logger.info("Mixing audio segments with background")
            
            # Load background audio
            background, bg_sr = torchaudio.load(background_path)
            
            # Convert to mono if needed
            if background.shape[0] > 1:
                background = torch.mean(background, dim=0, keepdim=True)
            
            # Initialize output audio (same length as background)
            output_audio = torch.zeros_like(background)
            
            # Mix each segment at its timestamp
            for i, segment in enumerate(segments):
                aligned_audio_path = segment.get('aligned_audio_path')
                
                if not aligned_audio_path or not Path(aligned_audio_path).exists():
                    continue
                
                # Load aligned audio
                seg_audio, seg_sr = torchaudio.load(aligned_audio_path)
                
                # Convert to mono
                if seg_audio.shape[0] > 1:
                    seg_audio = torch.mean(seg_audio, dim=0, keepdim=True)
                
                # Resample if needed
                if seg_sr != bg_sr:
                    resampler = torchaudio.transforms.Resample(seg_sr, bg_sr)
                    seg_audio = resampler(seg_audio)
                
                # Calculate position in output
                start_frame = int(segment['start'] * bg_sr)
                end_frame = start_frame + seg_audio.shape[1]
                
                # Ensure we don't exceed output length
                if end_frame > output_audio.shape[1]:
                    seg_audio = seg_audio[:, :output_audio.shape[1] - start_frame]
                    end_frame = output_audio.shape[1]
                
                # Add segment to output
                output_audio[0, start_frame:end_frame] += seg_audio[0, :end_frame - start_frame]
            
            # Mix with background
            mixed_audio = (output_audio * vocals_volume +
                          background * background_volume)
            
            # Normalize to prevent clipping
            max_val = torch.max(torch.abs(mixed_audio))
            if max_val > 1.0:
                mixed_audio = mixed_audio / max_val
            
            # Save mixed audio
            torchaudio.save(output_path, mixed_audio, bg_sr)
            
            logger.info(f"Audio mixing completed: {output_path}")
            
            return output_path
            
        except Exception as e:
            logger.error(f"Failed to mix audio: {e}")
            raise
    
    def process(
        self,
        tts_metadata: Dict[str, Any],
        background_path: str,
        output_dir: str
    ) -> Dict[str, Any]:
        """
        Process audio alignment and mixing.
        
        Args:
            tts_metadata: Metadata from TTS step
            background_path: Path to background audio
            output_dir: Directory for output files
            
        Returns:
            Dictionary with alignment results
        """
        segments = tts_metadata['segments']
        
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"Aligning {len(segments)} audio segments")
        
        # Align each segment
        aligned_segments = []
        for i, segment in enumerate(segments):
            aligned_audio_path = str(output_path / f"aligned_segment_{i:04d}.wav")
            
            try:
                aligned_path = self.align_segment_audio(
                    segment,
                    aligned_audio_path
                )
                
                aligned_segment = segment.copy()
                aligned_segment['aligned_audio_path'] = aligned_path
                aligned_segments.append(aligned_segment)
                
            except Exception as e:
                logger.error(f"Failed to align segment {i}: {e}")
                error_segment = segment.copy()
                error_segment['aligned_audio_path'] = None
                error_segment['error'] = str(e)
                aligned_segments.append(error_segment)
        
        # Mix all segments with background
        mixed_audio_path = str(output_path / "mixed_audio.wav")
        
        try:
            final_audio = self.mix_audio_segments(
                aligned_segments,
                background_path,
                mixed_audio_path
            )
        except Exception as e:
            logger.error(f"Failed to mix audio: {e}")
            raise
        
        result = {
            'segments': aligned_segments,
            'mixed_audio_path': final_audio,
            'background_path': background_path
        }
        
        logger.info("Audio alignment and mixing completed")
        
        return result
