"""Speaker diarization service."""

import torch
from pathlib import Path
from typing import Dict, Any, List, Optional
from utils import get_logger, cleanup_model

logger = get_logger(__name__)


class DiarizationService:
    """Performs speaker diarization using pyannote.audio."""
    
    def __init__(
        self,
        model_name: str = "pyannote/speaker-diarization-3.1",
        device: str = "cuda",
        auth_token: Optional[str] = None
    ):
        """
        Initialize diarization service.
        
        Args:
            model_name: Pyannote model name
            device: Device for inference
            auth_token: HuggingFace auth token (optional)
        """
        self.model_name = model_name
        self.device = device if torch.cuda.is_available() else "cpu"
        self.auth_token = auth_token
        self.pipeline = None
    
    def load_model(self):
        """Load pyannote diarization pipeline."""
        if self.pipeline is not None:
            return
        
        try:
            logger.info(f"Loading pyannote model: {self.model_name}")
            from pyannote.audio import Pipeline
            
            self.pipeline = Pipeline.from_pretrained(
                self.model_name,
                use_auth_token=self.auth_token
            )
            
            self.pipeline.to(torch.device(self.device))
            
            logger.info("Pyannote pipeline loaded successfully")
            
        except Exception as e:
            logger.error(f"Failed to load pyannote pipeline: {e}")
            logger.info(
                "Note: pyannote models may require authentication. "
                "Visit https://huggingface.co/pyannote/speaker-diarization-3.1"
            )
            raise
    
    def unload_model(self):
        """Unload pipeline from memory."""
        cleanup_model(self.pipeline)
        self.pipeline = None
    
    def diarize_audio(self, audio_path: str) -> List[Dict[str, Any]]:
        """
        Perform speaker diarization.
        
        Args:
            audio_path: Path to audio file
            
        Returns:
            List of speaker segments with timestamps
        """
        try:
            self.load_model()
            
            logger.info(f"Performing speaker diarization on {audio_path}")
            
            # Run diarization
            diarization = self.pipeline(audio_path)
            
            # Convert to list of segments
            segments = []
            for turn, _, speaker in diarization.itertracks(yield_label=True):
                segment = {
                    'speaker': speaker,
                    'start': turn.start,
                    'end': turn.end,
                    'duration': turn.end - turn.start
                }
                segments.append(segment)
            
            logger.info(f"Diarization completed - Found {len(segments)} segments")
            
            # Log speaker statistics
            speakers = set(seg['speaker'] for seg in segments)
            logger.info(f"Number of unique speakers: {len(speakers)}")
            
            for speaker in sorted(speakers):
                speaker_segments = [s for s in segments if s['speaker'] == speaker]
                total_duration = sum(s['duration'] for s in speaker_segments)
                logger.info(
                    f"Speaker {speaker}: {len(speaker_segments)} segments, "
                    f"total {total_duration:.2f}s"
                )
            
            return segments
            
        except Exception as e:
            logger.error(f"Failed to perform diarization: {e}")
            raise
    
    def merge_segments(
        self,
        segments: List[Dict[str, Any]],
        min_gap: float = 0.5
    ) -> List[Dict[str, Any]]:
        """
        Merge consecutive segments from same speaker with small gaps.
        
        Args:
            segments: List of diarization segments
            min_gap: Minimum gap (seconds) to keep segments separate
            
        Returns:
            Merged segments
        """
        if not segments:
            return []
        
        # Sort by start time
        sorted_segments = sorted(segments, key=lambda x: x['start'])
        
        merged = []
        current = sorted_segments[0].copy()
        
        for segment in sorted_segments[1:]:
            # Check if same speaker and close in time
            if (segment['speaker'] == current['speaker'] and
                segment['start'] - current['end'] <= min_gap):
                # Merge segments
                current['end'] = segment['end']
                current['duration'] = current['end'] - current['start']
            else:
                # Save current and start new
                merged.append(current)
                current = segment.copy()
        
        # Add last segment
        merged.append(current)
        
        logger.info(
            f"Merged {len(segments)} segments into {len(merged)} segments "
            f"(min_gap={min_gap}s)"
        )
        
        return merged
    
    def process(
        self,
        separation_metadata: Dict[str, Any],
        output_dir: str
    ) -> Dict[str, Any]:
        """
        Process speaker diarization.
        
        Args:
            separation_metadata: Metadata from separation step
            output_dir: Directory for output files
            
        Returns:
            Dictionary with diarization results
        """
        vocals_path = separation_metadata['vocals_path']
        
        try:
            # Perform diarization
            segments = self.diarize_audio(vocals_path)
            
            # Merge close segments
            merged_segments = self.merge_segments(segments, min_gap=0.5)
            
            result = {
                'segments': merged_segments,
                'num_segments': len(merged_segments),
                'num_speakers': len(set(s['speaker'] for s in merged_segments)),
                'vocals_path': vocals_path
            }
            
            return result
            
        finally:
            # Clean up model after use
            self.unload_model()
