FROM python:3.13-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install firebase-admin
RUN pip install google-cloud-aiplatform
RUN pip install vertexai
RUN pip install legacy-cgi
RUN pip install feedparser
RUN pip install python-dotenv

COPY gemini_wrapper.py .
COPY gemini.py .
COPY db_service.py .
COPY newsletter_service.py .

CMD ["python", "newsletter_service.py"]