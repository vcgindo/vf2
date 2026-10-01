FROM python:3.11.14-slim-bookworm
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PYTHONPATH=/app
WORKDIR /app
COPY requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt
COPY manage.py /app/
COPY vectorflow /app/vectorflow
COPY mta /app/mta
COPY parity /app/parity
COPY tests /app/tests
COPY baseline /app/baseline
RUN groupadd --gid 10001 vectorflow && useradd --uid 10001 --gid vectorflow vectorflow
USER 10001:10001
CMD ["gunicorn", "vectorflow.wsgi:application", "--preload", "--bind", "0.0.0.0:8000", "--workers", "2"]
