import logging
import mock
import os
import re
import responses
import unittest

import esridump.cli

class TestEsriDumpCommandlineHelpers(unittest.TestCase):
    def test_collect_headers(self):
        self.assertDictEqual(
            esridump.cli._collect_headers(['Content-Type: application/json']),
            {
                "Content-Type": "application/json"
            }
        )

    def test_collect_params(self):
        self.assertDictEqual(
            esridump.cli._collect_params(['outFields=PIN14']),
            {
                "outFields": "PIN14"
            }
        )


class TestEsriDumpCommandlineMain(unittest.TestCase):
    def setUp(self):
        self.responses = responses.RequestsMock()
        self.responses.start()

        self.add_fixture_response(
            '.*f=json.*',
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

        self.patcher = mock.patch('esridump.cli._parse_args')
        self.mock_parseargs = self.patcher.start()
        self.mock_outfile = mock.MagicMock()
        self.parse_return = mock.MagicMock()
        self.parse_return.url = 'http://example.com'
        self.parse_return.outfile = self.mock_outfile
        self.parse_return.loglevel = logging.ERROR
        self.parse_return.jsonlines = False
        self.parse_return.fields = None
        self.parse_return.request_geometry = True
        self.parse_return.headers = []
        self.parse_return.params = []
        self.parse_return.proxy = None
        self.mock_parseargs.return_value = self.parse_return

        self.fake_url = 'http://example.com'

    def tearDown(self):
        self.patcher.stop()
        self.responses.stop(allow_assert=False)
        self.responses.reset()

    def add_fixture_response(self, url_re, file, method='POST', **kwargs):
        with open(os.path.join('tests/fixtures', file), 'r') as f:
            self.responses.add(
                method=method,
                url=re.compile(url_re),
                body=f.read(),
                match_querystring=True,
                **kwargs
            )

    def test_cli_simple(self):
        esridump.cli.main()

        # Make sure it has the FeatureCollection "header" and footer
        self.mock_outfile.write.assert_any_call('{"type":"FeatureCollection","features":[\n')
        self.mock_outfile.write.assert_any_call(']}')
        self.assertEqual(self.mock_outfile.write.call_count, 14)

    def test_cli_jsonlines(self):
        self.parse_return.jsonlines = True

        esridump.cli.main()

        # jsonlines won't have FeatureCollection wrapper
        self.assertEqual(self.mock_outfile.write.call_count, 12)

    def test_cli_override_where(self):
        self.parse_return.params = ['where=foo=bar']

        esridump.cli.main()

        self.assertIn('where=foo%3Dbar', self.responses.calls[2].request.url)
        self.assertIn('where=%28OBJECTID+%3E%3D+70193+AND+OBJECTID+%3C%3D+70307%29+AND+%28foo%3Dbar%29', self.responses.calls[3].request.body)
        self.assertEqual(self.mock_outfile.write.call_count, 14)
