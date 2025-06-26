import os
import logging
from typing import Optional, Dict, Any
from google.cloud import aiplatform
from pydantic import BaseModel
import json

logger = logging.getLogger(__name__)

class VertexAIClient:
    """Client for interacting with Google Vertex AI"""

    def __init__(self):
        self.project_id = os.getenv("GOOGLE_CLOUD_PROJECT")
        self.location = os.getenv("GOOGLE_CLOUD_LOCATION", "us-central1")
        self.model_name = "gemini-1.5-pro"

        if not self.project_id:
            raise ValueError("GOOGLE_CLOUD_PROJECT environment variable is required")

        # Initialize Vertex AI
        aiplatform.init(project=self.project_id, location=self.location)
        self.model = aiplatform.GenerativeModel(self.model_name)

        logger.info(f"Vertex AI client initialized for project: {self.project_id}")

    async def generate_text(
        self,
        prompt: str,
        temperature: float = 0.7,
        max_tokens: int = 1000,
        system_prompt: Optional[str] = None
    ) -> str:
        """Generate text using Vertex AI Gemini model"""
        try:
            # Prepare the prompt
            if system_prompt:
                full_prompt = f"{system_prompt}\n\n{prompt}"
            else:
                full_prompt = prompt

            # Generate response
            response = self.model.generate_content(
                full_prompt,
                generation_config={
                    "temperature": temperature,
                    "max_output_tokens": max_tokens,
                }
            )

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
        system_prompt: Optional[str] = None
    ) -> BaseModel:
        """Generate structured response using Pydantic schema"""
        try:
            # Add schema instructions to prompt
            schema_instructions = f"""
            Respond with a valid JSON object that matches this schema:
            {response_schema.model_json_schema()}

            Ensure the response is valid JSON and matches the schema exactly.
            """

            full_prompt = f"{prompt}\n\n{schema_instructions}"

            if system_prompt:
                full_prompt = f"{system_prompt}\n\n{full_prompt}"

            # Generate response
            response = self.model.generate_content(full_prompt)

            # Parse JSON response
            try:
                json_response = json.loads(response.text)
                return response_schema.model_validate(json_response)
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse JSON response: {e}")
                raise ValueError(f"Invalid JSON response: {response.text}")
            except Exception as e:
                logger.error(f"Failed to validate response schema: {e}")
                raise

        except Exception as e:
            logger.error(f"Error generating structured response: {str(e)}")
            raise

    async def analyze_image(
        self,
        image_path: str,
        prompt: str,
        temperature: float = 0.3
    ) -> str:
        """Analyze image using Vertex AI multimodal capabilities"""
        try:
            # Load image
            with open(image_path, "rb") as image_file:
                image_data = image_file.read()

            # Create multimodal prompt
            multimodal_prompt = [
                prompt,
                {"mime_type": "image/jpeg", "data": image_data}
            ]

            # Generate response
            response = self.model.generate_content(
                multimodal_prompt,
                generation_config={"temperature": temperature}
            )

            logger.info("Image analysis completed successfully")
            return response.text

        except Exception as e:
            logger.error(f"Error analyzing image: {str(e)}")
            raise

    async def analyze_audio(
        self,
        audio_path: str,
        prompt: str,
        temperature: float = 0.3
    ) -> str:
        """Analyze audio using Vertex AI (if supported)"""
        try:
            # Load audio file
            with open(audio_path, "rb") as audio_file:
                audio_data = audio_file.read()

            # Create multimodal prompt for audio
            multimodal_prompt = [
                prompt,
                {"mime_type": "audio/wav", "data": audio_data}
            ]

            # Generate response
            response = self.model.generate_content(
                multimodal_prompt,
                generation_config={"temperature": temperature}
            )

            logger.info("Audio analysis completed successfully")
            return response.text

        except Exception as e:
            logger.error(f"Error analyzing audio: {str(e)}")
            raise

# Global client instance
vertex_client: Optional[VertexAIClient] = None

def get_vertex_client() -> VertexAIClient:
    """Get or create Vertex AI client instance"""
    global vertex_client
    if vertex_client is None:
        vertex_client = VertexAIClient()
    return vertex_client