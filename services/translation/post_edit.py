"""Post-editing service using LLM for natural spoken language."""

import torch
from typing import Dict, Any, List
from utils import get_logger, cleanup_model

logger = get_logger(__name__)


class PostEditService:
    """Post-edits translations for natural spoken language using Qwen."""
    
    def __init__(
        self,
        model_name: str = "Qwen/Qwen2.5-7B-Instruct",
        device: str = "cuda",
        quantization: str = "4bit"
    ):
        """
        Initialize post-edit service.
        
        Args:
            model_name: LLM model name
            device: Device for inference
            quantization: Quantization mode (4bit, 8bit, none)
        """
        self.model_name = model_name
        self.device = device if torch.cuda.is_available() else "cpu"
        self.quantization = quantization
        self.model = None
        self.tokenizer = None
    
    def load_model(self):
        """Load LLM model and tokenizer."""
        if self.model is not None:
            return
        
        try:
            logger.info(f"Loading LLM model: {self.model_name}")
            from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig
            
            self.tokenizer = AutoTokenizer.from_pretrained(self.model_name)
            
            # Configure quantization
            if self.quantization == "4bit":
                logger.info("Using 4-bit quantization")
                quantization_config = BitsAndBytesConfig(
                    load_in_4bit=True,
                    bnb_4bit_compute_dtype=torch.float16,
                    bnb_4bit_use_double_quant=True,
                    bnb_4bit_quant_type="nf4"
                )
                self.model = AutoModelForCausalLM.from_pretrained(
                    self.model_name,
                    quantization_config=quantization_config,
                    device_map="auto",
                    trust_remote_code=True
                )
            elif self.quantization == "8bit":
                logger.info("Using 8-bit quantization")
                quantization_config = BitsAndBytesConfig(load_in_8bit=True)
                self.model = AutoModelForCausalLM.from_pretrained(
                    self.model_name,
                    quantization_config=quantization_config,
                    device_map="auto",
                    trust_remote_code=True
                )
            else:
                self.model = AutoModelForCausalLM.from_pretrained(
                    self.model_name,
                    torch_dtype=torch.float16 if self.device == "cuda" else torch.float32,
                    device_map="auto",
                    trust_remote_code=True
                )
            
            self.model.eval()
            
            logger.info("LLM model loaded successfully")
            
        except Exception as e:
            logger.error(f"Failed to load LLM model: {e}")
            raise
    
    def unload_model(self):
        """Unload model from memory."""
        cleanup_model(self.model)
        cleanup_model(self.tokenizer)
        self.model = None
        self.tokenizer = None
    
    def post_edit_text(
        self,
        text: str,
        target_lang: str,
        emotion: str = None,
        context: str = None
    ) -> str:
        """
        Post-edit translated text for natural spoken language.
        
        Args:
            text: Translated text
            target_lang: Target language
            emotion: Emotion label (optional)
            context: Additional context (optional)
            
        Returns:
            Post-edited text
        """
        if not text.strip():
            return ""
        
        self.load_model()
        
        try:
            # Build prompt
            prompt = self._build_prompt(text, target_lang, emotion, context)
            
            # Tokenize
            inputs = self.tokenizer(
                prompt,
                return_tensors="pt",
                truncation=True,
                max_length=512
            )
            
            # Move to device
            if self.device != "auto":
                inputs = {k: v.to(self.device) for k, v in inputs.items()}
            
            # Generate
            with torch.no_grad():
                outputs = self.model.generate(
                    **inputs,
                    max_new_tokens=256,
                    temperature=0.7,
                    do_sample=True,
                    top_p=0.9,
                    pad_token_id=self.tokenizer.eos_token_id
                )
            
            # Decode
            response = self.tokenizer.decode(outputs[0], skip_special_tokens=True)
            
            # Extract edited text (remove prompt)
            edited_text = self._extract_response(response, prompt)
            
            return edited_text.strip()
            
        except Exception as e:
            logger.error(f"Failed to post-edit text: {e}")
            return text  # Return original text on error
    
    def _build_prompt(
        self,
        text: str,
        target_lang: str,
        emotion: str = None,
        context: str = None
    ) -> str:
        """Build prompt for post-editing."""
        prompt = f"""You are a professional translator. Your task is to improve the following machine-translated text to make it sound more natural and conversational in {target_lang}.

Original translation: {text}
"""
        
        if emotion:
            prompt += f"Emotional tone: {emotion}\n"
        
        if context:
            prompt += f"Context: {context}\n"
        
        prompt += """
Instructions:
- Make the text sound natural and conversational
- Preserve the original meaning
- Adjust for spoken language style
- Keep it concise
- Only output the improved translation, nothing else

Improved translation:"""
        
        return prompt
    
    def _extract_response(self, response: str, prompt: str) -> str:
        """Extract the edited text from the model response."""
        # Remove the prompt from response
        if prompt in response:
            response = response.replace(prompt, "")
        
        # Clean up
        response = response.strip()
        
        # If response is too long or contains unwanted text, take first sentence
        if len(response) > 500:
            # Take first few sentences
            sentences = response.split('.')
            response = '.'.join(sentences[:2]) + '.'
        
        return response
    
    def post_edit_segments(
        self,
        segments: List[Dict[str, Any]],
        target_lang: str
    ) -> List[Dict[str, Any]]:
        """
        Post-edit multiple segments.
        
        Args:
            segments: List of segments with translations
            target_lang: Target language
            
        Returns:
            List of segments with post-edited translations
        """
        self.load_model()
        
        logger.info(f"Post-editing {len(segments)} segments")
        
        edited_segments = []
        
        for i, segment in enumerate(segments):
            text = segment.get('translated_text', '')
            
            if not text.strip():
                # Keep empty segments
                edited_segment = segment.copy()
                edited_segment['final_text'] = ''
                edited_segments.append(edited_segment)
                continue
            
            try:
                # Post-edit
                emotion = segment.get('emotion', 'neutral')
                edited_text = self.post_edit_text(text, target_lang, emotion)
                
                # Add to segment
                edited_segment = segment.copy()
                edited_segment['post_edited_text'] = edited_text
                edited_segment['final_text'] = edited_text
                
                edited_segments.append(edited_segment)
                
                if (i + 1) % 10 == 0:
                    logger.info(f"Post-edited {i + 1}/{len(segments)} segments")
                
            except Exception as e:
                logger.error(f"Failed to post-edit segment {i}: {e}")
                # Keep original translation on error
                error_segment = segment.copy()
                error_segment['post_edited_text'] = text
                error_segment['final_text'] = text
                error_segment['error'] = str(e)
                edited_segments.append(error_segment)
        
        logger.info("Post-editing completed")
        
        return edited_segments
    
    def process(
        self,
        translation_metadata: Dict[str, Any],
        output_dir: str
    ) -> Dict[str, Any]:
        """
        Process post-editing.
        
        Args:
            translation_metadata: Metadata from translation step
            output_dir: Directory for output files
            
        Returns:
            Dictionary with post-editing results
        """
        segments = translation_metadata['segments']
        target_language = translation_metadata['target_language']
        
        try:
            # Post-edit all segments
            edited_segments = self.post_edit_segments(segments, target_language)
            
            result = {
                'segments': edited_segments,
                'num_segments': len(edited_segments),
                'target_language': target_language
            }
            
            return result
            
        finally:
            # Clean up model after use
            self.unload_model()
