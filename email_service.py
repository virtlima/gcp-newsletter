import smtplib
from email.mime.text import MIMEText

def send_email(sender_email, sender_password, receiver_email, subject, body):
  """Sends an email with the given parameters.

  Args:
    sender_email: The sender's email address.
    sender_password: The sender's email password.
    receiver_email: The recipient's email address.
    subject: The email subject.
    body: The email body.
  """
  msg = MIMEText(body)
  msg['Subject'] = subject
  msg['From'] = sender_email
  msg['To'] = receiver_email

  with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
    server.login(sender_email,
                 sender_password)
    server.sendmail(sender_email,
                    receiver_email,
                    msg.as_string())
