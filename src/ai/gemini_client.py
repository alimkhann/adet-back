import os
import logging
from typing import Optional
from pydantic import BaseModel
import json
from google import genai
from google.genai import types

logger = logging.getLogger(__name__)

class GeminiAIClient:
    """Client for interacting with Google Gemini via google-genai SDK"""

    def __init__(self):
        # Use direct Google AI API instead of Vertex AI
        self.api_key = os.getenv("GEMINI_API_KEY")
        self.model_name = os.getenv("GOOGLE_GENAI_MODEL", "gemini-2.5-flash")
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY environment variable is required")
        self.client = genai.Client(api_key=self.api_key)
        logger.info(f"Gemini client initialized with model: {self.model_name}")

    async def generate_text(
        self,
        prompt: str,
        temperature: float = 0.7,
        max_tokens: int = 5000,
        system_prompt: Optional[str] = None
    ) -> str:
        """Generate text using Gemini model"""
        try:
            if system_prompt:
                full_prompt = f"{system_prompt}\n\n{prompt}"
            else:
                full_prompt = prompt

            response = self.client.models.generate_content(
                model=self.model_name,
                contents=[full_prompt],
                config=types.GenerateContentConfig(
                    temperature=temperature,
                    max_output_tokens=max_tokens,
                )
            )

            # Better error handling for None response
            if not hasattr(response, 'text') or response.text is None:
                logger.error(f"Empty response from Gemini API. Response: {response}")
                raise ValueError("Received empty response from Gemini API")

            logger.info("Text generation completed successfully")
            return response.text
        except Exception as e:
            logger.error(f"Error generating text: {str(e)}")
            raise

    async def generate_structured_response(
        self,
        prompt: str,
        response_schema: BaseModel,
        temperature: float = 0.3,
        max_tokens: int = 5000,
        system_prompt: Optional[str] = None
    ) -> BaseModel:
        """Generate structured response using Pydantic schema"""
        try:
            schema_instructions = f"""
            IMPORTANT: Respond with ONLY a valid JSON object that matches this schema. Do not include any schema descriptions, explanations, or markdown formatting.

            Required JSON schema:
            {response_schema.model_json_schema()}

            Return ONLY the JSON object, nothing else. Example format:
            {{"field1": "value1", "field2": 123}}
            """
            full_prompt = f"{prompt}\n\n{schema_instructions}"
            if system_prompt:
                full_prompt = f"{system_prompt}\n\n{full_prompt}"

            response = self.client.models.generate_content(
                model=self.model_name,
                contents=[full_prompt],
                config=types.GenerateContentConfig(
                    temperature=temperature,
                    max_output_tokens=max_tokens,
                )
            )

            # Better error handling for None response
            if not hasattr(response, 'text') or response.text is None:
                logger.error(f"Empty response from Gemini API. Response: {response}")
                raise ValueError("Received empty response from Gemini API")

            text = response.text
            logger.info(f"Received response: {text[:200]}...")  # Log first 200 chars

            # Strip markdown code blocks if present
            if text.strip().startswith('```json'):
                text = text.strip()
                text = text[7:]  # Remove ```json
                if text.endswith('```'):
                    text = text[:-3]  # Remove ```
                text = text.strip()

            # Handle case where AI returns schema description + JSON
            # Look for the actual JSON response part
            if '```json' in text and '```' in text:
                # Extract JSON from markdown code blocks
                start_idx = text.find('```json') + 7
                end_idx = text.find('```', start_idx)
                if end_idx > start_idx:
                    text = text[start_idx:end_idx].strip()
            elif text.count('{') > 1:
                # Multiple JSON objects - find the last complete one
                json_parts = []
                brace_count = 0
                current_json = ""

                for char in text:
                    current_json += char
                    if char == '{':
                        brace_count += 1
                    elif char == '}':
                        brace_count -= 1
                        if brace_count == 0 and current_json.strip().startswith('{'):
                            json_parts.append(current_json.strip())
                            current_json = ""

                # Use the last valid JSON object
                if json_parts:
                    text = json_parts[-1]

            # Handle truncated JSON by trying to fix common issues
            if not text.strip().endswith('}'):
                logger.warning("Response appears truncated, attempting to fix...")
                text = text.strip()
                # Try to add missing closing brace
                if text.count('{') > text.count('}'):
                    text += '}'

            try:
                json_response = json.loads(text)
                return response_schema.model_validate(json_response)
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse JSON response: {e}")
                logger.error(f"Raw response: {text}")
                raise ValueError(f"Invalid JSON response: {text}")
            except Exception as e:
                logger.error(f"Failed to validate response schema: {e}")
                raise
        except Exception as e:
            logger.error(f"Error generating structured response: {str(e)}")
            raise

    async def analyze_image(self, image_path: str, prompt: str, temperature: float = 0.3) -> str:
        raise NotImplementedError("Image analysis is not implemented in this client. Use Gemini multimodal API when available.")

    async def analyze_audio(self, audio_path: str, prompt: str, temperature: float = 0.3) -> str:
        raise NotImplementedError("Audio analysis is not implemented in this client. Use Gemini multimodal API when available.")

# Global client instance
gemini_client: Optional[GeminiAIClient] = None

def get_gemini_client() -> GeminiAIClient:
    global gemini_client
    if gemini_client is None:
        gemini_client = GeminiAIClient()
    return gemini_client