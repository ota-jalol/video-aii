"""GitHub Models client using Azure AI Inference SDK."""

import os
from typing import Dict, Any, List, Optional
from utils import get_logger

logger = get_logger(__name__)


class GitHubModelsClient:
    """Client for GitHub Models via Azure AI Inference SDK."""

    def __init__(
        self,
        endpoint: str = "https://models.inference.ai.azure.com",
        token: Optional[str] = None
    ):
        """
        Initialize GitHub Models client.

        Args:
            endpoint: Azure AI Inference endpoint
            token: GitHub token (will use GITHUB_TOKEN env var if not provided)
        """
        self.endpoint = endpoint
        self.token = token or os.environ.get("GITHUB_TOKEN")

        if not self.token:
            raise ValueError(
                "GitHub token is required. Set GITHUB_TOKEN environment variable "
                "or provide token in config.yaml"
            )

        self.client = None
        self._initialize_client()

    def _initialize_client(self):
        """Initialize the Azure AI Inference client."""
        try:
            from azure.ai.inference import ChatCompletionsClient
            from azure.core.credentials import AzureKeyCredential

            self.client = ChatCompletionsClient(
                endpoint=self.endpoint,
                credential=AzureKeyCredential(self.token)
            )

            logger.info("GitHub Models client initialized successfully")

        except ImportError:
            logger.error(
                "azure-ai-inference package not found. "
                "Install it with: pip install azure-ai-inference"
            )
            raise
        except Exception as e:
            logger.error(f"Failed to initialize GitHub Models client: {e}")
            raise

    def complete(
        self,
        messages: List[Dict[str, str]],
        model: str = "gpt-4o-mini",
        temperature: float = 0.7,
        max_tokens: int = 1024,
        **kwargs
    ) -> str:
        """
        Complete a chat conversation.

        Args:
            messages: List of message dictionaries with 'role' and 'content'
            model: Model name (e.g., 'gpt-4o-mini', 'phi-4', 'mistral-large-3')
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate
            **kwargs: Additional parameters

        Returns:
            Generated response text
        """
        try:
            response = self.client.complete(
                messages=messages,
                model=model,
                temperature=temperature,
                max_tokens=max_tokens,
                **kwargs
            )

            return response.choices[0].message.content

        except Exception as e:
            logger.error(f"Failed to complete chat: {e}")
            raise

    def translate_text(
        self,
        text: str,
        source_lang: str,
        target_lang: str,
        model: str = "gpt-4o-mini"
    ) -> str:
        """
        Translate text using GitHub Models.

        Args:
            text: Text to translate
            source_lang: Source language code
            target_lang: Target language code
            model: Model to use for translation

        Returns:
            Translated text
        """
        if not text.strip():
            return ""

        try:
            # Build translation prompt
            messages = [
                {
                    "role": "system",
                    "content": f"You are a professional translator. Translate the following text from {source_lang} to {target_lang}. Only provide the translation, nothing else."
                },
                {
                    "role": "user",
                    "content": text
                }
            ]

            translation = self.complete(
                messages=messages,
                model=model,
                temperature=0.3,  # Lower temperature for more deterministic translation
                max_tokens=512
            )

            return translation.strip()

        except Exception as e:
            logger.error(f"Failed to translate text: {e}")
            return text  # Return original text on error

    def post_edit_text(
        self,
        text: str,
        target_lang: str,
        emotion: Optional[str] = None,
        context: Optional[str] = None,
        model: str = "gpt-4o-mini"
    ) -> str:
        """
        Post-edit translated text for natural spoken language.

        Args:
            text: Translated text
            target_lang: Target language
            emotion: Emotion label (optional)
            context: Additional context (optional)
            model: Model to use

        Returns:
            Post-edited text
        """
        if not text.strip():
            return ""

        try:
            # Build post-editing prompt
            system_prompt = (
                f"You are a professional translator specializing in {target_lang}. "
                "Your task is to improve machine-translated text to make it sound "
                "more natural and conversational while preserving the original meaning."
            )

            user_prompt = f"Original translation: {text}\n\n"

            if emotion:
                user_prompt += f"Emotional tone: {emotion}\n"

            if context:
                user_prompt += f"Context: {context}\n"

            user_prompt += (
                "\nInstructions:\n"
                "- Make the text sound natural and conversational\n"
                "- Preserve the original meaning\n"
                "- Adjust for spoken language style\n"
                "- Keep it concise\n"
                "- Only output the improved translation, nothing else\n\n"
                "Improved translation:"
            )

            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ]

            edited_text = self.complete(
                messages=messages,
                model=model,
                temperature=0.7,
                max_tokens=512
            )

            return edited_text.strip()

        except Exception as e:
            logger.error(f"Failed to post-edit text: {e}")
            return text  # Return original text on error
