import unittest

from esridump import esri2geojson

class TestEsriJsonToGeoJson(unittest.TestCase):
    def setUp(self):
        self.maxDiff = None

    def assertEsriJsonBecomesGeoJson(self, esrijson, geojson):
        out_json = esri2geojson(esrijson)
        self.assertDictEqual(out_json, geojson)


class TestGeoJsonPointConversion(TestEsriJsonToGeoJson):
    def test_point(self):
        self.assertEsriJsonBecomesGeoJson(
            {
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
            },

            {
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
        )

    def test_multi_point(self):
        self.assertEsriJsonBecomesGeoJson(
            {
                "geometry": {
                    "points": [
                        [41.83, 71.01],
                        [56.95, 33.75],
                        [21.79, 36.56]
                    ],
                },
                "attributes": {
                    "string_prop": 151,
                    "float_prop": 1004.623,
                    "str_prop": "County Road",
                    "str_int_prop": "16",
                }
            },

            {
                "type": "Feature",
                "properties": {
                    "string_prop": 151,
                    "float_prop": 1004.623,
                    "str_prop": "County Road",
                    "str_int_prop": "16",
                },
                "geometry": {
                    "type": "MultiPoint",
                    "coordinates": [
                        [41.83, 71.01],
                        [56.95, 33.75],
                        [21.79, 36.56]
                    ]
                }
            }
        )

    def test_empty_point(self):
        self.assertEsriJsonBecomesGeoJson(
            {
                "geometry": {
                    "x": None,
                },
            },

            {
                "type": "Feature",
                "properties": None,
                "geometry": None
            }
        )


class TestGeoJsonLinestringConversion(TestEsriJsonToGeoJson):
    def test_linestring(self):
        self.assertEsriJsonBecomesGeoJson(
            {
                "geometry": {
                    "paths" : [
                        [[-97.06138,32.837], [-97.06133,32.836], [-97.06124,32.834], [-97.06127,32.832]]
                    ],
                }
            },

            {
                "type": "Feature",
                "properties": None,
                "geometry": {
                    "type": "LineString",
                    "coordinates": [
                        [-97.06138,32.837], [-97.06133,32.836], [-97.06124,32.834], [-97.06127,32.832]
                    ],
                }
            }
        )

    def test_multi_linestring(self):
        self.assertEsriJsonBecomesGeoJson(
            {
                "geometry": {
                    "paths" : [
                        [[-97.06138,32.837], [-97.06133,32.836], [-97.06124,32.834], [-97.06127,32.832]],
                        [[-97.06326,32.759], [-97.06298,32.755]]
                    ],
                }
            },

            {
                "type": "Feature",
                "properties": None,
                "geometry": {
                    "type": "MultiLineString",
                    "coordinates": [
                        [ [-97.06138,32.837], [-97.06133,32.836], [-97.06124,32.834], [-97.06127,32.832] ],
                        [ [-97.06326,32.759], [-97.06298,32.755] ]
                    ],
                }
            }
        )

    def test_real_linstring(self):
        self.assertEsriJsonBecomesGeoJson(
            {
                "attributes": {
                    "objectid":187,
                    "st_length(shape)":1322.4896687156252
                },
                "geometry":{
                    "paths":[
                        [[-95.42428663740543,39.743798710848658],[-95.424285648691338,39.744302699946864],[-95.424279518608387,39.747429247542691]]
                    ]
                }
            },

            {
                "type": "Feature",
                "properties": {
                    "objectid": 187,
                    "st_length(shape)": 1322.4896687156252
                },
                "geometry": {
                    "type": "LineString",
                    "coordinates": [
                        [-95.42428663740543, 39.74379871084866], [-95.42428564869134, 39.744302699946864], [-95.42427951860839, 39.74742924754269]
                    ]
                }
            }
        )


class TestGeoJsonPolygonConversion(TestEsriJsonToGeoJson):
    def test_polygon(self):
        self.assertEsriJsonBecomesGeoJson(
            {
                "geometry": {
                    "rings" : [
                        [[-97.06138,32.837], [-97.06133,32.836], [-97.06124,32.834], [-97.06127,32.832], [-97.06138,32.837]]
                    ],
                }
            },

            {
                "type": "Feature",
                "properties": None,
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [
                        [[-97.06138,32.837], [-97.06133,32.836], [-97.06124,32.834], [-97.06127,32.832], [-97.06138,32.837]]
                    ],
                }
            }
        )

    def test_polygon_close(self):
        # Esri-JSON allows polygons that aren't closed. GeoJSON requires them to be closed.
        self.assertEsriJsonBecomesGeoJson(
            {
                "geometry": {
                    "rings" : [
                        [[-97.06138,32.837], [-97.06133,32.836], [-97.06124,32.834], [-97.06127,32.832]]
                    ],
                }
            },

            {
                "type": "Feature",
                "properties": None,
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [
                        [[-97.06138,32.837], [-97.06133,32.836], [-97.06124,32.834], [-97.06127,32.832], [-97.06138,32.837]]
                    ],
                }
            }
        )

    def test_polygon_strip_invalid_rings(self):
        # Esri JSON allows rings with three points (A-B-A) that are essentially lines. GeoJSON doesn't.
        self.assertEsriJsonBecomesGeoJson(
            {
                "geometry": {
                    "rings" : [
                        [[-97.06138,32.837], [-97.06133,32.836], [-97.06124,32.834], [-97.06127,32.832], [-97.06138,32.837]],
                        [[-97.06326,32.759], [-97.06298,32.755], [-97.06326,32.759]]
                    ],
                }
            },

            {
                "type": "Feature",
                "properties": None,
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [
                        [[-97.06138,32.837], [-97.06133,32.836], [-97.06124,32.834], [-97.06127,32.832], [-97.06138,32.837]]
                    ],
                }
            }
        )

    def test_multi_polygon(self):
        self.assertEsriJsonBecomesGeoJson(
            {
                "geometry": {
                    "rings" : [
                        [[-97.06138,32.837], [-97.06133,32.836], [-97.06124,32.834], [-97.06127,32.832], [-97.06138,32.837]],
                        [[-97.06326,32.759], [-97.06298,32.755], [-97.06153,32.749], [-97.06326,32.759]]
                    ],
                }
            },

            {
                "type": "Feature",
                "properties": None,
                "geometry": {
                    "type": "MultiPolygon",
                    "coordinates": [
                        [[-97.06138,32.837], [-97.06133,32.836], [-97.06124,32.834], [-97.06127,32.832], [-97.06138,32.837]],
                        [[-97.06326,32.759], [-97.06298,32.755], [-97.06153,32.749], [-97.06326,32.759]]
                    ],
                }
            }
        )

    def test_multi_polygon_close(self):
        # We should close the rings of a multipolygon if they aren't closed already
        self.assertEsriJsonBecomesGeoJson(
            {
                "geometry": {
                    "rings" : [
                        [[-97.06138,32.837], [-97.06133,32.836], [-97.06124,32.834], [-97.06127,32.832], [-97.06138,32.837]],
                        [[-97.06326,32.759], [-97.06298,32.755], [-97.06153,32.749], [-97.06326,32.759]]
                    ],
                }
            },

            {
                "type": "Feature",
                "properties": None,
                "geometry": {
                    "type": "MultiPolygon",
                    "coordinates": [
                        [[-97.06138,32.837], [-97.06133,32.836], [-97.06124,32.834], [-97.06127,32.832], [-97.06138,32.837]],
                        [[-97.06326,32.759], [-97.06298,32.755], [-97.06153,32.749], [-97.06326,32.759]]
                    ],
                }
            }
        )

    def test_empty_polygon(self):
        self.assertEsriJsonBecomesGeoJson(
            {
                "geometry": {
                    "rings" : [ ]
                },
            },

            {
                "type": "Feature",
                "properties": None,
                "geometry": None
            }
        )
