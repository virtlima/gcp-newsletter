import feedparser
import datetime
import ssl
import logging
import gemini_wrapper, email_service, db_service
import os
from jinja2 import Environment, FileSystemLoader


logger = logging.getLogger(__name__)

# --- Constants ---
RSS_FEED_URL_DEFAULT = "https://snownews.appspot.com/feed"
COLLECTION_SUMMARIES = 'newsletter_summaries'
COLLECTION_RECOMMENDATIONS = 'newsletter_recommendations'
COLLECTION_SETTINGS = 'gcp_newsletter'
DOCUMENT_SETTINGS = 'settings'
TIME_PERIOD_DAY = "day"
TIME_PERIOD_WEEK = "week"

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


def process_daily_articles(source=RSS_FEED_URL_DEFAULT,
                           num_days=1):
    """
    Fetches articles from an RSS feed, generates summaries and recommendations,
    and stores them in Firestore. Designed to be run as a background task.
    """
    logger.info(f"Starting article processing from source: {source} for the last {num_days} day(s).")
    # This is a security risk and should be avoided in production.
    # It's better to ensure the server environment has the correct CA certificates.
    logger.warning("Disabling SSL certificate verification for feedparser.")
    try:
        ssl._create_default_https_context = ssl._create_unverified_context
        feed = feedparser.parse(source)
    except Exception as e:
        logger.error(f"Error parsing RSS feed from {source}: {e}", exc_info=True)
        return

    entries = []
    target_date = datetime.date.today() - datetime.timedelta(days=num_days)
    logger.info(f"Filtering articles for target date: {target_date.strftime('%Y-%m-%d')}")

    for entry in feed.entries:
        published_date = datetime.datetime(*entry.published_parsed[:6])
        if published_date.date() == target_date:
            entries.append({
                "title": entry.title,
                "link": entry.link,
                "published": entry.published,
                "metadata": entry.summary,
            })
    
    logger.info(f"Found {len(entries)} articles for the target date.")
    if not entries:
        logger.warning("No articles found for the target date. Exiting process.")
        return
    
    try:
        # 1. Generate and store summaries
        summaries_list = gemini_wrapper.generate_summaries(entries)
        if not summaries_list:
            logger.error("Summary generation returned no results.")
            return
            
        day_summaries = {
            'summaries': summaries_list,
            'timestamp': datetime.datetime.now(datetime.timezone.utc)
        }
        db_service.write_to_firestore(COLLECTION_SUMMARIES, day_summaries, num_days=num_days)
        
        # 2. Generate and store recommendations for all personas and topics
        settings = db_service.get_components_from_firestore(COLLECTION_SETTINGS, DOCUMENT_SETTINGS)
        if not settings:
            logger.error("Failed to retrieve settings from Firestore. Cannot generate recommendations.")
            return
        
        get_persona = settings.get('persona', [])
        get_topic = settings.get('topic', [])
        persona_topic_matrix = [(p, t) for p in get_persona for t in get_topic]
        
        all_recommendations = {}
        for persona, topic in persona_topic_matrix:
            logger.info(f"Generating recommendations for persona: {persona}, topic: {topic}")
            rec_json = gemini_wrapper.generate_recommendation(user_topic=topic, user_persona=persona, summaries=summaries_list)
            all_recommendations[f"{persona}_{topic}"] = rec_json
            
        all_recommendations['timestamp'] = datetime.datetime.now(datetime.timezone.utc)
        db_service.write_to_firestore(COLLECTION_RECOMMENDATIONS, all_recommendations, num_days=num_days)
        
        logger.info("Successfully processed and stored summaries and recommendations.")
    except Exception as e:
        logger.error(f"An error occurred during article processing: {e}", exc_info=True)
        raise


def _render_newsletter_html(summaries, recommendations, user_persona, user_topic):
    """Helper function to render the newsletter HTML."""
    logger.info(f"Rendering HTML for persona: '{user_persona}', topic: '{user_topic}'")
    if not summaries or not recommendations:
        logger.warning("No summaries or recommendations found for the selected period. Returning empty message.")
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
            # This will gracefully skip non-date keys like 'timestamp'
            logger.debug(f"Skipping key '{date}' as it is not a valid date.")
            continue

    # Format output through Jinja2 template
    try:
        env = Environment(loader=FileSystemLoader(os.path.join(os.path.dirname(__file__), 'assets')))
        template = env.get_template('email_template.html')

        # Fill in values to render newsletter. Gets passed to Jinja2 template
        return template.render(
            recommended_articles=recommendations,
            all_articles=summaries,
            dates=enumerate(sorted_dates),
            formatted_dates=date_list,
            user_persona_topic=f"{user_persona}_{user_topic}",
            year=datetime.datetime.now().year)
    except Exception as e:
        logger.error(f"Error rendering Jinja2 template: {e}", exc_info=True)
        return "Error: Could not render the newsletter template."

def generate_newsletter_from_db(time_period="day",
                                user_topic="Any",
                                user_persona="All"):
    """
    Generates a single newsletter HTML string by fetching pre-processed data
    from Firestore for a given time period, persona, and topic.
    """
    logger.info(f"Generating newsletter from DB for period: '{time_period}', persona: '{user_persona}', topic: '{user_topic}'")
    if time_period.lower() == TIME_PERIOD_DAY:
        n = 1
    elif time_period.lower() == TIME_PERIOD_WEEK:
        n = 7
    else:
        logger.error(f"Invalid time period specified: '{time_period}'")
        return "Invalid time period specified. Please use 'day' or 'week'."

    try:
        summaries = db_service.get_documents_for_past_n_days(COLLECTION_SUMMARIES, n)
        recommendations = db_service.get_documents_for_past_n_days(COLLECTION_RECOMMENDATIONS, n)
        
        if not summaries or not recommendations:
            logger.warning(f"No data found in Firestore for the past {n} days.")
            # We can still try to render, the render function will handle the empty state.

        return _render_newsletter_html(summaries, recommendations, user_persona, user_topic)
    except Exception as e:
        logger.error(f"Failed to generate newsletter from DB: {e}", exc_info=True)
        return "Error: Could not retrieve data to generate the newsletter."

# This main block is useful for triggering the data processing job independently,
# for example, via a scheduled Cloud Function or Cloud Run Job.
if __name__ == "__main__":
    # Set up basic logging for standalone script execution
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    logger.info("Running newsletter_service as a standalone script.")
    process_daily_articles()
