import feedparser
import firebase_admin
from firebase_admin import credentials, firestore
import datetime
import ssl
import sys
import os
from dotenv import load_dotenv

# Get the absolute path of the current file
current_file_path = os.path.abspath(__file__)

# Get the directory containing the current file
current_dir = os.path.dirname(current_file_path)

# Get the parent directory
parent_dir = os.path.dirname(current_dir)

# Add the parent directory to sys.path
sys.path.insert(0, parent_dir)

# Now you can import the module
import gemini_wrapper


load_dotenv()
# Initialize Firestore
cred = credentials.ApplicationDefault()
firebase_admin.initialize_app(cred)
db = firestore.client()
"""
Function to generate a newsletter from RSS feed.

Arguments:
  - source (string): rss_url source - GCP blog feed by default
  - time_period (string): either "day" or "week"
  - user_topic (string): what topic is the user interested in (retail, finance, ai/ml, data, etc.)
  - user_persona (string): what persona is the user (cxo, dev, ce, etc.)

Response:
  - newsletter (string): formatted newsletter with recommendation and all article summaries
"""
# Getting all personas and topics stored in settings document in the newsletter_components collection
settings_ref = db.collection('gcp_newsletter').document('settings')
settings_get = settings_ref.get()
settings = settings_get.to_dict()

get_persona = settings['persona']
get_topic = settings['topic']

# Create a matrix to iterate through every combination of persona and topics
persona_topic_matrix = [(p, t) for p in get_persona for t in get_topic]

def get_newsletter_from_sources(source="https://snownews.appspot.com/feed",
                                time_period="day"):

    # Parse the RSS feed
    ssl._create_default_https_context = ssl._create_unverified_context
    feed = feedparser.parse(source)

    entries = []

    # Extract the entries depending on time period specified
    if time_period.lower() == "day":
        for entry in feed.entries:
            # Check if the entry was published within the last week
            published_date = datetime.datetime(*entry.published_parsed[:6])
            yesterday = datetime.date.today() - datetime.timedelta(days=1)
            if published_date.date() == yesterday:
                entries.append({
                    "title": entry.title,
                    "link": entry.link,
                    "published": entry.published,
                    "metadata": entry.summary,
                })
    elif time_period.lower() == "week":
        for entry in feed.entries:
            # Check if the entry was published within the last week
            published_date = datetime.datetime(*entry.published_parsed[:6])
            if published_date.isocalendar().week == datetime.datetime.now(
            ).isocalendar().week:
                entries.append({
                    "title": entry.title,
                    "link": entry.link,
                    "published": entry.published,
                    "metadata": entry.summary,
                })
    else:
        print("Please define time period")

    print(len(entries))

    # Generate summaries
    summaries = gemini_wrapper.generate_summaries(entries)

    day_summaries = {
        'summaries': summaries,
        'timestamp': datetime.datetime.now()
        }

    # Write summaries to firestore
    yesterday = datetime.date.today() - datetime.timedelta(days=1)
    yesterday_str = yesterday.strftime("%m_%d_%Y")
    sum_doc_ref = db.collection('newsletter_summaries').document(f"{yesterday_str}")
    sum_doc_ref.set(day_summaries)
    print(f"Data written to Firestore with ID: {sum_doc_ref.id}")


    # Create a dictionary to store recommendations for all persona-topic combinations
    all_recommendations = {}

    # Grabbing Summaries from Firestore
    sum_ref = db.collection('newsletter_summaries').document(sum_doc_ref.id)
    sum_get = sum_ref.get()
    sum = sum_get.to_dict()
    get_sum = sum['summaries']

    for persona, topic in persona_topic_matrix:
        print(f"Processing persona: {persona}, topic: {topic}")
        rec_json = gemini_wrapper.generate_recommendation(
            user_topic=topic, user_persona=persona, summaries=get_sum)
        
        # Store recommendations under the corresponding persona-topic key
        all_recommendations[f"{persona}_{topic}"] = rec_json

    all_recommendations['timestamp'] = datetime.datetime.now()

    # Write all recommendations to a single document in Firestore
    rec_doc_ref = db.collection('newsletter_recommendations').document(f"{yesterday_str}")
    rec_doc_ref.set(all_recommendations)
    print(f"Data written to Firestore with ID: {rec_doc_ref.id}")

if __name__ == "__main__":
    get_newsletter_from_sources() # This will run when the script is executed
    # generate_newsletter_from_db(wr_summaries, wr_rec)
    # send_email_test() # Call other functions if needed