"""Independent tests for the NASA FIRMS WMS proxy blueprint.

Mocks all external NASA requests. Never uses a real secret.
"""
import os
import unittest
from unittest.mock import patch

import requests

import server
import firms_wms


class FakeResponse:
    def __init__(self, content=b'\x89PNG\r\n\x1a\n', status_code=200,
                 headers=None):
        self.content = content
        self.status_code = status_code
        self.headers = dict(headers or {})
        if 'Content-Type' not in self.headers:
            self.headers['Content-Type'] = 'image/png'


SUPPORTED_LAYERS = (
    'fires_viirs_24', 'fires_viirs_48', 'fires_viirs_72', 'fires_viirs_7',
    'fires_modis_24', 'fires_modis_48', 'fires_modis_72', 'fires_modis_7',
)

FIRMS_HOST = 'firms.modaps.eosdis.nasa.gov'
FIRMS_PATH = '/mapserver/wms/fires/'


class WmsBlueprintTests(unittest.TestCase):
    def test_blueprint_registered(self):
        self.assertIn('firms_wms', server.app.blueprints)
        rules = [rule.rule for rule in server.app.url_map.iter_rules()]
        self.assertIn('/api/firms/wms', rules)

    def test_route_responds_to_get(self):
        response = self.client.get('/api/firms/wms?SERVICE=WMS&REQUEST=GetMap&LAYERS=fires_viirs_24')
        self.assertNotEqual(response.status_code, 405)

    @property
    def client(self):
        return server.app.test_client()


class WmsProxyTests(unittest.TestCase):
    def setUp(self):
        self.client = server.app.test_client()

    def _call(self, query):
        return self.client.get('/api/firms/wms?' + query)

    def test_blueprint_and_route(self):
        self.assertIn('firms_wms', server.app.blueprints)
        rules = [rule.rule for rule in server.app.url_map.iter_rules()]
        self.assertIn('/api/firms/wms', rules)

    def test_map_key_in_path_not_query(self):
        captured = {}

        def fake_get(url, **kwargs):
            captured['url'] = url
            return FakeResponse()

        with patch.dict(os.environ, {'FIRMS_MAP_KEY': 'dummy-key'}), \
                patch('firms_wms.requests.get', side_effect=fake_get):
            response = self._call(
                'SERVICE=WMS&REQUEST=GetMap&LAYERS=fires_viirs_24&'
                'FORMAT=image/png&WIDTH=256&HEIGHT=256&'
                'BBOX=-180,-90,180,90&CRS=EPSG:3857'
            )

        self.assertEqual(response.status_code, 200)
        url = captured['url']
        self.assertIn('https://%s%s' % (FIRMS_HOST, FIRMS_PATH), url)
        self.assertIn('/dummy-key/fires_viirs_24/', url)
        # MAP_KEY must not appear in the query string.
        if '?' in url:
            self.assertNotIn('dummy-key', url.split('?', 1)[1])

    def test_map_key_not_exposed_in_response(self):
        def fake_get(url, **kwargs):
            return FakeResponse(content=b'\x89PNG\r\n\x1a\n')

        with patch.dict(os.environ, {'FIRMS_MAP_KEY': 'secret-key-123'}), \
                patch('firms_wms.requests.get', side_effect=fake_get):
            response = self._call(
                'SERVICE=WMS&REQUEST=GetMap&LAYERS=fires_viirs_24&FORMAT=image/png'
            )

        self.assertEqual(response.status_code, 200)
        self.assertNotIn(b'secret-key-123', response.data)
        self.assertNotIn('secret-key-123', str(response.headers))

    def test_all_supported_layers(self):
        def fake_get(url, **kwargs):
            captured['url'] = url
            return FakeResponse()

        captured = {}
        with patch.dict(os.environ, {'FIRMS_MAP_KEY': 'key'}), \
                patch('firms_wms.requests.get', side_effect=fake_get):
            for layer in SUPPORTED_LAYERS:
                captured.clear()
                response = self._call(
                    'SERVICE=WMS&REQUEST=GetMap&LAYERS=%s&FORMAT=image/png' % layer
                )
                self.assertEqual(response.status_code, 200, layer)
                self.assertIn('/key/%s/' % layer, captured['url'], layer)

    def test_unsupported_layer_rejected(self):
        with patch.dict(os.environ, {'FIRMS_MAP_KEY': 'key'}):
            response = self._call(
                'SERVICE=WMS&REQUEST=GetMap&LAYERS=fires_unknown&FORMAT=image/png'
            )
        self.assertEqual(response.status_code, 400)

    def test_missing_layers_rejected(self):
        with patch.dict(os.environ, {'FIRMS_MAP_KEY': 'key'}):
            response = self._call('SERVICE=WMS&REQUEST=GetMap&FORMAT=image/png')
        self.assertEqual(response.status_code, 400)

    def test_missing_map_key(self):
        with patch.dict(os.environ, {'FIRMS_MAP_KEY': ''}):
            response = self._call(
                'SERVICE=WMS&REQUEST=GetMap&LAYERS=fires_viirs_24&FORMAT=image/png'
            )
        self.assertEqual(response.status_code, 400)
        self.assertIn('MAP_KEY', response.get_json()['error'])

    def test_lowercase_wms_parameters(self):
        def fake_get(url, **kwargs):
            captured['url'] = url
            return FakeResponse()

        captured = {}
        with patch.dict(os.environ, {'FIRMS_MAP_KEY': 'key'}), \
                patch('firms_wms.requests.get', side_effect=fake_get):
            response = self._call(
                'service=wms&request=getmap&layers=fires_viirs_24&'
                'format=image/png&width=256&height=256&'
                'bbox=-180,-90,180,90&crs=EPSG:3857'
            )
        self.assertEqual(response.status_code, 200)
        self.assertIn('/key/fires_viirs_24/', captured['url'])

    def test_uppercase_wms_parameters(self):
        def fake_get(url, **kwargs):
            captured['url'] = url
            return FakeResponse()

        captured = {}
        with patch.dict(os.environ, {'FIRMS_MAP_KEY': 'key'}), \
                patch('firms_wms.requests.get', side_effect=fake_get):
            response = self._call(
                'SERVICE=WMS&REQUEST=GetMap&LAYERS=fires_modis_7&'
                'FORMAT=image/png&WIDTH=512&HEIGHT=512&'
                'BBOX=94,-12,142,7&CRS=EPSG:3857'
            )
        self.assertEqual(response.status_code, 200)
        self.assertIn('/key/fires_modis_7/', captured['url'])

    def test_mixed_case_wms_parameters(self):
        def fake_get(url, **kwargs):
            captured['url'] = url
            return FakeResponse()

        captured = {}
        with patch.dict(os.environ, {'FIRMS_MAP_KEY': 'key'}), \
                patch('firms_wms.requests.get', side_effect=fake_get):
            response = self._call(
                'Service=WMS&Request=GetMap&LaYeRs=fires_viirs_48&'
                'Format=image/png&Transparent=true'
            )
        self.assertEqual(response.status_code, 200)
        self.assertIn('/key/fires_viirs_48/', captured['url'])

    def test_query_parameters_forwarded(self):
        captured = {}

        def fake_get(url, **kwargs):
            captured['url'] = url
            return FakeResponse()

        with patch.dict(os.environ, {'FIRMS_MAP_KEY': 'key'}), \
                patch('firms_wms.requests.get', side_effect=fake_get):
            self._call(
                'SERVICE=WMS&REQUEST=GetMap&LAYERS=fires_viirs_24&'
                'FORMAT=image/png&WIDTH=256&HEIGHT=256&'
                'BBOX=100,-5,110,5&CRS=EPSG:3857&STYLES='
            )
        url = captured['url']
        query = url.split('?', 1)[1] if '?' in url else ''
        self.assertIn('WIDTH=256', query)
        self.assertIn('HEIGHT=256', query)
        self.assertIn('BBOX=100%2C-5%2C110%2C5', query)
        self.assertIn('FORMAT=image%2Fpng', query)

    def test_no_unrestricted_upstream_host(self):
        captured = {}

        def fake_get(url, **kwargs):
            captured['url'] = url
            return FakeResponse()

        with patch.dict(os.environ, {'FIRMS_MAP_KEY': 'key'}), \
                patch('firms_wms.requests.get', side_effect=fake_get):
            self._call(
                'SERVICE=WMS&REQUEST=GetMap&LAYERS=fires_viirs_24&FORMAT=image/png'
            )
        url = captured['url']
        self.assertIn(FIRMS_HOST, url)
        for evil in ('evil.example.com', '169.254.169.254', 'localhost'):
            self.assertNotIn(evil, url)

    def test_upstream_timeout(self):
        def fake_get(url, **kwargs):
            raise requests.Timeout()

        with patch.dict(os.environ, {'FIRMS_MAP_KEY': 'key'}), \
                patch('firms_wms.requests.get', side_effect=fake_get):
            response = self._call(
                'SERVICE=WMS&REQUEST=GetMap&LAYERS=fires_viirs_24&FORMAT=image/png'
            )
        self.assertEqual(response.status_code, 504)

    def test_upstream_connection_failure(self):
        def fake_get(url, **kwargs):
            raise requests.ConnectionError('boom')

        with patch.dict(os.environ, {'FIRMS_MAP_KEY': 'key'}), \
                patch('firms_wms.requests.get', side_effect=fake_get):
            response = self._call(
                'SERVICE=WMS&REQUEST=GetMap&LAYERS=fires_viirs_24&FORMAT=image/png'
            )
        self.assertEqual(response.status_code, 502)

    def test_upstream_error_response(self):
        def fake_get(url, **kwargs):
            return FakeResponse(status_code=404, headers={'Content-Type': 'text/xml'})

        with patch.dict(os.environ, {'FIRMS_MAP_KEY': 'key'}), \
                patch('firms_wms.requests.get', side_effect=fake_get):
            response = self._call(
                'SERVICE=WMS&REQUEST=GetMap&LAYERS=fires_viirs_24&FORMAT=image/png'
            )
        self.assertEqual(response.status_code, 502)

    def test_upstream_non_image_200(self):
        def fake_get(url, **kwargs):
            return FakeResponse(status_code=200, headers={'Content-Type': 'application/json'})

        with patch.dict(os.environ, {'FIRMS_MAP_KEY': 'key'}), \
                patch('firms_wms.requests.get', side_effect=fake_get):
            response = self._call(
                'SERVICE=WMS&REQUEST=GetMap&LAYERS=fires_viirs_24&FORMAT=image/png'
            )
        self.assertEqual(response.status_code, 502)

    def test_valid_png_response(self):
        png = b'\x89PNG\r\n\x1a\n' + b'\x00' * 50

        def fake_get(url, **kwargs):
            return FakeResponse(content=png)

        with patch.dict(os.environ, {'FIRMS_MAP_KEY': 'key'}), \
                patch('firms_wms.requests.get', side_effect=fake_get):
            response = self._call(
                'SERVICE=WMS&REQUEST=GetMap&LAYERS=fires_modis_24&FORMAT=image/png'
            )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data, png)
        self.assertIn('image/png', response.headers.get('Content-Type', ''))


if __name__ == '__main__':
    unittest.main()
