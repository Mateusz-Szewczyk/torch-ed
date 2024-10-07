FROM python:3.10-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

COPY requirements.txt .
RUN apt-get update && \
    apt-get install -y build-essential libpq-dev && \
    apt-get install -y --no-install-recommends sqlite3 libsqlite3-dev && \
    apt-get clean && \
    pip install pysqlite3-binary && \
    rm -rf /var/lib/apt/lists/* && \
    pip install django-elasticsearch-dsl-drf && \
    pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
