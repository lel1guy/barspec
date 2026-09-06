# BarSpec — container image (portable setup path).
# Homelab KAIDO runs the systemd unit; this image is for any other machine
# (venue box, VPS, dev). Data lives in the bind-mounted ./data dir as a
# plain SQLite file — "here's your data file" stays true.
FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY main.py db.py pricing.py ./
COPY migrations ./migrations
COPY static ./static

ENV BARSPEC_DB=/app/data/barspec.db
EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
