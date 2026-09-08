# BarSpec — container image (portable setup path).
# Homelab KAIDO runs the systemd unit; this image is for any other machine
# (venue box, VPS, dev). Data lives in the bind-mounted ./data dir as a
# plain SQLite file — "here's your data file" stays true.
FROM python:3.12-slim

# non-root: the app never needs privileges (uid 1000 = typical host owner,
# so a ./data bind mount owned by the host user stays writable)
RUN useradd --create-home --uid 1000 barspec
WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY main.py db.py pricing.py auth.py exporters.py ./
COPY migrations ./migrations
COPY static ./static
RUN mkdir -p /app/data && chown -R 1000:1000 /app
USER 1000

ENV BARSPEC_DB=/app/data/barspec.db
EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
