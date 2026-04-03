"""Audio extraction service."""

import subprocess
from pathlib import Path
from typing import Dict, Any
from utils import get_logger

logger = get_logger(__name__)


class AudioExtractionService:
    """Extracts audio from video files."""
    
    def __init__(self, sample_rate: int = 16000):
        """
        Initialize audio extraction service.
        
        Args:
            sample_rate: Target sample rate for audio
        """
        self.sample_rate = sample_rate
    
    def extract_audio(
        self,
        video_path: str,
        output_path: str,
        sample_rate: int = None,
        channels: int = 1
    ) -> str:
        """
        Extract audio from video file using ffmpeg.
        
        Args:
            video_path: Path to input video
            output_path: Path for output audio file
            sample_rate: Sample rate (Hz), uses default if None
            channels: Number of audio channels (1=mono, 2=stereo)
            
        Returns:
            Path to extracted audio file
        """
        if sample_rate is None:
            sample_rate = self.sample_rate
        
        # Ensure output directory exists
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        
        try:
            logger.info(f"Extracting audio from {video_path}")
            
            # Build ffmpeg command
            cmd = [
                'ffmpeg',
                '-i', video_path,
                '-vn',  # No video
                '-acodec', 'pcm_s16le',  # PCM 16-bit little-endian
                '-ar', str(sample_rate),  # Sample rate
                '-ac', str(channels),  # Channels
                '-y',  # Overwrite output file
                output_path
            ]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=True
            )
            
            logger.info(f"Audio extracted successfully to {output_path}")
            return output_path
            
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to extract audio: {e.stderr}")
            raise
        except Exception as e:
            logger.error(f"Error during audio extraction: {e}")
            raise
    
    def get_audio_info(self, audio_path: str) -> Dict[str, Any]:
        """
        Get audio file information.
        
        Args:
            audio_path: Path to audio file
            
        Returns:
            Dictionary with audio information
        """
        try:
            cmd = [
                'ffprobe',
                '-v', 'quiet',
                '-print_format', 'json',
                '-show_streams',
                audio_path
            ]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=True
            )
            
            import json
            data = json.loads(result.stdout)
            
            audio_info = {
                'path': audio_path,
                'codec': None,
                'sample_rate': None,
                'channels': None,
                'duration': None
            }
            
            if 'streams' in data and len(data['streams']) > 0:
                stream = data['streams'][0]
                audio_info['codec'] = stream.get('codec_name')
                audio_info['sample_rate'] = int(stream.get('sample_rate', 0))
                audio_info['channels'] = stream.get('channels')
                audio_info['duration'] = float(stream.get('duration', 0))
            
            return audio_info
            
        except Exception as e:
            logger.error(f"Failed to get audio info: {e}")
            raise
    
    def process(
        self,
        video_metadata: Dict[str, Any],
        output_dir: str
    ) -> Dict[str, Any]:
        """
        Process audio extraction.
        
        Args:
            video_metadata: Video metadata from ingestion
            output_dir: Directory for output files
            
        Returns:
            Dictionary with audio extraction results
        """
        video_path = video_metadata['path']
        video_name = Path(video_path).stem
        
        # Output path for extracted audio
        audio_path = str(Path(output_dir) / f"{video_name}_audio.wav")
        
        # Extract audio
        extracted_path = self.extract_audio(
            video_path=video_path,
            output_path=audio_path,
            sample_rate=self.sample_rate,
            channels=1  # Mono for processing
        )
        
        # Get audio info
        audio_info = self.get_audio_info(extracted_path)
        
        result = {
            'audio_path': extracted_path,
            'sample_rate': audio_info['sample_rate'],
            'channels': audio_info['channels'],
            'duration': audio_info['duration'],
            'codec': audio_info['codec']
        }
        
        logger.info(
            f"Audio extraction completed - Duration: {result['duration']:.2f}s, "
            f"Sample rate: {result['sample_rate']}Hz"
        )
        
        return result
