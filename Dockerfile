FROM python:3.13-slim

WORKDIR /app

# Keep Python output unbuffered for container logs.
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

RUN adduser --disabled-password --gecos "" appuser

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY --chown=appuser:appuser . .

# /app is root-owned by default; without this, appuser cannot create SQLite DB or
# -journal/-wal files (OperationalError: attempt to write a readonly database).
RUN chown -R appuser:appuser /app

USER appuser

EXPOSE 5000

CMD ["python", "app.py"]

