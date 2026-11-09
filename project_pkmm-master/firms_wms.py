"""Independent NASA FIRMS WMS proxy blueprint.

Proxies WMS GetMap requests to the NASA FIRMS mapserver. The FIRMS MAP_KEY
is embedded in the upstream URL path and is never exposed to the browser,
logged, or returned to the client.
"""
import os
from urllib.parse import urlencode

import requests
from flask import Blueprint, current_app, jsonify, request as flask_request, Response

firms_wms_bp = Blueprint("firms_wms", __name__)

FIRMS_WMS_HOST = "firms.modaps.eosdis.nasa.gov"
FIRMS_WMS_BASE_PATH = "/mapserver/wms/fires"

SUPPORTED_LAYERS = (
    "fires_viirs_24",
    "fires_viirs_48",
    "fires_viirs_72",
    "fires_viirs_7",
    "fires_modis_24",
    "fires_modis_48",
    "fires_modis_72",
    "fires_modis_7",
)

REQUEST_TIMEOUT = 30

_FORWARD_PARAMS = (
    "SERVICE",
    "REQUEST",
    "VERSION",
    "LAYERS",
    "STYLES",
    "FORMAT",
    "TRANSPARENT",
    "HEIGHT",
    "WIDTH",
    "BBOX",
    "CRS",
    "SRS",
)


def _map_key() -> str:
    return os.getenv("FIRMS_MAP_KEY", "").strip()


def _ci_params(req):
    """Case-insensitive view of query parameters (first value wins)."""
    params = {}
    for key in req.args:
        params[key] = req.args.get(key)
    return params


def _get_param(params, name, default=None):
    for key, value in params.items():
        if key.lower() == name.lower():
            return value
    return default


def _parse_layers(value):
    if value is None:
        return []
    return [part.strip() for part in str(value).split(",") if part.strip()]


@firms_wms_bp.route("/api/firms/wms", methods=["GET"])
def wms_proxy():
    key = _map_key()
    if not key:
        current_app.logger.warning("FIRMS WMS: MAP_KEY not configured")
        return jsonify(error="NASA FIRMS MAP_KEY belum dikonfigurasi."), 400

    params = _ci_params(flask_request)

    service = _get_param(params, "SERVICE")
    req = _get_param(params, "REQUEST")
    if service is None or str(service).strip().upper() != "WMS":
        return jsonify(error="Parameter WMS SERVICE wajib bernilai WMS."), 400
    if req is None or str(req).strip().upper() != "GETMAP":
        return jsonify(error="Parameter WMS REQUEST wajib bernilai GetMap."), 400

    layers_value = _get_param(params, "LAYERS")
    layers = _parse_layers(layers_value)
    if not layers:
        return jsonify(error="Parameter WMS LAYERS wajib diisi."), 400
    for layer in layers:
        if layer not in SUPPORTED_LAYERS:
            current_app.logger.warning("FIRMS WMS: unsupported layer %s", layer)
            return jsonify(error="Lapisan WMS tidak didukung: %s" % layer), 400

    upstream_url = "https://%s%s/%s/%s/" % (
        FIRMS_WMS_HOST,
        FIRMS_WMS_BASE_PATH,
        key,
        layers[0],
    )

    forward = {}
    for name in _FORWARD_PARAMS:
        value = _get_param(params, name)
        if value is not None:
            forward[name] = value
    forward.setdefault("VERSION", "1.1.1")

    query = urlencode(forward)
    if query:
        upstream_url = "%s?%s" % (upstream_url, query)

    try:
        upstream = requests.get(upstream_url, timeout=REQUEST_TIMEOUT)
    except requests.Timeout:
        current_app.logger.warning("FIRMS WMS upstream timeout")
        return jsonify(error="Layanan peta satelit melewati batas waktu."), 504
    except requests.RequestException as exc:  # connection error, etc.
        current_app.logger.warning(
            "FIRMS WMS upstream connection error: %s", type(exc).__name__
        )
        return jsonify(error="Tidak dapat terhubung ke layanan peta satelit."), 502

    content_type = upstream.headers.get("Content-Type", "") or ""
    looks_like_image = content_type.lower().startswith("image/")

    if not looks_like_image:
        current_app.logger.warning(
            "FIRMS WMS upstream returned non-image: %s %s",
            upstream.status_code,
            content_type,
        )
        return jsonify(error="Layanan peta satelit menanggapi dengan kesalahan."), 502

    excluded_headers = {
        "content-encoding",
        "content-length",
        "transfer-encoding",
        "connection",
    }
    headers = [
        (name, value)
        for name, value in upstream.headers.items()
        if name.lower() not in excluded_headers
    ]

    return Response(
        upstream.content,
        status=upstream.status_code,
        headers=headers,
        content_type=content_type or "image/png",
    )
