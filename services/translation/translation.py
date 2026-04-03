"""Translation service using NLLB or GitHub Models."""

import torch
from typing import Dict, Any, List, Optional
from utils import get_logger, cleanup_model

logger = get_logger(__name__)


class TranslationService:
    """Performs translation using NLLB-200 (local) or GitHub Models (cloud)."""
    
    # Language code mapping (ISO to NLLB format)
    LANG_CODE_MAP = {
        'en': 'eng_Latn',
        'es': 'spa_Latn',
        'fr': 'fra_Latn',
        'de': 'deu_Latn',
        'zh': 'zho_Hans',
        'ja': 'jpn_Jpan',
        'ko': 'kor_Hang',
        'ar': 'arb_Arab',
        'hi': 'hin_Deva',
        'pt': 'por_Latn',
        'ru': 'rus_Cyrl',
        'it': 'ita_Latn',
        'tr': 'tur_Latn',
        'pl': 'pol_Latn',
        'nl': 'nld_Latn',
        'vi': 'vie_Latn',
        'th': 'tha_Thai',
        'id': 'ind_Latn',
        'uk': 'ukr_Cyrl',
        'ro': 'ron_Latn'
    }

    def __init__(
        self,
        model_name: str = "facebook/nllb-200-1.3B",
        device: str = "cuda",
        use_github_models: bool = False,
        github_model: str = "gpt-4o-mini",
        github_endpoint: str = "https://models.inference.ai.azure.com",
        github_token: Optional[str] = None
    ):
        """
        Initialize translation service.

        Args:
            model_name: NLLB model name (for local mode)
            device: Device for inference (for local mode)
            use_github_models: Whether to use GitHub Models instead of local
            github_model: GitHub model name
            github_endpoint: GitHub Models endpoint
            github_token: GitHub token
        """
        self.model_name = model_name
        self.device = device if torch.cuda.is_available() else "cpu"
        self.use_github_models = use_github_models
        self.github_model = github_model
        self.model = None
        self.tokenizer = None
        self.github_client = None

        # Initialize GitHub Models client if enabled
        if self.use_github_models:
            try:
                from services.github_models_client import GitHubModelsClient
                self.github_client = GitHubModelsClient(
                    endpoint=github_endpoint,
                    token=github_token
                )
                logger.info(f"Using GitHub Models for translation: {github_model}")
            except Exception as e:
                logger.warning(f"Failed to initialize GitHub Models, falling back to local: {e}")
                self.use_github_models = False
    
    def load_model(self):
        """Load NLLB model and tokenizer."""
        if self.model is not None:
            return
        
        try:
            logger.info(f"Loading NLLB model: {self.model_name}")
            from transformers import AutoModelForSeq2SeqLM, AutoTokenizer
            
            self.tokenizer = AutoTokenizer.from_pretrained(self.model_name)
            
            self.model = AutoModelForSeq2SeqLM.from_pretrained(
                self.model_name,
                torch_dtype=torch.float16 if self.device == "cuda" else torch.float32
            )
            
            self.model.to(self.device)
            self.model.eval()
            
            logger.info("NLLB model loaded successfully")
            
        except Exception as e:
            logger.error(f"Failed to load NLLB model: {e}")
            raise
    
    def unload_model(self):
        """Unload model from memory."""
        cleanup_model(self.model)
        cleanup_model(self.tokenizer)
        self.model = None
        self.tokenizer = None
    
    def get_nllb_lang_code(self, lang_code: str) -> str:
        """
        Convert ISO language code to NLLB format.
        
        Args:
            lang_code: ISO language code
            
        Returns:
            NLLB language code
        """
        return self.LANG_CODE_MAP.get(lang_code, 'eng_Latn')
    
    def translate_text(
        self,
        text: str,
        source_lang: str,
        target_lang: str,
        max_length: int = 512
    ) -> str:
        """
        Translate text from source to target language.

        Args:
            text: Text to translate
            source_lang: Source language code (ISO)
            target_lang: Target language code (ISO)
            max_length: Maximum output length

        Returns:
            Translated text
        """
        if not text.strip():
            return ""

        # Use GitHub Models if enabled
        if self.use_github_models and self.github_client:
            try:
                return self.github_client.translate_text(
                    text=text,
                    source_lang=source_lang,
                    target_lang=target_lang,
                    model=self.github_model
                )
            except Exception as e:
                logger.error(f"GitHub Models translation failed: {e}")
                # Fall through to local translation

        # Use local NLLB model
        self.load_model()

        try:
            # Convert to NLLB language codes
            src_lang = self.get_nllb_lang_code(source_lang)
            tgt_lang = self.get_nllb_lang_code(target_lang)

            # Set source language
            self.tokenizer.src_lang = src_lang

            # Tokenize
            inputs = self.tokenizer(
                text,
                return_tensors="pt",
                padding=True,
                truncation=True,
                max_length=max_length
            )

            # Move to device
            inputs = {k: v.to(self.device) for k, v in inputs.items()}

            # Generate translation
            with torch.no_grad():
                generated_tokens = self.model.generate(
                    **inputs,
                    forced_bos_token_id=self.tokenizer.lang_code_to_id[tgt_lang],
                    max_length=max_length,
                    num_beams=5,
                    early_stopping=True
                )

            # Decode
            translation = self.tokenizer.batch_decode(
                generated_tokens,
                skip_special_tokens=True
            )[0]

            return translation.strip()

        except Exception as e:
            logger.error(f"Failed to translate text: {e}")
            return text  # Return original text on error
    
    def translate_batch(
        self,
        texts: List[str],
        source_lang: str,
        target_lang: str,
        batch_size: int = 8
    ) -> List[str]:
        """
        Translate multiple texts in batches.
        
        Args:
            texts: List of texts to translate
            source_lang: Source language code
            target_lang: Target language code
            batch_size: Batch size
            
        Returns:
            List of translated texts
        """
        self.load_model()
        
        translations = []
        
        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            
            for text in batch:
                translation = self.translate_text(text, source_lang, target_lang)
                translations.append(translation)
        
        return translations
    
    def translate_segments(
        self,
        segments: List[Dict[str, Any]],
        source_lang: str,
        target_lang: str
    ) -> List[Dict[str, Any]]:
        """
        Translate segments.
        
        Args:
            segments: List of segments with text
            source_lang: Source language code
            target_lang: Target language code
            
        Returns:
            List of segments with translations
        """
        self.load_model()
        
        logger.info(
            f"Translating {len(segments)} segments from {source_lang} to {target_lang}"
        )
        
        translated_segments = []
        
        for i, segment in enumerate(segments):
            text = segment.get('text', '')
            
            if not text.strip():
                # Keep empty segments
                translated_segment = segment.copy()
                translated_segment['translated_text'] = ''
                translated_segments.append(translated_segment)
                continue
            
            try:
                # Translate
                translation = self.translate_text(text, source_lang, target_lang)
                
                # Add translation to segment
                translated_segment = segment.copy()
                translated_segment['original_text'] = text
                translated_segment['translated_text'] = translation
                translated_segment['source_lang'] = source_lang
                translated_segment['target_lang'] = target_lang
                
                translated_segments.append(translated_segment)
                
                if (i + 1) % 10 == 0:
                    logger.info(f"Translated {i + 1}/{len(segments)} segments")
                
            except Exception as e:
                logger.error(f"Failed to translate segment {i}: {e}")
                # Keep original text on error
                error_segment = segment.copy()
                error_segment['original_text'] = text
                error_segment['translated_text'] = text
                error_segment['error'] = str(e)
                translated_segments.append(error_segment)
        
        logger.info("Translation completed")
        
        return translated_segments
    
    def process(
        self,
        emotion_metadata: Dict[str, Any],
        target_language: str,
        source_language: str = None
    ) -> Dict[str, Any]:
        """
        Process translation.
        
        Args:
            emotion_metadata: Metadata from emotion step
            target_language: Target language code
            source_language: Source language code (auto-detect if None)
            
        Returns:
            Dictionary with translation results
        """
        segments = emotion_metadata['segments']
        
        # Auto-detect source language if not provided
        if source_language is None:
            # Use detected language from STT
            languages = [s.get('language', 'en') for s in segments if s.get('text')]
            source_language = max(set(languages), key=languages.count) if languages else 'en'
        
        logger.info(f"Source language: {source_language}, Target language: {target_language}")
        
        try:
            # Translate all segments
            translated_segments = self.translate_segments(
                segments,
                source_language,
                target_language
            )
            
            result = {
                'segments': translated_segments,
                'num_segments': len(translated_segments),
                'source_language': source_language,
                'target_language': target_language
            }
            
            return result
            
        finally:
            # Clean up model after use
            self.unload_model()
