import feedparser
import datetime
import ssl
import gemini_wrapper, email_service, db_service
import os
from jinja2 import Environment, FileSystemLoader

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
get_persona = db_service.get_components_from_firestore(
    'gcp_newsletter', 'settings')['settings']['persona']
get_topic = db_service.get_components_from_firestore(
    'gcp_newsletter', 'settings')['settings']['topic']

# Create a matrix to iterate through every combination of persona and topics
persona_topic_matrix = [(p, t) for p in get_persona for t in get_topic]


def get_newsletter_from_sources(source="https://snownews.appspot.com/feed",
                                num_days=1):

    # Parse the RSS feed
    ssl._create_default_https_context = ssl._create_unverified_context
    feed = feedparser.parse(source)

    entries = []

    # Extract the entries depending on time period specified
    for entry in feed.entries:
        # Check if the entry was published within the last week
        published_date = datetime.datetime(*entry.published_parsed[:6])
        time_period = datetime.date.today() - datetime.timedelta(days=num_days)
        if published_date.date() == time_period:
            entries.append({
                "title": entry.title,
                "link": entry.link,
                "published": entry.published,
                "metadata": entry.summary,
            })

    print(len(entries))

    if not entries:
        return "No articles found for that day"
    
    # Generate summaries
    summaries_list = gemini_wrapper.generate_summaries(entries)
    
    day_summaries = {
        'summaries': summaries_list,
        'timestamp': datetime.datetime.now()
    }

    # Write summaries to firestore
    db_service.write_to_firestore('newsletter_summaries',
                                                 day_summaries, num_days=num_days)

    # Create a dictionary to store recommendations for all persona-topic combinations
    all_recommendations = {}

    for persona, topic in persona_topic_matrix:
        print(f"Processing persona: {persona}, topic: {topic}")
        rec_json = gemini_wrapper.generate_recommendation(user_topic=topic,
                                                          user_persona=persona,
                                                          summaries=summaries_list)

        # Store recommendations under the corresponding persona-topic key
        all_recommendations[f"{persona}_{topic}"] = rec_json

    all_recommendations['timestamp'] = datetime.datetime.now()

    # Write all recommendations to a single document in Firestore
    db_service.write_to_firestore('newsletter_recommendations',
                                       all_recommendations, num_days=num_days)

def _render_newsletter_html(summaries, recommendations, user_persona, user_topic):
    """Helper function to render the newsletter HTML."""
    if not summaries or not recommendations:
        return "No articles found for the selected period."

    # Get the list of dates and format them for Jinja Template
    date_list = []
    # Sort keys to ensure chronological order
    sorted_dates = sorted(recommendations.keys())
    for date in sorted_dates:
        try:
            temp_date = datetime.datetime.strptime(date, "%m_%d_%Y")
            formatted_date = temp_date.strftime("%B %d, %Y")
            date_list.append(formatted_date)
        except ValueError:
            continue # Skip keys that are not dates, like 'timestamp'

    # Format output through Jinja2 template
    env = Environment(loader=FileSystemLoader('assets'))
    template = env.get_template('email_template.html')

    # Fill in values to render newsletter. Gets passed to Jinja2 template
    return template.render(
        recommended_articles=recommendations,
        all_articles=summaries,
        dates=enumerate(sorted_dates),
        formatted_dates=date_list,
        user_persona_topic=f"{user_persona}_{user_topic}",
        year=datetime.datetime.now().year)

def generate_newsletter_from_db(time_period="day",
                                user_topic="Any",
                                user_persona="All"):

    if time_period.lower() == "day":
        n = 1
    elif time_period.lower() == "week":
        n = 7
    else:
        print("Please define time period")
        return "Invalid time period specified. Please use 'day' or 'week'."

    summaries = db_service.get_documents_for_past_n_days('newsletter_summaries', n)
    recommendations = db_service.get_documents_for_past_n_days('newsletter_recommendations', n)

    return _render_newsletter_html(summaries, recommendations, user_persona, user_topic)

def send_email_test():
    _, summaries, rec_json = get_newsletter_from_sources()
    email_service.send_email(sender_email="geiger.ljo@gmail.com",
                             sender_password=os.getenv("SENDER_PASSWORD"),
                             receiver_email="lukasgeiger@google.com",
                             subject="GCP Newsletter",
                             recommendations=rec_json,
                             summaries=summaries)

# Enable this and run python3 newsletter_service.py for testing
if __name__ == "__main__":
    get_newsletter_from_sources() # This will run when the script is executed
    # generate_newsletter_from_db(wr_summaries, wr_rec)
    # send_email_test() # Call other functions if needed
