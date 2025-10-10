FROM python:3.13-slim

RUN apt-get update && apt-get upgrade -y

WORKDIR /app

COPY requirements.txt .

RUN pip install -r requirements.txt

COPY *.py /app/

ENTRYPOINT ["python", "newsletter_service.py"]