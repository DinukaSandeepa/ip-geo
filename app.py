import ipaddress
import logging
import os
from threading import Lock

from flask import Flask, jsonify, request
from geoip2 import database
from geoip2.errors import AddressNotFoundError

DB_PATH = "GeoLite2-City.mmdb"
TRUST_PROXY_CIDRS = os.getenv("TRUST_PROXY_CIDRS", "")
TRUST_PROXY_HEADERS = os.getenv("TRUST_PROXY_HEADERS", "").strip().lower()
RENDER_EXTERNAL_URL = os.getenv("RENDER_EXTERNAL_URL", "")
RENDER_ENV = os.getenv("RENDER", "").strip().lower()

app = Flask(__name__)
app.logger.setLevel(logging.INFO)

_reader = None
_reader_lock = Lock()
_db_missing_logged = False
_trusted_proxy_networks = []


def _load_trusted_proxy_networks():
    networks = []
    for cidr in TRUST_PROXY_CIDRS.split(","):
        value = cidr.strip()
        if not value:
            continue
        try:
            networks.append(ipaddress.ip_network(value, strict=False))
        except ValueError:
            app.logger.warning("Ignoring invalid TRUST_PROXY_CIDRS entry: %s", value)
    return networks


def _parse_ip(raw_ip):
    if not raw_ip:
        return None
    try:
        return ipaddress.ip_address(raw_ip.strip())
    except ValueError:
        return None


def _is_public_ip(ip_obj):
    return not (
        ip_obj.is_private
        or ip_obj.is_loopback
        or ip_obj.is_link_local
        or ip_obj.is_multicast
        or ip_obj.is_reserved
        or ip_obj.is_unspecified
    )


def _is_trusted_proxy(remote_ip):
    if remote_ip is None:
        return False

    if TRUST_PROXY_HEADERS in {"1", "true", "yes", "on"}:
        return True

    if RENDER_ENV in {"1", "true", "yes", "on"} or RENDER_EXTERNAL_URL:
        return True

    for network in _trusted_proxy_networks:
        if remote_ip in network:
            return True

    return False


def _get_reader():
    global _reader
    global _db_missing_logged

    if _reader is not None:
        return _reader

    with _reader_lock:
        if _reader is not None:
            return _reader

        if not os.path.exists(DB_PATH):
            if not _db_missing_logged:
                app.logger.error("GeoIP database not found at path: %s", DB_PATH)
                _db_missing_logged = True
            return None

        try:
            _reader = database.Reader(DB_PATH)
            app.logger.info("GeoIP database loaded from %s", DB_PATH)
            return _reader
        except Exception:
            app.logger.exception("Failed to initialize GeoIP reader from %s", DB_PATH)
            return None


def _extract_client_ip():
    if request.args.get("ip"):
        return request.args.get("ip", "").strip()

    remote_addr = _parse_ip(request.environ.get("REMOTE_ADDR", ""))
    use_proxy_headers = _is_trusted_proxy(remote_addr)

    if use_proxy_headers:
        cf_ip = _parse_ip(request.environ.get("HTTP_CF_CONNECTING_IP", ""))
        if cf_ip is not None:
            return str(cf_ip)

        x_real_ip = _parse_ip(request.environ.get("HTTP_X_REAL_IP", ""))
        if x_real_ip is not None:
            return str(x_real_ip)

        xff = request.environ.get("HTTP_X_FORWARDED_FOR", "").strip()
        if xff:
            candidates = []
            for value in xff.split(","):
                parsed = _parse_ip(value)
                if parsed is not None:
                    candidates.append(parsed)

            for candidate in candidates:
                if _is_public_ip(candidate):
                    return str(candidate)

            if candidates:
                return str(candidates[0])

    if remote_addr is not None:
        return str(remote_addr)

    return ""


def _validate_ip(raw_ip):
    if not raw_ip:
        return None
    try:
        return str(ipaddress.ip_address(raw_ip))
    except ValueError:
        return None


@app.route("/health", methods=["GET"])
def health():
    return "OK", 200


@app.route("/", methods=["GET"])
def lookup_ip():
    reader = _get_reader()
    if reader is None:
        return jsonify({"error": "GeoIP database is not available on the server."}), 500

    raw_ip = _extract_client_ip()
    ip_value = _validate_ip(raw_ip)
    if ip_value is None:
        return jsonify({"error": "Invalid or missing IP address."}), 400

    try:
        result = reader.city(ip_value)
        return (
            jsonify(
                {
                    "ip": ip_value,
                    "country": result.country.name,
                    "city": result.city.name,
                    "iso_code": result.country.iso_code,
                    "latitude": result.location.latitude,
                    "longitude": result.location.longitude,
                    "timezone": result.location.time_zone,
                }
            ),
            200,
        )
    except AddressNotFoundError:
        return jsonify({"error": "IP address not found in GeoIP database."}), 404
    except Exception:
        app.logger.exception("Unhandled error during GeoIP lookup")
        return jsonify({"error": "Internal server error."}), 500


@app.errorhandler(404)
def not_found(_):
    return jsonify({"error": "Not found."}), 404


@app.errorhandler(500)
def internal_server_error(_):
    return jsonify({"error": "Internal server error."}), 500


# Warm the reader at startup to surface DB availability issues early.
_get_reader()
_trusted_proxy_networks = _load_trusted_proxy_networks()


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)
