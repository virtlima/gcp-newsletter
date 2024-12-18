FROM python:3.13-slim

WORKDIR /app

COPY requirements.txt .

RUN pip install -r requirements.txt

COPY *.py /app/

ENTRYPOINT ["python", "newsletter_service.py"]