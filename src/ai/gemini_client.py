import os
import logging
import json
from typing import Optional, Type
from pydantic import BaseModel
import google.generativeai as genai

logger = logging.getLogger(__name__)

class GeminiClient:
    def __init__(self):
        """
        Initialize the Gemini client with configuration from environment variables.
        """
        api_key = os.getenv('GOOGLE_AI_API_KEY')
        if not api_key:
            logger.warning("GOOGLE_AI_API_KEY not found in environment variables")

        # Configure the Gemini client
        genai.configure(api_key=api_key)

        # Default model
        self.model_name = "gemini-1.5-flash"

        # Initialize the model
        self.model = genai.GenerativeModel(self.model_name)

        logger.info(f"Initialized Gemini client with model: {self.model_name}")

    def generate_text(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        max_tokens: int = 1000,
        temperature: float = 0.7,
        response_model: Optional[Type[BaseModel]] = None
    ) -> str:
        """
        Generate text using the Gemini model.

        Args:
            prompt: The user prompt
            system_prompt: Optional system prompt
            max_tokens: Maximum tokens to generate
            temperature: Temperature for generation
            response_model: Optional Pydantic model for structured output

        Returns:
            Generated text response
        """
        try:
            # Prepare the generation config
            generation_config = genai.types.GenerationConfig(
                max_output_tokens=max_tokens,
                temperature=temperature,
            )

            # If we need structured output
            if response_model:
                generation_config.response_mime_type = "application/json"
                generation_config.response_schema = response_model

            # Prepare the prompt with system instruction if provided
            full_prompt = prompt
            if system_prompt:
                full_prompt = f"System: {system_prompt}\n\nUser: {prompt}"

            # Generate content
            response = self.model.generate_content(
                full_prompt,
                generation_config=generation_config
            )

            if response.text:
                return response.text
            else:
                logger.error("No text in response")
                return ""

        except Exception as e:
            logger.error(f"Error generating text: {e}")
            return ""

    def generate_text_stream(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        max_tokens: int = 1000,
        temperature: float = 0.7
    ):
        """
        Generate text using streaming response.

        Args:
            prompt: The user prompt
            system_prompt: Optional system prompt
            max_tokens: Maximum tokens to generate
            temperature: Temperature for generation

        Yields:
            Text chunks as they are generated
        """
        try:
            # Prepare the generation config
            generation_config = genai.types.GenerationConfig(
                max_output_tokens=max_tokens,
                temperature=temperature,
            )

            # Prepare the prompt with system instruction if provided
            full_prompt = prompt
            if system_prompt:
                full_prompt = f"System: {system_prompt}\n\nUser: {prompt}"

            # Generate content with streaming
            response = self.model.generate_content(
                full_prompt,
                generation_config=generation_config,
                stream=True
            )

            for chunk in response:
                if chunk.text:
                    yield chunk.text

        except Exception as e:
            logger.error(f"Error generating streaming text: {e}")
            yield ""

    def analyze_image_with_text(
        self,
        prompt: str,
        image_bytes: bytes,
        system_prompt: Optional[str] = None,
        max_tokens: int = 1000,
        temperature: float = 0.7
    ) -> str:
        """
        Analyze an image with text prompt using Gemini Vision.

        Args:
            prompt: The text prompt
            image_bytes: Image data as bytes
            system_prompt: Optional system prompt
            max_tokens: Maximum tokens to generate
            temperature: Temperature for generation

        Returns:
            Analysis result as text
        """
        try:
            # Prepare the generation config
            generation_config = genai.types.GenerationConfig(
                max_output_tokens=max_tokens,
                temperature=temperature,
            )

            # Create parts for the content
            parts = []

            # Add system prompt if provided
            if system_prompt:
                parts.append(f"System: {system_prompt}\n\n")

            # Add the text prompt
            parts.append(prompt)

            # Add the image
            import PIL.Image
            import io

            # Convert bytes to PIL Image
            image = PIL.Image.open(io.BytesIO(image_bytes))
            parts.append(image)

            # Generate content using the model
            response = self.model.generate_content(
                parts,
                generation_config=generation_config
            )

            if response.text:
                return response.text
            else:
                logger.error("No text in response")
                return ""

        except Exception as e:
            logger.error(f"Error analyzing image: {e}")
            return ""

    def analyze_audio_with_text(
        self,
        prompt: str,
        audio_bytes: bytes,
        system_prompt: Optional[str] = None,
        max_tokens: int = 1000,
        temperature: float = 0.7
    ) -> str:
        """
        Analyze audio with text prompt.

        Args:
            prompt: The text prompt
            audio_bytes: Audio data as bytes
            system_prompt: Optional system prompt
            max_tokens: Maximum tokens to generate
            temperature: Temperature for generation

        Returns:
            Analysis result as text
        """
        try:
            # Note: For audio analysis, we would need to upload the file first
            # For now, return a placeholder
            logger.warning("Audio analysis not yet implemented")
            return "Audio analysis not yet implemented in this version."

        except Exception as e:
            logger.error(f"Error analyzing audio: {e}")
            return ""

# Global client instance
_client = None

def get_gemini_client() -> GeminiClient:
    """Get the global Gemini client instance."""
    global _client
    if _client is None:
        _client = GeminiClient()
    return _client
