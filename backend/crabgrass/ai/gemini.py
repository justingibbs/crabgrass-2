"""Gemini AI client wrapper."""

import google.generativeai as genai
import structlog

from ..config import settings

logger = structlog.get_logger()

# Configure the Gemini client
genai.configure(api_key=settings.google_api_key)

# Default model for agents
DEFAULT_MODEL = "gemini-2.0-flash"


def get_model(model_name: str = DEFAULT_MODEL) -> genai.GenerativeModel:
    """Get a Gemini generative model instance."""
    return genai.GenerativeModel(model_name)


async def generate_content(
    prompt: str,
    system_instruction: str | None = None,
    model_name: str = DEFAULT_MODEL,
) -> str:
    """
    Generate content using Gemini.

    Args:
        prompt: The user prompt/message
        system_instruction: Optional system instruction for the model
        model_name: Model to use (default: gemini-2.0-flash)

    Returns:
        Generated text response
    """
    model = genai.GenerativeModel(
        model_name,
        system_instruction=system_instruction,
    )

    try:
        response = await model.generate_content_async(prompt)
        return response.text
    except Exception as e:
        logger.error("gemini_error", error=str(e))
        raise


async def generate_json(
    prompt: str,
    system_instruction: str | None = None,
    model_name: str = DEFAULT_MODEL,
) -> dict:
    """
    Generate JSON content using Gemini.

    Args:
        prompt: The user prompt/message
        system_instruction: Optional system instruction for the model
        model_name: Model to use (default: gemini-2.0-flash)

    Returns:
        Parsed JSON response as dict
    """
    import json

    model = genai.GenerativeModel(
        model_name,
        system_instruction=system_instruction,
        generation_config={"response_mime_type": "application/json"},
    )

    try:
        response = await model.generate_content_async(prompt)
        return json.loads(response.text)
    except json.JSONDecodeError as e:
        logger.error("gemini_json_parse_error", error=str(e), response=response.text)
        raise
    except Exception as e:
        logger.error("gemini_error", error=str(e))
        raise


async def chat_with_history(
    messages: list[dict],
    system_instruction: str | None = None,
    model_name: str = DEFAULT_MODEL,
) -> str:
    """
    Generate a response with conversation history.

    Args:
        messages: List of message dicts with 'role' and 'content' keys
                  role should be 'user' or 'model'
        system_instruction: Optional system instruction
        model_name: Model to use

    Returns:
        Generated text response
    """
    model = genai.GenerativeModel(
        model_name,
        system_instruction=system_instruction,
    )

    # Convert messages to Gemini format
    history = []
    for msg in messages[:-1]:  # All but the last message go in history
        role = "model" if msg["role"] == "agent" else msg["role"]
        history.append({"role": role, "parts": [msg["content"]]})

    chat = model.start_chat(history=history)

    # Send the last message
    last_message = messages[-1]["content"] if messages else ""

    try:
        response = await chat.send_message_async(last_message)
        return response.text
    except Exception as e:
        logger.error("gemini_chat_error", error=str(e))
        raise
