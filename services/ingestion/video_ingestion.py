"""Video ingestion service."""

import os
from pathlib import Path
from typing import Dict, Any
import subprocess
from utils import get_logger

logger = get_logger(__name__)


class VideoIngestionService:
    """Handles video file validation and ingestion."""
    
    def __init__(self):
        """Initialize video ingestion service."""
        self.supported_formats = ['.mp4', '.avi', '.mkv', '.mov', '.flv', '.wmv', '.webm']
    
    def validate_video(self, video_path: str) -> bool:
        """
        Validate video file exists and is readable.
        
        Args:
            video_path: Path to video file
            
        Returns:
            True if valid, False otherwise
        """
        path = Path(video_path)
        
        if not path.exists():
            logger.error(f"Video file not found: {video_path}")
            return False
        
        if not path.is_file():
            logger.error(f"Path is not a file: {video_path}")
            return False
        
        if path.suffix.lower() not in self.supported_formats:
            logger.warning(
                f"Video format {path.suffix} may not be supported. "
                f"Supported formats: {self.supported_formats}"
            )
        
        return True
    
    def get_video_metadata(self, video_path: str) -> Dict[str, Any]:
        """
        Extract video metadata using ffprobe.
        
        Args:
            video_path: Path to video file
            
        Returns:
            Dictionary containing video metadata
        """
        try:
            # Use ffprobe to get video information
            cmd = [
                'ffprobe',
                '-v', 'quiet',
                '-print_format', 'json',
                '-show_format',
                '-show_streams',
                video_path
            ]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=True
            )
            
            import json
            metadata = json.loads(result.stdout)
            
            # Extract relevant information
            video_info = {
                'path': video_path,
                'filename': Path(video_path).name,
                'size_bytes': os.path.getsize(video_path),
                'size_mb': os.path.getsize(video_path) / (1024 * 1024),
                'format': None,
                'duration': None,
                'video_codec': None,
                'audio_codec': None,
                'video_width': None,
                'video_height': None,
                'video_fps': None,
                'audio_sample_rate': None,
                'audio_channels': None
            }
            
            # Extract format info
            if 'format' in metadata:
                fmt = metadata['format']
                video_info['format'] = fmt.get('format_name')
                video_info['duration'] = float(fmt.get('duration', 0))
            
            # Extract stream info
            if 'streams' in metadata:
                for stream in metadata['streams']:
                    if stream['codec_type'] == 'video':
                        video_info['video_codec'] = stream.get('codec_name')
                        video_info['video_width'] = stream.get('width')
                        video_info['video_height'] = stream.get('height')
                        
                        # Calculate FPS
                        if 'r_frame_rate' in stream:
                            num, den = stream['r_frame_rate'].split('/')
                            video_info['video_fps'] = int(num) / int(den)
                    
                    elif stream['codec_type'] == 'audio':
                        video_info['audio_codec'] = stream.get('codec_name')
                        video_info['audio_sample_rate'] = int(stream.get('sample_rate', 0))
                        video_info['audio_channels'] = stream.get('channels')
            
            logger.info(
                f"Video metadata extracted - Duration: {video_info['duration']:.2f}s, "
                f"Resolution: {video_info['video_width']}x{video_info['video_height']}, "
                f"FPS: {video_info['video_fps']:.2f}"
            )
            
            return video_info
            
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to extract video metadata: {e}")
            raise
        except Exception as e:
            logger.error(f"Error processing video metadata: {e}")
            raise
    
    def process(self, video_path: str) -> Dict[str, Any]:
        """
        Process video ingestion.
        
        Args:
            video_path: Path to video file
            
        Returns:
            Video metadata dictionary
        """
        logger.info(f"Ingesting video: {video_path}")
        
        if not self.validate_video(video_path):
            raise ValueError(f"Invalid video file: {video_path}")
        
        metadata = self.get_video_metadata(video_path)
        
        logger.info("Video ingestion completed successfully")
        return metadata
