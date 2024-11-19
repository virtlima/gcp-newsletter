import feedparser
import json
import datetime
import ssl
import gemini_wrapper, email_service, db_service
import os
from dotenv import load_dotenv

load_dotenv()
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
get_persona = db_service.get_components_from_firestore('gcp_newsletter', 'settings')['persona']
get_topic = db_service.get_components_from_firestore('gcp_newsletter', 'settings')['topic']

# Create a matrix to iterate through every combination of persona and topics
persona_topic_matrix = [(p, t) for p in get_persona for t in get_topic]

def get_newsletter_from_sources(source="https://snownews.appspot.com/feed",
                                num_days=0):

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

    # Generate summaries
    summaries = gemini_wrapper.generate_summaries(entries)

    day_summaries = {
        'summaries': summaries,
        'timestamp': datetime.datetime.now()
        }

    # Write summaries to firestore
    wr_summaries = db_service.write_to_firestore('newsletter_summaries', day_summaries)

    # Create a dictionary to store recommendations for all persona-topic combinations
    all_recommendations = {}

    # Grabbing Summaries from Firestore
    get_sum = db_service.get_components_from_firestore('newsletter_summaries', wr_summaries)['summaries']

    for persona, topic in persona_topic_matrix:
        print(f"Processing persona: {persona}, topic: {topic}")
        rec_json = gemini_wrapper.generate_recommendation(
            user_topic=topic, user_persona=persona, summaries=get_sum)
        
        # Store recommendations under the corresponding persona-topic key
        all_recommendations[f"{persona}_{topic}"] = rec_json

    all_recommendations['timestamp'] = datetime.datetime.now()

    # Write all recommendations to a single document in Firestore
    wr_rec = db_service.write_to_firestore('newsletter_recommendations', all_recommendations)

def generate_newsletter_from_db(time_period="day",
                                user_topic="Any",
                                user_persona="All"): 

    if time_period.lower() == "day":
        yesterday = datetime.date.today() - datetime.timedelta(days=1)
        doc = yesterday.strftime("%m_%d_%Y")

        # Grabbing Summaries from Firestore
        get_sum = db_service.get_components_from_firestore('newsletter_summaries', doc)['summaries']

        # Grabbing Recommendations from Firestore
        get_rec = db_service.get_components_from_firestore('newsletter_recommendations', doc)

        # Format output
        # Accessing summary_text (assuming it's a separate key in rec_json)
        rec_string = f"Recs: {get_rec[f'{user_persona}_{user_topic}'].get('summary_text', '')}\n\n" 
        
        # Iterating over recommendations (now a list)
        rec_string += "".join([
            f"{i+1}. {rec.get('recommendation_title', '')}\n\
                      Summary: {rec.get('recommendation_summary', '')}\n\
                      Reason: {rec.get('recommendation_reason', '')}\n\
                      Link: {rec.get('recommendation_link', '')}\n\n"
            for i, rec in enumerate(get_rec[f"{user_persona}_{user_topic}"].get('recommendations', []))
        ]) + "\n"
        
        summary_string = "Complete List of Articles:\n\n" + "".join([
            f"{j+1}. {summary['title']}\n\
                      Summary: {summary['summary']}\
                      Link: {summary['link']}\n\n"
            for j, summary in enumerate(get_sum)
        ]) + "\n"
        
        newsletter = f"""Hi!\n\n""" + rec_string + summary_string
        
        return newsletter

    elif time_period.lower() == "week":

        # Grabbing Summaries from the past week from Firestore
        get_sum = db_service.get_documents_for_past_week('newsletter_summaries')

        # Grabbing Recommendations from the past week from Firestore
        get_rec = db_service.get_documents_for_past_week('newsletter_recommendations')

        # Initialize rec_string
        rec_string = ""

        for daily_rec in get_rec:  # Iterate through each day's recommendations
            if f"{user_persona}_{user_topic}" in daily_rec: # Check if the key exists in current day's dict
                rec_string = f"Recs: {daily_rec[f'{user_persona}_{user_topic}'].get('summary_text', '')}\n\n"
                rec_string += "".join([
                    f"{i+1}. {rec.get('recommendation_title', '')}\n\
                          Summary: {rec.get('recommendation_summary', '')}\n\
                          Reason: {rec.get('recommendation_reason', '')}\n\
                          Link: {rec.get('recommendation_link', '')}\n\n"
                    for i, rec in enumerate(daily_rec[f"{user_persona}_{user_topic}"].get('recommendations', []))
                ]) + "\n"
            else:
                 # Handle the case where the key isn't found for any day of the week
                rec_string = f"No recommendations found for {user_persona} and {user_topic} this week.\n\n"
        
        summary_string = "Complete List of Articles for This Week:\n\n"
        for i, daily_summaries in enumerate(get_sum):  # Iterate through each day's summaries
            summary_string += f"Day {i+1}:\n\n" # Add day identifier

            if daily_summaries and "summaries" in daily_summaries:
                summary_string += "".join([
                    f"{j+1}. {summary.get('title', '')}\n\
                          Summary: {summary.get('summary', '')}\n\
                          Link: {summary.get('link', '')}\n\n"
                    for j, summary in enumerate(daily_summaries['summaries'])
                ]) + "\n"
            else:
                summary_string += "No articles found for this day.\n\n"

        newsletter = f"""Hi!\n\n""" + rec_string + summary_string
        
        return newsletter

    else:
        print("Please define time period")


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
