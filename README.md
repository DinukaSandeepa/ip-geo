# IP Geo API

A lightweight Flask API for IP geolocation using MaxMind GeoLite2 City and ASN databases.

## Features

- Detects client IP behind trusted proxies (Render/Cloudflare) or accepts `?ip=` override
- GeoLite2 City lookups (country, city, lat/long, timezone)
- GeoLite2 ASN lookups (ISP/ASN organization)
- API key protection for public lookup endpoint (`X-API-Key`)
- Docker-ready for self-hosting or Render deployment

## Endpoints

### GET /
Returns geo information for the client IP or the `ip` query param.
Requires `X-API-Key` request header.

**Query params**
- `ip` (optional): IP address to look up. If omitted, the API uses the request IP / proxy headers.

**Response**
```json
{
  "ip": "223.224.30.238",
  "country": "Sri Lanka",
  "city": "Colombo",
  "iso_code": "LK",
  "latitude": 6.8833,
  "longitude": 79.85,
  "timezone": "Asia/Colombo",
  "isp": "Example ISP",
  "asn": 12345,
  "asn_org": "Example ISP"
}
```

### GET /health
Health check.

## API Authentication

- `GET /` is protected and requires the request header `X-API-Key`.
- `GET /health` is public and does not require a key.
- Do not call this API directly from browser code with the key. Use your backend/server route.

### curl examples

Health check (no key required):
```bash
curl https://your-api.example.com/health
```

Protected lookup without key (`401` expected):
```bash
curl "https://your-api.example.com/?ip=8.8.8.8"
```

Protected lookup with key (`200` expected when lookup succeeds):
```bash
curl -H "X-API-Key: YOUR_API_ACCESS_KEY" "https://your-api.example.com/?ip=8.8.8.8"
```

## Environment Variables

- `API_ACCESS_KEY` (required): API key expected in the `X-API-Key` request header for protected endpoints.
- `TRUST_PROXY_HEADERS` (optional): `true|false`. Trust proxy headers for client IP extraction.
- `TRUST_PROXY_CIDRS` (optional): Comma-separated CIDRs for trusted proxies.
- Render environments are auto-detected (proxy headers are trusted when Render sets `RENDER_EXTERNAL_URL`).

## Using the API from React / Next.js (Server-side Key Usage)

Use your server-side code to call the public API and attach `X-API-Key`. Then your frontend calls your own backend route.

### Next.js (Route Handler)
Store `API_ACCESS_KEY` in the Next.js server environment (for example `.env.local`) and never expose it client-side.

```ts
// app/api/geo/route.ts
import { NextResponse } from "next/server";

export async function GET() {
  const apiKey = process.env.API_ACCESS_KEY;
  if (!apiKey) {
    return NextResponse.json({ error: "API key not configured" }, { status: 500 });
  }

  const res = await fetch("https://your-api.example.com/?ip=8.8.8.8", {
    cache: "no-store",
    headers: { "X-API-Key": apiKey },
  });

  if (!res.ok) {
    return NextResponse.json({ error: "Geo lookup failed" }, { status: 500 });
  }
  const data = await res.json();
  return NextResponse.json(data);
}
```

### React / Next.js Client Component
The frontend calls your own route only:

```tsx
"use client";

import { useEffect, useState } from "react";

export default function GeoWidget() {
  const [geo, setGeo] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    fetch("/api/geo")
      .then((r) => r.json())
      .then(setGeo)
      .catch((e) => setError(e.message));
  }, []);

  if (error) return <div>Error: {error}</div>;
  if (!geo) return <div>Loading...</div>;

  return (
    <pre>{JSON.stringify(geo, null, 2)}</pre>
  );
}
```

## Deploy Your Own API

### Option A: Render (Docker)
1. Push this repo to GitHub.
2. Create a new Web Service in Render.
3. Select Docker as the environment.
4. Render will build the image and download the latest GeoLite2 City/ASN databases at build time.
5. Set required environment variables:
   - `API_ACCESS_KEY=<your-secret-key>`
6. Optional proxy setting:
   - `TRUST_PROXY_HEADERS=true` (usually not required on Render)

### Option B: Your Own VPS (Docker)
1. Install Docker on your VPS.
2. Build and run the container:

```bash
docker build -t ip-geo .
docker run -d -p 8000:8000 --name ip-geo ip-geo
```

3. Test:
```bash
curl -H "X-API-Key: YOUR_API_ACCESS_KEY" http://YOUR_SERVER:8000/?ip=8.8.8.8
```

### Option C: Your Own VPS (Python)
1. Install Python 3.11+.
2. Install requirements:
```bash
pip install -r requirements.txt
```
3. Run:
```bash
gunicorn --bind 0.0.0.0:8000 --workers 3 app:app
```

## Notes

- The GeoLite2 databases are licensed by MaxMind. Make sure to comply with the GeoLite2 EULA.
- Build-time downloads use the latest GitHub release tag from P3TERX/GeoLite.mmdb.
