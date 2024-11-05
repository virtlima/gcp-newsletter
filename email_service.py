import smtplib, datetime
from email.mime.text import MIMEText
from jinja2 import Environment, FileSystemLoader


def send_email(sender_email, sender_password, receiver_email, subject,
               recommendations, summaries):
    """Sends an email with the given parameters.

  Args:
    sender_email: The sender's email address.
    sender_password: The sender's email password.
    receiver_email: The recipient's email address.
    subject: The email subject.
    recommendations: List of recommended articles.
    summaries: Full list of articles
  """
    env = Environment(loader=FileSystemLoader('assets'))
    template = env.get_template('email_template.html')

    email_content = template.render(recommended_articles=recommendations,
                                    all_articles=summaries,
                                    year=datetime.datetime.now().year)

    msg = MIMEText(email_content, 'html')
    msg['Subject'] = subject
    msg['From'] = sender_email
    msg['To'] = receiver_email

    with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
        server.login(sender_email, sender_password)
        server.sendmail(sender_email, receiver_email, msg.as_string())
