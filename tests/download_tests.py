import os
import responses
import unittest
import re

from esridump.dumper import EsriDumper
from esridump.errors import EsriDownloadError


class TestEsriDownload(unittest.TestCase):
    def setUp(self):
        self.responses = responses.RequestsMock()
        self.responses.start()

        self.fake_url = 'http://example.com'

    def tearDown(self):
        self.responses.stop()
        self.responses.reset()

    def add_fixture_response(self, url_re, file, method='POST', **kwargs):
        with open(os.path.join('tests/fixtures', file), 'rb') as f:
            self.responses.add(
                method=method,
                url=re.compile(url_re),
                body=f.read(),
                match_querystring=True,
                **kwargs
            )

    def test_object_id_enumeration(self):
        self.add_fixture_response(
            '.*/\?f=json.*',
            'us-ca-carson/us-ca-carson-metadata.json',
            method='GET',
        )
        self.add_fixture_response(
            '.*returnCountOnly=true.*',
            'us-ca-carson/us-ca-carson-count-only.json',
            method='GET',
        )
        self.add_fixture_response(
            '.*returnIdsOnly=true.*',
            'us-ca-carson/us-ca-carson-ids-only.json',
            method='GET',
        )
        self.add_fixture_response(
            '.*query.*',
            'us-ca-carson/us-ca-carson-0.json',
            method='POST',
        )

        dump = EsriDumper(self.fake_url)
        data = list(dump)

        self.assertEqual(6, len(data))

    def test_statistics_pagination(self):
        self.add_fixture_response(
            '.*/\?f=json.*',
            'us-ms-madison/us-ms-madison-metadata.json',
            method='GET',
        )
        self.add_fixture_response(
            '.*returnCountOnly=true.*',
            'us-ms-madison/us-ms-madison-count-only.json',
            method='GET',
        )
        self.add_fixture_response(
            '.*outStatistics=.*',
            'us-ms-madison/us-ms-madison-outStatistics.json',
            method='GET',
        )
        self.add_fixture_response(
            '.*returnIdsOnly=true.*',
            'us-ms-madison/us-ms-madison-ids-only.json',
            method='GET',
        )
        self.add_fixture_response(
            '.*returnIdsOnly=true.*',
            'us-ms-madison/us-ms-madison-ids-only.json',
            method='GET',
        )
        self.add_fixture_response(
            '.*query.*',
            'us-ms-madison/us-ms-madison-0.json',
            method='POST',
        )

        dump = EsriDumper(self.fake_url)
        data = list(dump)

        self.assertEqual(1, len(data))

    def test_advanced_query_pagination(self):
        self.add_fixture_response(
            '.*/\?f=json.*',
            'us-esri-test/us-esri-test-metadata.json',
            method='GET',
        )
        self.add_fixture_response(
            '.*returnCountOnly=true.*',
            'us-esri-test/us-esri-test-count-only.json',
            method='GET',
        )
        self.add_fixture_response(
            '.*query.*',
            'us-esri-test/us-esri-test-0.json',
            method='POST',
        )

        dump = EsriDumper(self.fake_url)
        data = list(dump)

        self.assertEqual(1000, len(data))

    def test_advanced_query_pagination_incorrect_outfield_name(self):
        self.add_fixture_response(
            '.*/\?f=json.*',
            'us-ca-tuolumne/us-ca-tuolumne-metadata.json',
            method='GET',
        )
        self.add_fixture_response(
            '.*returnCountOnly=true.*',
            'us-ca-tuolumne/us-ca-tuolumne-count-only.json',
            method='GET',
        )
        self.add_fixture_response(
            '.*outStatistics=.*',
            'us-ca-tuolumne/us-ca-tuolumne-statistics.json',
            method='GET',
        )
        self.add_fixture_response(
            '.*returnIdsOnly=true.*',
            'us-ca-tuolumne/us-ca-tuolumne-ids-only.json',
            method='GET',
        )
        self.add_fixture_response(
            '.*returnIdsOnly=true.*',
            'us-ca-tuolumne/us-ca-tuolumne-ids-only.json',
            method='GET',
        )
        self.add_fixture_response(
            '.*query.*',
            'us-ca-tuolumne/us-ca-tuolumne-0.json',
            method='POST',
        )

        dump = EsriDumper(self.fake_url)
        data = list(dump)

        self.assertEqual(15, len(data))

    def test_oid_enumeration_when_wrong_min_max_is_given(self):
        self.add_fixture_response(
            '.*/\?f=json.*',
            'us-fl-polk/us-fl-polk-metadata.json',
            method='GET',
        )
        self.add_fixture_response(
            '.*returnCountOnly=true.*',
            'us-fl-polk/us-fl-polk-count-only.json',
            method='GET',
        )
        self.add_fixture_response(
            '.*outStatistics=.*',
            'us-fl-polk/us-fl-polk-statistics.json',
            method='GET',
        )
        self.add_fixture_response(
            '.*returnIdsOnly=true.*',
            'us-fl-polk/us-fl-polk-ids-only.json',
            method='GET',
        )
        self.add_fixture_response(
            '.*returnIdsOnly=true.*',
            'us-fl-polk/us-fl-polk-ids-only.json',
            method='GET',
        )
        self.add_fixture_response(
            '.*query.*',
            'us-fl-polk/us-fl-polk-0.json',
            method='POST',
        )

        dump = EsriDumper(self.fake_url)
        data = list(dump)

        self.assertEqual(10, len(data))

    def test_oid_enumeration_when_statistics_doesnt_work(self):
        self.add_fixture_response(
            '.*/\?f=json.*',
            'us-mi-kent/us-mi-kent-metadata.json',
            method='GET',
        )
        self.add_fixture_response(
            '.*returnCountOnly=true.*',
            'us-mi-kent/us-mi-kent-count-only.json',
            method='GET',
        )
        self.add_fixture_response(
            '.*outStatistics=.*',
            'us-mi-kent/us-mi-kent-statistics.json',
            method='GET',
        )
        self.add_fixture_response(
            '.*returnIdsOnly=true.*',
            'us-mi-kent/us-mi-kent-ids-only.json',
            method='GET',
        )
        self.add_fixture_response(
            '.*query.*',
            'us-mi-kent/us-mi-kent-0.json',
            method='POST',
        )

        dump = EsriDumper(self.fake_url)
        data = list(dump)

        self.assertEqual(15, len(data))

    def test_coerces_floats_to_integer(self):
        self.add_fixture_response(
            '.*/\?f=json.*',
            'us-mo-columbia/us-mo-columbia-metadata.json',
            method='GET',
        )
        self.add_fixture_response(
            '.*returnCountOnly=true.*',
            'us-mo-columbia/us-mo-columbia-count-only.json',
            method='GET',
        )
        self.add_fixture_response(
            '.*returnIdsOnly=true.*',
            'us-mo-columbia/us-mo-columbia-ids-only.json',
            method='GET',
        )
        self.add_fixture_response(
            '.*query.*',
            'us-mo-columbia/us-mo-columbia-0.json',
            method='POST',
        )

        dump = EsriDumper(self.fake_url)
        data = list(dump)

        self.assertEqual(43, len(data))

    def test_proxy_requests(self):
        self.add_fixture_response(
            r'http://proxy/\?http://example\.com\?f=json',
            'us-mo-columbia/us-mo-columbia-metadata.json',
            method='GET',
        )
        self.add_fixture_response(
            r'http://proxy/\?http://example\.com/.*returnCountOnly=true.*',
            'us-mo-columbia/us-mo-columbia-count-only.json',
            method='GET',
        )
        self.add_fixture_response(
            r'http://proxy/\?http://example\.com/.*returnIdsOnly=true.*',
            'us-mo-columbia/us-mo-columbia-ids-only.json',
            method='GET',
        )
        self.add_fixture_response(
            r'http://proxy/\?http://example\.com/.*query.*',
            'us-mo-columbia/us-mo-columbia-0.json',
            method='POST',
        )

        dump = EsriDumper(self.fake_url, proxy='http://proxy?')
        data = list(dump)

        self.assertEqual(43, len(data))

    def test_handles_timeout_error(self):
        self.add_fixture_response(
            '.*/\?f=json.*',
            'us-mo-columbia/us-mo-columbia-metadata.json',
            method='GET',
        )
        self.add_fixture_response(
            '.*returnCountOnly=true.*',
            'us-mo-columbia/us-mo-columbia-count-only.json',
            method='GET',
        )
        self.add_fixture_response(
            '.*returnIdsOnly=true.*',
            'us-mo-columbia/us-mo-columbia-ids-only.json',
            method='GET',
        )
        import socket
        self.responses.add(
            method='POST',
            url=re.compile('.*query.*'),
            body=socket.timeout(),
        )

        dump = EsriDumper(self.fake_url)
        with self.assertRaisesRegexp(EsriDownloadError, "Timeout when connecting to URL"):
            list(dump)

    def test_handles_value_error(self):
        self.add_fixture_response(
            '.*/\?f=json.*',
            'us-mo-columbia/us-mo-columbia-metadata.json',
            method='GET',
        )
        self.add_fixture_response(
            '.*returnCountOnly=true.*',
            'us-mo-columbia/us-mo-columbia-count-only.json',
            method='GET',
        )
        self.add_fixture_response(
            '.*returnIdsOnly=true.*',
            'us-mo-columbia/us-mo-columbia-ids-only.json',
            method='GET',
        )
        self.responses.add(
            method='POST',
            url=re.compile('.*query.*'),
            body=ValueError(),
        )

        dump = EsriDumper(self.fake_url)
        with self.assertRaisesRegexp(EsriDownloadError, "Could not parse JSON"):
            list(dump)

    def test_handles_exception(self):
        self.add_fixture_response(
            '.*/\?f=json.*',
            'us-mo-columbia/us-mo-columbia-metadata.json',
            method='GET',
        )
        self.add_fixture_response(
            '.*returnCountOnly=true.*',
            'us-mo-columbia/us-mo-columbia-count-only.json',
            method='GET',
        )
        self.add_fixture_response(
            '.*returnIdsOnly=true.*',
            'us-mo-columbia/us-mo-columbia-ids-only.json',
            method='GET',
        )
        self.responses.add(
            method='POST',
            url=re.compile('.*query.*'),
            body=Exception(),
        )

        dump = EsriDumper(self.fake_url)
        with self.assertRaisesRegexp(EsriDownloadError, "Could not connect to URL"):
            list(dump)

    def test_geo_queries_when_oid_enumeration_doesnt_work(self):
        self.add_fixture_response(
            '.*/\?f=json.*',
            'us-il-cook/metadata.json',
            method='GET',
        )
        self.add_fixture_response(
            '.*returnCountOnly=true.*',
            'us-il-cook/count-only.json',
            method='GET',
        )
        self.add_fixture_response(
            '.*returnIdsOnly=true.*',
            'us-il-cook/ids-only.json',
            method='GET',
        )
        self.add_fixture_response(
            '.*geometry=.*',
            'us-il-cook/page-full.json',
            method='GET',
        )
        self.add_fixture_response(
            '.*geometry=.*',
            'us-il-cook/page-partial.json',
            method='GET',
        )
        self.add_fixture_response(
            '.*geometry=.*',
            'us-il-cook/page-partial.json',
            method='GET',
        )
        self.add_fixture_response(
            '.*geometry=.*',
            'us-il-cook/page-partial.json',
            method='GET',
        )
        self.add_fixture_response(
            '.*geometry=.*',
            'us-il-cook/page-partial.json',
            method='GET',
        )

        dump = EsriDumper(self.fake_url)
        data = list(dump)

        # Note that this count is entirely fake because of the deduping happening
        # This test is only designed to make sure we're splitting into smaller
        # bounding boxes.

        self.assertEqual(2, len(data))
