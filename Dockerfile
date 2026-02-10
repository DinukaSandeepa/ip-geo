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
from urllib.request import Request, urlopen

api_url = "https://api.github.com/repos/P3TERX/GeoLite.mmdb/releases/latest"
req = Request(api_url, headers={"Accept": "application/vnd.github+json"})
with urlopen(req, timeout=30) as response:
    data = json.load(response)

tag = data.get("tag_name")
if not tag:
    sys.exit("Could not determine latest GeoLite.mmdb tag")

print(tag)
PY

RUN LATEST_TAG=$(python - <<'PY'
import json
from urllib.request import Request, urlopen

api_url = "https://api.github.com/repos/P3TERX/GeoLite.mmdb/releases/latest"
req = Request(api_url, headers={"Accept": "application/vnd.github+json"})
with urlopen(req, timeout=30) as response:
    data = json.load(response)
print(data.get("tag_name", ""))
PY
) \
    && if [ -z "$LATEST_TAG" ]; then echo "Missing latest tag"; exit 1; fi \
    && curl -fsSL "https://github.com/P3TERX/GeoLite.mmdb/releases/download/${LATEST_TAG}/GeoLite2-City.mmdb" \
        -o /app/GeoLite2-City.mmdb \
    && curl -fsSL "https://github.com/P3TERX/GeoLite.mmdb/releases/download/${LATEST_TAG}/GeoLite2-ASN.mmdb" \
        -o /app/GeoLite2-ASN.mmdb

COPY app.py .

RUN addgroup --system appgroup \
    && adduser --system --ingroup appgroup appuser \
    && chown -R appuser:appgroup /app

USER appuser

EXPOSE 8000

CMD ["gunicorn", "--bind", "0.0.0.0:8000", "--workers", "3", "app:app"]
