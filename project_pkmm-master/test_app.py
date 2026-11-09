import os
import re
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import requests

import firms_sources
import server

ROOT = Path(__file__).resolve().parent

VIIRS_HEADER = (
    'latitude,longitude,bright_ti4,scan,track,acq_date,acq_time,'
    'satellite,instrument,confidence,version,bright_ti5,frp,daynight'
)
MODIS_HEADER = (
    'latitude,longitude,brightness,scan,track,acq_date,acq_time,'
    'satellite,instrument,confidence,version,bright_t31,frp,daynight'
)
VIIRS_ROW = (
    '-2.2,113.9,335.8,0.57,0.69,2026-11-08,325,N20,VIIRS,n,2.0NRT,292.31,4.05,D'
)
MODIS_ROW = (
    '-8.15986,114.24751,309.01,2.48,1.52,2026-11-08,119,Terra,MODIS,44,6.1NRT,294.43,19.85,D'
)
OUTSIDE_ROW = (
    '1.35,103.82,335.8,0.57,0.69,2026-11-08,325,N20,VIIRS,n,2.0NRT,292.31,4.05,D'
)


class CsvResponse:
    def __init__(self, text):
        self.text = text


def http_error(code=503):
    return requests.HTTPError('upstream error', response=SimpleNamespace(status_code=code))


def make_http(payloads, failures=None):
    failures = failures or {}

    def fake_http(url, **kwargs):
        source = re.search(r'/api/area/csv/[^/]+/([^/]+)/', url).group(1)
        if source in failures:
            raise failures[source]
        return CsvResponse(payloads[source])

    return fake_http


def clear_firms_cache():
    for key in list(server.CACHE):
        if isinstance(key, tuple) and key and key[0] == 'firms':
            server.CACHE.pop(key, None)


class AppTests(unittest.TestCase):
    def setUp(self):
        self.client = server.app.test_client()
        clear_firms_cache()

    def tearDown(self):
        clear_firms_cache()

    def test_page_and_status(self):
        with self.client.get('/') as response:
            self.assertEqual(response.status_code, 200)
        data = self.client.get('/api/status').get_json()
        self.assertEqual(len(data['features']), 10)
        self.assertIn('NDWI', data['features'])

    def test_missing_key_is_explicit(self):
        with patch.dict(os.environ, {'FIRMS_MAP_KEY': ''}):
            r = self.client.get('/api/hotspots')
        self.assertEqual(r.status_code, 400)
        self.assertIn('MAP_KEY', r.get_json()['error'])

    def test_indonesia_boundary(self):
        self.assertTrue(server.indonesia(113.9, -2.2))
        self.assertFalse(server.indonesia(103.82, 1.35))
        self.assertFalse(server.indonesia(0, 0))

    def test_reject_foreign_location(self):
        r = self.client.post('/api/predict', json={'lon':0,'lat':0,'start':'2025-01-01','end':'2025-01-02'})
        self.assertEqual(r.status_code, 400)

    def test_reject_missing_fields(self):
        self.assertEqual(self.client.post('/api/predict', json={}).status_code, 400)

    def test_actual_model_inference(self):
        values = dict(B2=635.5,B3=692,B4=790.5,B8=1325.5,B11=2117.5,B12=1728,NDVI=(1325.5-790.5)/(1325.5+790.5),NDWI=(692-1325.5)/(692+1325.5),longitude=111.8561,latitude=-3.4548)
        result = server.predict(values)
        self.assertIn(result['label'], result['classes'])
        self.assertAlmostEqual(sum(result['probabilities']), 1, places=6)
        self.assertEqual(len(result['probabilities']), 2)

    def test_firms_response(self):
        payload = VIIRS_HEADER + '\n' + VIIRS_ROW + '\n' + OUTSIDE_ROW + '\n'
        with patch.dict(os.environ, {'FIRMS_MAP_KEY':'test','FIRMS_SOURCES':'VIIRS_SNPP_NRT'}), \
                patch('server.http', side_effect=make_http({'VIIRS_SNPP_NRT': payload})) as fetch:
            r=self.client.get('/api/hotspots?days=1')
        fetch.assert_called_once_with(
            'https://firms.modaps.eosdis.nasa.gov/api/area/csv/test/VIIRS_SNPP_NRT/94,-12,142,7/1'
        )
        self.assertEqual(r.status_code, 200)
        data = r.get_json()
        self.assertEqual(len(data['points']), 1)
        self.assertEqual(data['status'], 'ok')
        self.assertEqual(data['points'][0]['source'], 'VIIRS_SNPP_NRT')
        self.assertEqual(data['points'][0]['source_label'], 'VIIRS S-NPP NRT')
        self.assertEqual(data['points'][0]['satellite'], 'N20')
        self.assertEqual(data['points'][0]['instrument'], 'VIIRS')
        self.assertEqual(data['points'][0]['confidence'], 'n')
        self.assertEqual(data['points'][0]['confidence_raw'], 'n')
        self.assertEqual(data['points'][0]['frp'], 4.05)
        self.assertEqual(data['points'][0]['time'], '0325')
        self.assertEqual(data['points'][0]['acquired_at'], '2026-11-08T03:25:00+00:00')


class FirmsParserTests(unittest.TestCase):
    def test_viirs_parser_preserves_source_metadata(self):
        payload = VIIRS_HEADER + '\n' + VIIRS_ROW + '\n'
        parsed = firms_sources.parse_firms_csv(payload, 'VIIRS_NOAA20_NRT', server.indonesia)
        self.assertEqual(parsed['total_rows'], 1)
        self.assertEqual(parsed['skipped_invalid'], 0)
        self.assertEqual(parsed['skipped_outside'], 0)
        point = parsed['points'][0]
        self.assertEqual(point['source'], 'VIIRS_NOAA20_NRT')
        self.assertEqual(point['source_label'], 'VIIRS NOAA-20 NRT')
        self.assertEqual(point['satellite'], 'N20')
        self.assertEqual(point['instrument'], 'VIIRS')
        self.assertEqual(point['confidence'], 'n')
        self.assertEqual(point['confidence_raw'], 'n')
        self.assertEqual(point['date'], '2026-11-08')
        self.assertEqual(point['time'], '0325')
        self.assertEqual(point['frp'], 4.05)
        self.assertEqual(point['daynight'], 'D')
        self.assertEqual(point['lat'], -2.2)
        self.assertEqual(point['lon'], 113.9)

    def test_noaa21_parser_uses_official_source_id(self):
        row = VIIRS_ROW.replace('N20', 'N21')
        payload = VIIRS_HEADER + '\n' + row + '\n'
        parsed = firms_sources.parse_firms_csv(payload, 'VIIRS_NOAA21_NRT', server.indonesia)
        self.assertEqual(parsed['points'][0]['source'], 'VIIRS_NOAA21_NRT')
        self.assertEqual(parsed['points'][0]['satellite'], 'N21')

    def test_modis_parser_normalizes_numeric_confidence(self):
        rows = [
            '-2.2,113.9,309.01,2.48,1.52,2026-11-08,119,Terra,MODIS,95,6.1NRT,294.43,19.85,D',
            '-2.3,114.0,309.01,2.48,1.52,2026-11-08,119,Terra,MODIS,44,6.1NRT,294.43,19.85,D',
            '-2.4,114.1,309.01,2.48,1.52,2026-11-08,119,Terra,MODIS,10,6.1NRT,294.43,19.85,D',
        ]
        payload = MODIS_HEADER + '\n' + '\n'.join(rows) + '\n'
        parsed = firms_sources.parse_firms_csv(payload, 'MODIS_NRT', server.indonesia)
        self.assertEqual([p['confidence'] for p in parsed['points']], ['h', 'n', 'l'])
        self.assertEqual([p['confidence_raw'] for p in parsed['points']], ['95', '44', '10'])
        self.assertEqual(parsed['points'][0]['instrument'], 'MODIS')
        self.assertEqual(parsed['points'][0]['source'], 'MODIS_NRT')

    def test_parser_handles_missing_optional_fields(self):
        header = 'latitude,longitude,acq_date,acq_time,satellite,instrument,confidence,frp'
        payload = header + '\n-2.2,113.9,2026-11-08,325,N20,VIIRS,,\n'
        parsed = firms_sources.parse_firms_csv(payload, 'VIIRS_NOAA20_NRT', server.indonesia)
        point = parsed['points'][0]
        self.assertIsNone(point['frp'])
        self.assertIsNone(point['confidence'])
        self.assertIsNone(point['confidence_raw'])
        self.assertEqual(point['time'], '0325')

    def test_parser_rejects_non_csv_and_missing_columns(self):
        for payload in ('Invalid MAP_KEY', 'latitude,longitude\n-2.2,113.9\n'):
            with self.assertRaises(ValueError):
                firms_sources.parse_firms_csv(payload, 'VIIRS_SNPP_NRT', server.indonesia)

    def test_parser_skips_invalid_and_outside_rows(self):
        rows = [
            'not-a-number,113.9,335.8,0.57,0.69,2026-11-08,325,N20,VIIRS,n,2.0NRT,292.31,4.05,D',
            OUTSIDE_ROW,
            VIIRS_ROW,
        ]
        payload = VIIRS_HEADER + '\n' + '\n'.join(rows) + '\n'
        parsed = firms_sources.parse_firms_csv(payload, 'VIIRS_SNPP_NRT', server.indonesia)
        self.assertEqual(len(parsed['points']), 1)
        self.assertEqual(parsed['skipped_invalid'], 1)
        self.assertEqual(parsed['skipped_outside'], 1)


class FirmsAggregationTests(unittest.TestCase):
    def setUp(self):
        self.client = server.app.test_client()
        clear_firms_cache()

    def tearDown(self):
        clear_firms_cache()

    def _hotspots(self, payloads, failures=None, sources=None, days=1):
        sources = sources or ','.join(payloads)
        with patch.dict(os.environ, {
            'FIRMS_MAP_KEY': 'test',
            'FIRMS_SOURCES': sources,
        }), patch('server.http', side_effect=make_http(payloads, failures)):
            return self.client.get('/api/hotspots?days=%s' % days)

    def test_multi_source_aggregation_and_metadata(self):
        payloads = {
            'VIIRS_NOAA20_NRT': VIIRS_HEADER + '\n' + VIIRS_ROW + '\n',
            'MODIS_NRT': MODIS_HEADER + '\n' + MODIS_ROW + '\n',
        }
        response = self._hotspots(payloads)
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertEqual(data['status'], 'ok')
        self.assertEqual(data['requested_source_count'], 2)
        self.assertEqual(data['successful_source_count'], 2)
        self.assertEqual(data['failed_source_count'], 0)
        self.assertEqual(len(data['points']), 2)
        self.assertEqual({p['source'] for p in data['points']},
                         {'VIIRS_NOAA20_NRT', 'MODIS_NRT'})
        self.assertEqual([s['status'] for s in data['sources']], ['ok', 'ok'])
        self.assertIn('VIIRS NOAA-20 NRT', data['source'])
        self.assertIn('MODIS NRT', data['source'])

    def test_partial_source_failure_keeps_successful_results(self):
        payloads = {
            'VIIRS_NOAA20_NRT': VIIRS_HEADER + '\n' + VIIRS_ROW + '\n',
            'MODIS_NRT': MODIS_HEADER + '\n',
        }
        failures = {'MODIS_NRT': http_error(503)}
        response = self._hotspots(payloads, failures=failures)
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertEqual(data['status'], 'partial')
        self.assertEqual(data['failed_source_count'], 1)
        self.assertEqual(len(data['points']), 1)
        self.assertEqual(data['points'][0]['source'], 'VIIRS_NOAA20_NRT')
        failed = [s for s in data['sources'] if s['status'] == 'error'][0]
        self.assertEqual(failed['source'], 'MODIS_NRT')
        self.assertEqual(failed['error'], 'HTTP 503')
        self.assertIn('Sebagian sumber', data['warning'])

    def test_successful_empty_response_is_not_safety(self):
        payloads = {
            'VIIRS_SNPP_NRT': VIIRS_HEADER + '\n',
            'MODIS_NRT': MODIS_HEADER + '\n',
        }
        response = self._hotspots(payloads)
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertEqual(data['status'], 'empty')
        self.assertEqual(data['points'], [])
        self.assertEqual(data['successful_source_count'], 2)
        self.assertIn('bukan jaminan', data['warning'])

    def test_complete_failure_returns_error_not_empty_success(self):
        payloads = {
            'VIIRS_SNPP_NRT': VIIRS_HEADER + '\n',
            'MODIS_NRT': MODIS_HEADER + '\n',
        }
        failures = {
            'VIIRS_SNPP_NRT': http_error(500),
            'MODIS_NRT': http_error(429),
        }
        response = self._hotspots(payloads, failures=failures)
        self.assertEqual(response.status_code, 502)
        data = response.get_json()
        self.assertEqual(data['status'], 'error')
        self.assertNotIn('points', data)
        self.assertEqual(len(data['sources']), 2)
        self.assertEqual({s['error'] for s in data['sources']}, {'HTTP 500', 'HTTP 429'})

    def test_duplicate_rows_removed_within_a_source(self):
        payload = VIIRS_HEADER + '\n' + VIIRS_ROW + '\n' + VIIRS_ROW + '\n'
        response = self._hotspots({'VIIRS_NOAA20_NRT': payload})
        data = response.get_json()
        self.assertEqual(len(data['points']), 1)
        self.assertEqual(data['duplicates_removed'], 1)

    def test_same_detection_retained_across_different_sources(self):
        payloads = {
            'VIIRS_NOAA20_NRT': VIIRS_HEADER + '\n' + VIIRS_ROW + '\n',
            'VIIRS_NOAA21_NRT': VIIRS_HEADER + '\n' + VIIRS_ROW.replace('N20', 'N21') + '\n',
        }
        response = self._hotspots(payloads)
        data = response.get_json()
        self.assertEqual(len(data['points']), 2)
        self.assertEqual(data['duplicates_removed'], 0)
        self.assertEqual({p['source'] for p in data['points']},
                         {'VIIRS_NOAA20_NRT', 'VIIRS_NOAA21_NRT'})

    def test_unknown_source_configuration_is_rejected(self):
        with patch.dict(os.environ, {'FIRMS_MAP_KEY': 'test', 'FIRMS_SOURCES': 'NOT_A_FIRMS_SOURCE'}):
            response = self.client.get('/api/hotspots?days=1')
        self.assertEqual(response.status_code, 400)
        self.assertIn('FIRMS_SOURCES', response.get_json()['error'])

    def test_default_source_set_matches_official_identifiers(self):
        with patch.dict(os.environ, {'FIRMS_SOURCES': ''}):
            self.assertEqual(server.firms_source_ids(), list(firms_sources.DEFAULT_SOURCES))
        self.assertEqual(
            set(firms_sources.DEFAULT_SOURCES),
            {'VIIRS_SNPP_NRT', 'VIIRS_NOAA20_NRT', 'VIIRS_NOAA21_NRT', 'MODIS_NRT'},
        )


class DependencyConfigurationTests(unittest.TestCase):
    def test_rasterio_is_declared_with_upper_bound(self):
        text = (ROOT / 'requirements.txt').read_text(encoding='utf-8')
        match = re.search(r'^rasterio\s*([<>=!~].*)$', text, re.MULTILINE)
        self.assertIsNotNone(match, 'rasterio must be declared in requirements.txt')
        self.assertIn('<', match.group(1), 'rasterio must have an upper bound')

    def test_gitignore_excludes_secrets_and_virtualenv(self):
        lines = {
            line.strip()
            for line in (ROOT / '.gitignore').read_text(encoding='utf-8').splitlines()
            if line.strip() and not line.strip().startswith('#')
        }
        self.assertIn('.env', lines)
        self.assertIn('.venv/', lines)
        self.assertIn('__pycache__/', lines)

    def test_env_example_documents_sources_without_real_secret(self):
        text = (ROOT / '.env.example').read_text(encoding='utf-8')
        self.assertIn('FIRMS_MAP_KEY=YOUR_MAP_KEY_HERE', text)
        self.assertIn('FIRMS_SOURCES=', text)
        self.assertIn('VIIRS_NOAA20_NRT', text)
        self.assertIn('MODIS_NRT', text)


if __name__ == '__main__':
    unittest.main()
