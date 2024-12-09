FROM python:3.13-slim

WORKDIR /app

RUN pip install flet
RUN pip install firebase-admin
RUN pip install jinja2

COPY db_service.py .
COPY newsletter_service.py .
COPY email_service.py .

EXPOSE 8080

CMD ["flet", "run", "-p", "8080", "--host", "*" "main.py"]