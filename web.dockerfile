FROM python:3.13-slim

WORKDIR /app
ENV FLET_FORCE_WEB_SERVER=true
COPY requirements.txt .

RUN pip install -r requirements.txt

COPY *.py /app/

EXPOSE 8000

CMD ["python", "main.py"]