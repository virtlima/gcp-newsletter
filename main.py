from flask import Flask, render_template_string, request, redirect, url_for, render_template
import os, requests, datetime
from google.cloud import storage
import newsletter_service, db_service
import google.auth.transport.requests
from google.auth import impersonated_credentials

app = Flask(__name__, template_folder="assets")

USER_PERSONA = db_service.get_components_from_firestore(
    'gcp_newsletter', 'settings')['settings']['persona']
USER_TOPIC = db_service.get_components_from_firestore(
    'gcp_newsletter', 'settings')['settings']['topic']
TIME_PERIOD = ["day", "week"]

PROJECT_ID = "project-ana-851024"
HTML_GCS_BUCKET = "rendered-newsletter-html-files"

# Define the RSS feed URL - "https://blog.google/products/google-cloud/rss/"
rss_url = "https://snownews.appspot.com/feed"

sender_email = os.environ.get("SENDER_EMAIL")
sender_password = os.environ.get("SENDER_PASSWORD")

# Define storage client for file uploads
storage_client = storage.Client(project=PROJECT_ID)


def getCreds():
    creds, _ = google.auth.default(
        scopes=['https://www.googleapis.com/auth/cloud-platform'])
    auth_req = google.auth.transport.requests.Request()
    creds.refresh(auth_req)
    return creds


# Function to get signed GCS urls
def getSignedURL(filename, bucket, action):
    creds = getCreds()

    signing_credentials = impersonated_credentials.Credentials(
        source_credentials=creds,
        target_principal='526257981680-compute@developer.gserviceaccount.com',
        target_scopes='',
        lifetime=500)

    blob = bucket.blob(filename)

    url = blob.generate_signed_url(expiration=datetime.timedelta(minutes=60),
                                   method=action,
                                   credentials=signing_credentials,
                                   version="v4")
    return url


# Function to upload bytes object to GCS bucket
def upload_file(uploaded_file_contents, uploaded_file_name, bucket_name, type):
    bucket = storage_client.bucket(bucket_name)

    url = getSignedURL(uploaded_file_name, bucket, "PUT")

    print(f"Upload Signed URL: {url}")

    response = requests.put(url,
                            uploaded_file_contents,
                            headers={'Content-Type': type})

    print(response.status_code)
    print(response.reason)
    output = f"Error in uploading content: {response.status_code} {response.reason} {response.text}"
    if response.status_code == 200:
        output = "Success"
    return output


@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        persona = request.form.get("persona", "no persona selected")
        topic = request.form.get("topic", "no topic selected")
        email = request.form.get("email", "no email specified")
        time_period_value = request.form.get("time_period",
                                             "no time period selected")

        # Call newsletter_service.py to Generate Newsletter, pass values along
        newsletter_value = newsletter_service.generate_newsletter_from_db(
            time_period=time_period_value,
            user_persona=persona,
            user_topic=topic,
        )

        # Create html formatted email
        newsletter_name = f"{persona}_{topic}_{time_period_value}_{datetime.date.today()}.html"
        # Write newsletter to GCS
        result = upload_file(uploaded_file_contents=newsletter_value,
                             uploaded_file_name=newsletter_name,
                             bucket_name=HTML_GCS_BUCKET,
                             type="text/html")
        print(f"File upload result: {result}")
        # Get signed url for said GCS file
        signed_url = getSignedURL(newsletter_name,
                                  storage_client.bucket(HTML_GCS_BUCKET),
                                  "GET")
        print(signed_url)

        return render_template("index.html",
                               user_persona=USER_PERSONA,
                               user_topic=USER_TOPIC,
                               time_period=TIME_PERIOD,
                               signed_url=signed_url,
                               newsletter_name=newsletter_name)

    return render_template("index.html",
                           user_persona=USER_PERSONA,
                           user_topic=USER_TOPIC,
                           time_period=TIME_PERIOD)


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=int(os.environ.get("PORT", 8000)))
