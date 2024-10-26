"""
Makes direct calls to the Gemini API.

Used for summarization, recommendation purposes.
"""
import vertexai, os, json, gemini
from vertexai.generative_models import GenerativeModel



# IN: RSS feed from last week
# OUT: List of Summarized articles with title,
#      link and summary
def generate_summaries(last_week_entries):
  """
  Generate a short summary for each articles.
  Must have access to article content otherwise the
  model will hallucinate summaries. We use Grounding
  with Google Search here.

  Arguments:
    - last_week_entries (list): list of title, link, and
      metadata provided by RSS feed

  Returns:
    - summaries (list): title, link, and generated summary
  """

  # Create a list to store the summaries
  summaries = []

  # Iterate over the last week's entries and generate summaries
  # TODO: For testing, restricting this to 5 entries
  for entry in last_week_entries[:5]:
      # Construct the prompt for the generative model
      summary_prompt = f"""
      Provide a very short summary, no more than three sentences, for this article:
      Title: {entry['title']}
      Link: {entry['link']}
      Metadata: {entry['metadata']}
      To generate the summary you must only include contents found at the corresponding link provided.
      """

      # Generate the summary using the generative model
      summary_response = gemini.generate(summary_prompt,
                                         gwgs = True)

      # Append the summary to the list
      summaries.append({
          "title": entry['title'],
          "link": entry['link'],
          "summary": summary_response.text,
      })

  return summaries

def generate_recommendation(user_industry, user_persona, summaries):
  """
  Makes a call to Gemini to get recommendations based on an audience group.

  Arguments:
    - user_industry (string): what industry vertical is the audience interested in
    - user_persona (string): what level of business/technical depth do they require

  Return:
    - rec_json (JSON): JSON object containing
  """

  # Create a recommendation from the summaries
  rec_prompt = f"""
  Based on the user industry and persona, recommend at most three articles from the list of summmaries provided.
  User Industry: {user_industry}
  User Persona: {user_persona}

  {summaries}

  Include the user_industry and user_persona in the output json.
  Include recommendation_reason, recommendation_title, recommendation_link, and recommendation_summary in the output json within a list object called 'recommendations'.
  Include a summary_text for why you recommended these articles in the output json. If there weren't any recommendations then explain why.
  """

  # Make the call to the model. Enforce JSON output.
  rec_response = gemini.generate(prompt = rec_prompt,
                                 gwgs = False,
                                 json_on = True)

  # Convert output of rec response
  # NOTE: should create checks in case LLM doesn't respond in JSON format
  is_json = True
  try:
    rec_json = json.loads(rec_response.text)
  except json.JSONDecodeError as e:
    print(f"Invalid JSON string: {e}")
    is_json = False

  if is_json:
    return rec_json
  else:
    return "Invalid JSON"
