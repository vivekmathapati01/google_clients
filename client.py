import logging
import requests
import json
import base64
import os  # Added for test block
from commons.llm_config.constants import Constants
from skills.aura_workflows.utils.logging_config import setup_colored_logging

setup_colored_logging()
logger = logging.getLogger(__name__)

# --- Constants from your setup ---
API_KEY = Constants.GOOGLE_GENAI_API_KEY
PROJECT_ID = Constants.GOOGLE_GENAI_PROJECT_ID
LOCATION = Constants.GOOGLE_GENAI_LOCATION
MODEL_ID = Constants.GOOGLE_GENAI_MODELS["veo-2.0"]
PROMPT = "A serene sunset over mountains with clouds moving slowly across the sky"
# We'll get the base URL template directly from Constants inside the function


def generate(prompt: str, model_id: str = None, aspect_ratio: str = "16:9", duration: str = "5s", data: dict = None) -> bytes | None:
    """Generates a video using the Veo REST API with an API key.

    Args:
        prompt: The text prompt for video generation
        model_id: The model ID to use (defaults to veo-2.0 from Constants)
        aspect_ratio: The aspect ratio for the video (default: "16:9")
        duration: The duration of the video (default: "5s", options: "5s", "10s")
        data: Optional custom request body to override defaults

    Returns:
        The generated video data as bytes, or None if generation failed.
    """
    if model_id is None:
        model_id = MODEL_ID

    # --- FIX 1: URL Construction ---
    # Get the template from Constants each time to avoid side-effects
    base_url_template = Constants.GOOGLE_GENAI_BASE_URL
    base_url = base_url_template.replace("{LOCATION}", LOCATION)
    url = f"{base_url}/{PROJECT_ID}/locations/{LOCATION}/publishers/google/models/{model_id}:predict?key={API_KEY}"

    headers = {
        "Content-Type": "application/json"
    }

    # The request body structure for the Veo model
    if data is None:
        data = {
            "instances": [
                {
                    "prompt": prompt
                }
            ],
            "parameters": {
                "sampleCount": 1,
                "aspectRatio": aspect_ratio,
                "duration": duration,
                "outputMimeType": "video/mp4"
            }
        }

    # Make the POST request
    logger.info(f"Sending video generation request for prompt: '{prompt[:100]}...'")
    logger.info(f"Video parameters: aspect_ratio={aspect_ratio}, duration={duration}")
    response = None
    
    try:
        response = requests.post(url, headers=headers, json=data)
        response.raise_for_status()  # Raise an exception for bad status codes (4XX or 5XX)

        # --- FIX 2: Handle the successful response ---
        response_data = response.json()

        # Extract the video data
        if 'predictions' not in response_data or not response_data['predictions']:
            logger.error("API response missing 'predictions' key or list is empty.")
            logger.debug(f"Full response: {response.text}")
            return None
        
        prediction = response_data['predictions'][0]
        if 'bytesB64Encoded' not in prediction:
            logger.error("Prediction object missing 'bytesB64Encoded' key.")
            logger.debug(f"Full response: {response.text}")
            return None

        # Decode the base64 string to bytes
        b64_video = prediction['bytesB64Encoded']
        video_bytes = base64.b64decode(b64_video)
        
        logger.info(f"Successfully generated video, {len(video_bytes)} bytes.")
        return video_bytes

    except requests.exceptions.RequestException as e:
        logger.error(f"An HTTP error occurred during the API call: {e}")
        if response is not None:
            logger.error(f"Response status code: {response.status_code}")
            logger.error(f"Response content: {response.text}")
        return None
    except (json.JSONDecodeError, KeyError, IndexError, base64.binascii.Error) as e:
        # Handle errors in parsing the successful response
        logger.error(f"Failed to parse or decode successful API response: {e}")
        if response is not None:
            logger.error(f"Response content that caused parse error: {response.text}")
        return None
    except Exception as e:
        # Catch any other unexpected errors
        logger.error(f"An unexpected error occurred: {e}", exc_info=True)
        return None

# --- Added for testing ---
if __name__ == "__main__":
    """
    This block allows you to run this python file directly to test
    the generate() function.
    
    Example:
    python your_video_client_file.py
    """
    
    # Simple logging setup if not already configured by setup_colored_logging
    if not logger.hasHandlers():
        logging.basicConfig(level=logging.INFO, 
                            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    logger.info("--- Running test video generation ---")
    
    # NOTE: Ensure your Constants (API_KEY, etc.) are valid
    video_data = generate(prompt=PROMPT, duration="5s")
    
    if video_data:
        output_filename = "test_video.mp4"
        try:
            with open(output_filename, "wb") as f:
                f.write(video_data)
            logger.info(f"--- Test video successfully saved to {os.path.abspath(output_filename)} ---")
        except IOError as e:
            logger.error(f"Failed to save video file: {e}")
    else:
        logger.error("--- Test video generation failed ---")
