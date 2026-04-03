"""Orchestrator for the video dubbing pipeline."""

import os
import time
from pathlib import Path
from typing import Dict, Any, Optional
from configs import get_config
from utils import (
    setup_logger,
    get_logger,
    generate_job_id,
    create_temp_dir,
    cleanup_temp_dir,
    save_json,
    load_json,
    GPUMemoryManager
)

# Import all services
from services.ingestion import VideoIngestionService
from services.audio_extraction import AudioExtractionService
from services.separation import SeparationService
from services.diarization import DiarizationService
from services.stt import STTService
from services.emotion import EmotionService
from services.translation import TranslationService, PostEditService
from services.tts import TTSService
from services.alignment import AlignmentService
from services.muxing import MuxingService

logger = get_logger(__name__)


class DubbingOrchestrator:
    """Orchestrates the complete video dubbing pipeline."""
    
    def __init__(self, config_path: str = None):
        """
        Initialize orchestrator.
        
        Args:
            config_path: Path to configuration file
        """
        self.config = get_config(config_path)
        self._setup_logging()
        self.gpu_manager = GPUMemoryManager(
            max_memory_gb=self.config.get('system.gpu_memory_gb', 12.0)
        )
        
        # Initialize services
        self._init_services()
        
        logger.info("Dubbing orchestrator initialized")
    
    def _setup_logging(self):
        """Set up logging system."""
        log_config = self.config.get_all().get('logging', {})
        log_file = log_config.get('file', 'logs/dubbing.log')
        log_level = log_config.get('level', 'INFO')
        
        # Create logs directory
        Path(log_file).parent.mkdir(parents=True, exist_ok=True)
        
        # Set up logger
        setup_logger(
            name='',  # Root logger
            log_file=log_file,
            level=log_level,
            console=log_config.get('console', True)
        )
    
    def _init_services(self):
        """Initialize all pipeline services."""
        logger.info("Initializing pipeline services")

        # Get configuration
        audio_config = self.config.get('audio', {})
        models_config = self.config.get('models', {})
        processing_config = self.config.get('processing', {})
        github_models_config = self.config.get('github_models', {})

        # Check if GitHub Models is enabled
        use_github_models = github_models_config.get('enabled', False)
        github_endpoint = github_models_config.get('endpoint', 'https://models.inference.ai.azure.com')
        github_token = github_models_config.get('token') or os.environ.get('GITHUB_TOKEN')

        if use_github_models:
            logger.info("GitHub Models enabled - using cloud-based AI models")
        else:
            logger.info("Using local AI models")

        # Initialize services
        self.ingestion_service = VideoIngestionService()

        self.extraction_service = AudioExtractionService(
            sample_rate=audio_config.get('sample_rate', 16000)
        )

        self.separation_service = SeparationService(
            model_name=audio_config.get('separation', {}).get('model', 'htdemucs'),
            device=models_config.get('whisper', {}).get('device', 'cuda')
        )

        self.diarization_service = DiarizationService(
            model_name=models_config.get('diarization', {}).get('name'),
            device=models_config.get('diarization', {}).get('device', 'cuda'),
            auth_token=models_config.get('diarization', {}).get('auth_token')
        )

        self.stt_service = STTService(
            model_name=models_config.get('whisper', {}).get('name'),
            device=models_config.get('whisper', {}).get('device', 'cuda'),
            quantization=models_config.get('whisper', {}).get('quantization', 'int8')
        )

        self.emotion_service = EmotionService(
            model_name=models_config.get('emotion', {}).get('name'),
            device=models_config.get('emotion', {}).get('device', 'cuda')
        )

        self.translation_service = TranslationService(
            model_name=models_config.get('translation', {}).get('name'),
            device=models_config.get('translation', {}).get('device', 'cuda'),
            use_github_models=use_github_models,
            github_model=models_config.get('translation', {}).get('github_model', 'gpt-4o-mini'),
            github_endpoint=github_endpoint,
            github_token=github_token
        )

        self.post_edit_service = PostEditService(
            model_name=models_config.get('post_edit_llm', {}).get('name'),
            device=models_config.get('post_edit_llm', {}).get('device', 'cuda'),
            quantization=models_config.get('post_edit_llm', {}).get('quantization', '4bit'),
            use_github_models=use_github_models,
            github_model=models_config.get('post_edit_llm', {}).get('github_model', 'gpt-4o-mini'),
            github_endpoint=github_endpoint,
            github_token=github_token
        )

        self.tts_service = TTSService(
            device=models_config.get('tts', {}).get('device', 'cuda')
        )

        self.alignment_service = AlignmentService(
            stretch_algorithm=audio_config.get('alignment', {}).get('stretch_algorithm', 'rubberband')
        )

        output_config = self.config.get('output', {})
        self.muxing_service = MuxingService(
            video_codec='copy',  # Don't re-encode video
            audio_codec=output_config.get('audio_codec', 'aac'),
            audio_bitrate=output_config.get('audio_bitrate', '192k')
        )

        logger.info("All services initialized")
    
    def _retry_with_backoff(self, func, *args, max_attempts: int = 3, **kwargs):
        """
        Execute function with retry logic.
        
        Args:
            func: Function to execute
            max_attempts: Maximum retry attempts
            
        Returns:
            Function result
        """
        retry_delay = self.config.get('processing.retry_delay', 5)
        
        for attempt in range(1, max_attempts + 1):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                if attempt == max_attempts:
                    logger.error(f"Failed after {max_attempts} attempts: {e}")
                    raise
                
                logger.warning(
                    f"Attempt {attempt} failed: {e}. "
                    f"Retrying in {retry_delay}s..."
                )
                time.sleep(retry_delay)
    
    def process_video(
        self,
        video_path: str,
        output_path: str,
        target_language: str = None,
        source_language: str = None,
        keep_temp: bool = False
    ) -> Dict[str, Any]:
        """
        Process video dubbing pipeline.
        
        Args:
            video_path: Path to input video
            output_path: Path for output video
            target_language: Target language code (default from config)
            source_language: Source language code (None for auto-detect)
            keep_temp: Keep temporary files
            
        Returns:
            Dictionary with processing results
        """
        # Generate job ID
        job_id = generate_job_id()
        
        logger.info(f"="*80)
        logger.info(f"Starting video dubbing job: {job_id}")
        logger.info(f"Input video: {video_path}")
        logger.info(f"Output video: {output_path}")
        logger.info(f"="*80)
        
        # Set target language
        if target_language is None:
            target_language = self.config.get('languages.target', 'en')
        
        # Create temporary directory
        temp_dir = self.config.get('system.temp_dir', '/tmp/video_dubbing')
        job_temp_dir = create_temp_dir(temp_dir, job_id)
        
        logger.info(f"Temporary directory: {job_temp_dir}")
        
        # Log GPU memory
        self.gpu_manager.log_memory_stats()
        
        start_time = time.time()
        
        try:
            # Step 1: Video ingestion
            logger.info("\n" + "="*80)
            logger.info("STEP 1: Video Ingestion")
            logger.info("="*80)
            
            video_metadata = self._retry_with_backoff(
                self.ingestion_service.process,
                video_path
            )
            save_json(video_metadata, str(job_temp_dir / "01_ingestion.json"))
            
            # Step 2: Audio extraction
            logger.info("\n" + "="*80)
            logger.info("STEP 2: Audio Extraction")
            logger.info("="*80)
            
            audio_metadata = self._retry_with_backoff(
                self.extraction_service.process,
                video_metadata,
                str(job_temp_dir)
            )
            save_json(audio_metadata, str(job_temp_dir / "02_extraction.json"))
            self.gpu_manager.clear_cache()
            
            # Step 3: Music/speech separation
            logger.info("\n" + "="*80)
            logger.info("STEP 3: Music/Speech Separation")
            logger.info("="*80)
            
            separation_metadata = self._retry_with_backoff(
                self.separation_service.process,
                audio_metadata,
                str(job_temp_dir)
            )
            save_json(separation_metadata, str(job_temp_dir / "03_separation.json"))
            self.gpu_manager.clear_cache()
            
            # Step 4: Speaker diarization
            logger.info("\n" + "="*80)
            logger.info("STEP 4: Speaker Diarization")
            logger.info("="*80)
            
            diarization_metadata = self._retry_with_backoff(
                self.diarization_service.process,
                separation_metadata,
                str(job_temp_dir)
            )
            save_json(diarization_metadata, str(job_temp_dir / "04_diarization.json"))
            self.gpu_manager.clear_cache()
            
            # Step 5: Speech-to-text
            logger.info("\n" + "="*80)
            logger.info("STEP 5: Speech-to-Text (STT)")
            logger.info("="*80)
            
            batch_size = self.config.get('processing.batch_size_stt', 8)
            stt_metadata = self._retry_with_backoff(
                self.stt_service.process,
                diarization_metadata,
                str(job_temp_dir),
                batch_size,
                source_language
            )
            save_json(stt_metadata, str(job_temp_dir / "05_stt.json"))
            self.gpu_manager.clear_cache()
            
            # Step 6: Emotion analysis
            logger.info("\n" + "="*80)
            logger.info("STEP 6: Emotion Analysis")
            logger.info("="*80)
            
            emotion_metadata = self._retry_with_backoff(
                self.emotion_service.process,
                stt_metadata,
                str(job_temp_dir)
            )
            save_json(emotion_metadata, str(job_temp_dir / "06_emotion.json"))
            self.gpu_manager.clear_cache()
            
            # Step 7: Translation
            logger.info("\n" + "="*80)
            logger.info("STEP 7: Translation")
            logger.info("="*80)
            
            translation_metadata = self._retry_with_backoff(
                self.translation_service.process,
                emotion_metadata,
                target_language,
                source_language
            )
            save_json(translation_metadata, str(job_temp_dir / "07_translation.json"))
            self.gpu_manager.clear_cache()
            
            # Step 8: Post-editing
            logger.info("\n" + "="*80)
            logger.info("STEP 8: Post-Editing")
            logger.info("="*80)
            
            post_edit_metadata = self._retry_with_backoff(
                self.post_edit_service.process,
                translation_metadata,
                str(job_temp_dir)
            )
            save_json(post_edit_metadata, str(job_temp_dir / "08_post_edit.json"))
            self.gpu_manager.clear_cache()
            
            # Step 9: Text-to-speech (sequential)
            logger.info("\n" + "="*80)
            logger.info("STEP 9: Text-to-Speech (TTS)")
            logger.info("="*80)
            
            tts_metadata = self._retry_with_backoff(
                self.tts_service.process,
                post_edit_metadata,
                separation_metadata['vocals_path'],
                str(job_temp_dir)
            )
            save_json(tts_metadata, str(job_temp_dir / "09_tts.json"))
            self.gpu_manager.clear_cache()
            
            # Step 10: Audio alignment and mixing
            logger.info("\n" + "="*80)
            logger.info("STEP 10: Audio Alignment and Mixing")
            logger.info("="*80)
            
            alignment_metadata = self._retry_with_backoff(
                self.alignment_service.process,
                tts_metadata,
                separation_metadata['background_path'],
                str(job_temp_dir)
            )
            save_json(alignment_metadata, str(job_temp_dir / "10_alignment.json"))
            
            # Step 11: Video muxing
            logger.info("\n" + "="*80)
            logger.info("STEP 11: Video Muxing")
            logger.info("="*80)
            
            muxing_metadata = self._retry_with_backoff(
                self.muxing_service.process,
                video_metadata,
                alignment_metadata,
                output_path
            )
            save_json(muxing_metadata, str(job_temp_dir / "11_muxing.json"))
            
            # Calculate total time
            total_time = time.time() - start_time
            
            # Compile results
            results = {
                'job_id': job_id,
                'input_video': video_path,
                'output_video': output_path,
                'source_language': stt_metadata.get('detected_language', source_language),
                'target_language': target_language,
                'num_segments': len(tts_metadata['segments']),
                'num_speakers': diarization_metadata.get('num_speakers', 0),
                'processing_time_seconds': total_time,
                'success': True,
                'temp_dir': str(job_temp_dir)
            }
            
            # Save final results
            save_json(results, str(job_temp_dir / "00_results.json"))
            
            logger.info("\n" + "="*80)
            logger.info("VIDEO DUBBING COMPLETED SUCCESSFULLY!")
            logger.info("="*80)
            logger.info(f"Job ID: {job_id}")
            logger.info(f"Output video: {output_path}")
            logger.info(f"Processing time: {total_time:.2f} seconds ({total_time/60:.2f} minutes)")
            logger.info(f"Source language: {results['source_language']}")
            logger.info(f"Target language: {target_language}")
            logger.info(f"Segments processed: {results['num_segments']}")
            logger.info(f"Speakers detected: {results['num_speakers']}")
            logger.info("="*80)
            
            return results
            
        except Exception as e:
            logger.error(f"Pipeline failed: {e}", exc_info=True)
            
            # Save error info
            error_results = {
                'job_id': job_id,
                'input_video': video_path,
                'success': False,
                'error': str(e),
                'processing_time_seconds': time.time() - start_time
            }
            
            try:
                save_json(error_results, str(job_temp_dir / "00_error.json"))
            except:
                pass
            
            raise
            
        finally:
            # Cleanup temporary directory if requested
            if not keep_temp:
                logger.info(f"Cleaning up temporary directory: {job_temp_dir}")
                cleanup_temp_dir(str(job_temp_dir), keep_artifacts=False)
            else:
                logger.info(f"Temporary files kept at: {job_temp_dir}")
