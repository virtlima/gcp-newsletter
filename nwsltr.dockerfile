FROM python:3.13-slim

WORKDIR /app

RUN pip install firebase-admin
RUN pip install google-cloud-aiplatform
RUN pip install vertexai
RUN pip install legacy-cgi
RUN pip install feedparser
RUN pip install python-dotenv
RUN pip install jinja2

COPY *.py /app/

CMD ["python", "newsletter_service.py"]