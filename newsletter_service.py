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


def get_newsletter_from_sources(source="https://snownews.appspot.com/feed",
                                time_period="day",
                                user_topic="Any",
                                user_persona="All"):

    # Parse the RSS feed
    ssl._create_default_https_context = ssl._create_unverified_context
    feed = feedparser.parse(source)

    entries = []
    # Extract the entries depending on time period specified
    if time_period.lower() == "day":

        for entry in feed.entries:
            # Check if the entry was published within the last week
            published_date = datetime.datetime(*entry.published_parsed[:6])
            if published_date.date() == datetime.datetime.now().date():
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

    # Write last week entries to output file
    with open(f"data/entries.json", "w") as f:
        json.dump(entries, f)

    # Generate summaries
    summaries = gemini_wrapper.generate_summaries(entries)

    # Write summaries to output file
    with open(f"data/summaries.json", "w") as f:
        json.dump(summaries, f)

    db_service.write_to_firestore('summaries', summaries)

    # Generate recommendations
    rec_json = gemini_wrapper.generate_recommendation(
        user_topic=user_topic, user_persona=user_persona, summaries=summaries)

    # Write recs to output file
    with open(f"data/recommended_articles.json", "w") as f:
        json.dump(rec_json, f)

    # Format output
    rec_string = f"Recs: {rec_json['summary_text']}\n\n" + "".join([
        f"{i+1}. {rec['recommendation_title']}\n\
                  Summary: {rec['recommendation_summary']}\n\
                  Reason: {rec['recommendation_reason']}\n\
                  Link: {rec['recommendation_link']}\n\n"
        for i, rec in enumerate(rec_json["recommendations"])
    ]) + "\n"
    summary_string = "Complete List of Articles:\n\n" + "".join([
        f"{j+1}. {summary['title']}\n\
                  Summary: {summary['summary']}\
                  Link: {summary['link']}\n\n"
        for j, summary in enumerate(summaries)
    ]) + "\n"
    newsletter = f"""Hi!\n\n""" + rec_string + summary_string

    print(newsletter)

    return newsletter
