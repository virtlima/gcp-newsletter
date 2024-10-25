import feedparser
import json
import datetime
import ssl
import os
from dotenv import load_dotenv

import vertexai
from vertexai.generative_models import GenerativeModel

load_dotenv()
PROJECT_ID = os.getenv("PROJECT_ID")


vertexai.init(project=PROJECT_ID, location="us-central1")
model = GenerativeModel("gemini-1.5-flash-002")

USER_PERSONA = ["CXO","Dev"]
USER_INDUSTRY = ["Financial","Retail"]

# Define the RSS feed URL - "https://blog.google/products/google-cloud/rss/"
rss_url = "https://snownews.appspot.com/feed"

# Parse the RSS feed
ssl._create_default_https_context = ssl._create_unverified_context
feed = feedparser.parse(rss_url)
print(feed)

# Extract the last week's entries
last_week_entries = []
for entry in feed.entries:
    # Check if the entry was published within the last week
    published_date = datetime.datetime(*entry.published_parsed[:6])
    if published_date.isocalendar().week == datetime.datetime.now().isocalendar().week:
        last_week_entries.append({
            "title": entry.title,
            "link": entry.link,
            "published": entry.published,
            "summary": entry.summary,
        })

with open(f"last_week_entries.json", "w") as f:
    json.dump(last_week_entries, f)

# Create a list to store the summaries
summaries = []

# Iterate over the last week's entries and generate summaries
for entry in last_week_entries:
    # Construct the prompt for the generative model
    summary_prompt = f"""
    Provide a very short summary, no more than three sentences, for this article:
    Title: {entry['title']}
    Link: {entry['link']}
    Summary: {entry['summary']}
    """

    # Generate the summary using the generative model
    summary_response = model.generate_content(contents=summary_prompt).text

    # Append the summary to the list
    summaries.append({
        "title": entry['title'],
        "link": entry['link'],
        "summary": summary_response,
    })

# Create a recommendation from the summaries
rec_prompt = f"""
Based on the user industry and persona, recommend three articles from the list of summmaries provided.
User Industry: {USER_INDUSTRY[1]}
User Persona: {USER_PERSONA[0]}

{summaries}

Include the user_industry and user_persona in the output json.
Include recommendation_reason, recommendation_title, recommendation_link, and recommendation_summary in the output json within a list object called 'recommendations'.
Include a summary_text for why you recommended these articles in the output json. If there weren't any recommendations then explain why.
"""

rec_response = model.generate_content(contents=rec_prompt,
                                      generation_config={"response_mime_type":"application/json"}
                                      ).text

with open(f"summaries.json", "w") as f:
    json.dump(summaries, f)

# Convert the summaries to JSON format
summary_json = json.dumps(summaries)

# Convert output of rec response
# NOTE: should create checks in case LLM doesn't respond in JSON format
is_json = True
try:
  rec_json = json.loads(rec_response)
except json.JSONDecodeError as e:
  print(f"Invalid JSON string: {e}")
  is_json = False

# Print the JSON data
print(summary_json)

# Format output
newsletter = f"""\n
Hi!

Recs: {rec_json['summary_text']}
"""
print(newsletter)
