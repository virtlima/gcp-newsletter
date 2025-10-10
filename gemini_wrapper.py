"""
Makes direct calls to the Gemini API.

Used for summarization, recommendation purposes.
"""
import json, gemini

# IN: RSS feed from last week
# OUT: List of Summarized articles with title,
#      link and summary
def generate_summaries(entries):
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

  # Construct the prompt for the generative model to process all entries at once
  articles_to_summarize = "\n".join(
      [f"- Title: {entry['title']}, Link: {entry['link']}" for entry in entries]
  )

  summary_prompt = f"""
  For each of the following articles, provide a very short summary of no more than three sentences.
  You must only include contents found at the corresponding link provided for each article.
  Return a JSON object with a key "summaries" which is a list of objects.
  Each object in the list should contain "title", "link", and "summary".
  The order of the summaries in the list must match the order of the articles provided.

  Articles:
  {articles_to_summarize}
  """

  # Generate the summary using the generative model
  summary_response = gemini.generate(summary_prompt, json_on=True)

  try:
    # The model should return a JSON object with a "summaries" key
    response_data = json.loads(summary_response.text)
    return response_data.get("summaries", [])
  except (json.JSONDecodeError, AttributeError) as e:
    print(f"Error decoding summaries JSON from model: {e}")
    # Fallback to creating summaries without the generated text
    return [{
        "title": entry['title'],
        "link": entry['link'],
        "summary": "Summary could not be generated."
    } for entry in entries]

def generate_recommendation(user_topic, user_persona, summaries):
  """
  Makes a call to Gemini to get recommendations based on an audience group.

  Arguments:
    - user_topic (string): what industry vertical is the audience interested in
    - user_persona (string): what level of business/technical depth do they require

  Return:
    - rec_json (JSON): JSON object containing
  """

  # Create a recommendation from the summaries
  rec_prompt = f"""
  Based on the user industry and persona, recommend at most three articles from the list of summmaries provided.
  User Industry: {user_topic}
  User Persona: {user_persona}

  {summaries}

  Include the user_topic and user_persona in the output json.
  Include recommendation_reason, recommendation_title, recommendation_link, and recommendation_summary in the output json within a list object called 'recommendations'.
  Include a summary_text for why you recommended these articles in the output json. If there weren't any recommendations then explain why.
  """

  # Make the call to the model. Enforce JSON output.
  rec_response = gemini.generate(prompt=rec_prompt,
                                 json_on=True)

  # Convert output of rec response
  try:
    rec_json = json.loads(rec_response.text)
    return rec_json
  except json.JSONDecodeError as e:
    print(f"Invalid JSON string: {e}")
    # Return a structured error object instead of a plain string
    return {
        "user_topic": user_topic,
        "user_persona": user_persona,
        "summary_text": "Could not generate recommendations due to an error.",
        "recommendations": []
    }
