import unittest

import esridump.cli

class TestEsriDumpCommandline(unittest.TestCase):
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
