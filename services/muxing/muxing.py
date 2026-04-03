"""Video muxing service - combines video with dubbed audio."""

import subprocess
from pathlib import Path
from typing import Dict, Any
from utils import get_logger

logger = get_logger(__name__)


class MuxingService:
    """Muxes video with dubbed audio."""
    
    def __init__(
        self,
        video_codec: str = "copy",
        audio_codec: str = "aac",
        audio_bitrate: str = "192k"
    ):
        """
        Initialize muxing service.
        
        Args:
            video_codec: Video codec (use 'copy' to avoid re-encoding)
            audio_codec: Audio codec for output
            audio_bitrate: Audio bitrate
        """
        self.video_codec = video_codec
        self.audio_codec = audio_codec
        self.audio_bitrate = audio_bitrate
    
    def mux_video_audio(
        self,
        video_path: str,
        audio_path: str,
        output_path: str
    ) -> str:
        """
        Mux video with new audio.
        
        Args:
            video_path: Path to original video
            audio_path: Path to dubbed audio
            output_path: Path for output video
            
        Returns:
            Path to output video
        """
        try:
            logger.info(f"Muxing video with dubbed audio")
            
            # Ensure output directory exists
            Path(output_path).parent.mkdir(parents=True, exist_ok=True)
            
            # Build ffmpeg command
            cmd = [
                'ffmpeg',
                '-i', video_path,  # Input video
                '-i', audio_path,  # Input audio
                '-map', '0:v:0',  # Use video from first input
                '-map', '1:a:0',  # Use audio from second input
                '-c:v', self.video_codec,  # Video codec
                '-c:a', self.audio_codec,  # Audio codec
                '-b:a', self.audio_bitrate,  # Audio bitrate
                '-shortest',  # End output at shortest input
                '-y',  # Overwrite output
                output_path
            ]
            
            logger.info(f"Running ffmpeg command: {' '.join(cmd)}")
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=True
            )
            
            logger.info(f"Video muxing completed successfully: {output_path}")
            
            return output_path
            
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to mux video: {e.stderr}")
            raise
        except Exception as e:
            logger.error(f"Error during video muxing: {e}")
            raise
    
    def validate_output(self, video_path: str) -> bool:
        """
        Validate output video.
        
        Args:
            video_path: Path to video file
            
        Returns:
            True if valid, False otherwise
        """
        try:
            # Use ffprobe to check video
            cmd = [
                'ffprobe',
                '-v', 'error',
                '-select_streams', 'v:0',
                '-show_entries', 'stream=codec_type',
                '-of', 'default=noprint_wrappers=1:nokey=1',
                video_path
            ]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=True
            )
            
            has_video = 'video' in result.stdout.lower()
            
            # Check for audio
            cmd = [
                'ffprobe',
                '-v', 'error',
                '-select_streams', 'a:0',
                '-show_entries', 'stream=codec_type',
                '-of', 'default=noprint_wrappers=1:nokey=1',
                video_path
            ]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=True
            )
            
            has_audio = 'audio' in result.stdout.lower()
            
            if has_video and has_audio:
                logger.info("Output video validated successfully")
                return True
            else:
                logger.error(
                    f"Output video validation failed - "
                    f"Video: {has_video}, Audio: {has_audio}"
                )
                return False
            
        except Exception as e:
            logger.error(f"Failed to validate output video: {e}")
            return False
    
    def process(
        self,
        video_metadata: Dict[str, Any],
        alignment_metadata: Dict[str, Any],
        output_path: str
    ) -> Dict[str, Any]:
        """
        Process video muxing.
        
        Args:
            video_metadata: Metadata from video ingestion
            alignment_metadata: Metadata from alignment step
            output_path: Path for output video
            
        Returns:
            Dictionary with muxing results
        """
        video_path = video_metadata['path']
        audio_path = alignment_metadata['mixed_audio_path']
        
        logger.info(f"Starting video muxing")
        logger.info(f"Input video: {video_path}")
        logger.info(f"Input audio: {audio_path}")
        logger.info(f"Output video: {output_path}")
        
        # Mux video and audio
        output_video = self.mux_video_audio(
            video_path=video_path,
            audio_path=audio_path,
            output_path=output_path
        )
        
        # Validate output
        is_valid = self.validate_output(output_video)
        
        if not is_valid:
            logger.warning("Output video validation failed, but file was created")
        
        result = {
            'output_video_path': output_video,
            'is_valid': is_valid,
            'video_codec': self.video_codec,
            'audio_codec': self.audio_codec
        }
        
        logger.info("Video muxing completed")
        
        return result
