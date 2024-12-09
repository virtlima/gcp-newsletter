import flet as ft
import tempfile
import os
import newsletter_service, db_service

USER_PERSONA = db_service.get_components_from_firestore(
    'gcp_newsletter', 'settings')['settings']['persona']
USER_TOPIC = db_service.get_components_from_firestore(
    'gcp_newsletter', 'settings')['settings']['topic']
TIME_PERIOD = ["day", "week"]

# Define the RSS feed URL - "https://blog.google/products/google-cloud/rss/"
rss_url = "https://snownews.appspot.com/feed"

sender_email = os.environ.get("SENDER_EMAIL")
sender_password = os.environ.get(
    "SENDER_PASSWORD"
)  # Make gmail app password from here:https://support.google.com/accounts/answer/185833?visit_id=638655613103411169-2477840836&p=InvalidSecondFactor&rd=1


def main(page: ft.Page):

    def button_clicked(e):
        loading = ft.Text(
            f"Generating Newsletter for values: '{persona.value}', '{topic.value}', '{email.value}'"
        )
        page.add(loading)
        # Call newsletter_service.py to Generate Newsletter, pass values along
        newsletter = newsletter_service.generate_newsletter_from_db(
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
        with tempfile.NamedTemporaryFile(mode="w",
                                         delete=False,
                                         dir="/tmp",
                                         suffix=".html") as f:
            f.write(newsletter)
            temp_file_path = f.name
        file_url = f"file://{temp_file_path}"
        page.launch_url(url=file_url)
        # page.add(newsletter_container)  # Add the container to the page
        page.update()

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
