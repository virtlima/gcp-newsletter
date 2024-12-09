FROM python:3.13-slim

WORKDIR /app

RUN pip install firebase-admin
RUN pip install google-cloud-aiplatform
RUN pip install vertexai
RUN pip install legacy-cgi
RUN pip install feedparser
RUN pip install python-dotenv
RUN pip install jinja2

COPY gemini_wrapper.py .
COPY gemini.py .
COPY db_service.py .
COPY newsletter_service.py .
COPY email_service.py .

CMD ["python", "newsletter_service.py"]