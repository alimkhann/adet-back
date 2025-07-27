import os
import logging
import json
from typing import Optional, Type
from pydantic import BaseModel
from google import genai
from google.genai import types
from google.genai.types import (
    GenerateContentConfig,
    LiveConnectConfig,
    Content,
    Part,
    SpeechConfig,
    VoiceConfig,
    PrebuiltVoiceConfig,
)

logger = logging.getLogger(__name__)

class GeminiAIClient:
    """Client for interacting with Google Gemini via google-genai SDK"""

    def __init__(self):
        self.api_key = os.getenv("GEMINI_API_KEY")
        self.model_name = os.getenv("GOOGLE_GENAI_MODEL", "gemini-2.5-flash")
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY environment variable is required")
        # VertexAI=False uses the direct GenAI endpoint
        self.client = genai.Client(api_key=self.api_key, vertexai=False)
        logger.info(f"Gemini client initialized with model: {self.model_name}")

    async def generate_text(
        self,
        prompt: str,
        temperature: float = 0.7,
        max_tokens: int = 5000,
        system_prompt: Optional[str] = None
    ) -> str:
        """Generate text using Gemini model"""
        full_prompt = f"{system_prompt}\n\n{prompt}" if system_prompt else prompt
        resp = self.client.models.generate_content(
                model=self.model_name,
                contents=[full_prompt],
            config=GenerateContentConfig(
                    temperature=temperature,
                    max_output_tokens=max_tokens,
                )
            )
        if not getattr(resp, "text", None):
            logger.error("Empty response from Gemini API: %r", resp)
            raise ValueError("Received empty response from Gemini API")
        return resp.text

    async def generate_structured_response(
        self,
        prompt: str,
        response_schema: Type[BaseModel],
        temperature: float = 0.3,
        max_tokens: int = 5000,
        system_prompt: Optional[str] = None
    ) -> BaseModel:
        """Generate structured response using a Pydantic schema"""
        schema_json = response_schema.model_json_schema()
        instructions = (
            "IMPORTANT: Respond with ONLY a valid JSON object that matches this schema. "
            "Do not include any prose or markdown.\n\n"
            f"{schema_json}"
        )
        full_prompt = "\n\n".join(filter(None, [system_prompt, prompt, instructions]))
        resp = self.client.models.generate_content(
            model=self.model_name,
            contents=[full_prompt],
            config=GenerateContentConfig(
                temperature=temperature,
                max_output_tokens=max_tokens,
            )
        )
        text = resp.text or ""
        # strip markdown code fences if present
        if text.strip().startswith("```"):
            text = text.strip().strip("```json").strip("```").strip()
        # attempt to grab last JSON object
        if text.count("{") > 1:
            objs, cur, depth = [], "", 0
            for c in text:
                cur += c
                if c == "{": depth += 1
                if c == "}":
                    depth -= 1
                    if depth == 0:
                        objs.append(cur)
                        cur = ""
            if objs:
                text = objs[-1]
        # close dangling braces
        if text.count("{") > text.count("}"):
            text += "}"
        try:
            data = json.loads(text)
            return response_schema.model_validate(data)
        except Exception as e:
            logger.error("Failed to parse/validate JSON response: %s\nRaw: %s", e, text)
            raise

    def analyze_image(
        self,
        image_bytes: bytes,
        prompt: str,
        temperature: float = 0.3,
        max_tokens: int = 500,  # Reduced from 1000 for faster responses
        system_prompt: Optional[str] = None
    ) -> str:
        """Analyze an image with Gemini Vision and return the response text."""
        try:
            # Use the correct google-genai SDK method for vision
            contents = []

            # Add system prompt if provided
            if system_prompt:
                contents.append(Part(text=system_prompt))

            # Add the image data
            contents.append(Part(inline_data={
                "mime_type": "image/jpeg",  # Assuming JPEG, could be PNG
                "data": image_bytes
            }))

            # Add the user prompt
            contents.append(Part(text=prompt))

            # Generate content using the client
            resp = self.client.models.generate_content(
                model="gemini-1.5-pro",  # Use the standard model, not vision-specific
                contents=contents,
                config=GenerateContentConfig(
                    temperature=temperature,
                    max_output_tokens=max_tokens,
                )
            )

            if not getattr(resp, "text", None):
                logger.error("Empty response from Gemini Vision: %r", resp)
                raise ValueError("Received empty response from Gemini Vision API")

            return resp.text

        except Exception as e:
            logger.error(f"Error in analyze_image: {e}")
            raise ValueError(f"Gemini Vision analysis failed: {e}")

    async def analyze_audio(
        self,
        audio_bytes: bytes,
        prompt: str,
        temperature: float = 0.3,
        max_tokens: int = 1000,
        system_prompt: Optional[str] = None
    ) -> str:
        """
        Analyze an audio clip using Gemini Live API in multimodal mode.
        Returns the model's text response once the turn completes.
        """
        # we spin up a live session with TEXT responses
        config = LiveConnectConfig(
            response_modalities=["TEXT"],
            temperature=temperature,
        )
        # if you wanted TTS output, add response_modalities=["AUDIO"] + SpeechConfig(...)
        async with self.client.aio.live.connect(
            model=f"{self.model_name}-live-preview",
            config=config
        ) as session:
            # first send any system instructions
            if system_prompt:
                await session.send_client_content(
                    turns=Content(role="system", parts=[Part(text=system_prompt)])
                )
            # then send your audio + prompt
            await session.send_client_content(
                turns=Content(
                    role="user",
                    parts=[
                        Part(inline_data={"mime_type": "audio/wav", "data": audio_bytes}),
                        Part(text=prompt),
                    ]
                )
            )
            # collect until turn_complete
            pieces = []
            async for msg in session.receive():
                if msg.text:
                    pieces.append(msg.text)
                if getattr(msg.server_content, "turn_complete", False):
                    break
            return "".join(pieces)

    async def analyze_audio_file(
        self,
        path: str,
        prompt: str,
        **kwargs
    ) -> str:
        """Convenience: read from disk then call analyze_audio."""
        with open(path, "rb") as f:
            b = f.read()
        return await self.analyze_audio(b, prompt, **kwargs)


# module‐level helpers

gemini_client: Optional[GeminiAIClient] = None

def get_gemini_client() -> GeminiAIClient:
    global gemini_client
    if gemini_client is None:
        gemini_client = GeminiAIClient()
    return gemini_client
