import flet as ft
import newsletter_service, os

USER_PERSONA = ["CXO", "Dev"]
USER_TOPIC = ["Financial", "Retail", "AI/ML"]
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
        n = ft.Text(value="waiting...")
        c = ft.Column()
        page.add(c, n)
        newsletter = newsletter_service.get_newsletter_from_sources(
            source=rss_url,
            time_period=time_period.value,
            user_persona=persona.value,
            user_topic=topic.value,
        )
        n.value = newsletter
        # Return Newsletter Content to Display on Webpage.
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
