import unittest

from esridump.dumper import EsriDumper

class TestEsriJsonToGeoJson(unittest.TestCase):
    def setUp(self):
        self.maxDiff = None

    def test_point(self):
        d = EsriDumper('http://example.com')

        in_json = {
            "geometry": {
                "x": 496814.6,
                "y": 265006.2
            },
            "attributes": {
                "string_prop": 151,
                "float_prop": 1004.623,
                "str_prop": "County Road",
                "str_int_prop": "16",
            }
        }
        out_json = d._build_geojson('esriGeometryPoint', in_json)

        expected_geojson = {
            "type": "Feature",
            "properties": {
                "string_prop": 151,
                "float_prop": 1004.623,
                "str_prop": "County Road",
                "str_int_prop": "16",
            },
            "geometry": {
                "type": "Point",
                "coordinates": [496814.6, 265006.2],
            }
        }
        self.assertDictEqual(out_json, expected_geojson)

    def test_empty_point(self):
        d = EsriDumper('http://example.com')

        in_json = {
            "geometry": {
                "x": None,
            },
        }

        out_json = d._build_geojson('esriGeometryPoint', in_json)

        expected_geojson = {
            "type": "Feature",
            "geometry": {
                "type": "Point",
                "coordinates": [],
            }
        }
        self.assertDictEqual(out_json, expected_geojson)

    def test_polyline(self):
        d = EsriDumper('http://example.com')

        in_json = {
            "geometry": {
                "paths" : [
                    [[-97.06138,32.837], [-97.06133,32.836], [-97.06124,32.834], [-97.06127,32.832]],
                    [[-97.06326,32.759], [-97.06298,32.755]]
                ],
            }
        }
        out_json = d._build_geojson('esriGeometryPolyline', in_json)

        expected_geojson = {
            "type": "Feature",
            "geometry": {
                "type": "LineString",
                "coordinates": [
                    [ [-97.06138,32.837], [-97.06133,32.836], [-97.06124,32.834], [-97.06127,32.832] ],
                    [ [-97.06326,32.759], [-97.06298,32.755] ]
                ],
            }
        }
        self.assertDictEqual(out_json, expected_geojson)

    def test_polygon(self):
        d = EsriDumper('http://example.com')

        in_json = {
            "geometry": {
                "rings" : [
                    [[-97.06138,32.837], [-97.06133,32.836], [-97.06124,32.834], [-97.06127,32.832], [-97.06138,32.837]],
                    [[-97.06326,32.759], [-97.06298,32.755], [-97.06153,32.749], [-97.06326,32.759]]
                ],
            }
        }
        out_json = d._build_geojson('esriGeometryPolygon', in_json)

        expected_geojson = {
            "type": "Feature",
            "geometry": {
                "type": "Polygon",
                "coordinates": [
                    [[-97.06138,32.837], [-97.06133,32.836], [-97.06124,32.834], [-97.06127,32.832], [-97.06138,32.837]],
                    [[-97.06326,32.759], [-97.06298,32.755], [-97.06153,32.749], [-97.06326,32.759]]
                ],
            }
        }
        self.assertDictEqual(out_json, expected_geojson)

    def test_empty_polygon(self):
        d = EsriDumper('http://example.com')

        in_json = {
            "geometry": {
                "rings" : [ ]
            },
        }

        out_json = d._build_geojson('esriGeometryPolygon', in_json)

        expected_geojson = {
            "type": "Feature",
            "geometry": {
                "type": "Polygon",
                "coordinates": [],
            }
        }
        self.assertDictEqual(out_json, expected_geojson)
