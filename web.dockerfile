FROM python:3.13-slim

WORKDIR /app

COPY requirements.txt .
COPY ./assets /app/assets

RUN pip install -r requirements.txt

COPY *.py /app/

EXPOSE 8000

ENTRYPOINT ["python", "main.py"]