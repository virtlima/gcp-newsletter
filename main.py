from flask import Flask, render_template_string, request, redirect, url_for, render_template
import os, requests, datetime
from google.cloud import storage
from google.cloud import secretmanager
import google.cloud.logging
import newsletter_service, db_service
import google.auth.transport.requests
from google.auth import impersonated_credentials
import logging


app = Flask(__name__, template_folder="assets")

# --- Logging Setup ---
# Instantiates a client and integrates with Python's logging module.
# This will automatically handle structured logging in a Google Cloud environment.
client = google.cloud.logging.Client()
client.setup_logging()

USER_PERSONA = db_service.get_components_from_firestore(
    'gcp_newsletter', 'settings')['settings']['persona']
USER_TOPIC = db_service.get_components_from_firestore(
    'gcp_newsletter', 'settings')['settings']['topic']
TIME_PERIOD = ["day", "week"]

# --- Configuration from Environment ---
# Get the Project ID from the Cloud Run environment
credentials, project_id = google.auth.default()
PROJECT_ID = project_id

# Get other configurations from environment variables
HTML_GCS_BUCKET = os.environ.get("HTML_GCS_BUCKET")
SIGNING_SERVICE_ACCOUNT = os.environ.get("SIGNING_SERVICE_ACCOUNT") # The SA that will sign the URL
SENDER_EMAIL = os.environ.get("SENDER_EMAIL")
SENDER_PASSWORD_SECRET_ID = os.environ.get("SENDER_PASSWORD_SECRET_ID") # e.g., "sender-password"
SENDER_PASSWORD_SECRET_VERSION = os.environ.get("SENDER_PASSWORD_SECRET_VERSION", "latest")

# Fail fast if required configuration is missing
if not all([PROJECT_ID, HTML_GCS_BUCKET, SIGNING_SERVICE_ACCOUNT]):
    logging.critical("FATAL: One or more required environment variables are not set.")
    raise ValueError("FATAL: One or more required environment variables are not set.")

logging.info(f"Configuration loaded successfully for project: {PROJECT_ID}")
logging.info(f"Using GCS bucket: {HTML_GCS_BUCKET}")

# --- Secret Manager Integration ---
def get_secret(project_id, secret_id, version_id="latest"):
    """Retrieves a secret from Google Secret Manager."""
    try:
        logging.info(f"Attempting to access secret: {secret_id}, version: {version_id}")
        client = secretmanager.SecretManagerServiceClient()
        name = f"projects/{project_id}/secrets/{secret_id}/versions/{version_id}"
        response = client.access_secret_version(request={"name": name})
        logging.info(f"Successfully accessed secret: {secret_id}")
        return response.payload.data.decode("UTF-8")
    except Exception as e:
        logging.error(f"Failed to access secret {secret_id}: {e}", exc_info=True)
        raise

# Define the RSS feed URL - "https://blog.google/products/google-cloud/rss/"
rss_url = "https://snownews.appspot.com/feed"

# Fetch the sender password from Secret Manager
#sender_password = get_secret(PROJECT_ID, SENDER_PASSWORD_SECRET_ID, SENDER_PASSWORD_SECRET_VERSION)

# Define storage client for file uploads
storage_client = storage.Client(project=PROJECT_ID)


# Function to get signed GCS urls
def getSignedURL(filename, bucket, action):
    logging.info(f"Generating v4 signed URL for '{filename}' in bucket '{bucket.name}' with action '{action}'")
    
    # 1. Get the default credentials from the environment (the Cloud Run service account's token)
    source_credentials = credentials 

    # 2. Create a credentials object that can be used for signing.
    # This uses the source credentials to impersonate the target service account (itself, in this case)
    # to gain the ability to sign.
    signing_credentials = impersonated_credentials.Credentials(
        source_credentials=source_credentials,
        target_principal=SIGNING_SERVICE_ACCOUNT,
        target_scopes=["https://www.googleapis.com/auth/devstorage.read_write"],
        lifetime=300,
    )

    blob = bucket.blob(filename)

    url = blob.generate_signed_url(expiration=datetime.timedelta(minutes=60),
                                   method=action,
                                   credentials=signing_credentials,
                                   version="v4")
    return url


# Function to upload bytes object to GCS bucket
def upload_file(uploaded_file_contents, uploaded_file_name, bucket_name, type):
    bucket = storage_client.bucket(bucket_name)

    try:
        url = getSignedURL(uploaded_file_name, bucket, "PUT")
        logging.info(f"Uploading to signed URL for {uploaded_file_name}")

        response = requests.put(url,
                                uploaded_file_contents,
                                headers={'Content-Type': type})
        response.raise_for_status()  # Raises an HTTPError for bad responses (4xx or 5xx)

        logging.info(f"Successfully uploaded file '{uploaded_file_name}' to GCS bucket '{bucket_name}'.")
        return "Success"
    except requests.exceptions.RequestException as e:
        logging.error(f"Error uploading file '{uploaded_file_name}': {e.response.text}", exc_info=True)
        return f"Error in uploading content: {e.response.status_code} {e.response.reason} {e.response.text}"


@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        persona = request.form.get("persona", "no persona selected")
        topic = request.form.get("topic", "no topic selected")
        email = request.form.get("email", "no email specified")
        time_period_value = request.form.get("time_period",
                                             "no time period selected")

        logging.info(f"Received POST request: persona='{persona}', topic='{topic}', email='{email}', time_period='{time_period_value}'")

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
        logging.info(f"File upload result: {result}")
        # Get signed url for said GCS file
        signed_url = getSignedURL(newsletter_name,
                                  storage_client.bucket(HTML_GCS_BUCKET),
                                  "GET")
        
        logging.info(f"Generated signed URL for viewing: {signed_url}")
        return render_template("index.html",
                               user_persona=USER_PERSONA,
                               user_topic=USER_TOPIC,
                               time_period=TIME_PERIOD,
                               signed_url=signed_url,
                               newsletter_name=newsletter_name)

    logging.info("Serving GET request for the index page.")
    return render_template("index.html",
                           user_persona=USER_PERSONA,
                           user_topic=USER_TOPIC,
                           time_period=TIME_PERIOD)


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=int(os.environ.get("PORT", 8000)))
