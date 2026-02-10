# IP Geo API

A lightweight Flask API for IP geolocation using MaxMind GeoLite2 City and ASN databases.

## Features

- Detects client IP behind trusted proxies (Render/Cloudflare) or accepts `?ip=` override
- GeoLite2 City lookups (country, city, lat/long, timezone)
- GeoLite2 ASN lookups (ISP/ASN organization)
- Docker-ready for self-hosting or Render deployment

## Endpoints

### GET /
Returns geo information for the client IP or the `ip` query param.

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

## Environment Variables

- `TRUST_PROXY_HEADERS` (optional): `true|false`. Trust proxy headers for client IP extraction.
- `TRUST_PROXY_CIDRS` (optional): Comma-separated CIDRs for trusted proxies.
- Render environments are auto-detected (proxy headers are trusted when Render sets `RENDER_EXTERNAL_URL`).

## Using the API from React / Next.js

### React (Fetch)
```js
const API_BASE = "https://your-api.example.com";

async function getMyGeo() {
  const res = await fetch(`${API_BASE}/`);
  if (!res.ok) throw new Error("Geo lookup failed");
  return res.json();
}
```

### Next.js (Route Handler)
Use your API server from a Next.js route handler to avoid exposing keys or to add caching.

```ts
// app/api/geo/route.ts
import { NextResponse } from "next/server";

export async function GET() {
  const res = await fetch("https://your-api.example.com", { cache: "no-store" });
  if (!res.ok) {
    return NextResponse.json({ error: "Geo lookup failed" }, { status: 500 });
  }
  const data = await res.json();
  return NextResponse.json(data);
}
```

### Next.js (Client Component)
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
5. Set environment variables if needed:
   - `TRUST_PROXY_HEADERS=true` (optional, usually not required on Render)

### Option B: Your Own VPS (Docker)
1. Install Docker on your VPS.
2. Build and run the container:

```bash
docker build -t ip-geo .
docker run -d -p 8000:8000 --name ip-geo ip-geo
```

3. Test:
```bash
curl http://YOUR_SERVER:8000/
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
