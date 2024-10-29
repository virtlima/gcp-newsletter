import feedparser
import json
import datetime
import ssl
import gemini_wrapper, email_service
import os
from dotenv import load_dotenv

load_dotenv()

sender_email = os.environ.get("SENDER_EMAIL")
sender_password = os.environ.get("SENDER_PASSWORD") # Make gmail app password from here:https://support.google.com/accounts/answer/185833?visit_id=638655613103411169-2477840836&p=InvalidSecondFactor&rd=1

USER_PERSONA = ["CXO","Dev"]
USER_INDUSTRY = ["Financial","Retail"]

# Define the RSS feed URL - "https://blog.google/products/google-cloud/rss/"
rss_url = "https://snownews.appspot.com/feed"

# Parse the RSS feed
ssl._create_default_https_context = ssl._create_unverified_context
feed = feedparser.parse(rss_url)

# Extract the last week's entries
last_day_entries = []
for entry in feed.entries:
    # Check if the entry was published within the last week
    published_date = datetime.datetime(*entry.published_parsed[:6])
    if published_date.date() == datetime.datetime.now().date():
        last_day_entries.append({
            "title": entry.title,
            "link": entry.link,
            "published": entry.published,
            "metadata": entry.summary,
        })

print(len(last_day_entries))

# Write last week entries to output file
with open(f"data/last_day_entries.json", "w") as f:
    json.dump(last_day_entries, f)

# Generate summaries
summaries = gemini_wrapper.generate_summaries(last_day_entries)

# Write summaries to output file
with open(f"data/summaries.json", "w") as f:
    json.dump(summaries, f)

# Generate recommendations
rec_json = gemini_wrapper.generate_recommendation(USER_INDUSTRY[0],
                                                USER_PERSONA[0],
                                                summaries)

# Write recs to output file
with open(f"data/recommended_articles.json", "w") as f:
    json.dump(rec_json, f)

# Format output
newsletter = f"""\n
Hi!

Recs: {rec_json['summary_text']}

""" + "\n".join([f"{i+1}. {item['recommendation_title']}\n\t\
                 Summary: {item['recommendation_summary']}\n\t\
                 Reason: {item['recommendation_reason']}\n\t\
                 Link: {item['recommendation_link']}"
                 for i, item in enumerate(rec_json["recommendations"])]) + "\n"

print(newsletter)

# Send the email
email_service.send_email(
    sender_email,
    sender_password,
    'lukasgeiger@google.com',
    'GCP Newsletter',
    newsletter
)
