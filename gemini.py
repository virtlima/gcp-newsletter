"""
A robust client for making generative content calls to the Google Gemini API via Vertex AI.

This module handles client initialization, error handling, and provides a configurable
interface for content generation.
"""

import os
import logging
from google import genai
from google.genai import types
import google.auth
from typing import Optional, Union

logger = logging.getLogger(__name__)

# --- Configuration ---
credentials, project_id = google.auth.default()
PROJECT_ID = project_id
LOCATION = 'us-central1'
MODEL_NAME = 'gemini-2.5-flash' # Updated to a more recent model
MAX_OUTPUT_TOKENS = 8192

# Define safety settings to block harmful content.
# Set to BLOCK_NONE for minimal filtering, but be aware of the implications.
SAFETY_SETTINGS = {
    types.HarmCategory.HARM_CATEGORY_HARASSMENT: types.HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
    types.HarmCategory.HARM_CATEGORY_HATE_SPEECH: types.HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
    types.HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: types.HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
    types.HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: types.HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
}


# --- Client Initialization ---
if not PROJECT_ID:
    raise ValueError("GOOGLE_CLOUD_PROJECT environment variable not set.")

try:
    genai_client = genai.Client(vertexai=True, project=PROJECT_ID, location=LOCATION)
    logger.info(f"Successfully initialized Gemini client for project '{PROJECT_ID}' in '{LOCATION}'.")
except Exception as e:
    logger.critical(f"Failed to initialize Gemini client: {e}", exc_info=True)
    # Re-raise the exception to prevent the application from starting in a broken state.
    raise

def generate(prompt: str, temp: float = 0.2, json_on: bool = False) -> Optional[types.GenerateContentResponse]:
    """
    Generates content using the configured Gemini model.

    Args:
        prompt: The text prompt to send to the model.
        temp: The temperature for generation (creativity). Defaults to 0.2.
        json_on: If True, sets the response MIME type to 'application/json'.

    Returns:
        A GenerateContentResponse object on success, or None on failure.
    """
    try:
        response = genai_client.models.generate_content(
            model=MODEL_NAME,
            contents=prompt,
            config=types.GenerateContentConfig(
                max_output_tokens=MAX_OUTPUT_TOKENS,
                temperature=temp,
                response_mime_type="application/json" if json_on else "text/plain",
            )
        )
        return response
    except Exception as e:
        logger.error(f"Error during Gemini content generation: {e}", exc_info=True)
        return None
