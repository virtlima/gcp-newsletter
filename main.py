import feedparser
import json
import datetime
import ssl

import vertexai
from vertexai.generative_models import GenerativeModel

vertexai.init(project="myproject", location="us-central1")
model = GenerativeModel("gemini-1.5-flash-002")

# Define the RSS feed URL
rss_url = "https://blog.google/products/google-cloud/rss/"

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
    prompt = f"""
    Provide a very short summary, no more than three sentences, for this article:
    Title: {entry['title']}
    Link: {entry['link']}
    Summary: {entry['summary']}
    """

    # Generate the summary using the generative model
    response = model.generate_content(contents=prompt).text

    # Append the summary to the list
    summaries.append({
        "title": entry['title'],
        "link": entry['link'],
        "summary": response,
    })

with open(f"summaries.json", "w") as f:
    json.dump(summaries, f)

# Convert the summaries to JSON format
json_data = json.dumps(summaries)

# Print the JSON data
print(json_data)