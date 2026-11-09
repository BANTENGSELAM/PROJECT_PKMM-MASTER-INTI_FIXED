import os
from pathlib import Path
import server

# Verify server app is configured with key from .env
client = server.app.test_client()

# 1. Test CSV Hotspots endpoint
print("=== 1. Testing /api/hotspots (Live CSV) ===")
res_csv = client.get('/api/hotspots?days=1')
print(f"Status: {res_csv.status_code}")
if res_csv.status_code == 200:
    data = res_csv.get_json()
    points = data.get('points', [])
    print(f"Points count: {len(points)}")
    print(f"Source: {data.get('source')}")
    print(f"Retrieved at: {data.get('retrieved_at')}")
    if points:
        first = points[0]
        print(f"Sample point: lat={first.get('lat')}, lon={first.get('lon')}, frp={first.get('frp')}, conf={first.get('confidence')}")
        assert -12 <= first.get('lat') <= 7 and 94 <= first.get('lon') <= 142, "Coordinates must be in Indonesia"
else:
    print("Error:", res_csv.get_json())

# 2. Test all 8 WMS layers via /api/firms/wms
print("\n=== 2. Testing /api/firms/wms (All 8 layers) ===")
layers = [
    "fires_viirs_24",
    "fires_viirs_48",
    "fires_viirs_72",
    "fires_viirs_7",
    "fires_modis_24",
    "fires_modis_48",
    "fires_modis_72",
    "fires_modis_7",
]

bbox = "100,-5,110,5"
for lyr in layers:
    url = f"/api/firms/wms?SERVICE=WMS&REQUEST=GetMap&LAYERS={lyr}&STYLES=&FORMAT=image/png&TRANSPARENT=TRUE&HEIGHT=256&WIDTH=256&BBOX={bbox}&SRS=EPSG:4326"
    res = client.get(url)
    ct = res.headers.get("Content-Type", "")
    is_png = res.data[:8] == b'\x89PNG\r\n\x1a\n'
    print(f"Layer {lyr:16}: HTTP {res.status_code}, Content-Type: {ct}, Size: {len(res.data)} bytes, Valid PNG: {is_png}")
    # Verify MAP_KEY is nowhere in response
    key = os.getenv('FIRMS_MAP_KEY', '')
    if key:
        assert key.encode() not in res.data, "MAP_KEY leaked in data!"
        assert key not in str(res.headers), "MAP_KEY leaked in headers!"

