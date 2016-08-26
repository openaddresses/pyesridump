import unittest

from esridump.dumper import EsriDumper

class TestEsriJsonToGeoJson(unittest.TestCase):
    def setUp(self):
        self.maxDiff = None

    def assertEsriJsonBecomesGeoJson(self, geom_type, esrijson, geojson):
        d = EsriDumper('http://example.com')
        out_json = d._build_geojson(geom_type, esrijson)
        self.assertDictEqual(out_json, geojson)


class TestGeoJsonPointConversion(TestEsriJsonToGeoJson):
    def test_point(self):
        self.assertEsriJsonBecomesGeoJson(
            'esriGeometryPoint',
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
            'esriGeometryPoint',
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
                        [
                            [41.83, 71.01],
                            [56.95, 33.75],
                            [21.79, 36.56]
                        ]
                    ]
                }
            }
        )

    def test_empty_point(self):

        self.assertEsriJsonBecomesGeoJson(
            'esriGeometryPoint',
            {
                "geometry": {
                    "x": None,
                },
            },

            {
                "type": "Feature",
                "geometry": {
                    "type": "Point",
                    "coordinates": [],
                }
            }
        )


class TestGeoJsonLinestringConversion(TestEsriJsonToGeoJson):
    def test_linestring(self):
        self.assertEsriJsonBecomesGeoJson(
            'esriGeometryPolyline',
            {
                "geometry": {
                    "paths" : [
                        [[-97.06138,32.837], [-97.06133,32.836], [-97.06124,32.834], [-97.06127,32.832]]
                    ],
                }
            },

            {
                "type": "Feature",
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
            'esriGeometryPolyline',
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
                "geometry": {
                    "type": "MultiLineString",
                    "coordinates": [
                        [ [-97.06138,32.837], [-97.06133,32.836], [-97.06124,32.834], [-97.06127,32.832] ],
                        [ [-97.06326,32.759], [-97.06298,32.755] ]
                    ],
                }
            }
        )


class TestGeoJsonPolygonConversion(TestEsriJsonToGeoJson):
    def test_polygon(self):
        self.assertEsriJsonBecomesGeoJson(
            'esriGeometryPolygon',
            {
                "geometry": {
                    "rings" : [
                        [[-97.06138,32.837], [-97.06133,32.836], [-97.06124,32.834], [-97.06127,32.832], [-97.06138,32.837]]
                    ],
                }
            },

            {
                "type": "Feature",
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
            'esriGeometryPolygon',
            {
                "geometry": {
                    "rings" : [
                        [[-97.06138,32.837], [-97.06133,32.836], [-97.06124,32.834], [-97.06127,32.832]]
                    ],
                }
            },

            {
                "type": "Feature",
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
            'esriGeometryPolygon',
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
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [
                        [-97.06138,32.837], [-97.06133,32.836], [-97.06124,32.834], [-97.06127,32.832], [-97.06138,32.837]
                    ],
                }
            }
        )

    def test_multi_polygon(self):
        self.assertEsriJsonBecomesGeoJson(
            'esriGeometryPolygon',
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
            'esriGeometryPolygon',
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
            'esriGeometryPolygon',
            {
                "geometry": {
                    "rings" : [ ]
                },
            },

            {
                "type": "Feature",
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [],
                }
            }
        )
