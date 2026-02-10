FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends curl ca-certificates \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

RUN python - <<'PY'
import json
import sys
from pathlib import Path
from urllib.request import Request, urlopen

api_url = "https://api.github.com/repos/P3TERX/GeoLite.mmdb/releases/latest"
req = Request(api_url, headers={"Accept": "application/vnd.github+json"})
with urlopen(req, timeout=30) as response:
    data = json.load(response)

tag = data.get("tag_name")
if not tag:
    sys.exit("Could not determine latest GeoLite.mmdb tag")

base = f"https://github.com/P3TERX/GeoLite.mmdb/releases/download/{tag}"
targets = {
    "GeoLite2-City.mmdb": "/app/GeoLite2-City.mmdb",
    "GeoLite2-ASN.mmdb": "/app/GeoLite2-ASN.mmdb",
}

for name, out_path in targets.items():
    url = f"{base}/{name}"
    with urlopen(url, timeout=60) as response:
        content = response.read()
    Path(out_path).write_bytes(content)
    print(f"Downloaded {name} from {url}")
PY

COPY app.py .

RUN addgroup --system appgroup \
    && adduser --system --ingroup appgroup appuser \
    && chown -R appuser:appgroup /app

USER appuser

EXPOSE 8000

CMD ["gunicorn", "--bind", "0.0.0.0:8000", "--workers", "3", "app:app"]
