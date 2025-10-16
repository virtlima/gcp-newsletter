"""
Makes direct calls to the Gemini API.

Used for summarization, recommendation purposes.
"""
import json
import logging
from typing import List, Dict, Any, Optional
import gemini

logger = logging.getLogger(__name__)

# --- Prompt Templates ---

SUMMARY_PROMPT_TEMPLATE = """
For each of the following articles, provide a very short summary of no more than three sentences.
You must only include contents found at the corresponding link provided for each article.

Your response must be a single, strictly valid JSON object and nothing else.
The JSON object must have a single key "summaries", which is a list of objects.
Each object in the list must contain "title", "link", and "summary" keys.
The order of the summaries in the list must match the order of the articles provided.
IMPORTANT: Ensure the JSON is well-formed. Do not use trailing commas.

Articles:
{articles_to_summarize}
"""

RECOMMENDATION_PROMPT_TEMPLATE = """
Based on the user industry and persona, recommend at most three articles from the list of summaries provided below.
User Industry: {user_topic}
User Persona: {user_persona}

Summaries:
{summaries}

Your response must be a single, strictly valid JSON object and nothing else. Do not include any text before or after the JSON object.
The JSON object must have the following structure:
- "user_topic": The user's topic.
- "user_persona": The user's persona.
- "recommendations": A list of recommended articles. Each item in the list must be an object with "recommendation_title", "recommendation_link", and "recommendation_summary" keys.
- "summary_text": A string explaining the recommendations. If no articles are recommended, explain why.

IMPORTANT: Ensure the JSON is well-formed. Do not use trailing commas in lists or objects.
"""

def _parse_json_response(response: Optional[Any], default_value: Optional[Dict] = None) -> Dict:
    """
    Safely parses a JSON string from a model response object.

    Args:
        response: The response object from the gemini.generate call.
        default_value: The value to return if parsing fails.

    Returns:
        The parsed JSON object or the default_value.
    """
    if default_value is None:
        default_value = {}

    try:
        if response and response.text:
            parsed_json = json.loads(response.text)
            if isinstance(parsed_json, dict):
                return parsed_json
            logger.warning(f"Parsed JSON is not a dictionary: {type(parsed_json)}")
            return default_value
        logger.warning("JSON parsing failed: Response or response.text is empty.")
        return default_value
    except json.JSONDecodeError as e:
        logger.error(f"JSON decoding failed: {e}. Raw response: '{response.text if response else 'N/A'}'", exc_info=True)
        return default_value
    except Exception as e:
        logger.error(f"An unexpected error occurred during JSON parsing: {e}", exc_info=True)
        return default_value

# IN: RSS feed from last week
# OUT: List of Summarized articles with title,
#      link and summary
def generate_summaries(entries: List[Dict[str, str]]) -> List[Dict[str, str]]:
  """
  Generate a short summary for each articles.
  Must have access to article content otherwise the
  model will hallucinate summaries. We use Grounding
  with Google Search here.

  Arguments:
    - entries (list): list of title, link, and
      metadata provided by RSS feed

  Returns:
    - summaries (list): title, link, and generated summary
  """

  if not entries:
    logger.info("No entries provided to generate_summaries. Returning empty list.")
    return []

  # Construct the prompt for the generative model to process all entries at once
  articles_to_summarize = "\n".join(
      [f"- Title: {entry['title']}, Link: {entry['link']}" for entry in entries]
  )

  summary_prompt = SUMMARY_PROMPT_TEMPLATE.format(articles_to_summarize=articles_to_summarize)

  try:
    # Generate the summary using the generative model
    logger.info(f"Generating summaries for {len(entries)} articles.")
    summary_response = gemini.generate(summary_prompt, json_on=True)
    response_data = _parse_json_response(summary_response)
    summaries = response_data.get("summaries", [])
    if not summaries:
        logger.warning("Model did not return a 'summaries' list or the list was empty.")
    return summaries
  except Exception as e:
    logger.error(f"Failed to generate summaries due to an API or processing error: {e}", exc_info=True)
    # Fallback to creating summaries with an error message
    return [{"title": entry['title'], "link": entry['link'], "summary": "Error: Summary could not be generated."} for entry in entries]


def generate_recommendation(user_topic: str, user_persona: str, summaries: List[Dict[str, str]]) -> Dict[str, Any]:
  """
  Makes a call to Gemini to get recommendations based on an audience group.

  Arguments:
    - user_topic (string): what industry vertical is the audience interested in
    - user_persona (string): what level of business/technical depth do they require

  Return:
    - rec_json (JSON): JSON object containing
  """

  if not summaries:
    logger.warning("No summaries provided to generate_recommendation. Returning structured error.")
    return {
        "user_topic": user_topic,
        "user_persona": user_persona,
        "summary_text": "Could not generate recommendations because no article summaries were provided.",
        "recommendations": []
    }

  # Format summaries into a clean, readable block for the prompt
  summaries_text = "\n\n".join(
      [f"Title: {s['title']}\nLink: {s['link']}\nSummary: {s['summary']}" for s in summaries]
  )
  rec_prompt = RECOMMENDATION_PROMPT_TEMPLATE.format(user_topic=user_topic, user_persona=user_persona, summaries=summaries_text)

  try:
    # Make the call to the model. Enforce JSON output.
    logger.info(f"Generating recommendations for persona '{user_persona}' and topic '{user_topic}'.")
    rec_response = gemini.generate(prompt=rec_prompt, json_on=True)
    rec_json = _parse_json_response(rec_response)
    if not rec_json:
        raise ValueError("Parsed JSON response is empty.")
    return rec_json
  except Exception as e:
    logger.error(f"Failed to generate recommendations due to an API or processing error: {e}", exc_info=True)
    # Return a structured error object instead of a plain string
    return {
        "user_topic": user_topic,
        "user_persona": user_persona,
        "summary_text": "Could not generate recommendations due to an error.",
        "recommendations": []
    }
