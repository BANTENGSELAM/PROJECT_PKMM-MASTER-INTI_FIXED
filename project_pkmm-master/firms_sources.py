"""NASA FIRMS multi-source definitions and CSV parsing helpers.

Official FIRMS area-API source identifiers covered here:

* ``VIIRS_SNPP_NRT``   -- VIIRS Suomi-NPP Near Real-Time
* ``VIIRS_NOAA20_NRT`` -- VIIRS NOAA-20 Near Real-Time
* ``VIIRS_NOAA21_NRT`` -- VIIRS NOAA-21 Near Real-Time
* ``MODIS_NRT``        -- MODIS Near Real-Time (Terra / Aqua)

The parsers deliberately keep source identity attached to every detection.
A thermal anomaly is not a confirmed wildfire; this module never creates
coordinates, confidence values, or detections that are absent from the CSV.
"""

from __future__ import annotations

import csv
import io
import math
from datetime import datetime, timezone

# Ordered mapping of official NASA FIRMS source identifiers. ``confidence``
# selects the documented field convention for that product.
SUPPORTED_SOURCES = {
    "VIIRS_SNPP_NRT": {
        "label": "VIIRS S-NPP NRT",
        "instrument": "VIIRS",
        "default_satellite": "N",
        "confidence": "viirs",
    },
    "VIIRS_NOAA20_NRT": {
        "label": "VIIRS NOAA-20 NRT",
        "instrument": "VIIRS",
        "default_satellite": "N20",
        "confidence": "viirs",
    },
    "VIIRS_NOAA21_NRT": {
        "label": "VIIRS NOAA-21 NRT",
        "instrument": "VIIRS",
        "default_satellite": "N21",
        "confidence": "viirs",
    },
    "MODIS_NRT": {
        "label": "MODIS NRT",
        "instrument": "MODIS",
        "default_satellite": "Terra/Aqua",
        "confidence": "modis",
    },
}

# All supported NRT products are queried by default. Order is deterministic so
# that API responses and tests remain stable.
DEFAULT_SOURCES = (
    "VIIRS_SNPP_NRT",
    "VIIRS_NOAA20_NRT",
    "VIIRS_NOAA21_NRT",
    "MODIS_NRT",
)

REQUIRED_COLUMNS = ("latitude", "longitude", "acq_date", "acq_time")

# Coordinates are rounded to four decimal places (~11 m at the equator) before
# duplicate comparison. Detections from different sources are never merged,
# even when geographically close, because source identity is part of the key.
COORDINATE_DECIMALS = 4


def source_label(source_id):
    """Return the human-readable label for a supported source."""
    return SUPPORTED_SOURCES[source_id]["label"]


def normalize_confidence(raw_value, convention):
    """Normalize product-specific confidence to ``l`` / ``n`` / ``h``.

    VIIRS NRT CSVs use the documented letter scale (low, nominal, high).
    MODIS NRT CSVs use a 0-100 integer scale. The raw value is always preserved
    separately by :func:`parse_firms_csv`; this helper only provides the
    categorical value used by existing UI filters and notification rules.

    MODIS thresholds follow NASA FIRMS guidance: <30 low, 30-80 nominal,
    >80 high.
    """
    if raw_value is None:
        return None
    text = str(raw_value).strip()
    if not text:
        return None

    lowered = text.lower()
    if convention == "viirs" and lowered in ("l", "n", "h"):
        return lowered

    try:
        value = float(text)
    except (TypeError, ValueError):
        return lowered
    if not math.isfinite(value):
        return None
    if value > 80:
        return "h"
    if value >= 30:
        return "n"
    return "l"


def _to_float(value):
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    try:
        number = float(text)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


def _normalize_time(value):
    text = str(value or "").strip()
    if not text:
        return ""
    # Some products may emit a decimal component; acquisition time is HHMM.
    text = text.split(".", 1)[0]
    return text.zfill(4)


def _acquired_at(date_text, time_text):
    if not date_text or not time_text:
        return None
    try:
        acquired = datetime.strptime(date_text + time_text, "%Y-%m-%d%H%M")
    except ValueError:
        return None
    return acquired.replace(tzinfo=timezone.utc).isoformat()


def parse_firms_csv(text, source_id, in_indonesia):
    """Parse one FIRMS area CSV response for a known source.

    ``in_indonesia`` is injected so this module stays independent from the
    Flask application's boundary loader. Returns a report with retained points
    and row-level skip counts. Raises ``ValueError`` when the response is not a
    usable FIRMS CSV (for example an error body or missing columns).
    """
    if source_id not in SUPPORTED_SOURCES:
        raise ValueError("Sumber FIRMS tidak didukung: %s" % source_id)

    meta = SUPPORTED_SOURCES[source_id]
    reader = csv.DictReader(io.StringIO(text or ""))
    fieldnames = [str(name).strip() for name in (reader.fieldnames or [])]
    reader.fieldnames = fieldnames

    missing = [name for name in REQUIRED_COLUMNS if name not in fieldnames]
    if missing:
        raise ValueError(
            "Respons %s tidak valid: kolom %s tidak ditemukan."
            % (meta["label"], ", ".join(missing))
        )

    points = []
    skipped_invalid = 0
    skipped_outside = 0
    total_rows = 0

    for row in reader:
        total_rows += 1
        try:
            lat = float(str(row.get("latitude") or "").strip())
            lon = float(str(row.get("longitude") or "").strip())
        except (TypeError, ValueError):
            skipped_invalid += 1
            continue
        if (
            not math.isfinite(lat)
            or not math.isfinite(lon)
            or not (-90 <= lat <= 90)
            or not (-180 <= lon <= 180)
        ):
            skipped_invalid += 1
            continue
        if not in_indonesia(lon, lat):
            skipped_outside += 1
            continue

        date_text = str(row.get("acq_date") or "").strip()
        time_text = _normalize_time(row.get("acq_time"))
        confidence_raw = row.get("confidence")
        confidence_text = (
            str(confidence_raw).strip()
            if confidence_raw is not None
            else ""
        )
        satellite = str(row.get("satellite") or "").strip()
        instrument = str(row.get("instrument") or "").strip()

        points.append(
            {
                "lat": lat,
                "lon": lon,
                "confidence": normalize_confidence(
                    confidence_raw, meta["confidence"]
                ),
                "confidence_raw": confidence_text or None,
                "frp": _to_float(row.get("frp")),
                "date": date_text or None,
                "time": time_text,
                "satellite": satellite or meta["default_satellite"],
                "instrument": instrument or meta["instrument"],
                "daynight": str(row.get("daynight") or "").strip() or None,
                "source": source_id,
                "source_label": meta["label"],
                "acquired_at": _acquired_at(date_text, time_text),
            }
        )

    return {
        "points": points,
        "total_rows": total_rows,
        "skipped_invalid": skipped_invalid,
        "skipped_outside": skipped_outside,
    }


def hotspot_identity(point):
    """Return the documented duplicate-identity key for one hotspot.

    Identity is ``(source, satellite, instrument, acq_date, acq_time, lat4dp,
    lon4dp)``. Different satellites observing the same fire at the same minute
    are retained as separate, source-labelled records. Repeating the same row
    within one source is a duplicate.
    """
    return (
        str(point.get("source") or ""),
        str(point.get("satellite") or ""),
        str(point.get("instrument") or ""),
        str(point.get("date") or ""),
        str(point.get("time") or ""),
        format(float(point["lat"]), ".%df" % COORDINATE_DECIMALS),
        format(float(point["lon"]), ".%df" % COORDINATE_DECIMALS),
    )


def deduplicate_hotspots(points):
    """Remove exact duplicate records while preserving first-seen order."""
    seen = set()
    unique = []
    removed = 0
    for point in points:
        identity = hotspot_identity(point)
        if identity in seen:
            removed += 1
            continue
        seen.add(identity)
        unique.append(point)
    return unique, removed
