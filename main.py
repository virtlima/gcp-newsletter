import flet as ft
import os, requests, datetime
from google.cloud import storage
import newsletter_service, db_service
import google.auth.transport.requests
from google.auth import impersonated_credentials

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
sender_password = os.environ.get(
    "SENDER_PASSWORD"
)  # Make gmail app password from here:https://support.google.com/accounts/answer/185833?visit_id=638655613103411169-2477840836&p=InvalidSecondFactor&rd=1

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

    # creds = service_account.Credentials.from_service_account_file('./credentials.json')
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
    # blob.upload_from_string(uploaded_file.read())

    print(f"Upload Signed URL: {url}")

    # encoded_content = base64.b64encode(uploaded_file.read()).decode("utf-8")

    # Again leverage signed URLs here to circumvence Cloud Run's 32 MB upload limit
    response = requests.put(url,
                            uploaded_file_contents,
                            headers={'Content-Type': type})

    #TODO: review. Returns unsuccessful upon success.
    print(response.status_code)
    print(response.reason)
    output = f"Error in uploading content: {response.status_code} {response.reason} {response.text}"
    if response.status_code == 200:
        output = "Success"
    return output


def main(page: ft.Page):
    signed_url = "error"  # Replace with error page url

    def open_newsletter_clicked(e, signed_url):
        page.launch_url(signed_url)

    def button_clicked(e):
        loading = ft.Text(
            f"Generating Newsletter for values: '{persona.value}', '{topic.value}', '{email.value}'"
        )
        page.add(loading)
        # Call newsletter_service.py to Generate Newsletter, pass values along
        newsletter_value = newsletter_service.generate_newsletter_from_db(
            time_period=time_period.value,
            user_persona=persona.value,
            user_topic=topic.value,
        )
        # Return Newsletter Content to Display on Webpage.
        # newsletter_container = ft.Container(
        #     content=ft.Column(
        #         [
        #             ft.Text(value=newsletter),
        #         ],
        #         scroll=ft.ScrollMode.AUTO,  # Enable scrolling
        #         expand=True,  # Allow the container to expand to fit content
        #     ),
        #     expand=True,  # Allow the container to take up available space
        # )

        # Create html formatted email
        newsletter_name = f"{persona.value}_{topic.value}_{datetime.date.today()}.html"
        # Write newsletter to GCS
        result = upload_file(uploaded_file_contents=newsletter_value,
                             uploaded_file_name=newsletter_name,
                             bucket_name=HTML_GCS_BUCKET,
                             type="text/html")
        print(f"File upload result: {result}")
        # Get signed url for said GCS file
        signed_url = getSignedURL(
            newsletter_name,
            storage_client.bucket("rendered-newsletter-html-files"), "GET")
        print(signed_url)
        # Display link to open GCS file
        page.add(
            ft.TextButton(
                f"Click here to open generated newsletter: {newsletter_name}",
                on_click=lambda e: open_newsletter_clicked(e, signed_url)))
        # page.add(ft.Text(signed_url, selectable=True))
        # page.add(newsletter_container)  # Add the container to the page


    p = ft.Text()
    b = ft.ElevatedButton(text="Generate", on_click=button_clicked)
    persona = ft.Dropdown(
        width=500,
        label="Persona",
        options=[ft.dropdown.Option(persona) for persona in USER_PERSONA],
    )
    topic = ft.Dropdown(
        width=500,
        label="Topic",
        options=[ft.dropdown.Option(topic) for topic in USER_TOPIC],
    )
    time_period = ft.Dropdown(
        width=500,
        label="Time Period",
        options=[ft.dropdown.Option(period) for period in TIME_PERIOD],
    )
    email = ft.TextField(width=500,
                         label="E-Mail (if you want us to send via email)")
    page.add(persona, topic, email, time_period, b, p)


ft.app(main)
