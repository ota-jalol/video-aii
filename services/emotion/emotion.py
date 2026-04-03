"""Emotion recognition service using SpeechBrain."""

import torch
import torchaudio
from pathlib import Path
from typing import Dict, Any, List
from utils import get_logger, cleanup_model

logger = get_logger(__name__)


class EmotionService:
    """Performs emotion recognition using SpeechBrain."""
    
    def __init__(
        self,
        model_name: str = "speechbrain/emotion-recognition-wav2vec2-IEMOCAP",
        device: str = "cuda"
    ):
        """
        Initialize emotion service.
        
        Args:
            model_name: SpeechBrain model name
            device: Device for inference
        """
        self.model_name = model_name
        self.device = device if torch.cuda.is_available() else "cpu"
        self.classifier = None
    
    def load_model(self):
        """Load SpeechBrain emotion classifier."""
        if self.classifier is not None:
            return
        
        try:
            logger.info(f"Loading emotion recognition model: {self.model_name}")
            from speechbrain.pretrained import EncoderClassifier
            
            self.classifier = EncoderClassifier.from_hparams(
                source=self.model_name,
                run_opts={"device": self.device}
            )
            
            logger.info("Emotion recognition model loaded successfully")
            
        except Exception as e:
            logger.error(f"Failed to load emotion model: {e}")
            raise
    
    def unload_model(self):
        """Unload model from memory."""
        cleanup_model(self.classifier)
        self.classifier = None
    
    def load_audio_segment(
        self,
        audio_path: str,
        start: float,
        end: float,
        target_sr: int = 16000
    ) -> torch.Tensor:
        """
        Load audio segment.
        
        Args:
            audio_path: Path to audio file
            start: Start time (seconds)
            end: End time (seconds)
            target_sr: Target sample rate
            
        Returns:
            Audio tensor
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
        
        return segment.squeeze()
    
    def analyze_emotion(self, audio_tensor: torch.Tensor) -> Dict[str, Any]:
        """
        Analyze emotion from audio.
        
        Args:
            audio_tensor: Audio tensor
            
        Returns:
            Emotion analysis result
        """
        self.load_model()
        
        try:
            # Classify emotion
            with torch.no_grad():
                out_prob, score, index, text_lab = self.classifier.classify_batch(
                    audio_tensor.unsqueeze(0)
                )
            
            # Get emotion label and confidence
            emotion = text_lab[0]
            confidence = score[0].item()
            
            # Get all emotion probabilities
            probabilities = {
                label: prob.item()
                for label, prob in zip(
                    self.classifier.hparams.label_encoder.decode_ndim,
                    out_prob[0]
                )
            }
            
            return {
                'emotion': emotion,
                'confidence': confidence,
                'probabilities': probabilities
            }
            
        except Exception as e:
            logger.error(f"Failed to analyze emotion: {e}")
            # Return neutral emotion on error
            return {
                'emotion': 'neutral',
                'confidence': 0.0,
                'probabilities': {},
                'error': str(e)
            }
    
    def analyze_segments(
        self,
        audio_path: str,
        segments: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Analyze emotion for multiple segments.
        
        Args:
            audio_path: Path to audio file
            segments: List of segments with start/end times
            
        Returns:
            List of segments with emotion analysis
        """
        self.load_model()
        
        logger.info(f"Analyzing emotion for {len(segments)} segments")
        
        analyzed_segments = []
        
        for i, segment in enumerate(segments):
            try:
                # Load audio segment
                audio_tensor = self.load_audio_segment(
                    audio_path,
                    segment['start'],
                    segment['end']
                )
                
                # Skip very short segments
                if audio_tensor.shape[0] < 1600:  # Less than 0.1s at 16kHz
                    logger.debug(f"Skipping very short segment {i}")
                    analyzed_segment = segment.copy()
                    analyzed_segment['emotion'] = 'neutral'
                    analyzed_segment['emotion_confidence'] = 0.0
                    analyzed_segments.append(analyzed_segment)
                    continue
                
                # Analyze emotion
                emotion_result = self.analyze_emotion(audio_tensor)
                
                # Add emotion to segment
                analyzed_segment = segment.copy()
                analyzed_segment['emotion'] = emotion_result['emotion']
                analyzed_segment['emotion_confidence'] = emotion_result['confidence']
                analyzed_segment['emotion_probabilities'] = emotion_result.get('probabilities', {})
                
                analyzed_segments.append(analyzed_segment)
                
                if (i + 1) % 10 == 0:
                    logger.info(f"Processed {i + 1}/{len(segments)} segments")
                
            except Exception as e:
                logger.error(f"Failed to analyze segment {i}: {e}")
                # Add segment with neutral emotion
                error_segment = segment.copy()
                error_segment['emotion'] = 'neutral'
                error_segment['emotion_confidence'] = 0.0
                error_segment['error'] = str(e)
                analyzed_segments.append(error_segment)
        
        logger.info("Emotion analysis completed")
        
        # Log emotion distribution
        emotions = [s.get('emotion', 'unknown') for s in analyzed_segments]
        emotion_counts = {}
        for emotion in emotions:
            emotion_counts[emotion] = emotion_counts.get(emotion, 0) + 1
        
        logger.info(f"Emotion distribution: {emotion_counts}")
        
        return analyzed_segments
    
    def process(
        self,
        stt_metadata: Dict[str, Any],
        output_dir: str
    ) -> Dict[str, Any]:
        """
        Process emotion analysis.
        
        Args:
            stt_metadata: Metadata from STT step
            output_dir: Directory for output files
            
        Returns:
            Dictionary with emotion analysis results
        """
        vocals_path = stt_metadata['vocals_path']
        segments = stt_metadata['segments']
        
        try:
            # Analyze emotion for all segments
            analyzed_segments = self.analyze_segments(vocals_path, segments)
            
            result = {
                'segments': analyzed_segments,
                'num_segments': len(analyzed_segments),
                'vocals_path': vocals_path
            }
            
            return result
            
        finally:
            # Clean up model after use
            self.unload_model()
