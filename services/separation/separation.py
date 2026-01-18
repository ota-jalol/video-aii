"""Music and speech separation service."""

import torch
from pathlib import Path
from typing import Dict, Any, Optional
from utils import get_logger, cleanup_model

logger = get_logger(__name__)


class SeparationService:
    """Separates music and speech using Demucs."""
    
    def __init__(self, model_name: str = "htdemucs", device: str = "cuda"):
        """
        Initialize separation service.
        
        Args:
            model_name: Demucs model name
            device: Device for inference
        """
        self.model_name = model_name
        self.device = device if torch.cuda.is_available() else "cpu"
        self.model = None
    
    def load_model(self):
        """Load Demucs model."""
        if self.model is not None:
            return
        
        try:
            logger.info(f"Loading Demucs model: {self.model_name}")
            from demucs.pretrained import get_model
            from demucs.apply import apply_model
            
            self.model = get_model(self.model_name)
            self.model.to(self.device)
            self.model.eval()
            
            logger.info("Demucs model loaded successfully")
            
        except Exception as e:
            logger.error(f"Failed to load Demucs model: {e}")
            raise
    
    def unload_model(self):
        """Unload model from memory."""
        cleanup_model(self.model)
        self.model = None
    
    def separate_audio(
        self,
        audio_path: str,
        output_dir: str
    ) -> Dict[str, str]:
        """
        Separate audio into vocals and background music.
        
        Args:
            audio_path: Path to input audio
            output_dir: Directory for output files
            
        Returns:
            Dictionary with paths to separated audio files
        """
        try:
            import torchaudio
            from demucs.apply import apply_model
            
            self.load_model()
            
            logger.info(f"Separating audio: {audio_path}")
            
            # Load audio
            wav, sr = torchaudio.load(audio_path)
            
            # Ensure stereo for Demucs (it expects stereo input)
            if wav.shape[0] == 1:
                wav = wav.repeat(2, 1)
            
            # Move to device
            wav = wav.to(self.device)
            
            # Apply separation
            with torch.no_grad():
                sources = apply_model(
                    self.model,
                    wav[None],  # Add batch dimension
                    device=self.device,
                    split=True,
                    overlap=0.25
                )[0]
            
            # Extract vocals and accompaniment
            # Demucs outputs: [drums, bass, other, vocals]
            vocals = sources[3]  # vocals
            
            # Combine other sources as background
            background = sources[0] + sources[1] + sources[2]  # drums + bass + other
            
            # Save separated audio
            output_path = Path(output_dir)
            audio_name = Path(audio_path).stem
            
            vocals_path = str(output_path / f"{audio_name}_vocals.wav")
            background_path = str(output_path / f"{audio_name}_background.wav")
            
            # Convert to mono for processing
            vocals_mono = vocals.mean(dim=0, keepdim=True).cpu()
            background_mono = background.mean(dim=0, keepdim=True).cpu()
            
            # Save files
            torchaudio.save(vocals_path, vocals_mono, sr)
            torchaudio.save(background_path, background_mono, sr)
            
            logger.info("Audio separation completed successfully")
            
            return {
                'vocals_path': vocals_path,
                'background_path': background_path,
                'sample_rate': sr
            }
            
        except Exception as e:
            logger.error(f"Failed to separate audio: {e}")
            raise
    
    def process(
        self,
        audio_metadata: Dict[str, Any],
        output_dir: str
    ) -> Dict[str, Any]:
        """
        Process audio separation.
        
        Args:
            audio_metadata: Audio metadata from extraction
            output_dir: Directory for output files
            
        Returns:
            Dictionary with separation results
        """
        audio_path = audio_metadata['audio_path']
        
        try:
            result = self.separate_audio(audio_path, output_dir)
            
            # Add original metadata
            result.update({
                'original_audio_path': audio_path,
                'duration': audio_metadata.get('duration')
            })
            
            return result
            
        finally:
            # Clean up model after use
            self.unload_model()
